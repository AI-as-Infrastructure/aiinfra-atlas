"""
Unit tests for BuildProgressManager class.

Tests cover:
- Build lifecycle (start, update, complete, fail)
- Concurrent access with async lock
- State transitions
- Progress data management
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

from backend.modules.build_progress import (
    BuildProgressManager,
    BuildState,
    BuildProgressTracker,
    build_progress_manager,
)


class TestBuildState:
    """Tests for BuildState dataclass."""

    def test_build_state_creation(self):
        """BuildState should initialize with default values."""
        state = BuildState(build_id="test_build_123")
        assert state.build_id == "test_build_123"
        assert state.status == "initializing"
        assert state.config == {}
        assert state.completed_at is None
        assert state.failed_at is None
        assert state.error is None
        assert state.results is None
        assert state.progress == {}

    def test_build_state_to_dict(self):
        """BuildState should convert to dictionary correctly."""
        state = BuildState(
            build_id="test_123",
            status="building",
            config={"mode": "cpu"},
            progress={"percentage": 50, "current_document": "doc.txt"}
        )
        result = state.to_dict()

        assert result["build_id"] == "test_123"
        assert result["status"] == "building"
        assert result["config"] == {"mode": "cpu"}
        assert result["percentage"] == 50
        assert result["current_document"] == "doc.txt"
        assert "started_at" in result


class TestBuildProgressManager:
    """Tests for BuildProgressManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh BuildProgressManager for each test."""
        return BuildProgressManager()

    @pytest.mark.asyncio
    async def test_start_build(self, manager):
        """start_build should create and track a new build."""
        config = {"mode": "cpu", "doc_count": 100}
        state = await manager.start_build("build_001", config)

        assert state.build_id == "build_001"
        assert state.status == "initializing"
        assert state.config == config
        assert manager.current_build == "build_001"
        assert manager.has_build("build_001")

    @pytest.mark.asyncio
    async def test_start_multiple_builds(self, manager):
        """Manager should track multiple builds."""
        await manager.start_build("build_001", {"mode": "cpu"})
        await manager.start_build("build_002", {"mode": "gpu"})

        assert manager.has_build("build_001")
        assert manager.has_build("build_002")
        # Current build should be the last one started
        assert manager.current_build == "build_002"

    @pytest.mark.asyncio
    async def test_update_progress(self, manager):
        """update_progress should update build state."""
        await manager.start_build("build_001", {})

        success = await manager.update_progress("build_001", {
            "percentage": 25,
            "processed_documents": 25,
            "current_document": "file_25.txt"
        })

        assert success is True
        progress = await manager.get_progress("build_001")
        assert progress["percentage"] == 25
        assert progress["processed_documents"] == 25
        assert progress["current_document"] == "file_25.txt"

    @pytest.mark.asyncio
    async def test_update_progress_unknown_build(self, manager):
        """update_progress should return False for unknown builds."""
        success = await manager.update_progress("unknown_build", {"percentage": 50})
        assert success is False

    @pytest.mark.asyncio
    async def test_update_progress_with_status(self, manager):
        """update_progress should update status when provided."""
        await manager.start_build("build_001", {})

        await manager.update_progress("build_001", {"status": "building"})
        progress = await manager.get_progress("build_001")
        assert progress["status"] == "building"

    @pytest.mark.asyncio
    async def test_get_progress(self, manager):
        """get_progress should return build progress as dict."""
        await manager.start_build("build_001", {"mode": "cpu"})
        progress = await manager.get_progress("build_001")

        assert progress is not None
        assert progress["build_id"] == "build_001"
        assert progress["status"] == "initializing"
        assert progress["config"] == {"mode": "cpu"}

    @pytest.mark.asyncio
    async def test_get_progress_unknown_build(self, manager):
        """get_progress should return None for unknown builds."""
        progress = await manager.get_progress("unknown_build")
        assert progress is None

    def test_get_progress_sync(self, manager):
        """get_progress_sync should work without async context."""
        # First need to add a build (using event loop)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(manager.start_build("build_001", {}))
        loop.close()

        # Now test sync access
        progress = manager.get_progress_sync("build_001")
        assert progress is not None
        assert progress["build_id"] == "build_001"

    def test_get_progress_sync_unknown(self, manager):
        """get_progress_sync should return None for unknown builds."""
        progress = manager.get_progress_sync("unknown_build")
        assert progress is None

    @pytest.mark.asyncio
    async def test_mark_complete(self, manager):
        """mark_complete should update build to completed state."""
        await manager.start_build("build_001", {})

        results = {
            "total_documents": 100,
            "total_chunks": 500,
            "vector_store_path": "/path/to/store"
        }
        success = await manager.mark_complete("build_001", results)

        assert success is True
        progress = await manager.get_progress("build_001")
        assert progress["status"] == "completed"
        assert progress["results"] == results
        assert progress["completed_at"] is not None
        # Current build should be cleared
        assert manager.current_build is None

    @pytest.mark.asyncio
    async def test_mark_complete_unknown_build(self, manager):
        """mark_complete should return False for unknown builds."""
        success = await manager.mark_complete("unknown_build", {})
        assert success is False

    @pytest.mark.asyncio
    async def test_mark_failed(self, manager):
        """mark_failed should update build to failed state."""
        await manager.start_build("build_001", {})

        success = await manager.mark_failed("build_001", "Out of memory")

        assert success is True
        progress = await manager.get_progress("build_001")
        assert progress["status"] == "failed"
        assert progress["error"] == "Out of memory"
        assert progress["failed_at"] is not None
        # Current build should be cleared
        assert manager.current_build is None

    @pytest.mark.asyncio
    async def test_mark_failed_unknown_build(self, manager):
        """mark_failed should return False for unknown builds."""
        success = await manager.mark_failed("unknown_build", "error")
        assert success is False

    def test_has_build(self, manager):
        """has_build should correctly check build existence."""
        assert manager.has_build("build_001") is False

        # Add build
        loop = asyncio.new_event_loop()
        loop.run_until_complete(manager.start_build("build_001", {}))
        loop.close()

        assert manager.has_build("build_001") is True
        assert manager.has_build("build_002") is False

    @pytest.mark.asyncio
    async def test_get_all_builds(self, manager):
        """get_all_builds should return all tracked builds."""
        await manager.start_build("build_001", {"mode": "cpu"})
        await manager.start_build("build_002", {"mode": "gpu"})

        all_builds = manager.get_all_builds()

        assert len(all_builds) == 2
        assert "build_001" in all_builds
        assert "build_002" in all_builds
        assert all_builds["build_001"]["config"]["mode"] == "cpu"
        assert all_builds["build_002"]["config"]["mode"] == "gpu"

    @pytest.mark.asyncio
    async def test_enabled_property(self, manager):
        """enabled property should track wizard mode state."""
        assert manager.enabled is False

        manager.enabled = True
        assert manager.enabled is True

        manager.enabled = False
        assert manager.enabled is False

    @pytest.mark.asyncio
    async def test_current_build_property(self, manager):
        """current_build should track the active build."""
        assert manager.current_build is None

        await manager.start_build("build_001", {})
        assert manager.current_build == "build_001"

        await manager.start_build("build_002", {})
        assert manager.current_build == "build_002"

        await manager.mark_complete("build_002", {})
        assert manager.current_build is None

    @pytest.mark.asyncio
    async def test_clear_completed(self, manager):
        """clear_completed should remove old completed builds."""
        # Create and complete builds
        await manager.start_build("build_001", {})
        await manager.mark_complete("build_001", {})

        await manager.start_build("build_002", {})
        await manager.mark_failed("build_002", "error")

        await manager.start_build("build_003", {})  # Still in progress

        # All should exist initially
        assert manager.has_build("build_001")
        assert manager.has_build("build_002")
        assert manager.has_build("build_003")

        # Mock the completed_at to be old
        manager._builds["build_001"].completed_at = (
            datetime.now() - timedelta(hours=25)
        ).isoformat()

        # Clear builds older than 24 hours
        manager.clear_completed(max_age_hours=24)

        # build_001 should be removed (completed > 24h ago)
        assert not manager.has_build("build_001")
        # build_002 should still exist (failed recently)
        assert manager.has_build("build_002")
        # build_003 should still exist (in progress)
        assert manager.has_build("build_003")


class TestBuildProgressManagerConcurrency:
    """Tests for concurrent access to BuildProgressManager."""

    @pytest.mark.asyncio
    async def test_concurrent_updates(self):
        """Multiple concurrent updates should be handled safely."""
        manager = BuildProgressManager()
        await manager.start_build("build_001", {})

        async def update_progress(i):
            await manager.update_progress("build_001", {
                f"update_{i}": True,
                "last_update": i
            })

        # Run 10 concurrent updates
        await asyncio.gather(*[update_progress(i) for i in range(10)])

        progress = await manager.get_progress("build_001")
        # All updates should be present
        for i in range(10):
            assert progress.get(f"update_{i}") is True

    @pytest.mark.asyncio
    async def test_concurrent_start_and_complete(self):
        """Concurrent start and complete operations should be safe."""
        manager = BuildProgressManager()

        async def start_and_complete(build_id):
            await manager.start_build(build_id, {"id": build_id})
            await asyncio.sleep(0.01)  # Small delay
            await manager.mark_complete(build_id, {"id": build_id})

        # Start 5 builds concurrently
        await asyncio.gather(*[
            start_and_complete(f"build_{i}") for i in range(5)
        ])

        # All should be completed
        all_builds = manager.get_all_builds()
        assert len(all_builds) == 5
        for i in range(5):
            assert all_builds[f"build_{i}"]["status"] == "completed"


class TestBuildProgressTracker:
    """Tests for BuildProgressTracker class."""

    def test_tracker_initialization(self):
        """Tracker should initialize with default values."""
        tracker = BuildProgressTracker(total_docs=100)
        assert tracker.total_docs == 100
        assert tracker.processed_docs == 0
        assert tracker.current_doc == ""
        assert tracker.errors == []
        assert tracker.warnings == []

    def test_get_progress(self):
        """get_progress should return progress metrics."""
        tracker = BuildProgressTracker(total_docs=100)
        tracker.processed_docs = 25

        progress = tracker.get_progress()

        assert progress["status"] == "building"
        assert progress["percentage"] == 25.0
        assert progress["processed_documents"] == 25
        assert progress["total_documents"] == 100
        assert "elapsed_seconds" in progress
        assert "memory" in progress

    def test_increment_processed(self):
        """increment_processed should update document count."""
        tracker = BuildProgressTracker(total_docs=100)

        tracker.increment_processed()
        assert tracker.processed_docs == 1

        tracker.increment_processed(5)
        assert tracker.processed_docs == 6

    def test_add_error(self):
        """add_error should track errors."""
        tracker = BuildProgressTracker(total_docs=100)

        tracker.add_error("File not found")
        tracker.add_error("Permission denied")

        assert len(tracker.errors) == 2
        assert tracker.errors[0]["message"] == "File not found"
        assert "timestamp" in tracker.errors[0]

    def test_add_warning(self):
        """add_warning should track warnings."""
        tracker = BuildProgressTracker(total_docs=100)

        tracker.add_warning("Large file detected")

        assert len(tracker.warnings) == 1
        assert tracker.warnings[0]["message"] == "Large file detected"

    def test_pause_resume(self):
        """pause and resume should update status."""
        tracker = BuildProgressTracker(total_docs=100)

        tracker.pause()
        assert tracker.paused is True
        progress = tracker.get_progress()
        assert progress["status"] == "paused"

        tracker.resume()
        assert tracker.paused is False
        progress = tracker.get_progress()
        assert progress["status"] == "building"


class TestGlobalInstance:
    """Tests for the global build_progress_manager instance."""

    def test_global_instance_exists(self):
        """Global instance should be available."""
        assert build_progress_manager is not None
        assert isinstance(build_progress_manager, BuildProgressManager)

    @pytest.mark.asyncio
    async def test_global_instance_usable(self):
        """Global instance should be functional."""
        # Use a unique build ID to avoid conflicts
        build_id = f"test_global_{datetime.now().timestamp()}"

        state = await build_progress_manager.start_build(build_id, {"test": True})
        assert state.build_id == build_id

        # Clean up
        await build_progress_manager.mark_complete(build_id, {})

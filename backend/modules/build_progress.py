"""
Build progress tracking for corpus creation.

This module provides progress tracking functionality for the corpus building process,
including async callbacks, checkpoint/resume capability, and system statistics.
"""

import asyncio
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

import psutil
import torch

logger = logging.getLogger(__name__)


@dataclass
class BuildState:
    """State for a single corpus build."""
    build_id: str
    status: str = "initializing"
    config: Dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    error: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    progress: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "build_id": self.build_id,
            "status": self.status,
            "config": self.config,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "failed_at": self.failed_at,
            "error": self.error,
            "results": self.results,
            **self.progress
        }


class BuildProgressManager:
    """
    Manages build progress state for all corpus builds.

    This class encapsulates the global wizard state, providing thread-safe
    access to build progress information.
    """

    def __init__(self):
        self._builds: Dict[str, BuildState] = {}
        self._lock = asyncio.Lock()
        self._enabled = False
        self._current_build: Optional[str] = None

    @property
    def enabled(self) -> bool:
        """Check if wizard mode is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        """Set wizard mode enabled state."""
        self._enabled = value

    @property
    def current_build(self) -> Optional[str]:
        """Get the current active build ID."""
        return self._current_build

    async def start_build(
        self,
        build_id: str,
        config: Dict[str, Any]
    ) -> BuildState:
        """
        Start tracking a new build.

        Args:
            build_id: Unique identifier for the build
            config: Build configuration

        Returns:
            The new BuildState instance
        """
        async with self._lock:
            state = BuildState(
                build_id=build_id,
                status="initializing",
                config=config
            )
            self._builds[build_id] = state
            self._current_build = build_id
            logger.info(f"Started tracking build: {build_id}")
            return state

    async def update_progress(
        self,
        build_id: str,
        progress_data: Dict[str, Any]
    ) -> bool:
        """
        Update progress for a build.

        Args:
            build_id: The build to update
            progress_data: Progress data to merge

        Returns:
            True if update succeeded, False if build not found
        """
        async with self._lock:
            if build_id not in self._builds:
                logger.warning(f"Attempted to update unknown build: {build_id}")
                return False

            self._builds[build_id].progress.update(progress_data)

            # Update status if provided
            if "status" in progress_data:
                self._builds[build_id].status = progress_data["status"]

            return True

    async def get_progress(self, build_id: str) -> Optional[Dict[str, Any]]:
        """
        Get progress for a specific build.

        Args:
            build_id: The build to query

        Returns:
            Progress dict or None if not found
        """
        async with self._lock:
            if build_id not in self._builds:
                return None
            return self._builds[build_id].to_dict()

    def get_progress_sync(self, build_id: str) -> Optional[Dict[str, Any]]:
        """
        Synchronous version of get_progress for non-async contexts.

        Args:
            build_id: The build to query

        Returns:
            Progress dict or None if not found
        """
        if build_id not in self._builds:
            return None
        return self._builds[build_id].to_dict()

    async def mark_complete(
        self,
        build_id: str,
        results: Dict[str, Any]
    ) -> bool:
        """
        Mark a build as completed successfully.

        Args:
            build_id: The build to mark complete
            results: Build results

        Returns:
            True if successful, False if build not found
        """
        async with self._lock:
            if build_id not in self._builds:
                return False

            state = self._builds[build_id]
            state.status = "completed"
            state.completed_at = datetime.now().isoformat()
            state.results = results

            if self._current_build == build_id:
                self._current_build = None

            logger.info(f"Build completed: {build_id}")
            return True

    async def mark_failed(
        self,
        build_id: str,
        error: str
    ) -> bool:
        """
        Mark a build as failed.

        Args:
            build_id: The build to mark failed
            error: Error message

        Returns:
            True if successful, False if build not found
        """
        async with self._lock:
            if build_id not in self._builds:
                return False

            state = self._builds[build_id]
            state.status = "failed"
            state.failed_at = datetime.now().isoformat()
            state.error = error

            if self._current_build == build_id:
                self._current_build = None

            logger.error(f"Build failed: {build_id} - {error}")
            return True

    def has_build(self, build_id: str) -> bool:
        """Check if a build exists."""
        return build_id in self._builds

    def get_all_builds(self) -> Dict[str, Dict[str, Any]]:
        """Get all build states as dictionaries."""
        return {
            bid: state.to_dict()
            for bid, state in self._builds.items()
        }

    def clear_completed(self, max_age_hours: int = 24):
        """
        Remove completed builds older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours for completed builds
        """
        now = datetime.now()
        to_remove = []

        for build_id, state in self._builds.items():
            if state.status in ("completed", "failed") and state.completed_at:
                completed = datetime.fromisoformat(state.completed_at)
                age_hours = (now - completed).total_seconds() / 3600
                if age_hours > max_age_hours:
                    to_remove.append(build_id)

        for build_id in to_remove:
            del self._builds[build_id]
            logger.info(f"Cleaned up old build: {build_id}")


# Global instance for use across the application
build_progress_manager = BuildProgressManager()


class BuildProgressTracker:
    """Tracks and reports build progress with checkpoint/resume capability."""

    def __init__(self, total_docs: int = 0, callback: Optional[Callable] = None,
                 checkpoint_dir: Optional[Path] = None):
        """
        Initialize progress tracker.

        Args:
            total_docs: Total number of documents to process
            callback: Async callback function for progress updates
            checkpoint_dir: Directory for checkpoint files (default: backend/corpus/tmp)
        """
        self.total_docs = total_docs
        self.processed_docs = 0
        self.current_doc = ""
        self.current_chunk = 0
        self.start_time = time.time()
        self.callback = callback
        self.errors = []
        self.warnings = []
        self.filter_progress = {}
        self.paused = False

        # Allow configurable checkpoint location
        if checkpoint_dir is None:
            checkpoint_dir = Path("backend/corpus/tmp")
        self.checkpoint_file = checkpoint_dir / ".build_checkpoint.json"

    async def update(self, doc_path: str, chunk_num: int = 0, filter_id: str = None):
        """
        Update progress and notify callback.

        Args:
            doc_path: Path of current document being processed
            chunk_num: Current chunk number
            filter_id: Optional filter ID for filter-specific progress
        """
        self.current_doc = doc_path
        self.current_chunk = chunk_num

        if filter_id:
            if filter_id not in self.filter_progress:
                self.filter_progress[filter_id] = {"processed": 0, "total": 0}
            self.filter_progress[filter_id]["processed"] += 1

        progress_data = self.get_progress()

        if self.callback:
            await self.callback(progress_data)

        # Save checkpoint periodically (every 10 docs)
        if self.processed_docs % 10 == 0:
            self.save_checkpoint()

    def get_progress(self) -> Dict[str, Any]:
        """
        Get current progress data including statistics.

        Returns:
            Dictionary with progress metrics and system statistics
        """
        elapsed = time.time() - self.start_time
        docs_per_second = self.processed_docs / elapsed if elapsed > 0 else 0

        if docs_per_second > 0:
            remaining_docs = self.total_docs - self.processed_docs
            estimated_remaining = remaining_docs / docs_per_second
        else:
            estimated_remaining = 0

        return {
            "status": "paused" if self.paused else "building",
            "percentage": (self.processed_docs / self.total_docs * 100) if self.total_docs > 0 else 0,
            "processed_documents": self.processed_docs,
            "total_documents": self.total_docs,
            "current_document": self.current_doc,
            "current_chunk": self.current_chunk,
            "elapsed_seconds": elapsed,
            "estimated_remaining_seconds": estimated_remaining,
            "docs_per_second": docs_per_second,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "filter_progress": self.filter_progress,
            "memory": self._get_memory_stats(),
            "performance": self._get_performance_stats()
        }

    def _get_memory_stats(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        memory = psutil.virtual_memory()
        gpu_memory = {}

        if torch.cuda.is_available():
            gpu_memory = {
                "gpu_allocated_gb": torch.cuda.memory_allocated() / 1e9,
                "gpu_reserved_gb": torch.cuda.memory_reserved() / 1e9,
                "gpu_percent": (torch.cuda.memory_allocated() / torch.cuda.get_device_properties(0).total_memory) * 100
            }

        return {
            "ram_used_gb": memory.used / 1e9,
            "ram_percent": memory.percent,
            "ram_available_gb": memory.available / 1e9,
            **gpu_memory
        }

    def _get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        disk_io = psutil.disk_io_counters()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "disk_io_read_mb": disk_io.read_bytes / 1e6 if disk_io else 0,
            "disk_io_write_mb": disk_io.write_bytes / 1e6 if disk_io else 0
        }

    def save_checkpoint(self):
        """Save progress checkpoint for recovery."""
        checkpoint = {
            "processed_docs": self.processed_docs,
            "total_docs": self.total_docs,
            "filter_progress": self.filter_progress,
            "timestamp": datetime.now().isoformat()
        }

        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f)

    def load_checkpoint(self) -> bool:
        """
        Load checkpoint if available.

        Returns:
            True if checkpoint was loaded successfully
        """
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                self.processed_docs = checkpoint["processed_docs"]
                self.filter_progress = checkpoint["filter_progress"]
                logger.info(f"Loaded checkpoint: {self.processed_docs}/{self.total_docs} documents processed")
                return True
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
        return False

    def pause(self):
        """Pause progress tracking and save checkpoint."""
        self.paused = True
        self.save_checkpoint()

    def resume(self):
        """Resume progress tracking."""
        self.paused = False

    def add_error(self, error: str):
        """Add an error to the tracking list."""
        self.errors.append({
            "message": error,
            "timestamp": datetime.now().isoformat()
        })

    def add_warning(self, warning: str):
        """Add a warning to the tracking list."""
        self.warnings.append({
            "message": warning,
            "timestamp": datetime.now().isoformat()
        })

    def increment_processed(self, count: int = 1):
        """Increment the processed documents counter."""
        self.processed_docs += count

    def cleanup_checkpoint(self):
        """Remove checkpoint file after successful completion."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            logger.info("Checkpoint file removed after successful completion")
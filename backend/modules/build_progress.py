"""
Build progress tracking for corpus creation.

This module provides progress tracking functionality for the corpus building process,
including async callbacks, checkpoint/resume capability, and system statistics.
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

import psutil
import torch

logger = logging.getLogger(__name__)


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
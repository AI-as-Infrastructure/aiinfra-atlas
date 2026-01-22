"""
System requirements checker for corpus building.

This module validates system capabilities before corpus building,
checking CPU, GPU, memory, and disk requirements.
"""

import logging
from typing import Dict, Any, List

import psutil
import torch

logger = logging.getLogger(__name__)


class SystemRequirementsChecker:
    """Check system capabilities for corpus building."""

    @staticmethod
    def check_requirements(doc_count: int, mode: str = "cpu") -> Dict[str, Any]:
        """
        Check if system meets requirements for building corpus.

        Args:
            doc_count: Number of documents to process
            mode: Processing mode ('cpu' or 'gpu')

        Returns:
            Dictionary with system capabilities and issues
        """
        requirements = {
            "cpu": SystemRequirementsChecker._check_cpu(),
            "gpu": SystemRequirementsChecker._check_gpu(),
            "memory": SystemRequirementsChecker._check_memory(doc_count),
            "disk": SystemRequirementsChecker._check_disk(doc_count)
        }

        # Check for critical issues
        issues = []

        # GPU issues only matter if GPU mode requested
        if mode == "gpu" and not requirements["gpu"]["available"]:
            issues.append("GPU requested but not available - will fall back to CPU")

        if not requirements["memory"]["sufficient"]:
            issues.append(
                f"Insufficient memory: {requirements['memory']['available_gb']:.1f}GB available, "
                f"{requirements['memory']['required_gb']:.1f}GB required"
            )

        if not requirements["disk"]["sufficient"]:
            issues.append(
                f"Insufficient disk space: {requirements['disk']['free_gb']:.1f}GB available, "
                f"{requirements['disk']['required_gb']:.1f}GB required"
            )

        requirements["issues"] = issues
        requirements["can_proceed"] = len([i for i in issues if "Insufficient" in i]) == 0
        requirements["mode"] = "gpu" if mode == "gpu" and requirements["gpu"]["available"] else "cpu"
        requirements["estimated_time"] = SystemRequirementsChecker._estimate_build_time(
            doc_count, requirements["mode"]
        )

        return requirements

    @staticmethod
    def _check_cpu() -> Dict[str, Any]:
        """Check CPU capabilities."""
        return {
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
            "available": True,
            "current_load_percent": psutil.cpu_percent(interval=1)
        }

    @staticmethod
    def _check_gpu() -> Dict[str, Any]:
        """Check GPU capabilities."""
        gpu_info = {
            "available": torch.cuda.is_available(),
            "count": 0,
            "name": None,
            "memory_gb": 0,
            "cuda_version": None
        }

        if torch.cuda.is_available():
            gpu_info.update({
                "count": torch.cuda.device_count(),
                "name": torch.cuda.get_device_name(0),
                "memory_gb": torch.cuda.get_device_properties(0).total_memory / 1e9,
                "cuda_version": torch.version.cuda
            })

        return gpu_info

    @staticmethod
    def _check_memory(doc_count: int) -> Dict[str, Any]:
        """
        Check memory requirements.

        Args:
            doc_count: Number of documents to process

        Returns:
            Memory information and requirements
        """
        memory = psutil.virtual_memory()

        # Estimate memory requirements based on document count
        # Base requirement: 4GB minimum
        # Per-document: ~1MB for embeddings and processing
        base_requirement_gb = 4.0
        per_doc_requirement_gb = 0.001
        required_gb = max(base_requirement_gb, doc_count * per_doc_requirement_gb)

        return {
            "total_gb": memory.total / 1e9,
            "available_gb": memory.available / 1e9,
            "used_gb": memory.used / 1e9,
            "percent_used": memory.percent,
            "required_gb": required_gb,
            "sufficient": memory.available / 1e9 > required_gb
        }

    @staticmethod
    def _check_disk(doc_count: int) -> Dict[str, Any]:
        """
        Check disk space requirements.

        Args:
            doc_count: Number of documents to process

        Returns:
            Disk information and requirements
        """
        disk = psutil.disk_usage('/')

        # Estimate disk requirements
        # Vector store: ~5MB per 1000 documents
        # BM25 corpus: ~2MB per 1000 documents
        # Temporary files: ~3MB per 1000 documents
        per_1k_docs_mb = 10
        required_gb = (doc_count / 1000) * per_1k_docs_mb / 1000

        # Add buffer for safety
        required_gb = max(1.0, required_gb * 1.5)

        return {
            "total_gb": disk.total / 1e9,
            "free_gb": disk.free / 1e9,
            "used_gb": disk.used / 1e9,
            "percent_used": disk.percent,
            "required_gb": required_gb,
            "sufficient": disk.free / 1e9 > required_gb
        }

    @staticmethod
    def _estimate_build_time(doc_count: int, mode: str) -> Dict[str, Any]:
        """
        Estimate build time based on document count and mode.

        Args:
            doc_count: Number of documents
            mode: Processing mode ('cpu' or 'gpu')

        Returns:
            Time estimates in different units
        """
        # Rough estimates based on typical performance
        # GPU: ~100 docs/minute
        # CPU: ~20 docs/minute
        docs_per_minute = 100 if mode == "gpu" else 20
        minutes = doc_count / docs_per_minute

        return {
            "minutes": round(minutes, 1),
            "hours": round(minutes / 60, 2),
            "formatted": SystemRequirementsChecker._format_time(minutes * 60)
        }

    @staticmethod
    def _format_time(seconds: float) -> str:
        """
        Format seconds into human-readable time string.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string (e.g., "1h 30m")
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s" if secs else f"{minutes}m"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m" if minutes else f"{hours}h"

    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """
        Get comprehensive system information.

        Returns:
            Dictionary with detailed system information
        """
        import platform

        return {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version()
            },
            "cpu": SystemRequirementsChecker._check_cpu(),
            "gpu": SystemRequirementsChecker._check_gpu(),
            "memory": {
                "total_gb": psutil.virtual_memory().total / 1e9,
                "available_gb": psutil.virtual_memory().available / 1e9,
                "percent_used": psutil.virtual_memory().percent
            },
            "disk": {
                "total_gb": psutil.disk_usage('/').total / 1e9,
                "free_gb": psutil.disk_usage('/').free / 1e9,
                "percent_used": psutil.disk_usage('/').percent
            },
            "pytorch": {
                "version": torch.__version__,
                "cuda_available": torch.cuda.is_available(),
                "cuda_version": torch.version.cuda if torch.cuda.is_available() else None
            }
        }

    @staticmethod
    def validate_output_directory(path: str) -> Dict[str, Any]:
        """
        Validate output directory has sufficient space and permissions.

        Args:
            path: Path to output directory

        Returns:
            Validation results
        """
        import os
        from pathlib import Path

        output_path = Path(path)
        issues = []

        # Check if path exists or can be created
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            issues.append(f"No permission to create directory: {path}")
        except Exception as e:
            issues.append(f"Cannot create directory: {e}")

        # Check write permissions
        if output_path.exists():
            test_file = output_path / ".write_test"
            try:
                test_file.touch()
                test_file.unlink()
            except PermissionError:
                issues.append(f"No write permission in directory: {path}")
            except Exception as e:
                issues.append(f"Cannot write to directory: {e}")

        # Check available space
        if output_path.exists():
            disk = psutil.disk_usage(str(output_path))
            if disk.free < 1e9:  # Less than 1GB
                issues.append(f"Low disk space: {disk.free / 1e9:.1f}GB available")

        return {
            "path": str(output_path),
            "exists": output_path.exists(),
            "writable": len([i for i in issues if "permission" in i.lower()]) == 0,
            "space_available_gb": psutil.disk_usage(str(output_path)).free / 1e9 if output_path.exists() else 0,
            "issues": issues,
            "valid": len(issues) == 0
        }
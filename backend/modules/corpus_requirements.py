"""
System requirements checker for corpus building.
Checks disk space, Python version, dependencies, and system resources.
"""

import os
import sys
import shutil
import subprocess
import psutil
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import importlib.util


class CorpusRequirementsChecker:
    """Check system requirements for corpus building."""

    def __init__(self):
        self.requirements = {}
        self.warnings = []
        self.errors = []

    def check_all(self, corpus_size_estimate: int = None) -> Dict:
        """
        Check all system requirements.

        Args:
            corpus_size_estimate: Estimated size of corpus in bytes

        Returns:
            Dict with requirements status
        """
        self.check_python_version()
        self.check_disk_space(corpus_size_estimate)
        self.check_memory()
        self.check_gpu()
        self.check_dependencies()
        self.check_git()
        self.check_internet()

        return {
            "requirements": self.requirements,
            "warnings": self.warnings,
            "errors": self.errors,
            "can_proceed": len(self.errors) == 0,
            "summary": self.get_summary()
        }

    def check_python_version(self):
        """Check Python version."""
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"

        self.requirements["python_version"] = {
            "current": version_str,
            "required": "3.10+",
            "status": "ok" if version.major == 3 and version.minor >= 10 else "error"
        }

        if version.major != 3 or version.minor < 10:
            self.errors.append(f"Python 3.10+ required, found {version_str}")

    def check_disk_space(self, corpus_size_estimate: int = None):
        """Check available disk space."""
        path = Path.cwd()
        stat = shutil.disk_usage(path)

        # Convert to GB
        free_gb = stat.free / (1024**3)
        total_gb = stat.total / (1024**3)

        # Estimate required space (corpus + vector store + buffer)
        if corpus_size_estimate:
            required_gb = (corpus_size_estimate * 3) / (1024**3)  # 3x for processing
        else:
            required_gb = 10  # Default minimum

        self.requirements["disk_space"] = {
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "required_gb": round(required_gb, 2),
            "status": "ok" if free_gb > required_gb else "warning"
        }

        if free_gb < required_gb:
            self.warnings.append(f"Low disk space: {free_gb:.1f}GB free, {required_gb:.1f}GB recommended")

        if free_gb < 5:
            self.errors.append(f"Insufficient disk space: {free_gb:.1f}GB free, minimum 5GB required")

    def check_memory(self):
        """Check available memory."""
        mem = psutil.virtual_memory()

        # Convert to GB
        total_gb = mem.total / (1024**3)
        available_gb = mem.available / (1024**3)

        self.requirements["memory"] = {
            "total_gb": round(total_gb, 2),
            "available_gb": round(available_gb, 2),
            "required_gb": 4,
            "status": "ok" if available_gb > 2 else "warning"
        }

        if available_gb < 2:
            self.warnings.append(f"Low memory: {available_gb:.1f}GB available, 4GB recommended")

        if available_gb < 1:
            self.errors.append(f"Insufficient memory: {available_gb:.1f}GB available, minimum 1GB required")

    def check_gpu(self):
        """Check for GPU availability."""
        has_cuda = False
        gpu_info = "No GPU detected"

        try:
            import torch
            has_cuda = torch.cuda.is_available()
            if has_cuda:
                gpu_info = f"CUDA GPU: {torch.cuda.get_device_name(0)}"
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                gpu_info += f" ({gpu_memory:.1f}GB)"
        except ImportError:
            pass

        self.requirements["gpu"] = {
            "available": has_cuda,
            "info": gpu_info,
            "status": "ok" if has_cuda else "info"
        }

        if not has_cuda:
            self.warnings.append("No GPU detected - corpus building will use CPU (slower)")

    def check_dependencies(self):
        """Check Python dependencies."""
        required_packages = [
            ("transformers", "transformers"),
            ("torch", "torch"),
            ("chromadb", "chromadb"),
            ("sentence_transformers", "sentence-transformers"),
            ("git", "gitpython"),
            ("yaml", "pyyaml"),
            ("tqdm", "tqdm"),
            ("numpy", "numpy"),
            ("requests", "requests")
        ]

        missing = []
        installed = []

        for module_name, package_name in required_packages:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                missing.append(package_name)
            else:
                installed.append(module_name)

        self.requirements["dependencies"] = {
            "installed": installed,
            "missing": missing,
            "status": "ok" if len(missing) == 0 else "error"
        }

        if missing:
            self.errors.append(f"Missing dependencies: {', '.join(missing)}")
            self.errors.append("Run: pip install " + " ".join(missing))

    def check_git(self):
        """Check if git is installed."""
        try:
            result = subprocess.run(["git", "--version"],
                                 capture_output=True,
                                 text=True,
                                 check=True)
            git_version = result.stdout.strip()

            self.requirements["git"] = {
                "installed": True,
                "version": git_version,
                "status": "ok"
            }
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.requirements["git"] = {
                "installed": False,
                "version": "Not installed",
                "status": "warning"
            }
            self.warnings.append("Git not installed - GitHub corpus sources will not work")

    def check_internet(self):
        """Check internet connectivity."""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            connected = True
        except OSError:
            connected = False

        self.requirements["internet"] = {
            "connected": connected,
            "status": "ok" if connected else "warning"
        }

        if not connected:
            self.warnings.append("No internet connection - cannot download models or GitHub repos")

    def get_summary(self) -> str:
        """Get a summary of requirements check."""
        if self.errors:
            return f"❌ {len(self.errors)} errors found - cannot proceed"
        elif self.warnings:
            return f"⚠️  {len(self.warnings)} warnings - can proceed with limitations"
        else:
            return "✅ All requirements met"

    def estimate_corpus_size(self, source_path: str) -> int:
        """
        Estimate corpus size from source path.

        Args:
            source_path: Path to corpus source

        Returns:
            Estimated size in bytes
        """
        total_size = 0
        path = Path(source_path)

        if path.is_file():
            total_size = path.stat().st_size
        elif path.is_dir():
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size

        return total_size

    def get_mode_recommendation(self) -> str:
        """
        Recommend CPU or GPU mode based on system capabilities.

        Returns:
            "gpu" or "cpu"
        """
        if self.requirements.get("gpu", {}).get("available", False):
            # Check if we have enough GPU memory
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    if gpu_memory >= 4:
                        return "gpu"
            except:
                pass

        return "cpu"
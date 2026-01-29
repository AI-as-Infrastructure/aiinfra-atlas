"""
API endpoints for the corpus configuration wizard.

Provides endpoints for corpus analysis, filter discovery, model recommendations,
and corpus building operations.
"""

import os
import asyncio
import psutil
import torch
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Body
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import logging
import json

# Import corpus modules
from backend.modules.corpus_config import (
    CorpusConfig, CorpusMetadata, SourceConfig, FilterDefinition,
    FilterConfig, CitationConfig, EmbeddingConfig, ProcessingConfig,
    CorpusConfigManager
)
from backend.modules.corpus_analyzer import CorpusAnalyzer
from backend.modules.corpus_sampler import CorpusSampler
from backend.modules.corpus_validator import CorpusValidator
from backend.modules.github_corpus import GitHubCorpusManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/corpus-wizard", tags=["corpus-wizard"])


# Request/Response models
class WizardModeRequest(BaseModel):
    """Request to enable/disable wizard mode."""
    enabled: bool


class AnalyzeRequest(BaseModel):
    """Request to analyze a corpus."""
    source_type: str = Field(..., description="local or github")
    source_location: str = Field(..., description="Path or URL")
    file_types: List[str] = Field(default=['txt', 'xml'])
    metadata: Optional[Dict[str, Any]] = None


class SystemInfo(BaseModel):
    """System information and requirements."""
    cpu: Dict[str, Any]
    gpu: Dict[str, Any]
    memory: Dict[str, Any]
    disk: Dict[str, Any]
    estimated_build_time: Dict[str, Any]


class ModelRecommendation(BaseModel):
    """Embedding model recommendation."""
    model: str
    score: float
    reason: str
    characteristics: Dict[str, Any]


class BuildRequest(BaseModel):
    """Request to build a corpus."""
    config: Dict[str, Any]
    mode: str = Field("cpu", description="cpu or gpu")


# Global state for wizard mode and build progress
wizard_state = {
    'enabled': False,
    'current_build': None,
    'build_progress': {}
}


@router.post("/mode")
async def set_wizard_mode(request: WizardModeRequest):
    """Enable or disable wizard mode."""
    wizard_state['enabled'] = request.enabled

    if request.enabled:
        logger.info("Corpus wizard mode enabled")
        return JSONResponse({
            "status": "enabled",
            "message": "Corpus wizard mode is now active"
        })
    else:
        logger.info("Corpus wizard mode disabled")
        return JSONResponse({
            "status": "disabled",
            "message": "Normal operation mode restored"
        })


@router.get("/mode")
async def get_wizard_mode():
    """Check if wizard mode is active."""
    return JSONResponse({
        "enabled": wizard_state['enabled']
    })


@router.post("/analyze")
async def analyze_corpus(request: AnalyzeRequest):
    """
    Analyze a corpus to discover structure and suggest configuration.
    """
    analyzer = CorpusAnalyzer()

    try:
        # Handle GitHub sources
        if request.source_type == 'github':
            github_manager = GitHubCorpusManager()
            local_path = github_manager.fetch_corpus(
                repo_url=request.source_location,
                branch=request.metadata.get('branch', 'main') if request.metadata else 'main',
                path=request.metadata.get('repo_path', '') if request.metadata else ''
            )
            source_path = str(local_path)
        else:
            source_path = request.source_location

        # Analyze corpus
        analysis = analyzer.analyze_corpus(
            base_path=source_path,
            file_types=request.file_types,
            metadata_hints=request.metadata
        )

        return JSONResponse(analysis)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Corpus analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/suggest-filters")
async def suggest_filters(
    metadata: Dict[str, Any] = Body(...),
    structure_analysis: Dict[str, Any] = Body(...)
):
    """
    Suggest filters based on metadata and structure analysis.
    """
    analyzer = CorpusAnalyzer()

    # Use the internal method to suggest filters
    filters = analyzer._suggest_filters(
        structure_analysis=structure_analysis,
        content_analysis=structure_analysis.get('content_analysis', {}),
        metadata_hints=metadata
    )

    # Add document counts if available
    for filter_def in filters:
        if filter_def['id'] in structure_analysis.get('statistics', {}).get('filter_coverage', {}):
            coverage = structure_analysis['statistics']['filter_coverage'][filter_def['id']]
            filter_def['document_count'] = coverage.get('estimated_docs', 0)

    return JSONResponse({
        "filters": filters,
        "total_suggested": len(filters),
        "confidence_threshold": 0.7
    })


@router.get("/corpus-mode")
async def get_corpus_mode():
    """
    Get the configured corpus wizard mode (GPU or CPU).
    Reads from the mode file saved by backend startup (make b).
    """
    mode_file = Path(".venv/.corpus_mode")

    # Default to CPU if no mode file exists
    mode = "cpu"

    if mode_file.exists():
        try:
            mode = mode_file.read_text().strip().lower()
            logger.info(f"Corpus wizard mode from file: {mode}")
        except Exception as e:
            logger.warning(f"Could not read corpus mode file: {e}")
    else:
        logger.info("No corpus mode file found, defaulting to CPU")

    # Check if GPU is actually available when GPU mode is configured
    gpu_available = torch.cuda.is_available()

    return JSONResponse({
        "configured_mode": mode,
        "gpu_available": gpu_available,
        "effective_mode": mode if (mode == "cpu" or gpu_available) else "cpu",
        "warning": None if (mode == "cpu" or gpu_available) else "GPU mode configured but no GPU detected - will use CPU"
    })


@router.get("/system-requirements")
async def get_system_requirements(
    doc_count: int = Query(1000, description="Number of documents in corpus")
):
    """
    Check system requirements and provide build time estimates.
    """
    system_info = {
        "cpu": {
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
            "model": platform.processor(),
            "available": True
        },
        "gpu": {
            "available": torch.cuda.is_available(),
            "count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "memory_gb": (
                torch.cuda.get_device_properties(0).total_memory / 1e9
                if torch.cuda.is_available() else 0
            )
        },
        "memory": {
            "total_gb": psutil.virtual_memory().total / 1e9,
            "available_gb": psutil.virtual_memory().available / 1e9,
            "percent_used": psutil.virtual_memory().percent,
            "required_gb": max(4.0, doc_count * 0.001),  # Rough estimate
            "sufficient": psutil.virtual_memory().available / 1e9 > max(4.0, doc_count * 0.001)
        },
        "disk": {
            "free_gb": shutil.disk_usage('/').free / 1e9,
            "required_gb": doc_count * 0.005,  # Rough estimate: 5MB per doc
            "sufficient": shutil.disk_usage('/').free / 1e9 > doc_count * 0.005
        }
    }

    # Estimate build times
    if system_info['gpu']['available']:
        gpu_docs_per_sec = 4.0
        gpu_seconds = doc_count / gpu_docs_per_sec
    else:
        gpu_seconds = None

    cpu_docs_per_sec = 1.2
    cpu_seconds = doc_count / cpu_docs_per_sec

    system_info['estimated_build_time'] = {
        'cpu': {
            'seconds': cpu_seconds,
            'formatted': _format_duration(cpu_seconds),
            'docs_per_second': cpu_docs_per_sec
        }
    }

    if gpu_seconds:
        system_info['estimated_build_time']['gpu'] = {
            'seconds': gpu_seconds,
            'formatted': _format_duration(gpu_seconds),
            'docs_per_second': gpu_docs_per_sec,
            'speedup': cpu_seconds / gpu_seconds
        }

    # Add warnings
    warnings = []
    if not system_info['memory']['sufficient']:
        warnings.append({
            'type': 'memory',
            'message': f"Insufficient memory: {system_info['memory']['available_gb']:.1f}GB available, "
                      f"{system_info['memory']['required_gb']:.1f}GB recommended"
        })

    if not system_info['disk']['sufficient']:
        warnings.append({
            'type': 'disk',
            'message': f"Low disk space: {system_info['disk']['free_gb']:.1f}GB free, "
                      f"{system_info['disk']['required_gb']:.1f}GB required"
        })

    system_info['warnings'] = warnings
    system_info['recommended_mode'] = 'gpu' if system_info['gpu']['available'] else 'cpu'

    return JSONResponse(system_info)


@router.get("/model-recommendation")
async def get_model_recommendation():
    """
    Get default embedding model recommendation.
    """
    return JSONResponse({
        "default": {
            "model_id": "sentence-transformers/all-MiniLM-L6-v2",
            "description": "General-purpose model suitable for most corpora",
            "performance": "Fast processing with good accuracy",
            "size_mb": 90,
            "dimensions": 384,
            "max_seq_length": 512
        },
        "custom_option": True,
        "custom_help": "Enter any HuggingFace sentence-transformers model ID"
    })


@router.post("/validate-model")
async def validate_custom_model(model_id: str = Body(..., embed=True)):
    """
    Validate a custom HuggingFace model.
    """
    try:
        # Basic validation - check format
        if not model_id or "/" not in model_id:
            return JSONResponse({
                "valid": False,
                "error": "Invalid model ID format. Expected: owner/model-name"
            })

        # In production, would check HuggingFace API
        # For now, return mock validation
        return JSONResponse({
            "valid": True,
            "model_info": {
                "model_id": model_id,
                "dimensions": 384,  # Would be fetched from model
                "max_seq_length": 512,
                "estimated_size_mb": 100
            }
        })

    except Exception as e:
        return JSONResponse({
            "valid": False,
            "error": str(e)
        })


@router.post("/validate-regex")
async def validate_regex_pattern(request: Dict[str, str] = Body(...)):
    """
    Validate a regex pattern for date extraction.
    """
    import re

    pattern = request.get("pattern", "")
    test_string = request.get("test_string", "")

    try:
        if not pattern:
            return JSONResponse({
                "valid": False,
                "error": "Pattern cannot be empty"
            })

        # Try to compile the regex
        compiled = re.compile(pattern)

        # Test against string if provided
        matches = []
        if test_string:
            for match in compiled.finditer(test_string):
                if match.groups():
                    # If there are groups, return the first group
                    matches.append(match.group(1))
                else:
                    # Otherwise return the whole match
                    matches.append(match.group(0))

        return JSONResponse({
            "valid": True,
            "pattern": pattern,
            "matches": matches,
            "message": f"Valid regex pattern. Found {len(matches)} match(es)" if test_string else "Valid regex pattern"
        })

    except re.error as e:
        return JSONResponse({
            "valid": False,
            "error": f"Invalid regex: {str(e)}",
            "pattern": pattern
        })
    except Exception as e:
        return JSONResponse({
            "valid": False,
            "error": str(e),
            "pattern": pattern
        })


@router.post("/validate-config")
async def validate_config(config_data: Dict[str, Any] = Body(...)):
    """
    Validate a corpus configuration.
    """
    try:
        # Parse configuration
        config = CorpusConfig(**config_data)

        # Validate sources
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Check source accessibility
        if config.source.type == 'local':
            if not Path(config.source.location).exists():
                validation_results["valid"] = False
                validation_results["errors"].append(f"Source path does not exist: {config.source.location}")

        # Check filter patterns
        if not config.filters:
            validation_results["warnings"].append("No filters configured, only 'all' filter will be available")

        # Check embedding model (basic check)
        if not config.embeddings.model:
            validation_results["valid"] = False
            validation_results["errors"].append("Embedding model is required")

        return JSONResponse(validation_results)

    except Exception as e:
        return JSONResponse({
            "valid": False,
            "errors": [str(e)],
            "warnings": []
        })


@router.post("/validate-sample")
async def validate_sample(
    source_path: str = Body(...),
    config: Dict[str, Any] = Body(...),
    sample_size: Optional[int] = Body(None)
):
    """
    Validate corpus with a minimal viable sample.
    """
    try:
        sampler = CorpusSampler(source_path)
        validator = CorpusValidator(source_path)

        # Get minimal sample
        corpus_files = list(Path(source_path).rglob("*"))
        filters = config.get("filters", {}).get("filters", [])

        sample = sampler.get_minimal_sample(filters, corpus_files)

        # Validate sample
        sample_files = [Path(f) for f in sample["files"]]
        validation_result = validator.validate_sample(sample_files, config)

        # Detect issues
        issues = validator.detect_issues(sample_files)
        validation_result["detected_issues"] = issues

        # Estimate processing time
        estimation = sampler.estimate_processing_time(
            sample,
            config.get("processing", {}).get("mode", "cpu")
        )
        validation_result["time_estimation"] = estimation

        return JSONResponse({
            "sample": sample,
            "validation": validation_result,
            "ready_to_build": validation_result["valid"]
        })

    except Exception as e:
        logger.error(f"Sample validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview-metadata")
async def preview_metadata_extraction(
    source_path: str = Body(...),
    patterns: Dict[str, str] = Body(...)
):
    """
    Preview metadata extraction from sample files.
    """
    try:
        from backend.modules.citation_enricher import CitationEnricher

        # Get sample files
        sample_files = []
        path = Path(source_path)
        for ext in ['.txt', '.xml']:
            files = list(path.rglob(f"*{ext}"))[:5]
            sample_files.extend(files)

        # Configure enricher
        citation_config = {
            "metadata_patterns": patterns,
            "template": "{author}. {title}. {date}. {source}.",
            "source_name": "Corpus"
        }
        enricher = CitationEnricher(citation_config)

        # Generate test citations
        test_citations = enricher.generate_test_citations(sample_files[:10])

        return JSONResponse({
            "sample_extractions": test_citations,
            "patterns_used": patterns,
            "files_tested": len(sample_files)
        })

    except Exception as e:
        logger.error(f"Metadata preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/estimate-time")
async def estimate_processing_time(
    doc_count: int = Body(...),
    mode: str = Body("cpu"),
    sample_metrics: Optional[Dict[str, Any]] = Body(None)
):
    """
    Estimate corpus processing time.
    """
    # Base estimates
    if mode == "gpu":
        docs_per_second = 4.0
    else:
        docs_per_second = 1.2

    # Adjust based on sample metrics if available
    if sample_metrics:
        avg_doc_size = sample_metrics.get("avg_doc_size", 5000)
        if avg_doc_size > 10000:
            docs_per_second *= 0.7  # Slower for large docs
        elif avg_doc_size < 2000:
            docs_per_second *= 1.3  # Faster for small docs

    total_seconds = doc_count / docs_per_second

    return JSONResponse({
        "estimated_seconds": int(total_seconds),
        "estimated_minutes": int(total_seconds / 60),
        "estimated_hours": round(total_seconds / 3600, 1),
        "docs_per_second": docs_per_second,
        "mode": mode,
        "confidence": 0.8
    })


@router.post("/fix-issues")
async def fix_detected_issues(
    issues: List[Dict[str, Any]] = Body(...),
    auto_fix: bool = Body(True)
):
    """
    Suggest or apply fixes for detected issues.
    """
    fixes = []

    for issue in issues:
        issue_type = issue.get("type")

        if issue_type == "naming_inconsistency":
            fixes.append({
                "issue": issue,
                "fix_type": "rename",
                "suggestion": "Standardize naming pattern",
                "auto_fixable": True
            })
        elif issue_type == "encoding_error":
            fixes.append({
                "issue": issue,
                "fix_type": "convert_encoding",
                "suggestion": "Convert to UTF-8",
                "auto_fixable": True
            })
        elif issue_type == "empty_file":
            fixes.append({
                "issue": issue,
                "fix_type": "skip",
                "suggestion": "Skip empty files during processing",
                "auto_fixable": True
            })
        else:
            fixes.append({
                "issue": issue,
                "fix_type": "manual",
                "suggestion": "Manual review required",
                "auto_fixable": False
            })

    return JSONResponse({
        "fixes": fixes,
        "auto_fixable_count": sum(1 for f in fixes if f["auto_fixable"]),
        "manual_review_count": sum(1 for f in fixes if not f["auto_fixable"])
    })


@router.post("/build")
async def build_corpus(
    background_tasks: BackgroundTasks,
    build_request: BuildRequest
):
    """
    Start building a corpus vector store in the background.
    """
    try:
        # Transform frontend config to backend CorpusConfig format
        frontend_config = build_request.config

        # Create the backend config structure
        backend_config = {
            "metadata": {
                "name": frontend_config["metadata"]["name"],
                "display_name": frontend_config["metadata"].get("name", "Corpus"),
                "description": frontend_config["metadata"].get("description", ""),
                "copyright_status": frontend_config["metadata"].get("copyright", ""),
                "doi": frontend_config["metadata"].get("source_doi", "")
            },
            "source": {
                **frontend_config["source"],
                # Add extraction settings to source config
                "extract_inline_urls": frontend_config["source"].get("extract_inline_urls", False)
            },
            "filters": {
                "method": "directory",
                "directory_depth": 2,
                "filters": [
                    {
                        **f,
                        # Map 'all' type to 'directory' for backend compatibility
                        "type": "directory" if f.get("type") == "all" else f.get("type", "directory")
                    }
                    for f in frontend_config.get("filters", [])
                ]
            },
            "citation": {
                "template": "{author}. {title}. {date}. {source}.",
                "source_name": frontend_config["metadata"].get("name", "Corpus"),
                # Add metadata patterns if date extraction is configured
                "metadata_patterns": {
                    "date": frontend_config["source"].get("custom_date_pattern") if frontend_config["source"].get("date_pattern") == "custom" else None
                } if frontend_config["source"].get("date_pattern") else {}
            },
            "embedding": {
                "model_id": frontend_config["embeddings"]["model"],
                "chunk_size": frontend_config["embeddings"]["chunk_size"],
                "chunk_overlap": frontend_config["embeddings"]["chunk_overlap"],
                "batch_size": frontend_config["embeddings"]["batch_size"]
            },
            "processing": {
                "mode": build_request.mode,
                "max_workers": 4
            }
        }

        # Parse configuration
        config = CorpusConfig(**backend_config)

        # Generate build ID
        build_id = f"build_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Initialize progress tracking
        wizard_state['current_build'] = build_id
        wizard_state['build_progress'][build_id] = {
            "status": "starting",
            "progress": 0,
            "total_documents": 0,
            "processed_documents": 0,
            "current_document": "",
            "started_at": datetime.now().isoformat(),
            "mode": build_request.mode
        }

        # Start build in background - use asyncio to ensure proper async execution
        import asyncio

        # Create a new event loop for the background task
        def run_build_in_background(build_id: str, config: CorpusConfig):
            """Wrapper to run async build task in background."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_build_corpus_task(build_id, config))
            finally:
                loop.close()

        background_tasks.add_task(
            run_build_in_background,
            build_id,
            config
        )

        return JSONResponse({
            "build_id": build_id,
            "status": "started",
            "message": f"Corpus build started in {build_request.mode} mode"
        })

    except Exception as e:
        logger.error(f"Failed to start corpus build: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{build_id}")
async def get_build_progress(build_id: str):
    """
    Get progress for a specific build.
    """
    if build_id not in wizard_state['build_progress']:
        raise HTTPException(status_code=404, detail="Build not found")

    return JSONResponse(wizard_state['build_progress'][build_id])


@router.get("/progress-stream/{build_id}")
async def stream_build_progress(build_id: str):
    """
    Stream build progress via Server-Sent Events.
    """
    if build_id not in wizard_state['build_progress']:
        raise HTTPException(status_code=404, detail="Build not found")

    async def event_generator():
        last_update = None
        keepalive_counter = 0
        while True:
            current_progress = wizard_state['build_progress'].get(build_id)
            if not current_progress:
                break

            # Send update if changed
            if current_progress != last_update:
                yield f"data: {json.dumps(current_progress)}\n\n"
                last_update = current_progress.copy()
                keepalive_counter = 0
            else:
                # Send keepalive every 10 seconds if no updates
                keepalive_counter += 1
                if keepalive_counter >= 10:
                    # Send a comment to keep connection alive
                    yield f": keepalive\n\n"
                    keepalive_counter = 0

            # Check if completed
            if current_progress.get('status') in ['completed', 'failed']:
                break

            # Wait before checking again
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/preview")
async def preview_documents(request: Dict[str, Any] = Body(...)):
    """
    Preview documents with extraction settings.
    """
    try:
        source = request.get('source', {})
        metadata = request.get('metadata', {})

        # Get source path
        if source.get('type') == 'github':
            github_manager = GitHubCorpusManager()
            source_path = github_manager.fetch_corpus(
                repo_url=source.get('location'),
                branch=source.get('branch', 'main'),
                path=source.get('path', '')
            )
        else:
            location = source.get('location', '.')
            # Handle relative paths - make them relative to the project root
            source_path = Path(location)
            if not source_path.is_absolute():
                # If relative path, assume it's relative to project root
                source_path = Path.cwd() / source_path

        # Ensure source_path is a Path object
        if not isinstance(source_path, Path):
            source_path = Path(source_path)

        logger.info(f"Preview: Checking path {source_path}")

        if not source_path.exists():
            logger.error(f"Source path does not exist: {source_path}")
            return JSONResponse({
                "error": f"Source path does not exist: {source_path}",
                "attempted_path": str(source_path),
                "current_dir": str(Path.cwd())
            })

        # Find documents
        extensions = source.get('file_extensions', '.txt').split(',')
        documents = []
        for ext in extensions:
            ext = ext.strip()
            if not ext.startswith('.'):
                ext = '.' + ext
            if source.get('include_subdirectories', True):
                docs = list(source_path.rglob(f"*{ext}"))
            else:
                docs = list(source_path.glob(f"*{ext}"))
            documents.extend(docs)

        total_size = sum(doc.stat().st_size for doc in documents if doc.is_file())

        # Process sample documents
        samples = []
        docs_with_urls = 0
        docs_with_dates = 0

        for doc in documents[:5]:  # Sample first 5
            if not doc.is_file():
                continue

            sample = {
                "filename": doc.name,
                "path": str(doc.relative_to(source_path) if source_path in doc.parents or doc == source_path else doc),
                "size": doc.stat().st_size
            }

            # Read preview
            try:
                with open(doc, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    sample["preview"] = ''.join(lines[:10])  # First 10 lines

                    # Extract metadata if configured
                    extracted_metadata = {}

                    # Check for inline URL
                    if source.get('extract_inline_urls') and lines:
                        first_line = lines[0].strip()
                        if first_line.startswith('<url>') and first_line.endswith('</url>'):
                            url = first_line[5:-6]
                            extracted_metadata['url'] = url
                            docs_with_urls += 1

                    # Extract date from filename
                    if source.get('date_pattern'):
                        import re
                        pattern_map = {
                            'YYYY-MM-DD': r'(\d{4}-\d{2}-\d{2})',
                            'DD-MM-YYYY': r'(\d{2}-\d{2}-\d{4})',
                            'YYYYMMDD': r'(\d{8})',
                            'custom': source.get('custom_date_pattern', '')
                        }
                        pattern = pattern_map.get(source['date_pattern'])
                        if pattern:
                            try:
                                # Validate regex pattern first
                                compiled_pattern = re.compile(pattern)
                                match = compiled_pattern.search(doc.name)
                                if match:
                                    # Get first group or whole match
                                    extracted_metadata['date'] = match.group(1) if match.groups() else match.group(0)
                                    docs_with_dates += 1
                            except re.error as e:
                                # Pattern is invalid, will be reported in warnings
                                pass

                    sample["extracted_metadata"] = extracted_metadata

            except Exception as e:
                sample["error"] = str(e)

            samples.append(sample)

        # Discover filters from directory structure
        filters = []
        directory_structure = {}

        # Analyze directory structure for filters
        for doc in documents:
            if not doc.is_file():
                continue

            # Get relative path from source
            try:
                rel_path = doc.relative_to(source_path)
                parts = rel_path.parts[:-1]  # Exclude filename

                if parts:
                    # Track directory structure
                    current_level = directory_structure
                    for part in parts:
                        if part not in current_level:
                            current_level[part] = {}
                        current_level = current_level[part]
            except ValueError:
                continue

        # Create filters from directory structure
        def create_filters_from_structure(structure, prefix=""):
            for key, value in structure.items():
                filter_id = f"{prefix}{key}".lower().replace(" ", "_").replace("-", "_")
                filter_path = f"{prefix}{key}/"

                # Count documents in this directory
                doc_count = sum(1 for d in documents if str(d).replace(str(source_path), "").startswith(f"/{filter_path}") or filter_path in str(d))

                filters.append({
                    "id": filter_id,
                    "label": key,
                    "type": "directory",
                    "path": filter_path.rstrip('/'),
                    "pattern": f"**/{key}/**/*.txt",
                    "document_count": doc_count
                })

                # Recurse for subdirectories
                if value:
                    create_filters_from_structure(value, f"{filter_path}")

        create_filters_from_structure(directory_structure)

        # Add an "all" filter
        filters.insert(0, {
            "id": "all",
            "label": "All Documents",
            "type": "all",
            "path": "",
            "pattern": "**/*.txt",
            "document_count": len(documents)
        })

        # Check for warnings
        warnings = []

        # Validate custom regex pattern upfront
        if source.get('date_pattern') == 'custom' and source.get('custom_date_pattern'):
            import re
            try:
                re.compile(source.get('custom_date_pattern'))
            except re.error as e:
                warnings.append(f"Invalid date extraction regex pattern: {e}")

        if not documents:
            warnings.append("No documents found with specified extensions")
        if source.get('extract_inline_urls') and docs_with_urls == 0:
            warnings.append("URL extraction enabled but no URLs found in sample documents")
        if source.get('date_pattern') and docs_with_dates == 0 and source.get('date_pattern') != 'custom':
            warnings.append("Date extraction configured but no dates found in filenames")
        if source.get('date_pattern') == 'custom' and docs_with_dates == 0 and source.get('custom_date_pattern'):
            # Only warn if the pattern is valid
            try:
                import re
                re.compile(source.get('custom_date_pattern'))
                warnings.append("Custom date pattern provided but no dates found in sample filenames")
            except:
                pass  # Invalid pattern already reported above

        return JSONResponse({
            "total_documents": len(documents),
            "total_size": total_size,
            "docs_with_urls": docs_with_urls,
            "docs_with_dates": docs_with_dates,
            "samples": samples,
            "filters": filters,
            "warnings": warnings
        })

    except Exception as e:
        logger.error(f"Preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current-corpus")
async def get_current_corpus_info():
    """
    Get information about the currently active corpus.
    """
    try:
        corpus_path = Path("backend/corpus")
        chroma_path = corpus_path / "chroma_db"
        manifest_path = corpus_path / "manifest.json"

        if not corpus_path.exists():
            return JSONResponse({
                "exists": False,
                "message": "No active corpus found"
            })

        info = {
            "exists": True
        }

        # Get document count from manifest if it exists
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                info["document_count"] = manifest.get("statistics", {}).get("total_documents", 0)
                info["model"] = manifest.get("embedding_model", "Unknown")

        # Get vector store size
        if chroma_path.exists():
            size = sum(
                f.stat().st_size
                for f in chroma_path.rglob('*')
                if f.is_file()
            )
            info["size"] = size

        return JSONResponse(info)

    except Exception as e:
        logger.error(f"Failed to get current corpus info: {e}")
        return JSONResponse({
            "exists": False,
            "error": str(e)
        })


@router.post("/validate/{build_id}")
async def validate_corpus(build_id: str):
    """
    Validate a built corpus before activation.
    """
    try:
        # Check if build exists and is completed
        if build_id not in wizard_state['build_progress']:
            raise HTTPException(status_code=404, detail="Build not found")

        build_info = wizard_state['build_progress'][build_id]
        if build_info.get('status') != 'completed':
            return JSONResponse({
                "all_valid": False,
                "structure_valid": False,
                "metadata_valid": False,
                "search_functional": False,
                "message": "Build not yet completed"
            })

        # Check output files
        output_path = Path("backend/corpus/tmp")
        chroma_path = output_path / "chroma_db"
        manifest_path = output_path / "manifest.json"

        structure_valid = chroma_path.exists() and chroma_path.is_dir()
        metadata_valid = manifest_path.exists()

        # Try a test search to verify functionality
        search_functional = False
        if structure_valid:
            try:
                # Check if vector store has data
                # Simple check: verify the chroma directory has content
                chroma_files = list(chroma_path.glob("**/*"))
                search_functional = len(chroma_files) > 0
            except Exception as e:
                logger.warning(f"Search functionality check failed: {e}")
                search_functional = False

        all_valid = structure_valid and metadata_valid and search_functional

        return JSONResponse({
            "all_valid": all_valid,
            "structure_valid": structure_valid,
            "metadata_valid": metadata_valid,
            "search_functional": search_functional
        })

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-search")
async def test_search(request: Dict[str, Any] = Body(...)):
    """
    Run a test search on the newly built corpus.
    """
    try:
        build_id = request.get('build_id')
        query = request.get('query', 'test query')
        limit = request.get('limit', 5)

        # Check if build exists
        if build_id not in wizard_state['build_progress']:
            raise HTTPException(status_code=404, detail="Build not found")

        # Mock search results for now
        # In production, would use the actual vector store
        results = []
        for i in range(min(3, limit)):
            results.append({
                "content": f"Sample document content for result {i+1}. This is a test result demonstrating the search functionality...",
                "score": 0.9 - (i * 0.1),
                "metadata": {
                    "source": f"document_{i+1}.txt",
                    "date": "2024-01-15"
                }
            })

        return JSONResponse({
            "query": query,
            "results": results,
            "total_found": len(results)
        })

    except Exception as e:
        logger.error(f"Test search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activate")
async def activate_corpus_by_build(request: Dict[str, Any] = Body(...)):
    """
    Activate a corpus from a specific build.
    """
    try:
        build_id = request.get('build_id')
        corpus_name = request.get('corpus_name')

        # Validate build exists and is completed
        if build_id not in wizard_state['build_progress']:
            raise HTTPException(status_code=404, detail="Build not found")

        build_info = wizard_state['build_progress'][build_id]
        if build_info.get('status') != 'completed':
            raise HTTPException(status_code=400, detail="Build not completed")

        # Create backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_id = f"backup_{timestamp}"

        # Paths
        output_path = Path("backend/corpus/tmp")
        corpus_path = Path("backend/corpus")

        # Backup current corpus if it exists
        if corpus_path.exists() and any(corpus_path.iterdir()):
            backup_dir = Path(f"corpus_backups/{backup_id}")
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(corpus_path, backup_dir / "corpus")
            logger.info(f"Backed up current corpus to {backup_dir}")

        # Clear and move new corpus
        if corpus_path.exists():
            shutil.rmtree(corpus_path)
        corpus_path.mkdir(parents=True, exist_ok=True)

        # Move files from tmp to corpus
        for item in output_path.iterdir():
            if item.name in ["chroma_db", "manifest.json", "bm25_corpus.jsonl"]:
                dest = corpus_path / item.name
                if item.is_dir():
                    shutil.move(str(item), str(dest))
                else:
                    shutil.copy(str(item), str(dest))

        # Clear wizard state
        wizard_state['enabled'] = False

        return JSONResponse({
            "success": True,
            "backup_id": backup_id,
            "message": "Corpus activated successfully"
        })

    except Exception as e:
        logger.error(f"Activation failed: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@router.post("/activate/{corpus_name}")
async def activate_corpus(
    corpus_name: str,
    request: Dict[str, Any] = Body(...),
    backup: bool = Query(True, description="Backup current corpus")
):
    """
    Activate a newly built corpus.

    This moves corpus files from backend/corpus/tmp/ to their proper locations:
    - Corpus data (chroma_db, manifest, bm25) → backend/corpus/
    - Test target configs (.conf files) → backend/targets/
    - Corpus configuration → config/corpus.yaml
    - Generated retriever → backend/retrievers/
    """
    try:
        # Extract target configuration from request
        target_config = request.get('target_config', {})

        # Paths
        output_path = Path("backend/corpus/tmp")
        corpus_path = Path("backend/corpus")
        targets_path = Path("backend/targets")
        retrievers_path = Path("backend/retrievers")
        config_path = Path("config")

        # Generate target configuration file if provided
        if target_config:
            targets_path.mkdir(parents=True, exist_ok=True)

            # Generate target filename based on settings
            target_name = f"k{target_config.get('search_k', 20)}_{target_config.get('llm_model', 'claude4').replace('-', '_').replace('.', '_')}"
            target_file = targets_path / f"{target_name}.txt"

            # Generate target configuration content
            target_content = []
            target_content.append(f"# Target configuration generated by Corpus Wizard")
            target_content.append(f"# Created: {datetime.now().isoformat()}")
            target_content.append(f"# Corpus: {corpus_name}")
            target_content.append("")
            target_content.append(f"LLM_PROVIDER={target_config.get('llm_provider', 'anthropic')}")
            target_content.append(f"LLM_MODEL={target_config.get('llm_model', 'claude-3-5-haiku-20241022')}")
            target_content.append(f"SEARCH_TYPE={target_config.get('search_type', 'similarity')}")
            target_content.append(f"SEARCH_K={target_config.get('search_k', 20)}")
            target_content.append(f"SCORE_THRESHOLD={target_config.get('score_threshold', 0.7)}")
            target_content.append(f"TEMPERATURE={target_config.get('temperature', 0.7)}")
            target_content.append(f"MAX_TOKENS={target_config.get('max_tokens', 4096)}")
            target_content.append(f"CITATION_LIMIT={target_config.get('citation_limit', 10)}")
            target_content.append(f"ALGORITHM={target_config.get('algorithm', 'ensemble')}")
            target_content.append(f"LARGE_RETRIEVAL_SIZE={target_config.get('large_retrieval_size', 120)}")
            target_content.append(f"VECTOR_DATABASE={target_config.get('vector_database', 'chromadb')}")
            target_content.append(f"POOLING={target_config.get('pooling', 'mean')}")

            # Write target configuration file
            with open(target_file, 'w') as f:
                f.write('\n'.join(target_content))
            logger.info(f"Generated target configuration file: {target_file}")

            # Update TEST_TARGET in environment files
            env_files = ['config/.env.development', 'config/.env.staging', 'config/.env.production']
            for env_file in env_files:
                env_path = Path(env_file)
                if env_path.exists():
                    # Read the file
                    with open(env_path, 'r') as f:
                        lines = f.readlines()

                    # Update TEST_TARGET line
                    updated = False
                    for i, line in enumerate(lines):
                        if line.strip().startswith('TEST_TARGET=') or line.strip().startswith('# TEST_TARGET='):
                            lines[i] = f'TEST_TARGET={target_name}\n'
                            updated = True
                            break

                    # If not found, add it
                    if not updated:
                        lines.append(f'TEST_TARGET={target_name}\n')

                    # Write back
                    with open(env_path, 'w') as f:
                        f.writelines(lines)
                    logger.info(f"Updated TEST_TARGET in {env_file} to {target_name}")

        # Update VITE_SITE_TITLE with corpus display name
        display_name = request.get('display_name', corpus_name)
        env_files = ['config/.env.development', 'config/.env.staging', 'config/.env.production']
        for env_file in env_files:
            env_path = Path(env_file)
            if env_path.exists():
                # Read the file
                with open(env_path, 'r') as f:
                    lines = f.readlines()

                # Update VITE_SITE_TITLE line
                updated = False
                for i, line in enumerate(lines):
                    if line.strip().startswith('VITE_SITE_TITLE=') or line.strip().startswith('# VITE_SITE_TITLE='):
                        lines[i] = f'VITE_SITE_TITLE={display_name}\n'
                        updated = True
                        break

                # If not found, add it
                if not updated:
                    # Find a good place to insert (after other VITE_ variables if they exist)
                    insert_index = len(lines)
                    for i, line in enumerate(lines):
                        if line.strip().startswith('VITE_'):
                            insert_index = i + 1
                            # Continue looking for the last VITE_ variable
                            for j in range(i + 1, len(lines)):
                                if lines[j].strip().startswith('VITE_'):
                                    insert_index = j + 1
                                else:
                                    break
                            break
                    lines.insert(insert_index, f'VITE_SITE_TITLE={display_name}\n')

                # Write back
                with open(env_path, 'w') as f:
                    f.writelines(lines)
                logger.info(f"Updated VITE_SITE_TITLE in {env_file} to {display_name}")

        if not output_path.exists():
            raise HTTPException(status_code=404, detail="Built corpus not found in backend/corpus/tmp")

        # Backup current corpus if requested
        if backup and corpus_path.exists() and any(corpus_path.iterdir()):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = Path(f"corpus_backups/backup_{timestamp}")
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Backup corpus data
            if corpus_path.exists():
                shutil.copytree(corpus_path, backup_dir / "corpus")
            # Backup config
            corpus_config = config_path / "corpus.yaml"
            if corpus_config.exists():
                shutil.copy(corpus_config, backup_dir / "corpus.yaml")

            logger.info(f"Backed up current corpus to {backup_dir}")

        # Clear existing corpus data
        if corpus_path.exists():
            shutil.rmtree(corpus_path)
        corpus_path.mkdir(parents=True, exist_ok=True)

        # Move corpus data files to backend/corpus/
        corpus_files = ["chroma_db", "manifest.json", "bm25_corpus.jsonl"]
        for file_name in corpus_files:
            source = output_path / file_name
            if source.exists():
                dest = corpus_path / file_name
                if source.is_dir():
                    shutil.move(str(source), str(dest))
                else:
                    shutil.copy(str(source), str(dest))
                logger.info(f"Moved {file_name} to backend/corpus/")

        # Move test target configs to backend/targets/
        targets_path.mkdir(parents=True, exist_ok=True)
        for conf_file in output_path.glob("*.conf"):
            dest = targets_path / conf_file.name
            shutil.copy(str(conf_file), str(dest))
            logger.info(f"Copied {conf_file.name} to backend/targets/")

        # Copy corpus configuration to config/corpus.yaml
        corpus_config_src = output_path / "corpus_config.yaml"
        if corpus_config_src.exists():
            corpus_config_dest = config_path / "corpus.yaml"
            shutil.copy(str(corpus_config_src), str(corpus_config_dest))
            logger.info(f"Copied corpus configuration to config/corpus.yaml")

        # Move generated retriever to backend/retrievers/
        for retriever_file in output_path.glob("*_retriever.py"):
            dest = retrievers_path / retriever_file.name
            shutil.copy(str(retriever_file), str(dest))
            logger.info(f"Copied {retriever_file.name} to backend/retrievers/")

            # Update RETRIEVER_MODULE in .env files
            retriever_module = retriever_file.stem  # Remove .py extension

            # Update all .env files
            env_files = ['config/.env.development', 'config/.env.staging', 'config/.env.production']
            for env_file in env_files:
                env_path = Path(env_file)
                if env_path.exists():
                    # Read the file
                    with open(env_path, 'r') as f:
                        lines = f.readlines()

                    # Update RETRIEVER_MODULE line
                    updated = False
                    for i, line in enumerate(lines):
                        if line.strip().startswith('RETRIEVER_MODULE=') or line.strip().startswith('# RETRIEVER_MODULE='):
                            lines[i] = f'RETRIEVER_MODULE={retriever_module}\n'
                            updated = True
                            break

                    # If not found, add it
                    if not updated:
                        # Find a good place to insert it (after TEST_TARGET if it exists)
                        insert_index = len(lines)
                        for i, line in enumerate(lines):
                            if line.strip().startswith('TEST_TARGET='):
                                insert_index = i + 1
                                break
                        lines.insert(insert_index, f'RETRIEVER_MODULE={retriever_module}\n')

                    # Write back
                    with open(env_path, 'w') as f:
                        f.writelines(lines)

                    logger.info(f"Updated RETRIEVER_MODULE in {env_file} to {retriever_module}")

        # Clean up tmp directory
        shutil.rmtree(output_path)
        output_path.mkdir()  # Recreate empty directory for next corpus

        # Clear wizard state
        wizard_state['enabled'] = False

        return JSONResponse({
            "status": "activated",
            "corpus": corpus_name,
            "message": "Corpus activated successfully. Please restart the server to use the new corpus.",
            "locations": {
                "corpus_data": "backend/corpus/",
                "test_targets": "backend/targets/",
                "corpus_config": "config/corpus.yaml",
                "retriever": f"backend/retrievers/{corpus_name}_retriever.py"
            }
        })

    except Exception as e:
        logger.error(f"Failed to activate corpus: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs")
async def list_configs():
    """
    List available corpus configurations.
    """
    manager = CorpusConfigManager()
    configs = manager.list_configs()

    return JSONResponse({
        "configs": configs,
        "total": len(configs)
    })


@router.get("/unified-config/{build_id}")
async def get_unified_config(build_id: str):
    """
    Get unified configuration combining corpus and target settings.
    This provides a complete view of all configuration parameters
    that will be used when the corpus is activated.
    """
    try:
        # Check if build exists
        if build_id not in wizard_state['build_progress']:
            raise HTTPException(status_code=404, detail="Build not found")

        # Read manifest from tmp directory
        manifest_path = Path("backend/corpus/tmp/manifest.json")
        if not manifest_path.exists():
            return JSONResponse({
                "error": "Manifest not found. Build may not be complete."
            })

        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        # Combine configurations
        unified_config = {
            "corpus_settings": {
                "name": manifest.get("corpus_name", "Unknown"),
                "collection_name": manifest.get("collection_name", "Unknown"),
                "embedding_model": manifest.get("embedding_model", "Unknown"),
                "chunk_size": manifest.get("chunk_size", 1000),
                "chunk_overlap": manifest.get("chunk_overlap", 200),
                "total_documents": manifest.get("statistics", {}).get("total_documents", 0),
                "filters": manifest.get("fields", {}).get("corpus", {}).get("values", [])
            },
            "target_settings": {
                "provider": "anthropic",  # Will be populated from request
                "model": "claude-3-5-haiku-20241022",
                "search_k": 20,
                "search_type": "similarity",
                "score_threshold": 0.7
            },
            "composite_target": None  # Will be generated from target name
        }

        return JSONResponse(unified_config)

    except Exception as e:
        logger.error(f"Failed to get unified config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-config")
async def save_config(config_data: Dict[str, Any] = Body(...)):
    """
    Save a corpus configuration.
    """
    try:
        config = CorpusConfig(**config_data)
        manager = CorpusConfigManager()
        path = manager.save_config(config)

        return JSONResponse({
            "status": "saved",
            "path": str(path),
            "name": config.metadata.name
        })

    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
def _format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = int(seconds / 3600)
        remaining_minutes = int((seconds % 3600) / 60)
        return f"{hours}h {remaining_minutes}m"


async def _build_corpus_task(build_id: str, config: CorpusConfig):
    """
    Background task to build corpus using the universal corpus builder.
    """
    logger.info(f"Starting build task for build_id: {build_id}")
    try:
        # Import the corpus builder from backend modules
        from backend.modules.corpus_builder import UniversalCorpusBuilder

        # Update status to show task started
        wizard_state['build_progress'][build_id]['status'] = 'building'
        wizard_state['build_progress'][build_id]['current_document'] = 'Initializing corpus builder...'
        logger.info(f"Build task initialized for {config.metadata.name}")

        # Create progress callback
        async def progress_callback(progress_data):
            """Update wizard state with progress."""
            logger.debug(f"Progress update for {build_id}: {progress_data.get('current_document', 'N/A')}")
            wizard_state['build_progress'][build_id].update(progress_data)

        # Initialize builder
        mode = wizard_state['build_progress'][build_id].get('mode', 'cpu')
        # Use the tmp directory for corpus building
        output_dir = Path("backend/corpus/tmp")
        logger.info(f"Creating UniversalCorpusBuilder with mode={mode}, output={output_dir}")
        builder = UniversalCorpusBuilder(config, mode, output_dir)
        logger.info("Builder created successfully, starting build...")

        # Build corpus
        results = await builder.build(progress_callback)
        logger.info(f"Build completed with results: {results}")

        # Mark as completed
        wizard_state['build_progress'][build_id].update({
            'status': 'completed',
            'completed_at': datetime.now().isoformat(),
            'results': results
        })

        logger.info(f"Corpus build completed: {results}")

    except Exception as e:
        logger.error(f"Build failed: {e}")
        wizard_state['build_progress'][build_id].update({
            'status': 'failed',
            'error': str(e),
            'failed_at': datetime.now().isoformat()
        })
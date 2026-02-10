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
import re

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
    target: Optional[Dict[str, Any]] = Field(None, description="Target configuration to save after build")


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
        # First check if source path exists
        source_path_obj = Path(source_path)
        if not source_path_obj.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Source path does not exist: {source_path}"
            )
        if not source_path_obj.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Source path is not a directory: {source_path}"
            )

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


@router.get("/check-existing")
async def check_existing_corpus():
    """
    Check if an existing corpus is present and return its metadata.

    Returns:
        JSONResponse with corpus metadata if exists, empty response if not
    """
    try:
        corpus_path = Path("backend/corpus")
        manifest_path = corpus_path / "manifest.json"

        if not manifest_path.exists():
            return JSONResponse({
                "exists": False
            })

        # Read existing manifest
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        # Calculate corpus size
        corpus_size = 0
        chroma_path = corpus_path / "chroma_db"
        if chroma_path.exists():
            for item in chroma_path.rglob("*"):
                if item.is_file():
                    corpus_size += item.stat().st_size

        # Get build date from manifest or file modification time
        build_date = manifest.get("build_date", "Unknown")
        if build_date == "Unknown":
            build_date = datetime.fromtimestamp(manifest_path.stat().st_mtime).isoformat()

        return JSONResponse({
            "exists": True,
            "corpus_name": manifest.get("corpus_name", "Unknown"),
            "build_date": build_date,
            "document_count": manifest.get("total_documents", 0),
            "chunk_count": manifest.get("total_chunks", 0),
            "size_bytes": corpus_size,
            "size_mb": round(corpus_size / (1024 * 1024), 2)
        })

    except Exception as e:
        logger.error(f"Error checking existing corpus: {e}")
        return JSONResponse({
            "exists": False,
            "error": str(e)
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

        # Extract and save system configuration if provided
        if "systemConfig" in frontend_config:
            from backend.modules.system_configuration import get_system_config
            system_config = get_system_config()
            system_config.save_config(frontend_config["systemConfig"])
            logger.info(f"Updated system configuration: {frontend_config['systemConfig']}")

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
                "text_splitter_type": frontend_config["embeddings"].get("text_splitter_type", "RecursiveCharacterTextSplitter"),
                "pooling": frontend_config["embeddings"].get("pooling", "mean"),
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

        # Extract target configuration if provided
        target_config = build_request.target if build_request.target else {}

        # Initialize progress tracking
        wizard_state['current_build'] = build_id
        wizard_state['build_progress'][build_id] = {
            "status": "starting",
            "progress": 0,
            "total_documents": 0,
            "processed_documents": 0,
            "current_document": "",
            "started_at": datetime.now().isoformat(),
            "mode": build_request.mode,
            "target_config": target_config,  # Store target config for later use
            "corpus_name": config.metadata.name  # Store corpus name for target generation
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
            # If date extraction is configured but no documents found, this is an error
            if source.get('date_pattern'):
                return JSONResponse({
                    "error": "Date extraction configured but no documents found. Check your source path and file extensions.",
                    "source_path": str(source_path),
                    "file_extensions": extensions,
                    "path_exists": source_path.exists()
                }, status_code=400)
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


@router.post("/validate")
async def validate_corpus():
    """
    Validate a built corpus before activation.

    This checks the actual filesystem for corpus files rather than relying on
    in-memory state, making it robust against server restarts.
    """
    try:
        import time

        # Check output files directly on filesystem
        output_path = Path("backend/corpus")
        chroma_path = output_path / "chroma_db"
        manifest_path = output_path / "manifest.json"

        # Check if files exist
        structure_valid = chroma_path.exists() and chroma_path.is_dir()
        metadata_valid = manifest_path.exists()

        # Optional: Check if build is recent (within last 2 hours)
        build_is_fresh = False
        build_age_message = None
        if manifest_path.exists():
            age_seconds = time.time() - manifest_path.stat().st_mtime
            age_minutes = age_seconds / 60
            build_is_fresh = age_seconds < 7200  # 2 hours

            if age_minutes < 60:
                build_age_message = f"Build completed {int(age_minutes)} minutes ago"
            else:
                build_age_message = f"Build completed {int(age_minutes/60)} hours ago"
        else:
            build_age_message = "No corpus build found"

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
            "search_functional": search_functional,
            "build_is_fresh": build_is_fresh,
            "build_age": build_age_message,
            "message": "Validation based on filesystem state" if all_valid else build_age_message
        })

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Validation failed: {e}")
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

        # Read manifest from corpus directory
        manifest_path = Path("backend/corpus/manifest.json")
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
        # Build in temporary directory first to avoid conflicts with existing ChromaDB instances
        temp_output_dir = Path("backend/corpus_build_temp")

        # Clean temp directory if it exists from a previous failed build
        if temp_output_dir.exists():
            import shutil
            logger.info(f"Cleaning existing temp directory: {temp_output_dir}")
            shutil.rmtree(temp_output_dir)

        logger.info(f"Creating UniversalCorpusBuilder with mode={mode}, output={temp_output_dir}")
        builder = UniversalCorpusBuilder(config, mode, temp_output_dir)
        logger.info("Builder created successfully, starting build...")

        # Build corpus in temp directory
        results = await builder.build(progress_callback)
        logger.info(f"Build completed with results: {results}")

        # Move from temp to final location
        import shutil
        final_corpus_dir = Path("backend/corpus")

        try:
            # Clean up final location
            if final_corpus_dir.exists():
                logger.info(f"Removing existing corpus directory: {final_corpus_dir}")
                shutil.rmtree(final_corpus_dir)

            # Move temp build to final location
            logger.info(f"Moving built corpus from {temp_output_dir} to {final_corpus_dir}")
            shutil.move(str(temp_output_dir), str(final_corpus_dir))

            # Update results paths to reflect final location
            for key in ['vector_store_path', 'manifest_path', 'bm25_corpus_path', 'config_path', 'retriever_path']:
                if key in results and results[key]:
                    results[key] = results[key].replace(str(temp_output_dir), str(final_corpus_dir))

            logger.info("Successfully moved corpus to final location")

        except Exception as e:
            logger.error(f"Failed to move corpus to final location: {e}")
            raise

        # Set retriever module name and copy manifest to targets directory
        try:
            import shutil

            # Just set the adapter module name - no need to copy since it stays in corpus/
            adapter_source = Path(results.get('adapter_path', ''))
            if adapter_source.exists():
                adapter_name = adapter_source.name
                results['corpus_adapter'] = adapter_name.replace('.py', '')
                logger.info(f"Corpus adapter: {results['corpus_adapter']} (in backend/corpus/)")
            else:
                # If adapter_path doesn't exist in results, try to get from corpus directory
                # First try the new naming convention
                corpus_adapter = Path("backend/corpus") / f"{corpus_name}_adapter.py"
                if corpus_adapter.exists():
                    adapter_name = corpus_adapter.name
                    results['corpus_adapter'] = adapter_name.replace('.py', '')
                    logger.info(f"Corpus adapter: {results['corpus_adapter']} (in backend/corpus/)")
                else:
                    # Fallback to old naming for existing corpora
                    corpus_retriever = Path("backend/corpus") / f"{corpus_name}_retriever.py"
                    if corpus_retriever.exists():
                        retriever_name = corpus_retriever.name
                        results['corpus_adapter'] = retriever_name.replace('.py', '').replace('_retriever', '_adapter')
                        logger.info(f"Corpus adapter: {results['corpus_adapter']} (fallback from old retriever naming)")

            # Copy manifest to targets directory
            manifest_source = Path(results.get('manifest_path', ''))
            if manifest_source.exists():
                manifest_dest = Path("backend/targets/manifest.json")
                shutil.copy2(manifest_source, manifest_dest)
                logger.info(f"Copied manifest to: {manifest_dest}")
        except Exception as e:
            logger.error(f"Failed to copy retriever/manifest files: {e}")
            # Don't fail the build, just log the error
            wizard_state['build_progress'][build_id]['copy_error'] = str(e)

        # UNCONDITIONALLY create corpus_active.json after successful build
        corpus_name = wizard_state['build_progress'][build_id].get('corpus_name', 'corpus')
        target_config = wizard_state['build_progress'][build_id].get('target_config', {})

        # Use target_config if provided, otherwise use defaults
        if not target_config:
            target_config = {
                'llm_provider': 'anthropic',
                'llm_model': 'claude-3-5-haiku-20241022',
                'search_k': 20,
                'citation_limit': 5,
                'temperature': 0.7,
                'max_tokens': 4096
            }

        # NO CONDITIONS - JUST CREATE THE FILE
        try:
                # Import mode_manager
                from backend.modules.mode_manager import mode_manager

                # Generate and save target configuration file
                targets_path = Path("backend/targets")
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
                # Core LLM configuration
                target_content.append(f"LLM_PROVIDER={target_config.get('llm_provider', 'anthropic')}")
                target_content.append(f"LLM_MODEL={target_config.get('llm_model', 'claude-3-5-haiku-20241022')}")
                # Search configuration
                target_content.append(f"SEARCH_TYPE={target_config.get('search_type', 'similarity')}")
                target_content.append(f"SEARCH_K={target_config.get('search_k', 20)}")
                target_content.append(f"SEARCH_SCORE_THRESHOLD={target_config.get('score_threshold', 0.7)}")
                target_content.append(f"CITATION_LIMIT={target_config.get('citation_limit', 10)}")
                # Retrieval size configuration
                target_content.append(f"LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS={target_config.get('large_retrieval_size_single_corpus', 120)}")
                target_content.append(f"LARGE_RETRIEVAL_SIZE_ALL_CORPUS={target_config.get('large_retrieval_size_all_corpus', 80)}")
                # Algorithm and chunking configuration
                target_content.append(f"ALGORITHM={target_config.get('algorithm', 'ensemble')}")
                chunk_size = target_config.get('chunk_size', 1000)
                chunk_overlap = target_config.get('chunk_overlap', 200)
                target_content.append(f"CHUNK_SIZE={chunk_size}")
                target_content.append(f"CHUNK_OVERLAP={chunk_overlap}")
                # Vector database and pooling
                target_content.append(f"VECTOR_DATABASE={target_config.get('vector_database', 'chromadb')}")
                target_content.append(f"POOLING={target_config.get('pooling', 'mean')}")
                # Target version for tracking
                target_content.append(f"TARGET_VERSION=1.0")
                # Optional temperature and max tokens
                target_content.append(f"TEMPERATURE={target_config.get('temperature', 0.7)}")
                target_content.append(f"MAX_TOKENS={target_config.get('max_tokens', 4096)}")

                # Write target configuration file
                with open(target_file, 'w') as f:
                    f.write('\n'.join(target_content))
                logger.info(f"Generated target configuration file: {target_file}")

                # Store build results for later deployment
                # corpus_active.json will be created when user confirms deployment
                logger.info(f"Build completed successfully - configuration stored for deployment")

                # Update VITE_SITE_TITLE with corpus display_name
                try:
                    # Read the manifest to get display_name
                    manifest_path = Path("backend/corpus/manifest.json")
                    if manifest_path.exists():
                        with open(manifest_path, 'r') as f:
                            manifest_data = json.load(f)

                        # Get display_name from manifest, fallback to name if not present
                        display_name = manifest_data.get('metadata', {}).get('display_name', '')
                        if not display_name:
                            display_name = manifest_data.get('metadata', {}).get('name', 'ATLAS')

                        logger.info(f"Updating VITE_SITE_TITLE to: {display_name}")

                        # Determine which env file to update based on runtime mode
                        if mode_manager.is_locked():
                            logger.info("System in deploy mode - skipping VITE_SITE_TITLE file update")
                        else:
                            # Update the appropriate environment file
                            env_file = Path("config/.env.development")

                            if env_file.exists():
                                # Read existing environment file
                                lines = []
                                title_updated = False

                                with open(env_file, 'r') as f:
                                    for line in f:
                                        if line.startswith('VITE_SITE_TITLE='):
                                            lines.append(f'VITE_SITE_TITLE="{display_name}"\n')
                                            title_updated = True
                                            logger.info(f"Updated VITE_SITE_TITLE in {env_file}")
                                        else:
                                            lines.append(line)

                                # If VITE_SITE_TITLE wasn't found, add it
                                if not title_updated:
                                    lines.append(f'\n# Updated by corpus wizard\n')
                                    lines.append(f'VITE_SITE_TITLE="{display_name}"\n')
                                    logger.info(f"Added VITE_SITE_TITLE to {env_file}")

                                # Write back to file
                                with open(env_file, 'w') as f:
                                    f.writelines(lines)

                                logger.info(f"Successfully updated VITE_SITE_TITLE to '{display_name}'")
                                logger.info("Note: Frontend restart may be required to see the title change")
                            else:
                                logger.warning(f"Environment file {env_file} not found - skipping VITE_SITE_TITLE update")
                    else:
                        logger.warning("Manifest file not found - skipping VITE_SITE_TITLE update")

                except Exception as e:
                    logger.error(f"Failed to update VITE_SITE_TITLE: {e}")
                    # Don't fail the build for title update issues
                    wizard_state['build_progress'][build_id]['title_update_error'] = str(e)

        except Exception as e:
            logger.error(f"Failed to process target configuration: {e}")
            # Don't fail the build for target config issues
            wizard_state['build_progress'][build_id]['target_error'] = str(e)

        # Mark as completed
        wizard_state['build_progress'][build_id].update({
            'status': 'completed',
            'completed_at': datetime.now().isoformat(),
            'results': results
        })

        logger.info(f"Corpus build completed: {results}")
        # corpus_active.json will be created when user confirms deployment
        # All necessary information is already in manifest.json

    except Exception as e:
        logger.error(f"Build failed: {e}")
        wizard_state['build_progress'][build_id].update({
            'status': 'failed',
            'error': str(e),
            'failed_at': datetime.now().isoformat()
        })


# Target management endpoints for ConfigManager

@router.get("/list-targets")
async def list_targets():
    """List all configured test targets."""
    try:
        targets = []
        targets_path = Path("backend/targets")

        if targets_path.exists():
            for target_file in targets_path.glob("*.txt"):
                # Skip template files
                if target_file.name.startswith("_") or target_file.name.startswith("."):
                    continue

                try:
                    config = {}
                    with open(target_file) as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, value = line.split("=", 1)
                                config[key.strip()] = value.strip().strip('"').strip("'")

                    # Map config keys to frontend expectations
                    targets.append({
                        "id": target_file.stem,
                        "llm_provider": config.get("LLM_PROVIDER", ""),
                        "llm_model": config.get("LLM_MODEL", ""),
                        "search_k": int(config.get("SEARCH_K", 20)),
                        "search_score_threshold": float(config.get("SEARCH_SCORE_THRESHOLD", 0.7)),
                        "large_retrieval_size_single": int(config.get("LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS", 120)),
                        "large_retrieval_size_all": int(config.get("LARGE_RETRIEVAL_SIZE_ALL_CORPUS", 120)),
                        "algorithm": config.get("ALGORITHM", "ensemble"),
                        "citation_limit": int(config.get("CITATION_LIMIT", 10)),
                        "temperature": float(config.get("TEMPERATURE", 0.7)),
                        "max_tokens": int(config.get("MAX_TOKENS", 4096)),
                        "pooling": config.get("POOLING", "mean")
                    })
                except Exception as e:
                    logger.error(f"Error reading target {target_file.name}: {e}")

        # Get default target from environment
        default_target = os.getenv("TEST_TARGET")

        return JSONResponse({
            "targets": targets,
            "default": default_target
        })

    except Exception as e:
        logger.error(f"Failed to list targets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add-target")
async def add_target(target_config: Dict[str, Any] = Body(...)):
    """Add a new test target configuration."""
    try:
        target_id = target_config.get("id")
        if not target_id:
            raise HTTPException(status_code=400, detail="Target ID is required")

        # Validate target ID format
        if not re.match(r'^[a-zA-Z0-9_-]+$', target_id):
            raise HTTPException(status_code=400, detail="Invalid target ID format")

        targets_path = Path("backend/targets")
        targets_path.mkdir(exist_ok=True)

        target_file = targets_path / f"{target_id}.txt"
        if target_file.exists():
            raise HTTPException(status_code=400, detail="Target already exists")

        # Generate target file content
        content = []
        content.append(f"# Target configuration created by ConfigManager")
        content.append(f"# Created: {datetime.now().isoformat()}")
        content.append("")
        content.append(f"LLM_PROVIDER={target_config.get('llm_provider', 'anthropic')}")
        content.append(f"LLM_MODEL={target_config.get('llm_model', '')}")
        content.append(f"SEARCH_TYPE={target_config.get('search_type', 'similarity')}")
        content.append(f"SEARCH_K={target_config.get('search_k', 20)}")
        content.append(f"SEARCH_SCORE_THRESHOLD={target_config.get('search_score_threshold', 0.7)}")
        content.append(f"CITATION_LIMIT={target_config.get('citation_limit', 10)}")
        content.append(f"LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS={target_config.get('large_retrieval_size_single', 120)}")
        content.append(f"LARGE_RETRIEVAL_SIZE_ALL_CORPUS={target_config.get('large_retrieval_size_all', 120)}")
        content.append(f"ALGORITHM={target_config.get('algorithm', 'ensemble')}")
        content.append(f"TEMPERATURE={target_config.get('temperature', 0.7)}")
        content.append(f"MAX_TOKENS={target_config.get('max_tokens', 4096)}")
        content.append(f"POOLING={target_config.get('pooling', 'mean')}")
        content.append(f"TARGET_VERSION=1.0")

        with open(target_file, 'w') as f:
            f.write('\n'.join(content))

        logger.info(f"Created target configuration: {target_id}")

        return JSONResponse({
            "success": True,
            "message": f"Target {target_id} created successfully"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add target: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-target/{target_id}")
async def update_target(target_id: str, target_config: Dict[str, Any] = Body(...)):
    """Update an existing test target configuration."""
    try:
        targets_path = Path("backend/targets")
        target_file = targets_path / f"{target_id}.txt"

        if not target_file.exists():
            raise HTTPException(status_code=404, detail="Target not found")

        # Generate updated content
        content = []
        content.append(f"# Target configuration updated by ConfigManager")
        content.append(f"# Updated: {datetime.now().isoformat()}")
        content.append("")
        content.append(f"LLM_PROVIDER={target_config.get('llm_provider', 'anthropic')}")
        content.append(f"LLM_MODEL={target_config.get('llm_model', '')}")
        content.append(f"SEARCH_TYPE={target_config.get('search_type', 'similarity')}")
        content.append(f"SEARCH_K={target_config.get('search_k', 20)}")
        content.append(f"SEARCH_SCORE_THRESHOLD={target_config.get('search_score_threshold', 0.7)}")
        content.append(f"CITATION_LIMIT={target_config.get('citation_limit', 10)}")
        content.append(f"LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS={target_config.get('large_retrieval_size_single', 120)}")
        content.append(f"LARGE_RETRIEVAL_SIZE_ALL_CORPUS={target_config.get('large_retrieval_size_all', 120)}")
        content.append(f"ALGORITHM={target_config.get('algorithm', 'ensemble')}")
        content.append(f"TEMPERATURE={target_config.get('temperature', 0.7)}")
        content.append(f"MAX_TOKENS={target_config.get('max_tokens', 4096)}")
        content.append(f"POOLING={target_config.get('pooling', 'mean')}")
        content.append(f"TARGET_VERSION=1.0")

        with open(target_file, 'w') as f:
            f.write('\n'.join(content))

        logger.info(f"Updated target configuration: {target_id}")

        return JSONResponse({
            "success": True,
            "message": f"Target {target_id} updated successfully"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update target: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-target/{target_id}")
async def delete_target(target_id: str):
    """Delete a test target configuration."""
    try:
        targets_path = Path("backend/targets")
        target_file = targets_path / f"{target_id}.txt"

        if not target_file.exists():
            raise HTTPException(status_code=404, detail="Target not found")

        # Check if this is the current default target
        current_target = os.getenv("TEST_TARGET")
        if current_target == target_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the current default target. Please set a different default first."
            )

        target_file.unlink()
        logger.info(f"Deleted target configuration: {target_id}")

        return JSONResponse({
            "success": True,
            "message": f"Target {target_id} deleted successfully"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete target: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/set-default-target/{target_id}")
async def set_default_target(target_id: str):
    """Set a target as the default TEST_TARGET."""
    try:
        from backend.modules.mode_manager import mode_manager

        targets_path = Path("backend/targets")
        target_file = targets_path / f"{target_id}.txt"

        if not target_file.exists():
            raise HTTPException(status_code=404, detail="Target not found")

        # Check if we're in deploy mode
        if mode_manager.is_locked():
            # In deploy mode, only update runtime environment
            os.environ["TEST_TARGET"] = target_id
            logger.info(f"Updated runtime TEST_TARGET to {target_id} (deploy mode - no file changes)")

            return JSONResponse({
                "success": True,
                "message": f"Set {target_id} as runtime target (deploy mode)",
                "deploy_mode": True
            })

        # In configure mode, update corpus_active.json
        corpus_active_path = Path("backend/corpus/corpus_active.json")

        # Load existing config or create new
        if corpus_active_path.exists():
            with open(corpus_active_path, 'r') as f:
                corpus_active_config = json.load(f)
        else:
            corpus_active_config = {}

        # Update target
        corpus_active_config["target"] = target_id
        corpus_active_config["last_updated"] = datetime.now().isoformat()

        # Write back
        corpus_active_path.parent.mkdir(parents=True, exist_ok=True)
        with open(corpus_active_path, 'w') as f:
            json.dump(corpus_active_config, f, indent=2)

        logger.info(f"Updated target in corpus_active.json to {target_id}")

        # Update current environment
        os.environ["TEST_TARGET"] = target_id

        return JSONResponse({
            "success": True,
            "message": f"Set {target_id} as default target"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set default target: {e}")
        raise HTTPException(status_code=500, detail=str(e))
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
    CorpusConfig, CorpusMetadata, CorpusSource, CorpusFilter,
    EmbeddingConfig, VectorStoreConfig, SearchConfig, CorpusConfigManager
)
from backend.modules.corpus_analyzer import CorpusAnalyzer
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


@router.post("/recommend-model")
async def recommend_model(metadata: Dict[str, Any] = Body(...)):
    """
    Recommend embedding models based on corpus metadata.
    """
    recommendations = []

    # Extract time period if available
    time_from = metadata.get('time_period_from')
    time_to = metadata.get('time_period_to')
    material_type = metadata.get('material_type', 'general')

    # Historical models
    if time_from and time_to:
        avg_year = (time_from + time_to) / 2

        if 1760 <= avg_year <= 1900:
            recommendations.append({
                "model": "Livingwithmachines/bert_1760_1900",
                "score": 0.95,
                "reason": "Trained on texts from your corpus time period",
                "characteristics": {
                    "period": "1760-1900",
                    "training_data": "Historical newspapers and books",
                    "size_mb": 420,
                    "context_length": 512
                }
            })

            if avg_year >= 1850:
                recommendations.append({
                    "model": "Livingwithmachines/bert_1890_1900",
                    "score": 0.85,
                    "reason": "Optimized for late Victorian period",
                    "characteristics": {
                        "period": "1890-1900",
                        "training_data": "Late Victorian texts",
                        "size_mb": 420,
                        "context_length": 512
                    }
                })

        elif avg_year > 1900 and avg_year < 1950:
            recommendations.append({
                "model": "sentence-transformers/all-MiniLM-L12-v2",
                "score": 0.8,
                "reason": "Good for early 20th century texts",
                "characteristics": {
                    "period": "General",
                    "training_data": "Mixed modern texts",
                    "size_mb": 120,
                    "context_length": 512
                }
            })

    # Modern models
    if not recommendations or (time_from and time_from >= 1950):
        recommendations.append({
            "model": "sentence-transformers/all-mpnet-base-v2",
            "score": 0.9 if not time_from or time_from >= 1950 else 0.7,
            "reason": "Best general-purpose model for modern texts",
            "characteristics": {
                "period": "Modern",
                "training_data": "Contemporary texts",
                "size_mb": 420,
                "context_length": 512
            }
        })

    # Domain-specific recommendations
    if material_type == 'scientific':
        recommendations.append({
            "model": "allenai/scibert_scivocab_uncased",
            "score": 0.85,
            "reason": "Optimized for scientific texts",
            "characteristics": {
                "period": "Modern",
                "training_data": "Scientific papers",
                "size_mb": 440,
                "context_length": 512
            }
        })

    # Always include a fast fallback
    recommendations.append({
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "score": 0.6,
        "reason": "Fast, lightweight, general-purpose",
        "characteristics": {
            "period": "General",
            "training_data": "Mixed texts",
            "size_mb": 80,
            "context_length": 512
        }
    })

    # Sort by score
    recommendations.sort(key=lambda x: x['score'], reverse=True)

    return JSONResponse({
        "recommendations": recommendations[:5],  # Return top 5
        "primary_recommendation": recommendations[0],
        "metadata_used": {
            "time_period": f"{time_from}-{time_to}" if time_from else "Not specified",
            "material_type": material_type
        }
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


@router.post("/build")
async def build_corpus(
    background_tasks: BackgroundTasks,
    build_request: BuildRequest
):
    """
    Start building a corpus vector store in the background.
    """
    try:
        # Parse configuration
        config = CorpusConfig(**build_request.config)
        config.processing_mode = build_request.mode

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

        # Start build in background
        background_tasks.add_task(
            _build_corpus_task,
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
        while True:
            current_progress = wizard_state['build_progress'].get(build_id)
            if not current_progress:
                break

            # Send update if changed
            if current_progress != last_update:
                yield f"data: {json.dumps(current_progress)}\n\n"
                last_update = current_progress.copy()

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


@router.post("/activate/{corpus_name}")
async def activate_corpus(
    corpus_name: str,
    backup: bool = Query(True, description="Backup current corpus")
):
    """
    Activate a newly built corpus.
    """
    try:
        # Path to new corpus
        new_corpus_path = Path("create/output")
        target_path = Path("backend/targets")

        if not new_corpus_path.exists():
            raise HTTPException(status_code=404, detail="New corpus not found")

        # Backup current corpus if requested
        if backup and target_path.exists():
            backup_path = Path(f"backend/targets.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            shutil.move(str(target_path), str(backup_path))
            logger.info(f"Backed up current corpus to {backup_path}")

        # Move new corpus to active location
        shutil.move(str(new_corpus_path), str(target_path))
        logger.info(f"Activated new corpus: {corpus_name}")

        # Clear wizard state
        wizard_state['enabled'] = False

        return JSONResponse({
            "status": "activated",
            "corpus": corpus_name,
            "message": "Corpus activated successfully. Please restart the server."
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
    try:
        # Import the corpus builder
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent.parent))
        from create.create_corpus_store import UniversalCorpusBuilder

        # Update status
        wizard_state['build_progress'][build_id]['status'] = 'building'

        # Create progress callback
        async def progress_callback(progress_data):
            """Update wizard state with progress."""
            wizard_state['build_progress'][build_id].update(progress_data)

        # Initialize builder
        mode = wizard_state['build_progress'][build_id].get('mode', 'cpu')
        builder = UniversalCorpusBuilder(config, mode)

        # Build corpus
        results = await builder.build(progress_callback)

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
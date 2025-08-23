#!/usr/bin/env python3
"""
Background Worker for Async LLM Processing

This worker process runs continuously, consuming LLM requests from the Redis queue
and processing them in the background. It can be run as a separate process or
integrated into the main application.
"""

import asyncio
import sys
import os
import signal
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables early and strictly
def _load_env_file(env_file: Path, override: bool = True) -> None:
    """Minimal .env loader to avoid external dependency."""
    try:
        with env_file.open("r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export "):]
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if override or key not in os.environ:
                    os.environ[key] = value
    except Exception as e:
        raise RuntimeError(f"Failed to load environment file {env_file}: {e}")

# Require ENVIRONMENT and load matching env file
env_name = os.getenv("ENVIRONMENT")
if not env_name:
    raise EnvironmentError("ENVIRONMENT must be set (e.g., 'development', 'staging', 'production') in your .env file")

env_path = project_root / "config" / f".env.{env_name.lower()}"
if not env_path.exists():
    raise FileNotFoundError(f"Cannot find environment file: {env_path}. Deployment is misconfigured.")

_load_env_file(env_path, override=True)

# Import after env is loaded
from backend.services.queue_manager import get_queue_manager
from backend.services.llm_service import process_query_async

class LLMWorker:
    """Background worker for processing LLM requests"""
    
    def __init__(self, worker_id: str = "worker-1"):
        self.worker_id = worker_id
        self.queue_manager = get_queue_manager()
        self.running = False
        self.processed_count = 0
        
    async def start(self):
        """Start the worker loop"""
        self.running = True
        
        while self.running:
            try:
                # Get next request from queue (blocks for 1 second)
                request = await self.queue_manager.get_next_request(timeout=1)
                
                if not request:
                    # No request available, continue loop
                    await asyncio.sleep(0.1)
                    continue
                
                await self.process_request(request)
                self.processed_count += 1
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                await asyncio.sleep(1)  # Brief pause before continuing
        
    
    async def process_request(self, request):
        """Process a single LLM request"""
        try:
            # Update status to processing
            await self.queue_manager.update_request_status(
                request.request_id, 
                "processing"
            )
            
            # Process the LLM query
            start_time = time.time()
            result = await process_query_async(request.query)
            processing_time = time.time() - start_time
            
            # Add metadata to result
            result_with_metadata = {
                **result,
                "processing_time": processing_time,
                "worker_id": self.worker_id,
                "processed_at": time.time()
            }
            
            # Update status to completed with result
            await self.queue_manager.update_request_status(
                request.request_id,
                "completed",
                result_with_metadata
            )
            
            
        except Exception as e:
            
            # Update status to failed with error
            await self.queue_manager.update_request_status(
                request.request_id,
                "failed",
                {"error": str(e), "worker_id": self.worker_id}
            )
    
    def stop(self):
        """Stop the worker"""
        self.running = False

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global worker
    if worker:
        worker.stop()

async def main():
    """Main worker function"""
    global worker
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start worker
    worker_id = os.getenv("WORKER_ID", f"worker-{os.getpid()}")
    worker = LLMWorker(worker_id)
    
    try:
        await worker.start()
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    # Global worker instance for signal handling
    worker = None
    
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
    except Exception as e:
        sys.exit(1) 
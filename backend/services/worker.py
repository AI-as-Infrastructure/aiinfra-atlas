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

# Import after path setup
from backend.services.queue_manager import get_queue_manager
from backend.services.llm_service import process_query_async
import backend.load_env  # Load environment variables

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
        print(f"🚀 Starting LLM worker {self.worker_id}")
        
        while self.running:
            try:
                # Get next request from queue (blocks for 1 second)
                request = await self.queue_manager.get_next_request(timeout=1)
                
                if not request:
                    # No request available, continue loop
                    await asyncio.sleep(0.1)
                    continue
                
                print(f"🔄 Processing request {request.request_id}")
                await self.process_request(request)
                self.processed_count += 1
                
            except KeyboardInterrupt:
                print(f"\n⏹️ Worker {self.worker_id} received shutdown signal")
                break
            except Exception as e:
                print(f"❌ Worker {self.worker_id} error: {e}")
                await asyncio.sleep(1)  # Brief pause before continuing
        
        print(f"✅ Worker {self.worker_id} stopped. Processed {self.processed_count} requests")
    
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
            
            print(f"✅ Completed request {request.request_id} in {processing_time:.2f}s")
            
        except Exception as e:
            print(f"❌ Failed to process request {request.request_id}: {e}")
            
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
    print(f"\n📡 Received signal {signum}")
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
        print(f"❌ Worker failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Global worker instance for signal handling
    worker = None
    
    print("🔧 Starting Atlas LLM Background Worker")
    print(f"📁 Project root: {project_root}")
    print(f"🐍 Python path: {sys.path[0]}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Worker shutdown complete")
    except Exception as e:
        print(f"❌ Worker startup failed: {e}")
        sys.exit(1) 
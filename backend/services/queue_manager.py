"""
Queue Manager for Async LLM Request Processing

This module handles Redis-based queuing for LLM requests, allowing the API
to respond immediately while processing happens in the background.
"""

import redis
import json
import os
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel

class QueuedRequest(BaseModel):
    """Model for queued LLM requests"""
    request_id: str
    query: Dict[str, Any]
    user_id: Optional[str] = None
    created_at: str
    status: str = "queued"

class QueueManager:
    """Manages Redis-based async LLM request queuing"""
    
    def __init__(self):
        # Get Redis connection details from environment
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_password = os.getenv("REDIS_PASSWORD", "")
        
        if redis_password and ":" not in redis_url.split("//")[1]:
            # Add password to URL if not already present
            redis_url = redis_url.replace("://", f"://:{redis_password}@")
        
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.request_queue = "llm_request_queue"
        self.request_prefix = "request:"
        self.result_prefix = "result:"
        
        # Test connection
        try:
            self.redis_client.ping()
            print("✅ Redis connection established")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            raise
    
    async def queue_request(self, query_data: Dict[str, Any], user_id: Optional[str] = None) -> str:
        """Queue an LLM request and return request ID"""
        request_id = str(uuid.uuid4())
        
        request = QueuedRequest(
            request_id=request_id,
            query=query_data,
            user_id=user_id,
            created_at=datetime.now().isoformat(),
            status="queued"
        )
        
        # Store request metadata
        self.redis_client.hmset(f"{self.request_prefix}{request_id}", {
            "status": request.status,
            "created_at": request.created_at,
            "user_id": user_id or "",
            "query": json.dumps(query_data)
        })
        
        # Set TTL for request (1 hour)
        self.redis_client.expire(f"{self.request_prefix}{request_id}", 3600)
        
        # Add to processing queue
        self.redis_client.lpush(self.request_queue, request_id)
        
        print(f"📝 Queued request {request_id}")
        return request_id
    
    async def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """Get current status and result of a request"""
        if not self.redis_client.exists(f"{self.request_prefix}{request_id}"):
            return {"status": "not_found", "error": "Request not found or expired"}
        
        # Get request metadata
        request_data = self.redis_client.hgetall(f"{self.request_prefix}{request_id}")
        status = request_data.get("status", "unknown")
        
        response = {
            "request_id": request_id,
            "status": status,
            "created_at": request_data.get("created_at"),
            "user_id": request_data.get("user_id")
        }
        
        # If completed, get the result
        if status == "completed":
            result_data = self.redis_client.get(f"{self.result_prefix}{request_id}")
            if result_data:
                response["result"] = json.loads(result_data)
        elif status == "failed":
            error_data = self.redis_client.get(f"{self.result_prefix}{request_id}")
            if error_data:
                response["error"] = json.loads(error_data)
        
        return response
    
    async def update_request_status(self, request_id: str, status: str, result: Any = None):
        """Update request status and store result if provided"""
        if not self.redis_client.exists(f"{self.request_prefix}{request_id}"):
            print(f"⚠️ Request {request_id} not found for status update")
            return
        
        # Update status
        self.redis_client.hset(f"{self.request_prefix}{request_id}", "status", status)
        
        # Store result if provided
        if result is not None:
            self.redis_client.set(
                f"{self.result_prefix}{request_id}", 
                json.dumps(result),
                ex=3600  # 1 hour TTL
            )
        
        print(f"📊 Updated request {request_id} status to {status}")
    
    async def get_next_request(self, timeout: int = 1) -> Optional[QueuedRequest]:
        """Get the next request from the queue (blocking)"""
        try:
            # Block for up to timeout seconds waiting for a request
            result = self.redis_client.brpop(self.request_queue, timeout)
            
            if not result:
                return None
            
            _, request_id = result
            
            # Get request data
            request_data = self.redis_client.hgetall(f"{self.request_prefix}{request_id}")
            if not request_data:
                print(f"⚠️ Request data not found for {request_id}")
                return None
            
            return QueuedRequest(
                request_id=request_id,
                query=json.loads(request_data["query"]),
                user_id=request_data.get("user_id") or None,
                created_at=request_data["created_at"],
                status=request_data["status"]
            )
            
        except Exception as e:
            print(f"❌ Error getting next request: {e}")
            return None
    
    async def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        queue_length = self.redis_client.llen(self.request_queue)
        
        # Count requests by status
        request_keys = self.redis_client.keys(f"{self.request_prefix}*")
        status_counts = {"queued": 0, "processing": 0, "completed": 0, "failed": 0}
        
        for key in request_keys:
            status = self.redis_client.hget(key, "status")
            if status in status_counts:
                status_counts[status] += 1
        
        return {
            "queue_length": queue_length,
            **status_counts
        }

# Global queue manager instance
queue_manager = None

def get_queue_manager() -> QueueManager:
    """Get or create the global queue manager instance"""
    global queue_manager
    if queue_manager is None:
        queue_manager = QueueManager()
    return queue_manager 
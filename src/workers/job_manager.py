"""
Simple Background Job Manager for Render Free Tier
==================================================
Uses in-memory storage with threading for async tasks.
For production, consider Redis + Celery/RQ.
"""

import uuid
import threading
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum


class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SimpleJobManager:
    """Simple in-memory job manager for background tasks"""
    
    def __init__(self, max_jobs: int = 100, job_ttl_hours: int = 24):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.max_jobs = max_jobs
        self.job_ttl = timedelta(hours=job_ttl_hours)
    
    def create_job(self, job_type: str, data: Dict[str, Any]) -> str:
        """Create a new job and return job_id"""
        job_id = str(uuid.uuid4())
        
        with self.lock:
            # Clean up old jobs if we're at capacity
            if len(self.jobs) >= self.max_jobs:
                self._cleanup_old_jobs()
            
            self.jobs[job_id] = {
                "job_id": job_id,
                "job_type": job_type,
                "status": JobStatus.PENDING.value,
                "data": data,
                "result": None,
                "error": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "started_at": None,
                "completed_at": None,
            }
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and result"""
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                # Return a copy to avoid race conditions
                return job.copy()
            return None
    
    def update_job(self, job_id: str, **updates):
        """Update job status/result"""
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].update(updates)
                self.jobs[job_id]["updated_at"] = datetime.now()
    
    def start_job(self, job_id: str, worker_func: Callable):
        """Start processing a job in background thread"""
        def worker():
            try:
                self.update_job(job_id, 
                    status=JobStatus.PROCESSING.value,
                    started_at=datetime.now()
                )
                
                # Get job data
                job = self.get_job(job_id)
                if not job:
                    return
                
                # Run the worker function
                result = worker_func(job["data"])
                
                # Store result
                self.update_job(job_id,
                    status=JobStatus.COMPLETED.value,
                    result=result,
                    completed_at=datetime.now()
                )
            except Exception as e:
                self.update_job(job_id,
                    status=JobStatus.FAILED.value,
                    error=str(e),
                    completed_at=datetime.now()
                )
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread
    
    def _cleanup_old_jobs(self):
        """Remove old completed/failed jobs"""
        now = datetime.now()
        to_remove = []
        
        for job_id, job in self.jobs.items():
            if job["status"] in [JobStatus.COMPLETED.value, JobStatus.FAILED.value]:
                age = now - job["updated_at"]
                if age > self.job_ttl:
                    to_remove.append(job_id)
        
        for job_id in to_remove:
            del self.jobs[job_id]


# Global job manager instance
_job_manager = None

def get_job_manager() -> SimpleJobManager:
    """Get or create global job manager instance"""
    global _job_manager
    if _job_manager is None:
        _job_manager = SimpleJobManager()
    return _job_manager


"""
Feedback Loop Scheduler

Orchestrates the pattern extraction and synchronization process.
Runs on different schedules based on pattern type importance.
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import structlog
from google.cloud import scheduler_v1
from google.cloud import tasks_v2
import os

from src.services.pattern_extractor import pattern_extractor, PatternType
from src.services.pattern_synchronizer import pattern_synchronizer

logger = structlog.get_logger()


class FeedbackLoopScheduler:
    """Manages scheduled pattern extraction and sync jobs"""
    
    def __init__(self, project_id: str = "leafloafai", location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        
        # Initialize Cloud Scheduler client
        self.scheduler_client = scheduler_v1.CloudSchedulerClient()
        self.parent = f"projects/{project_id}/locations/{location}"
        
        # Job configurations
        self.job_configs = {
            "hourly_patterns": {
                "schedule": "0 * * * *",  # Every hour
                "pattern_types": [PatternType.PREFERENCE, PatternType.SESSION],
                "description": "Extract user preferences and session patterns"
            },
            "six_hour_patterns": {
                "schedule": "0 */6 * * *",  # Every 6 hours
                "pattern_types": [PatternType.REORDER],
                "description": "Extract reorder patterns"
            },
            "daily_patterns": {
                "schedule": "0 2 * * *",  # 2 AM daily
                "pattern_types": [PatternType.ASSOCIATION, PatternType.BEHAVIOR],
                "description": "Extract product associations and behavior patterns"
            }
        }
        
        # Track last run times
        self.last_run_times = {}
    
    async def setup_scheduled_jobs(self):
        """Create Cloud Scheduler jobs for pattern extraction"""
        
        for job_name, config in self.job_configs.items():
            try:
                job_path = f"{self.parent}/jobs/{job_name}"
                
                # Create HTTP target
                http_target = scheduler_v1.HttpTarget(
                    uri=f"https://leafloaf-v2srnrkkhq-uc.a.run.app/internal/extract-patterns",
                    http_method=scheduler_v1.HttpMethod.POST,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {os.getenv('SERVICE_ACCOUNT_TOKEN', '')}"
                    },
                    body=self._create_job_body(config["pattern_types"]).encode()
                )
                
                # Create job
                job = scheduler_v1.Job(
                    name=job_path,
                    description=config["description"],
                    schedule=config["schedule"],
                    time_zone="UTC",
                    http_target=http_target,
                    retry_config=scheduler_v1.RetryConfig(
                        retry_count=3,
                        min_backoff_duration={"seconds": 60}
                    )
                )
                
                # Try to create or update the job
                try:
                    self.scheduler_client.create_job(
                        parent=self.parent,
                        job=job
                    )
                    logger.info(f"Created scheduled job: {job_name}")
                except Exception as e:
                    if "already exists" in str(e):
                        # Update existing job
                        self.scheduler_client.update_job(job=job)
                        logger.info(f"Updated scheduled job: {job_name}")
                    else:
                        raise
                        
            except Exception as e:
                logger.error(f"Failed to setup job {job_name}: {e}")
    
    def _create_job_body(self, pattern_types: List[PatternType]) -> str:
        """Create JSON body for scheduled job"""
        import json
        
        return json.dumps({
            "pattern_types": [pt.value for pt in pattern_types],
            "source": "scheduled_job"
        })
    
    async def run_pattern_extraction(self, pattern_types: List[PatternType], 
                                   user_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run pattern extraction and sync process"""
        
        start_time = datetime.utcnow()
        results = {
            "start_time": start_time.isoformat(),
            "pattern_types": [pt.value for pt in pattern_types],
            "extraction_results": {},
            "sync_results": {},
            "errors": []
        }
        
        try:
            # 1. Extract patterns
            logger.info(f"Starting pattern extraction for types: {[pt.value for pt in pattern_types]}")
            
            # Determine since parameter based on pattern type
            since = self._get_since_timestamp(pattern_types[0] if pattern_types else None)
            
            # Extract patterns
            patterns = await pattern_extractor.extract_all_patterns(
                user_ids=user_ids,
                since=since
            )
            
            results["extraction_results"] = {
                "total_patterns": len(patterns),
                "by_type": self._count_patterns_by_type(patterns)
            }
            
            # 2. Filter patterns for sync
            filtered_patterns = pattern_extractor.filter_patterns_for_sync(patterns)
            
            # 3. Sync to Graphiti
            logger.info(f"Syncing {len(filtered_patterns)} patterns to Graphiti")
            
            sync_result = await pattern_synchronizer.sync_patterns(filtered_patterns)
            
            results["sync_results"] = {
                "total_patterns": sync_result.total_patterns,
                "synced": sync_result.synced_count,
                "updated": sync_result.updated_count,
                "failed": sync_result.failed_count,
                "duration_ms": sync_result.duration_ms
            }
            
            # 4. Update last run time
            for pt in pattern_types:
                self.last_run_times[pt.value] = datetime.utcnow()
            
            # 5. Calculate total duration
            results["duration_ms"] = (datetime.utcnow() - start_time).total_seconds() * 1000
            results["success"] = True
            
            logger.info(
                "Pattern extraction and sync completed",
                extracted=len(patterns),
                synced=sync_result.synced_count,
                duration_ms=results["duration_ms"]
            )
            
        except Exception as e:
            logger.error(f"Pattern extraction failed: {e}")
            results["errors"].append(str(e))
            results["success"] = False
        
        return results
    
    def _get_since_timestamp(self, pattern_type: Optional[PatternType]) -> Optional[datetime]:
        """Get the appropriate since timestamp based on pattern type"""
        
        if not pattern_type:
            return None
        
        # Different lookback periods for different patterns
        lookback_hours = {
            PatternType.SESSION: 4,  # Only recent sessions
            PatternType.PREFERENCE: 24,  # Last day
            PatternType.REORDER: 24 * 7,  # Last week
            PatternType.ASSOCIATION: 24 * 30,  # Last month
            PatternType.BEHAVIOR: 24 * 30  # Last month
        }
        
        hours = lookback_hours.get(pattern_type, 24)
        return datetime.utcnow() - timedelta(hours=hours)
    
    def _count_patterns_by_type(self, patterns: List[Any]) -> Dict[str, int]:
        """Count patterns by type"""
        counts = {}
        
        for pattern in patterns:
            pt = pattern.pattern_type.value
            counts[pt] = counts.get(pt, 0) + 1
        
        return counts
    
    async def run_immediate_extraction(self, user_id: str, 
                                     pattern_types: Optional[List[PatternType]] = None):
        """Run immediate pattern extraction for a specific user"""
        
        if not pattern_types:
            # Extract all pattern types for immediate feedback
            pattern_types = [
                PatternType.PREFERENCE,
                PatternType.SESSION,
                PatternType.REORDER
            ]
        
        logger.info(f"Running immediate extraction for user {user_id}")
        
        return await self.run_pattern_extraction(
            pattern_types=pattern_types,
            user_ids=[user_id]
        )
    
    async def cleanup_old_patterns(self, days: int = 90):
        """Cleanup patterns older than specified days"""
        
        try:
            logger.info(f"Starting cleanup of patterns older than {days} days")
            
            # Run cleanup in pattern synchronizer
            await pattern_synchronizer.cleanup_stale_patterns(older_than_days=days)
            
            logger.info("Pattern cleanup completed")
            
        except Exception as e:
            logger.error(f"Pattern cleanup failed: {e}")
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        
        status = {
            "jobs": {},
            "last_run_times": self.last_run_times,
            "next_runs": {}
        }
        
        # Get job status from Cloud Scheduler
        try:
            jobs = self.scheduler_client.list_jobs(parent=self.parent)
            
            for job in jobs:
                job_name = job.name.split("/")[-1]
                if job_name in self.job_configs:
                    status["jobs"][job_name] = {
                        "state": job.state.name,
                        "schedule": job.schedule,
                        "last_attempt_time": job.last_attempt_time.isoformat() if job.last_attempt_time else None,
                        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
                    }
                    
                    if job.next_run_time:
                        status["next_runs"][job_name] = job.next_run_time.isoformat()
        
        except Exception as e:
            logger.error(f"Failed to get scheduler status: {e}")
            status["error"] = str(e)
        
        return status


# Global instance
feedback_loop_scheduler = FeedbackLoopScheduler()


# Cloud Function entry point for scheduled jobs
async def extract_patterns_handler(request):
    """HTTP handler for scheduled pattern extraction"""
    
    try:
        # Parse request
        data = request.get_json()
        pattern_type_names = data.get("pattern_types", [])
        
        # Convert to PatternType enums
        pattern_types = []
        for name in pattern_type_names:
            try:
                pattern_types.append(PatternType(name))
            except ValueError:
                logger.error(f"Invalid pattern type: {name}")
        
        if not pattern_types:
            return {"error": "No valid pattern types specified"}, 400
        
        # Run extraction
        result = await feedback_loop_scheduler.run_pattern_extraction(pattern_types)
        
        return result, 200
        
    except Exception as e:
        logger.error(f"Pattern extraction handler failed: {e}")
        return {"error": str(e)}, 500
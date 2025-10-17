"""
Scheduler for periodic learning cycles and automated system improvement.

This module implements:
1. Daily learning cycles at 2 AM
2. Feedback-count-based triggers (every 100 feedback items)
3. Manual trigger support
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import asyncio
from typing import Optional
import logging

from app.feedback import FeedbackManager, FeedbackLearningPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LearningCycleScheduler:
    """Manages automated learning cycle execution."""
    
    def __init__(self):
        """Initialize scheduler with AsyncIO support."""
        self.scheduler = AsyncIOScheduler()
        self.feedback_manager = FeedbackManager()
        self.learning_pipeline = FeedbackLearningPipeline()
        self.is_running = False
        self._last_cycle_time: Optional[datetime] = None
        
    def start(self):
        """Start the scheduler with all configured jobs."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        # Job 1: Daily learning cycle at 2 AM
        self.scheduler.add_job(
            self._run_daily_learning_cycle,
            CronTrigger(hour=2, minute=0),
            id='daily_learning_cycle',
            name='Daily Learning Cycle at 2 AM',
            replace_existing=True
        )
        logger.info("✅ Scheduled daily learning cycle at 2 AM")
        
        # Job 2: Check feedback count every hour for 100-feedback trigger
        self.scheduler.add_job(
            self._check_feedback_count_trigger,
            IntervalTrigger(hours=1),
            id='feedback_count_check',
            name='Check feedback count every hour',
            replace_existing=True
        )
        logger.info("✅ Scheduled hourly feedback count check")
        
        # Job 3: Periodic health check every 6 hours
        self.scheduler.add_job(
            self._health_check,
            IntervalTrigger(hours=6),
            id='scheduler_health_check',
            name='Scheduler health check',
            replace_existing=True
        )
        logger.info("✅ Scheduled health check every 6 hours")
        
        self.scheduler.start()
        self.is_running = True
        logger.info("🚀 Learning Cycle Scheduler started successfully")
    
    def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            return
        
        self.scheduler.shutdown(wait=False)
        self.is_running = False
        logger.info("⏹️  Learning Cycle Scheduler stopped")
    
    async def _run_daily_learning_cycle(self):
        """Execute daily learning cycle at 2 AM."""
        logger.info("⏰ [DAILY LEARNING CYCLE] Starting scheduled cycle at 2 AM")
        try:
            # Create new DSPy context for this async task
            import dspy
            from app.config import settings
            
            # Setup DSPy context for this scheduler job
            try:
                lm = dspy.LM(
                    model=f"openai/{settings.llm_model}",
                    api_key=settings.github_token,
                    api_base=settings.github_api_base
                )
                with dspy.context(lm=lm):
                    result = await self.learning_pipeline.run_learning_cycle()
            except Exception as dspy_error:
                # If DSPy context fails, try without it
                logger.warning(f"DSPy context setup failed: {dspy_error}")
                result = await self.learning_pipeline.run_learning_cycle()
            
            self._last_cycle_time = datetime.utcnow()
            
            logger.info(f"✅ [DAILY LEARNING CYCLE] Completed successfully")
            logger.info(f"   - Feedback stats: {result.get('feedback_stats', {})}")
            logger.info(f"   - Suggestions: {result.get('suggestions_count', 0)}")
            logger.info(f"   - Optimization: {result.get('optimization_result', {}).get('success', False)}")
            
            # Store cycle result in database
            await self._store_cycle_result(result, trigger_type='daily_scheduled')
            
        except Exception as e:
            logger.error(f"❌ [DAILY LEARNING CYCLE] Failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def _check_feedback_count_trigger(self):
        """Check if learning cycle should be triggered based on feedback count."""
        try:
            should_trigger = await self.feedback_manager.should_trigger_learning_cycle()
            
            if should_trigger:
                logger.info("📊 [FEEDBACK COUNT TRIGGER] 100+ feedback items collected since last cycle")
                logger.info("🔄 [FEEDBACK COUNT TRIGGER] Starting learning cycle...")
                
                # Create new DSPy context for this async task
                import dspy
                from app.config import settings
                
                # Setup DSPy context for this scheduler job
                try:
                    lm = dspy.LM(
                        model=f"openai/{settings.llm_model}",
                        api_key=settings.github_token,
                        api_base=settings.github_api_base
                    )
                    with dspy.context(lm=lm):
                        result = await self.learning_pipeline.run_learning_cycle()
                except Exception as dspy_error:
                    # If DSPy context fails, try without it
                    logger.warning(f"DSPy context setup failed: {dspy_error}")
                    result = await self.learning_pipeline.run_learning_cycle()
                
                self._last_cycle_time = datetime.utcnow()
                
                logger.info(f"✅ [FEEDBACK COUNT TRIGGER] Completed successfully")
                
                # Store cycle result
                await self._store_cycle_result(result, trigger_type='feedback_count_100')
            else:
                count = await self.feedback_manager.get_feedback_count_since_last_cycle()
                logger.debug(f"📊 Feedback count check: {count}/100 (no trigger)")
                
        except Exception as e:
            logger.error(f"❌ [FEEDBACK COUNT TRIGGER] Failed: {e}")
    
    async def _health_check(self):
        """Periodic health check for scheduler."""
        logger.info("🏥 [HEALTH CHECK] Scheduler is running")
        logger.info(f"   - Last cycle: {self._last_cycle_time or 'Never'}")
        logger.info(f"   - Active jobs: {len(self.scheduler.get_jobs())}")
        
        try:
            # Check feedback count
            count = await self.feedback_manager.get_feedback_count_since_last_cycle()
            logger.info(f"   - Feedback since last cycle: {count}")
            
            # Check feedback stats
            stats = await self.feedback_manager.get_feedback_stats()
            logger.info(f"   - Total feedback: {stats.get('total_feedback', 0)}")
            logger.info(f"   - Average rating: {stats.get('average_rating', 0):.2f}")
            
        except Exception as e:
            logger.warning(f"⚠️  Health check warning: {e}")
    
    async def trigger_manual_cycle(self) -> dict:
        """Manually trigger a learning cycle (called by API)."""
        logger.info("🔧 [MANUAL TRIGGER] Learning cycle triggered manually")
        
        try:
            # Create new DSPy context for this async task
            import dspy
            from app.config import settings
            
            # Setup DSPy context for this scheduler job
            try:
                lm = dspy.LM(
                    model=f"openai/{settings.llm_model}",
                    api_key=settings.github_token,
                    api_base=settings.github_api_base
                )
                with dspy.context(lm=lm):
                    result = await self.learning_pipeline.run_learning_cycle()
            except Exception as dspy_error:
                # If DSPy context fails, try without it
                logger.warning(f"DSPy context setup failed: {dspy_error}")
                result = await self.learning_pipeline.run_learning_cycle()
            
            self._last_cycle_time = datetime.utcnow()
            
            logger.info(f"✅ [MANUAL TRIGGER] Completed successfully")
            
            # Store cycle result
            await self._store_cycle_result(result, trigger_type='manual')
            
            return {
                'success': True,
                'message': 'Learning cycle completed successfully',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"❌ [MANUAL TRIGGER] Failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _store_cycle_result(self, result: dict, trigger_type: str):
        """Store learning cycle results in database for tracking."""
        try:
            from supabase import create_client
            from app.config import settings
            
            supabase = create_client(settings.supabase_url, settings.supabase_key)
            
            cycle_data = {
                'trigger_type': trigger_type,
                'completed_at': datetime.utcnow().isoformat(),
                'feedback_count': result.get('feedback_stats', {}).get('total_feedback', 0),
                'average_rating': result.get('feedback_stats', {}).get('average_rating', 0.0),
                'accuracy_rate': result.get('feedback_stats', {}).get('accuracy_rate', 0.0),
                'suggestions_count': result.get('suggestions_count', 0),
                'optimization_success': result.get('optimization_result', {}).get('success', False),
                'optimization_score': result.get('optimization_result', {}).get('optimization_score', 0.0),
                'training_examples': result.get('optimization_result', {}).get('examples_used', 0),
                'metadata': {
                    'feedback_by_rating': result.get('feedback_stats', {}).get('feedback_by_rating', {}),
                    'optimization_details': result.get('optimization_result', {})
                }
            }
            
            supabase.table('learning_cycles').insert(cycle_data).execute()
            logger.info(f"💾 Stored learning cycle result in database")
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to store cycle result: {e}")
    
    def get_status(self) -> dict:
        """Get current scheduler status."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            })
        
        return {
            'is_running': self.is_running,
            'last_cycle': self._last_cycle_time.isoformat() if self._last_cycle_time else None,
            'active_jobs': jobs
        }


# Global scheduler instance
_scheduler_instance: Optional[LearningCycleScheduler] = None


def get_scheduler() -> LearningCycleScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = LearningCycleScheduler()
    return _scheduler_instance


def start_scheduler():
    """Start the global scheduler instance."""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """Stop the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop()
        _scheduler_instance = None

"""FastAPI Main Application for Math Agent."""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uvicorn

from app.config import settings
from app.agents import MathRoutingAgent
from app.feedback import FeedbackManager, FeedbackLearningPipeline
from app.vectorstore import SupabaseVectorStore
from app.scheduler import get_scheduler, start_scheduler, stop_scheduler

# Initialize FastAPI app
app = FastAPI(
    title="Math Agent API",
    description="Agentic RAG system for mathematical question answering with human-in-the-loop feedback",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
math_agent = MathRoutingAgent()
feedback_manager = FeedbackManager()
learning_pipeline = FeedbackLearningPipeline()
vector_store = SupabaseVectorStore()


# Startup and Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Initialize scheduler and services on startup."""
    print("🚀 Starting Math Agent API...")
    print("📅 Initializing Learning Cycle Scheduler...")
    try:
        start_scheduler()
        print("✅ Scheduler started successfully")
    except Exception as e:
        print(f"⚠️  Warning: Scheduler failed to start: {e}")
        print("   The API will continue without automated learning cycles")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("⏹️  Shutting down Math Agent API...")
    try:
        stop_scheduler()
        print("✅ Scheduler stopped")
    except Exception as e:
        print(f"⚠️  Warning during shutdown: {e}")


# Pydantic models
class QuestionRequest(BaseModel):
    """Request model for asking a question."""
    question: str = Field(..., min_length=5, max_length=500, description="Mathematical question")
    user_id: Optional[str] = Field(None, description="Optional user identifier")


class QuestionResponse(BaseModel):
    """Response model for question answers."""
    success: bool
    question: str
    answer: str
    solution_steps: List[Dict[str, Any]]
    confidence_score: float
    sources: List[str]
    routing_decision: str
    topic: str
    mcp_used: bool = False
    session_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FeedbackRequest(BaseModel):
    """Request model for submitting feedback."""
    question: str
    answer: str
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    user_feedback: Optional[str] = None
    corrections: Optional[Dict[str, Any]] = None
    is_correct: Optional[bool] = None
    session_id: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Response model for feedback submission."""
    success: bool
    message: str
    feedback_id: Optional[int] = None


class KnowledgeBaseDocument(BaseModel):
    """Model for adding documents to knowledge base."""
    question: str
    answer: str
    solution_steps: Optional[Dict[str, Any]] = None
    topic: str = "general"
    difficulty: str = "medium"
    source: str = "manual"
    metadata: Optional[Dict[str, Any]] = None


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Math Agent API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "ask_question": "/api/v1/ask",
            "submit_feedback": "/api/v1/feedback",
            "get_stats": "/api/v1/stats",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.post("/api/v1/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a mathematical question and get a step-by-step solution.
    
    The system will:
    1. Validate the question through input guardrails
    2. Route to either knowledge base or web search
    3. Generate a detailed step-by-step solution
    4. Validate the output through output guardrails
    """
    try:
        print(f"[DEBUG] Received question: {request.question}")
        
        # Process question through the routing agent
        result = await math_agent.process_question(request.question)
        
        print(f"[DEBUG] Agent result: success={result.get('success')}, error={result.get('error')}")
        
        if not result.get("success", False):
            error_msg = result.get("error", "Processing failed")
            print(f"[DEBUG] Raising HTTPException with error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        return QuestionResponse(
            success=True,
            question=result["question"],
            answer=result["answer"],
            solution_steps=result.get("solution_steps", []),
            confidence_score=result.get("confidence_score", 0.0),
            sources=result.get("sources", []),
            routing_decision=result.get("routing_decision", "unknown"),
            topic=result.get("topic", "general"),
            mcp_used=result.get("mcp_used", False),
            error=result.get("error")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEBUG] Exception caught: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest, background_tasks: BackgroundTasks):
    """
    Submit feedback for a generated answer.
    
    This feedback is used for:
    1. Improving the system through learning
    2. Identifying problematic responses
    3. Updating the knowledge base
    4. Optimizing prompts with DSPy
    """
    try:
        result = await feedback_manager.submit_feedback(
            question=request.question,
            generated_answer=request.answer,
            rating=request.rating,
            user_feedback=request.user_feedback,
            corrections=request.corrections,
            is_correct=request.is_correct
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Feedback submission failed"))
        
        # Check if we should trigger learning cycle based on feedback count
        should_trigger = await feedback_manager.should_trigger_learning_cycle()
        if should_trigger:
            print("📊 [FEEDBACK TRIGGER] 100+ feedback items collected, triggering learning cycle...")
            scheduler = get_scheduler()
            background_tasks.add_task(scheduler.trigger_manual_cycle)
        
        return FeedbackResponse(
            success=True,
            message="Feedback submitted successfully. Thank you for helping improve the system!",
            feedback_id=result.get("feedback_id")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/stats")
async def get_statistics():
    """
    Get system statistics including:
    - Feedback statistics
    - Knowledge base statistics
    - System performance metrics
    """
    try:
        feedback_stats = await feedback_manager.get_feedback_stats()
        kb_stats = await vector_store.get_statistics()
        
        return {
            "success": True,
            "feedback_stats": feedback_stats,
            "knowledge_base_stats": kb_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/feedback/suggestions")
async def get_improvement_suggestions():
    """
    Get suggestions for system improvement based on user feedback.
    
    Returns problematic questions and recommended actions.
    """
    try:
        suggestions = await feedback_manager.get_improvement_suggestions()
        
        return {
            "success": True,
            "suggestions": suggestions,
            "count": len(suggestions),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/feedback/all")
async def get_all_feedback(limit: int = 100, offset: int = 0):
    """
    Get all feedback entries from the database.
    
    Returns feedback with pagination support.
    """
    try:
        from app.config import settings
        from supabase import create_client
        
        supabase = create_client(settings.supabase_url, settings.supabase_key)
        
        # Get total count
        count_result = supabase.table('feedback').select('id', count='exact').execute()
        total_count = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
        
        # Get paginated feedback
        result = supabase.table('feedback')\
            .select('*')\
            .order('created_at', desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        return {
            "success": True,
            "feedback": result.data,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/learning/cycle")
async def trigger_learning_cycle_endpoint(background_tasks: BackgroundTasks):
    """
    Manually trigger a learning cycle.
    
    This will:
    1. Analyze recent feedback
    2. Optimize prompts using DSPy
    3. Update knowledge base with corrections
    """
    try:
        scheduler = get_scheduler()
        result = await scheduler.trigger_manual_cycle()
        
        return {
            "success": result['success'],
            "message": result.get('message', ''),
            "result": result.get('result', {}),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/learning/status")
async def get_learning_status():
    """
    Get the status of the learning cycle scheduler.
    
    Returns:
    - Scheduler status (running/stopped)
    - Last cycle execution time
    - Next scheduled cycles
    - Active jobs
    """
    try:
        scheduler = get_scheduler()
        status = scheduler.get_status()
        
        # Get feedback count
        count = await feedback_manager.get_feedback_count_since_last_cycle()
        
        return {
            "success": True,
            "scheduler": status,
            "feedback_count_since_last_cycle": count,
            "next_trigger_at": 100,  # Will trigger at 100 feedback items
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/learning/history")
async def get_learning_history(limit: int = 10):
    """
    Get history of learning cycles.
    
    Shows:
    - When cycles ran
    - What triggered them
    - Results and improvements
    - Metrics over time
    """
    try:
        from supabase import create_client
        
        supabase = create_client(settings.supabase_url, settings.supabase_key)
        
        result = supabase.table('learning_cycles')\
            .select('*')\
            .order('completed_at', desc=True)\
            .limit(limit)\
            .execute()
        
        return {
            "success": True,
            "cycles": result.data,
            "count": len(result.data),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/learning/metrics")
async def get_learning_metrics():
    """
    Get aggregated metrics showing system improvement over time.
    
    Returns:
    - Average rating trend
    - Accuracy rate trend
    - Total learning cycles
    - Knowledge base growth
    """
    try:
        from supabase import create_client
        
        supabase = create_client(settings.supabase_url, settings.supabase_key)
        
        # Get all cycles
        cycles = supabase.table('learning_cycles')\
            .select('*')\
            .order('completed_at', desc=False)\
            .execute()
        
        if not cycles.data:
            return {
                "success": True,
                "metrics": {
                    "total_cycles": 0,
                    "improvement_trend": "No data yet"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Calculate trends
        ratings = [c.get('average_rating', 0) for c in cycles.data]
        accuracies = [c.get('accuracy_rate', 0) for c in cycles.data]
        
        metrics = {
            "total_cycles": len(cycles.data),
            "average_rating": {
                "first": ratings[0] if ratings else 0,
                "latest": ratings[-1] if ratings else 0,
                "trend": ratings
            },
            "accuracy_rate": {
                "first": accuracies[0] if accuracies else 0,
                "latest": accuracies[-1] if accuracies else 0,
                "trend": accuracies
            },
            "last_cycle": cycles.data[-1] if cycles.data else None
        }
        
        return {
            "success": True,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/knowledge-base/add")
async def add_to_knowledge_base(documents: List[KnowledgeBaseDocument]):
    """
    Add documents to the knowledge base.
    
    This endpoint is for administrators to manually add validated
    mathematical questions and solutions to the knowledge base.
    """
    try:
        docs_to_add = []
        for doc in documents:
            docs_to_add.append({
                'question': doc.question,
                'answer': doc.answer,
                'solution_steps': doc.solution_steps or {},
                'topic': doc.topic,
                'difficulty': doc.difficulty,
                'source': doc.source,
                'metadata': doc.metadata or {}
            })
        
        inserted_ids = await vector_store.add_documents(docs_to_add)
        
        return {
            "success": True,
            "message": f"Successfully added {len(inserted_ids)} documents to knowledge base",
            "document_ids": inserted_ids,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/knowledge-base/search")
async def search_knowledge_base(query: str, k: int = 5):
    """
    Search the knowledge base for similar questions.
    
    Useful for debugging and seeing what's in the knowledge base.
    """
    try:
        results = await vector_store.similarity_search(query, k=k)
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def trigger_learning_cycle():
    """Background task to run learning cycle."""
    try:
        result = await learning_pipeline.run_learning_cycle()
        print(f"Learning cycle completed: {result}")
    except Exception as e:
        print(f"Learning cycle error: {e}")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Add parent directory to path so imports work
    backend_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(backend_dir))
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )

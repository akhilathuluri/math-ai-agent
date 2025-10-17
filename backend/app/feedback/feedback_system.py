"""Human-in-the-Loop Feedback System with DSPy Integration."""
from typing import Dict, Any, List, Optional
from datetime import datetime
from supabase import create_client, Client
from app.config import settings
import dspy
from openai import OpenAI


class FeedbackManager:
    """Manages user feedback and system improvement."""
    
    def __init__(self):
        """Initialize feedback manager with GitHub Models."""
        self.supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        self.openai_client = OpenAI(
            api_key=settings.github_token,
            base_url=settings.github_api_base
        )
    
    async def submit_feedback(
        self,
        question: str,
        generated_answer: str,
        rating: int,
        user_feedback: Optional[str] = None,
        corrections: Optional[Dict[str, Any]] = None,
        is_correct: Optional[bool] = None,
        question_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Submit user feedback for a generated answer.
        
        Args:
            question: Original question
            generated_answer: The answer provided by the system
            rating: User rating (1-5)
            user_feedback: Optional text feedback
            corrections: Optional corrections to the answer
            is_correct: Whether the answer was correct
            question_id: Optional reference to knowledge base question
        
        Returns:
            Dict with feedback submission result
        """
        try:
            feedback_data = {
                'question_id': question_id,
                'user_question': question,
                'generated_answer': generated_answer,
                'user_feedback': user_feedback,
                'rating': rating,
                'corrections': corrections or {},
                'is_correct': is_correct,
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table('feedback').insert(feedback_data).execute()
            
            # If rating is low or marked incorrect, analyze and learn
            if rating <= 2 or is_correct is False:
                await self._analyze_failure(feedback_data)
            
            return {
                'success': True,
                'feedback_id': result.data[0]['id'] if result.data else None,
                'message': 'Feedback submitted successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _analyze_failure(self, feedback_data: Dict[str, Any]):
        """Analyze failed responses to improve the system."""
        # This triggers immediate analysis for low ratings
        # 1. LLM analysis of what went wrong
        # 2. Pattern detection
        # 3. Flag for review in database
        
        analysis_prompt = f"""Analyze this failed math question response:

Question: {feedback_data['user_question']}
Generated Answer: {feedback_data['generated_answer']}
User Feedback: {feedback_data.get('user_feedback', 'N/A')}
Rating: {feedback_data['rating']}/5

Provide:
1. Why the answer might have failed
2. What improvements are needed
3. Whether this should be added to the knowledge base
4. Suggested corrected answer if possible

Respond in JSON format with keys: failure_reason, improvements_needed, add_to_kb (boolean), suggested_correction."""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            import json
            analysis_result = json.loads(response.choices[0].message.content)
            
            # Store analysis in database for review
            analysis_data = {
                'feedback_id': feedback_data.get('feedback_id'),
                'user_question': feedback_data['user_question'],
                'failure_reason': analysis_result.get('failure_reason', ''),
                'improvements_needed': analysis_result.get('improvements_needed', ''),
                'should_add_to_kb': analysis_result.get('add_to_kb', False),
                'suggested_correction': analysis_result.get('suggested_correction', ''),
                'status': 'pending_review',
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Store in failure_analysis table
            self.supabase.table('failure_analysis').insert(analysis_data).execute()
            
            print(f"[FAILURE ANALYSIS] Stored analysis for question: {feedback_data['user_question'][:50]}...")
            print(f"[FAILURE ANALYSIS] Reason: {analysis_result.get('failure_reason', 'N/A')}")
            
        except Exception as e:
            print(f"Analysis error: {e}")
    
    async def get_recent_corrections(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent corrections from feedback with high ratings."""
        try:
            result = self.supabase.table('feedback')\
                .select('user_question, corrections, rating, created_at')\
                .not_.is_('corrections', 'null')\
                .gte('rating', 4)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            corrections = []
            for row in result.data:
                if row.get('corrections') and isinstance(row['corrections'], dict):
                    if 'corrected_answer' in row['corrections']:
                        corrections.append({
                            'question': row['user_question'],
                            'corrected_answer': row['corrections']['corrected_answer'],
                            'rating': row['rating'],
                            'created_at': row['created_at']
                        })
            
            return corrections
            
        except Exception as e:
            print(f"Error getting recent corrections: {e}")
            return []
    
    async def get_feedback_count_since_last_cycle(self) -> int:
        """Get count of feedback since last learning cycle."""
        try:
            # Get last cycle timestamp from learning_cycles table
            last_cycle = self.supabase.table('learning_cycles')\
                .select('completed_at')\
                .order('completed_at', desc=True)\
                .limit(1)\
                .execute()
            
            if last_cycle.data:
                last_timestamp = last_cycle.data[0]['completed_at']
                # Count feedback since then
                result = self.supabase.table('feedback')\
                    .select('id', count='exact')\
                    .gte('created_at', last_timestamp)\
                    .execute()
                return result.count if hasattr(result, 'count') else len(result.data)
            else:
                # No cycles yet, count all feedback
                result = self.supabase.table('feedback')\
                    .select('id', count='exact')\
                    .execute()
                return result.count if hasattr(result, 'count') else len(result.data)
                
        except Exception as e:
            print(f"Error counting feedback: {e}")
            return 0
    
    async def should_trigger_learning_cycle(self) -> bool:
        """Check if learning cycle should be triggered based on feedback count."""
        count = await self.get_feedback_count_since_last_cycle()
        return count >= 100
    
    async def get_feedback_stats(self) -> Dict[str, Any]:
        """Get statistics about feedback."""
        try:
            # Get all feedback
            result = self.supabase.table('feedback')\
                .select('rating, is_correct')\
                .execute()
            
            total = len(result.data)
            if total == 0:
                return {
                    'total_feedback': 0,
                    'average_rating': 0,
                    'accuracy_rate': 0
                }
            
            # Calculate stats
            total_rating = sum(f['rating'] for f in result.data)
            correct_count = sum(1 for f in result.data if f.get('is_correct') is True)
            
            return {
                'total_feedback': total,
                'average_rating': total_rating / total,
                'accuracy_rate': correct_count / total if total > 0 else 0,
                'feedback_by_rating': self._group_by_rating(result.data)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _group_by_rating(self, feedback_list: List[Dict]) -> Dict[int, int]:
        """Group feedback by rating."""
        groups = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for f in feedback_list:
            rating = f.get('rating')
            if rating in groups:
                groups[rating] += 1
        return groups
    
    async def get_improvement_suggestions(self) -> List[Dict[str, Any]]:
        """Get suggestions for system improvement based on feedback."""
        try:
            # Get low-rated feedback
            result = self.supabase.table('feedback')\
                .select('*')\
                .lte('rating', 2)\
                .order('created_at', desc=True)\
                .limit(10)\
                .execute()
            
            suggestions = []
            for feedback in result.data:
                suggestions.append({
                    'question': feedback['user_question'],
                    'issue': feedback.get('user_feedback', 'Low rating'),
                    'rating': feedback['rating'],
                    'suggested_action': self._suggest_action(feedback)
                })
            
            return suggestions
            
        except Exception as e:
            return []

    async def get_recent_corrections(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Return recent feedback entries that include corrections with a corrected_answer."""
        try:
            # Fetch recent rows where corrections.corrected_answer exists
            result = self.supabase.table('feedback')\
                .select('user_question, generated_answer, corrections, created_at, rating, is_correct')\
                .not_.is_('corrections', 'null')\
                .order('created_at', desc=True)\
                .limit(50)\
                .execute()

            items: List[Dict[str, Any]] = []
            for row in result.data or []:
                corrections = row.get('corrections') or {}
                corrected_answer = corrections.get('corrected_answer') if isinstance(corrections, dict) else None
                if corrected_answer:
                    items.append({
                        'question': row.get('user_question'),
                        'generated_answer': row.get('generated_answer'),
                        'corrected_answer': corrected_answer,
                        'created_at': row.get('created_at'),
                        'rating': row.get('rating'),
                        'is_correct': row.get('is_correct')
                    })
                if len(items) >= limit:
                    break

            return items
        except Exception:
            return []
    
    def _suggest_action(self, feedback: Dict[str, Any]) -> str:
        """Suggest action based on feedback."""
        if feedback.get('is_correct') is False:
            return "Review and correct answer, add to knowledge base"
        elif feedback['rating'] <= 2:
            return "Improve explanation clarity and step-by-step details"
        else:
            return "Monitor for patterns"


class DSPyOptimizer:
    """DSPy-based prompt and system optimization."""
    
    def __init__(self):
        """Initialize DSPy optimizer with GitHub Models (lazy loading)."""
        self.lm = None
        self.math_solver = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of DSPy to avoid async context issues."""
        if self._initialized:
            return
        
        try:
            import dspy
            
            # Create LM instance but DON'T call configure()
            # We'll use context managers instead
            try:
                self.lm = dspy.LM(
                    model=f"openai/{settings.llm_model}",
                    api_key=settings.github_token,
                    api_base=settings.github_api_base
                )
                # Create the math solver module (not just signature)
                self.math_solver = MathSolverModule()
                self._initialized = True
                
            except (AttributeError, TypeError) as e:
                print(f"Warning: DSPy initialization failed: {e}")
                self.lm = None
                self.math_solver = None
            
        except ImportError:
            print("Warning: DSPy not installed. Optimization features disabled.")
            self.lm = None
            self.math_solver = None
    
    async def optimize_prompts(
        self,
        training_examples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Optimize prompts based on feedback examples using DSPy.
        
        Args:
            training_examples: List of dicts with 'question', 'answer', 'feedback'
        
        Returns:
            Optimization results
        """
        # Ensure DSPy is initialized
        self._ensure_initialized()
        
        if self.lm is None:
            return {
                'success': False,
                'error': 'DSPy not properly configured',
                'message': 'Optimization requires DSPy setup'
            }
        
        try:
            import dspy
            
            # Use context manager for this async task
            with dspy.context(lm=self.lm):
                # Convert examples to DSPy format
                dspy_examples = []
                for ex in training_examples:
                    dspy_examples.append(
                        dspy.Example(
                            question=ex['question'],
                            answer=ex['answer']
                        ).with_inputs('question')
                    )
                
                # Create optimizer
                optimizer = dspy.BootstrapFewShot(
                    metric=self._math_accuracy_metric,
                    max_bootstrapped_demos=4,
                    max_labeled_demos=8
                )
                
                # Compile optimized program
                optimized_solver = optimizer.compile(
                    self.math_solver,
                    trainset=dspy_examples[:int(len(dspy_examples) * 0.8)]
                )
                
                # Evaluate
                testset = dspy_examples[int(len(dspy_examples) * 0.8):]
                evaluation = dspy.Evaluate(
                    devset=testset,
                    metric=self._math_accuracy_metric,
                    num_threads=1
                )
                
                score_result = evaluation(optimized_solver)
                
                # Extract numeric score from EvaluationResult
                # score_result could be a float or an EvaluationResult object
                if hasattr(score_result, '__float__'):
                    score = float(score_result)
                elif isinstance(score_result, (int, float)):
                    score = float(score_result)
                else:
                    # Fallback: try to get the score attribute or use repr
                    score = getattr(score_result, 'score', 0.0)
            
            return {
                'success': True,
                'optimization_score': score,
                'examples_used': len(training_examples),
                'optimized_solver': optimized_solver
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _math_accuracy_metric(self, example, prediction, trace=None) -> float:
        """
        Metric to evaluate mathematical answer accuracy.
        
        Simple version - checks if key terms match.
        In production, would use more sophisticated evaluation.
        """
        if not prediction or not hasattr(prediction, 'answer'):
            return 0.0
        
        # Basic similarity check
        pred_answer = str(prediction.answer).lower()
        true_answer = str(example.answer).lower()
        
        # Simple word overlap
        pred_words = set(pred_answer.split())
        true_words = set(true_answer.split())
        
        if not true_words:
            return 0.0
        
        overlap = len(pred_words.intersection(true_words))
        return overlap / len(true_words)


class MathSolverSignature(dspy.Signature):
    """DSPy signature for math problem solving."""
    question = dspy.InputField(desc="Mathematical question to solve")
    answer = dspy.OutputField(desc="Step-by-step solution with final answer")


class MathSolverModule(dspy.Module):
    """DSPy module for math problem solving."""
    
    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(MathSolverSignature)
    
    def forward(self, question):
        """Forward pass for the math solver."""
        return self.predictor(question=question)


class FeedbackLearningPipeline:
    """Complete pipeline for learning from feedback."""
    
    def __init__(self):
        """Initialize learning pipeline."""
        self.feedback_manager = FeedbackManager()
        self.optimizer = DSPyOptimizer()
        self.supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
    
    async def run_learning_cycle(self) -> Dict[str, Any]:
        """
        Run a complete learning cycle:
        1. Gather feedback
        2. Analyze patterns
        3. Optimize prompts
        4. Update knowledge base
        """
        print("\n" + "="*70)
        print("🎓 LEARNING CYCLE STARTED")
        print("="*70)
        
        # 1. Get recent feedback
        print("\n📊 Step 1: Gathering feedback statistics...")
        feedback_stats = await self.feedback_manager.get_feedback_stats()
        print(f"   ✓ Total feedback: {feedback_stats.get('total_feedback', 0)}")
        print(f"   ✓ Average rating: {feedback_stats.get('average_rating', 0):.2f}/5.0")
        print(f"   ✓ Accuracy rate: {feedback_stats.get('accuracy_rate', 0)*100:.1f}%")
        print(f"   ✓ Feedback by rating: {feedback_stats.get('feedback_by_rating', {})}")
        
        # 2. Get improvement suggestions
        print("\n💡 Step 2: Analyzing feedback for improvements...")
        suggestions = await self.feedback_manager.get_improvement_suggestions()
        print(f"   ✓ Found {len(suggestions)} areas for improvement")
        if suggestions:
            print(f"   ✓ Low-rated feedback items ready for analysis")
        
        # 3. Get training examples from positive feedback
        print("\n📚 Step 3: Collecting training examples...")
        training_examples = await self._get_training_examples()
        print(f"   ✓ Collected {len(training_examples)} high-quality examples")
        
        # 4. Optimize if we have enough examples
        print("\n🧠 Step 4: Running DSPy optimization...")
        if len(training_examples) >= 5:
            print(f"   → Optimizing with {len(training_examples)} training examples...")
            optimization_result = await self.optimizer.optimize_prompts(training_examples)
            if optimization_result.get('success'):
                print(f"   ✅ Optimization successful!")
                try:
                    # Safely get and format score
                    score = optimization_result.get('optimization_score', 0)
                    if isinstance(score, (int, float)):
                        # Score is already a ratio (0.0-1.0), multiply by 100 for percentage display
                        print(f"   ✓ Score: {score * 100:.2f}%")
                    else:
                        print(f"   ✓ Score: {score}")
                    print(f"   ✓ Examples used: {optimization_result.get('examples_used', 0)}")
                except Exception as e:
                    print(f"   ✓ Score: {optimization_result.get('optimization_score', 'N/A')}")
                    print(f"   ✓ Examples used: {optimization_result.get('examples_used', 0)}")
            else:
                print(f"   ⚠️  Optimization skipped: {optimization_result.get('error', 'Unknown')}")
        else:
            print(f"   ⚠️  Not enough training examples (need 5, have {len(training_examples)})")
            optimization_result = {
                'success': False,
                'reason': f'Not enough training examples (need 5, have {len(training_examples)})'
            }
        
        # 5. Add validated corrections to knowledge base
        print("\n📖 Step 5: Updating knowledge base...")
        kb_result = await self._update_knowledge_base(suggestions)
        print(f"   ✓ Knowledge base updated with corrections")

        # 6. If we produced an optimized solver, publish it globally for the agent to consume
        print("\n🚀 Step 6: Publishing optimized model...")
        try:
            if optimization_result.get('success') and optimization_result.get('optimized_solver') is not None:
                OPTIMIZED_PROGRAM_STORE.set(optimization_result['optimized_solver'])
                print("   ✅ Published optimized DSPy solver to global store")
                print("   ✓ Math agent will use improved prompts for future queries")
            else:
                print("   ⚠️  No optimized solver to publish (skipped)")
        except Exception as e:
            print(f"   ❌ Failed to publish optimized solver: {e}")
        
        print("\n" + "="*70)
        print("✅ LEARNING CYCLE COMPLETED SUCCESSFULLY")
        print("="*70 + "\n")
        
        # Remove non-serializable objects from optimization_result before returning
        optimization_result_safe = {
            'success': optimization_result.get('success', False),
            'optimization_score': optimization_result.get('optimization_score', 0),
            'examples_used': optimization_result.get('examples_used', 0)
        }
        if not optimization_result.get('success'):
            optimization_result_safe['error'] = optimization_result.get('error', 'Unknown')
            if 'reason' in optimization_result:
                optimization_result_safe['reason'] = optimization_result['reason']
        
        return {
            'feedback_stats': feedback_stats,
            'suggestions_count': len(suggestions),
            'optimization_result': optimization_result_safe,
            'learning_cycle_complete': True
        }
    
    async def _get_training_examples(self) -> List[Dict[str, Any]]:
        """
        Get high-quality examples from feedback.
        
        Prioritizes:
        1. High rating (≥4) + explicitly marked correct
        2. High rating (≥4) even without explicit correctness flag
        
        Rationale: Users giving 4-5 stars generally means the answer was good.
        """
        try:
            # First, try to get explicitly correct high-rated examples
            result = self.supabase.table('feedback')\
                .select('user_question, generated_answer, corrections, rating, is_correct')\
                .gte('rating', 4)\
                .eq('is_correct', True)\
                .limit(50)\
                .execute()
            
            examples = []
            for row in result.data:
                examples.append({
                    'question': row['user_question'],
                    'answer': row.get('corrections', {}).get('corrected_answer', row['generated_answer']),
                    'rating': row.get('rating', 5)
                })
            
            # If we don't have enough, add high-rated items (even without explicit is_correct)
            if len(examples) < 5:
                print(f"   → Only {len(examples)} explicitly correct examples, adding high-rated items...")
                additional = self.supabase.table('feedback')\
                    .select('user_question, generated_answer, corrections, rating, is_correct')\
                    .gte('rating', 4)\
                    .limit(50)\
                    .execute()
                
                # Add items that aren't explicitly marked as incorrect
                for row in additional.data:
                    # Skip if already added or explicitly marked incorrect
                    if any(ex['question'] == row['user_question'] for ex in examples):
                        continue
                    if row.get('is_correct') is False:
                        continue
                    
                    examples.append({
                        'question': row['user_question'],
                        'answer': row.get('corrections', {}).get('corrected_answer', row['generated_answer']),
                        'rating': row.get('rating', 5)
                    })
                    
                    if len(examples) >= 50:
                        break
            
            return examples
            
        except Exception as e:
            print(f"Error getting training examples: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _update_knowledge_base(self, suggestions: List[Dict[str, Any]]):
        """Update knowledge base with validated corrections."""
        # Add corrected entries found in feedback to the knowledge base
        try:
            recent = await self.feedback_manager.get_recent_corrections(limit=5)
            if not recent:
                return
            docs = []
            for item in recent:
                docs.append({
                    'question': item['question'],
                    'answer': item['corrected_answer'],
                    'solution_steps': {'source': 'feedback_correction'},
                    'topic': 'general',
                    'difficulty': 'medium',
                    'source': 'feedback',
                    'metadata': {'origin': 'feedback_learning_pipeline'}
                })
            from app.vectorstore import SupabaseVectorStore
            store = SupabaseVectorStore()
            try:
                await store.add_documents(docs)
                print(f"Added {len(docs)} corrected documents to knowledge base from feedback")
            except Exception as e:
                print(f"KB update failed: {e}")
        except Exception as e:
            print(f"Error during KB update from feedback: {e}")

# -----------------------
# Global optimized program store for DSPy
# -----------------------
class _OptimizedProgramStore:
    """Thread-safe in-memory store for the latest optimized DSPy solver."""
    def __init__(self):
        try:
            import threading
            self._lock = threading.Lock()
        except Exception:
            self._lock = None
        self._program = None

    def get(self):
        if self._lock:
            with self._lock:
                return self._program
        return self._program

    def set(self, program):
        if self._lock:
            with self._lock:
                self._program = program
        else:
            self._program = program


# Module-level singleton store
OPTIMIZED_PROGRAM_STORE = _OptimizedProgramStore()

def get_optimized_solver():
    """Expose latest optimized solver if available, else None."""
    return OPTIMIZED_PROGRAM_STORE.get()

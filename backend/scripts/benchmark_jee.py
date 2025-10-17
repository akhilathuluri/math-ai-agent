"""
JEE Bench Benchmarking Script

This script evaluates the Math Agent's performance on JEE (Joint Entrance Examination) 
style mathematical problems.
"""
import asyncio
import json
import time
from typing import List, Dict, Any
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from backend directory
from dotenv import load_dotenv
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / '.env'
load_dotenv(env_path)

from app.agents import MathRoutingAgent
from datetime import datetime


# Sample JEE-style problems (In production, load from actual JEE Bench dataset)
JEE_BENCH_PROBLEMS = [
    {
        "id": 1,
        "question": "If f(x) = x³ - 3x² + 4, find the value of f(2) + f(-1)",
        "correct_answer": "2",
        "topic": "algebra",
        "difficulty": "easy",
        "solution_steps": 3
    },
    {
        "id": 2,
        "question": "Find the derivative of y = (x² + 1)(x³ - 2x) using the product rule",
        "correct_answer": "5x⁴ - 4x² + 3x² - 2 or simplified: 5x⁴ - x² - 2",
        "topic": "calculus",
        "difficulty": "medium",
        "solution_steps": 4
    },
    {
        "id": 3,
        "question": "In a triangle ABC, if a = 5, b = 6, and c = 7, find the area using Heron's formula",
        "correct_answer": "≈14.7 square units or 6√6",
        "topic": "geometry",
        "difficulty": "medium",
        "solution_steps": 5
    },
    {
        "id": 4,
        "question": "Solve the system: 2x + y = 7 and x - y = 2",
        "correct_answer": "x = 3, y = 1",
        "topic": "algebra",
        "difficulty": "easy",
        "solution_steps": 3
    },
    {
        "id": 5,
        "question": "Find the equation of the tangent line to f(x) = x² at the point (2, 4)",
        "correct_answer": "y = 4x - 4",
        "topic": "calculus",
        "difficulty": "medium",
        "solution_steps": 4
    },
    {
        "id": 6,
        "question": "If sin(θ) = 3/5 and θ is in the first quadrant, find cos(θ) and tan(θ)",
        "correct_answer": "cos(θ) = 4/5, tan(θ) = 3/4",
        "topic": "trigonometry",
        "difficulty": "medium",
        "solution_steps": 3
    },
    {
        "id": 7,
        "question": "Evaluate the integral: ∫(3x² - 2x + 1)dx",
        "correct_answer": "x³ - x² + x + C",
        "topic": "calculus",
        "difficulty": "easy",
        "solution_steps": 3
    },
    {
        "id": 8,
        "question": "Find the 10th term of the arithmetic sequence: 3, 7, 11, 15, ...",
        "correct_answer": "39",
        "topic": "sequences",
        "difficulty": "easy",
        "solution_steps": 2
    },
    {
        "id": 9,
        "question": "If log₂(x) = 5, find the value of x",
        "correct_answer": "32",
        "topic": "algebra",
        "difficulty": "easy",
        "solution_steps": 2
    },
    {
        "id": 10,
        "question": "Find the probability of getting exactly 2 heads when flipping a fair coin 4 times",
        "correct_answer": "3/8 or 0.375",
        "topic": "probability",
        "difficulty": "medium",
        "solution_steps": 4
    }
]


class JEEBenchEvaluator:
    """Evaluator for JEE Bench problems."""
    
    def __init__(self):
        """Initialize evaluator."""
        self.agent = MathRoutingAgent()
        self.results = []
    
    async def evaluate_problem(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a single problem.
        
        Returns:
            Dict with evaluation metrics
        """
        print(f"\n{'='*60}")
        print(f"Problem {problem['id']}: {problem['topic'].upper()}")
        print(f"Question: {problem['question']}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Get answer from agent
            response = await self.agent.process_question(problem['question'])
            
            elapsed_time = time.time() - start_time
            
            # Evaluate answer quality (simplified - in production would use more sophisticated matching)
            is_correct = self._check_answer_correctness(
                response.get('answer', ''),
                problem['correct_answer']
            )
            
            # Check if steps were provided
            has_steps = len(response.get('solution_steps', [])) > 0
            
            # Calculate completeness score
            provided_steps = len(response.get('solution_steps', []))
            expected_steps = problem['solution_steps']
            completeness_score = min(provided_steps / expected_steps, 1.0) if expected_steps > 0 else 0.0
            
            result = {
                'problem_id': problem['id'],
                'topic': problem['topic'],
                'difficulty': problem['difficulty'],
                'question': problem['question'],
                'correct_answer': problem['correct_answer'],
                'agent_answer': response.get('answer', ''),
                'is_correct': is_correct,
                'has_steps': has_steps,
                'num_steps_provided': provided_steps,
                'num_steps_expected': expected_steps,
                'completeness_score': completeness_score,
                'confidence_score': response.get('confidence_score', 0.0),
                'routing_decision': response.get('routing_decision', 'unknown'),
                'response_time': elapsed_time,
                'sources': response.get('sources', []),
                'success': response.get('success', False),
                'error': response.get('error')
            }
            
            print(f"\n✓ Completed in {elapsed_time:.2f}s")
            print(f"Routing: {result['routing_decision']}")
            print(f"Confidence: {result['confidence_score']:.2%}")
            print(f"Correctness Check: {'✓ Correct' if is_correct else '✗ Incorrect/Uncertain'}")
            print(f"Steps Provided: {provided_steps}/{expected_steps}")
            
            return result
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n✗ Error: {str(e)}")
            
            return {
                'problem_id': problem['id'],
                'topic': problem['topic'],
                'difficulty': problem['difficulty'],
                'is_correct': False,
                'has_steps': False,
                'completeness_score': 0.0,
                'confidence_score': 0.0,
                'response_time': elapsed_time,
                'success': False,
                'error': str(e)
            }
    
    def _check_answer_correctness(self, agent_answer: str, correct_answer: str) -> bool:
        """
        Simple correctness check (simplified version).
        In production, would use more sophisticated answer matching.
        """
        agent_lower = agent_answer.lower()
        correct_lower = correct_answer.lower()
        
        # Extract numbers from both answers
        import re
        agent_numbers = set(re.findall(r'\d+\.?\d*', agent_answer))
        correct_numbers = set(re.findall(r'\d+\.?\d*', correct_answer))
        
        # Check if key numbers match
        number_match = len(agent_numbers.intersection(correct_numbers)) > 0
        
        # Check if correct answer appears in agent answer
        substring_match = correct_lower in agent_lower
        
        return number_match or substring_match
    
    async def evaluate_all(self, problems: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate all problems and generate report.
        
        Returns:
            Comprehensive evaluation report
        """
        print(f"\n{'='*60}")
        print(f"JEE BENCH EVALUATION")
        print(f"Total Problems: {len(problems)}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        self.results = []
        
        for problem in problems:
            result = await self.evaluate_problem(problem)
            self.results.append(result)
            
            # Small delay between requests
            await asyncio.sleep(1)
        
        # Generate report
        report = self._generate_report()
        
        return report
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive evaluation report."""
        total = len(self.results)
        
        if total == 0:
            return {'error': 'No results to report'}
        
        # Overall metrics
        correct_count = sum(1 for r in self.results if r['is_correct'])
        has_steps_count = sum(1 for r in self.results if r['has_steps'])
        successful_count = sum(1 for r in self.results if r['success'])
        
        accuracy = correct_count / total
        step_provision_rate = has_steps_count / total
        success_rate = successful_count / total
        
        avg_response_time = sum(r['response_time'] for r in self.results) / total
        avg_confidence = sum(r['confidence_score'] for r in self.results) / total
        avg_completeness = sum(r['completeness_score'] for r in self.results) / total
        
        # By topic
        topics = {}
        for result in self.results:
            topic = result['topic']
            if topic not in topics:
                topics[topic] = {'total': 0, 'correct': 0}
            topics[topic]['total'] += 1
            if result['is_correct']:
                topics[topic]['correct'] += 1
        
        topic_accuracy = {
            topic: stats['correct'] / stats['total'] 
            for topic, stats in topics.items()
        }
        
        # By difficulty
        difficulties = {}
        for result in self.results:
            diff = result['difficulty']
            if diff not in difficulties:
                difficulties[diff] = {'total': 0, 'correct': 0}
            difficulties[diff]['total'] += 1
            if result['is_correct']:
                difficulties[diff]['correct'] += 1
        
        difficulty_accuracy = {
            diff: stats['correct'] / stats['total']
            for diff, stats in difficulties.items()
        }
        
        # Routing analysis
        routing_stats = {}
        for result in self.results:
            routing = result['routing_decision']
            if routing not in routing_stats:
                routing_stats[routing] = {'count': 0, 'correct': 0}
            routing_stats[routing]['count'] += 1
            if result['is_correct']:
                routing_stats[routing]['correct'] += 1
        
        report = {
            'evaluation_date': datetime.now().isoformat(),
            'total_problems': total,
            'overall_metrics': {
                'accuracy': accuracy,
                'success_rate': success_rate,
                'step_provision_rate': step_provision_rate,
                'avg_response_time': avg_response_time,
                'avg_confidence_score': avg_confidence,
                'avg_completeness_score': avg_completeness
            },
            'performance_by_topic': topic_accuracy,
            'performance_by_difficulty': difficulty_accuracy,
            'routing_analysis': routing_stats,
            'detailed_results': self.results
        }
        
        return report
    
    def print_report(self, report: Dict[str, Any]):
        """Print formatted report."""
        print(f"\n{'='*60}")
        print(f"JEE BENCH EVALUATION REPORT")
        print(f"{'='*60}\n")
        
        metrics = report['overall_metrics']
        
        print("OVERALL PERFORMANCE:")
        print(f"  Accuracy: {metrics['accuracy']:.2%}")
        print(f"  Success Rate: {metrics['success_rate']:.2%}")
        print(f"  Step Provision Rate: {metrics['step_provision_rate']:.2%}")
        print(f"  Avg Response Time: {metrics['avg_response_time']:.2f}s")
        print(f"  Avg Confidence: {metrics['avg_confidence_score']:.2%}")
        print(f"  Avg Completeness: {metrics['avg_completeness_score']:.2%}")
        
        print(f"\nPERFORMANCE BY TOPIC:")
        for topic, accuracy in report['performance_by_topic'].items():
            print(f"  {topic.capitalize()}: {accuracy:.2%}")
        
        print(f"\nPERFORMANCE BY DIFFICULTY:")
        for diff, accuracy in report['performance_by_difficulty'].items():
            print(f"  {diff.capitalize()}: {accuracy:.2%}")
        
        print(f"\nROUTING ANALYSIS:")
        for routing, stats in report['routing_analysis'].items():
            accuracy = stats['correct'] / stats['count'] if stats['count'] > 0 else 0
            print(f"  {routing}: {stats['count']} problems, {accuracy:.2%} accuracy")
        
        print(f"\n{'='*60}")
    
    def save_report(self, report: Dict[str, Any], filename: str = "jee_bench_report.json"):
        """Save report to JSON file."""
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n✓ Report saved to {filename}")


async def main():
    """Run JEE Bench evaluation."""
    evaluator = JEEBenchEvaluator()
    
    # Run evaluation
    report = await evaluator.evaluate_all(JEE_BENCH_PROBLEMS)
    
    # Print report
    evaluator.print_report(report)
    
    # Save report
    evaluator.save_report(report)
    
    print(f"\n{'='*60}")
    print("Evaluation completed!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    print("="*60)
    print("JEE BENCH BENCHMARKING SCRIPT")
    print("="*60)
    print("\nThis script evaluates the Math Agent on JEE-style problems.")
    print("Press Ctrl+C to cancel.\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nEvaluation cancelled by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()

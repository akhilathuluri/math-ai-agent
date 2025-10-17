"""
Script to ingest JSONL mathematical problems into the knowledge base.
Supports formats like GSM8K, MathQA, etc.
"""
import asyncio
import json
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / '.env'
load_dotenv(env_path)

from app.vectorstore import SupabaseVectorStore


def parse_jsonl_file(filepath: str):
    """
    Parse a JSONL file containing math problems.
    
    Expected format:
    {"question": "...", "answer": "..."}
    """
    problems = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                
                # Extract question and answer
                question = data.get('question', '').strip()
                answer = data.get('answer', '').strip()
                
                if not question or not answer:
                    print(f"Warning: Line {line_num} missing question or answer, skipping...")
                    continue
                
                # Parse solution steps from answer if formatted with "#### "
                final_answer = answer
                solution_steps = []
                
                # GSM8K format: steps separated by newlines, final answer after "#### "
                if '#### ' in answer:
                    parts = answer.split('#### ')
                    steps_text = parts[0].strip()
                    final_answer = parts[1].strip() if len(parts) > 1 else answer
                    
                    # Parse individual steps (format: "Question ** explanation")
                    step_lines = steps_text.split('\n')
                    step_num = 1
                    for step_line in step_lines:
                        step_line = step_line.strip()
                        if step_line and '**' in step_line:
                            # Extract question and calculation
                            parts = step_line.split('**')
                            if len(parts) >= 2:
                                step_question = parts[0].strip()
                                step_calculation = parts[1].strip()
                                solution_steps.append({
                                    "step": step_num,
                                    "description": f"{step_question}: {step_calculation}"
                                })
                                step_num += 1
                
                # Determine topic (simple classification)
                topic = classify_topic(question, answer)
                
                # Create document
                document = {
                    "question": question,
                    "answer": final_answer if final_answer else answer,
                    "solution_steps": {
                        "steps": solution_steps
                    } if solution_steps else None,
                    "topic": topic,
                    "difficulty": "medium",  # Default, could be enhanced
                    "source": "jsonl_import"
                }
                
                problems.append(document)
                
            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")
                continue
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
                continue
    
    return problems


def classify_topic(question: str, answer: str = "") -> str:
    """
    Simple topic classification based on keywords.
    """
    text = (question + " " + answer).lower()
    
    topic_keywords = {
        'algebra': ['equation', 'variable', 'polynomial', 'solve for', 'x =', 'linear', 'quadratic'],
        'arithmetic': ['add', 'subtract', 'multiply', 'divide', 'sum', 'difference', 'product', 'total', 'cost', 'price', 'dollars', 'cents'],
        'geometry': ['triangle', 'circle', 'square', 'rectangle', 'area', 'perimeter', 'volume', 'angle', 'radius', 'diameter'],
        'calculus': ['derivative', 'integral', 'limit', 'differential', 'rate of change'],
        'trigonometry': ['sin', 'cos', 'tan', 'sine', 'cosine', 'tangent'],
        'statistics': ['mean', 'median', 'mode', 'average', 'standard deviation', 'probability'],
        'probability': ['chance', 'odds', 'likelihood', 'random', 'dice', 'coin'],
        'number_theory': ['prime', 'factor', 'divisor', 'gcd', 'lcm', 'modulo']
    }
    
    for topic, keywords in topic_keywords.items():
        if any(keyword in text for keyword in keywords):
            return topic
    
    return 'general'


async def ingest_jsonl_data(filepath: str, batch_size: int = 50):
    """
    Ingest JSONL data into the knowledge base.
    
    Args:
        filepath: Path to the JSONL file
        batch_size: Number of documents to insert at once
    """
    print(f"Reading JSONL file: {filepath}")
    
    # Parse the file
    problems = parse_jsonl_file(filepath)
    
    if not problems:
        print("No valid problems found in the file.")
        return
    
    print(f"Parsed {len(problems)} problems")
    
    # Show sample
    print("\nSample problem:")
    print(f"Question: {problems[0]['question'][:100]}...")
    print(f"Answer: {problems[0]['answer'][:100]}...")
    print(f"Topic: {problems[0]['topic']}")
    print(f"Steps: {len(problems[0].get('solution_steps', {}).get('steps', []))}")
    
    # Initialize vector store
    vector_store = SupabaseVectorStore()
    
    # Ingest in batches
    total_inserted = 0
    
    for i in range(0, len(problems), batch_size):
        batch = problems[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(problems) + batch_size - 1) // batch_size
        
        print(f"\nIngesting batch {batch_num}/{total_batches} ({len(batch)} problems)...")
        
        try:
            inserted_ids = await vector_store.add_documents(batch)
            total_inserted += len(inserted_ids)
            print(f"✓ Batch {batch_num} completed: {len(inserted_ids)} documents inserted")
        except Exception as e:
            print(f"✗ Error in batch {batch_num}: {e}")
            continue
    
    print(f"\n{'='*50}")
    print(f"✓ Ingestion completed!")
    print(f"Total documents inserted: {total_inserted}/{len(problems)}")
    print(f"{'='*50}\n")
    
    # Get statistics
    try:
        stats = await vector_store.get_statistics()
        print("Knowledge Base Statistics:")
        print(f"  Total documents: {stats['total_documents']}")
        print(f"  Topics distribution: {stats.get('topics', {})}")
    except Exception as e:
        print(f"Could not retrieve statistics: {e}")


async def test_search_after_import():
    """Test search functionality with imported data."""
    print("\n" + "="*50)
    print("Testing search with imported data...")
    print("="*50 + "\n")
    
    vector_store = SupabaseVectorStore()
    
    test_queries = [
        "How much money does someone make?",
        "Calculate total cost or price",
        "How many items in total?"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            results = await vector_store.similarity_search(query, k=3)
            
            if results:
                print(f"Found {len(results)} results:")
                for idx, result in enumerate(results, 1):
                    question = result.get('question', 'N/A')
                    similarity = result.get('similarity', 0)
                    print(f"  {idx}. (similarity: {similarity:.3f}) {question[:80]}...")
            else:
                print("  No results found")
        except Exception as e:
            print(f"  Error: {e}")
        
        print("-" * 50)


def main():
    """Main entry point."""
    print("="*50)
    print("JSONL Data Ingestion for Math Agent")
    print("="*50 + "\n")
    
    if len(sys.argv) < 2:
        print("Usage: python ingest_jsonl.py <path_to_jsonl_file> [batch_size]")
        print("\nExample:")
        print("  python ingest_jsonl.py data/gsm8k_train.jsonl")
        print("  python ingest_jsonl.py data/math_problems.jsonl 100")
        print("\nExpected JSONL format:")
        print('  {"question": "...", "answer": "..."}')
        print('  One JSON object per line')
        sys.exit(1)
    
    filepath = sys.argv[1]
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    # Run ingestion
    asyncio.run(ingest_jsonl_data(filepath, batch_size))
    
    # Run search test
    try:
        asyncio.run(test_search_after_import())
    except Exception as e:
        print(f"Search test skipped: {e}")


if __name__ == "__main__":
    main()

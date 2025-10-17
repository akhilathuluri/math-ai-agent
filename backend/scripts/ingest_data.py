"""Script to ingest mathematical problems into the knowledge base."""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.vectorstore import SupabaseVectorStore

# Sample mathematical problems for the knowledge base
# In production, this would load from a larger dataset like MATH, GSM8K, or Khan Academy

SAMPLE_MATH_PROBLEMS = [
    {
        "question": "Solve the quadratic equation: x² + 5x + 6 = 0",
        "answer": "x = -2 or x = -3",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "Factor the quadratic: (x + 2)(x + 3) = 0"},
                {"step": 2, "description": "Apply zero product property: x + 2 = 0 or x + 3 = 0"},
                {"step": 3, "description": "Solve each equation: x = -2 or x = -3"}
            ]
        },
        "topic": "algebra",
        "difficulty": "easy",
        "source": "sample_dataset"
    },
    {
        "question": "What is the derivative of f(x) = 3x² + 2x - 5?",
        "answer": "f'(x) = 6x + 2",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "Apply power rule to each term"},
                {"step": 2, "description": "d/dx(3x²) = 6x"},
                {"step": 3, "description": "d/dx(2x) = 2"},
                {"step": 4, "description": "d/dx(-5) = 0"},
                {"step": 5, "description": "Combine: f'(x) = 6x + 2"}
            ]
        },
        "topic": "calculus",
        "difficulty": "easy",
        "source": "sample_dataset"
    },
    {
        "question": "Find the area of a circle with radius 5 units",
        "answer": "The area is 25π square units or approximately 78.54 square units",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "Use the formula A = πr²"},
                {"step": 2, "description": "Substitute r = 5: A = π(5)²"},
                {"step": 3, "description": "Calculate: A = 25π"},
                {"step": 4, "description": "Approximate: A ≈ 78.54 square units"}
            ]
        },
        "topic": "geometry",
        "difficulty": "easy",
        "source": "sample_dataset"
    },
    {
        "question": "Calculate the sum of the first 10 natural numbers",
        "answer": "The sum is 55",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "Use the formula: Sum = n(n+1)/2"},
                {"step": 2, "description": "Substitute n = 10: Sum = 10(10+1)/2"},
                {"step": 3, "description": "Calculate: Sum = 10(11)/2 = 110/2"},
                {"step": 4, "description": "Final answer: Sum = 55"}
            ]
        },
        "topic": "arithmetic",
        "difficulty": "easy",
        "source": "sample_dataset"
    },
    {
        "question": "Solve for x: 2x + 5 = 13",
        "answer": "x = 4",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "Subtract 5 from both sides: 2x = 8"},
                {"step": 2, "description": "Divide both sides by 2: x = 4"}
            ]
        },
        "topic": "algebra",
        "difficulty": "easy",
        "source": "sample_dataset"
    },
    {
        "question": "What is the value of sin(30°)?",
        "answer": "sin(30°) = 1/2 or 0.5",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "Recall the special angle: 30° = π/6 radians"},
                {"step": 2, "description": "Use the unit circle or 30-60-90 triangle"},
                {"step": 3, "description": "sin(30°) = opposite/hypotenuse = 1/2"}
            ]
        },
        "topic": "trigonometry",
        "difficulty": "easy",
        "source": "sample_dataset"
    },
    {
        "question": "Find the mean of the dataset: 4, 8, 6, 5, 7",
        "answer": "The mean is 6",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "Sum all values: 4 + 8 + 6 + 5 + 7 = 30"},
                {"step": 2, "description": "Count the number of values: n = 5"},
                {"step": 3, "description": "Divide sum by count: 30/5 = 6"}
            ]
        },
        "topic": "statistics",
        "difficulty": "easy",
        "source": "sample_dataset"
    },
    {
        "question": "Simplify: 3(x + 4) - 2(x - 1)",
        "answer": "x + 14",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "Distribute: 3x + 12 - 2x + 2"},
                {"step": 2, "description": "Combine like terms: (3x - 2x) + (12 + 2)"},
                {"step": 3, "description": "Simplify: x + 14"}
            ]
        },
        "topic": "algebra",
        "difficulty": "easy",
        "source": "sample_dataset"
    },
    {
        "question": "What is the Pythagorean theorem?",
        "answer": "The Pythagorean theorem states that in a right triangle, a² + b² = c², where c is the hypotenuse",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "Identify the components: a and b are the legs of the right triangle"},
                {"step": 2, "description": "c is the hypotenuse (longest side opposite the right angle)"},
                {"step": 3, "description": "The relationship: a² + b² = c²"}
            ]
        },
        "topic": "geometry",
        "difficulty": "easy",
        "source": "sample_dataset"
    },
    {
        "question": "Integrate ∫2x dx",
        "answer": "x² + C, where C is the constant of integration",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "Apply the power rule for integration: ∫x^n dx = x^(n+1)/(n+1) + C"},
                {"step": 2, "description": "∫2x dx = 2∫x dx"},
                {"step": 3, "description": "= 2 × (x²/2) + C"},
                {"step": 4, "description": "= x² + C"}
            ]
        },
        "topic": "calculus",
        "difficulty": "easy",
        "source": "sample_dataset"
    },
    {
        "question": "Factor completely: x² - 9",
        "answer": "(x + 3)(x - 3)",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "Recognize difference of squares: a² - b² = (a + b)(a - b)"},
                {"step": 2, "description": "Identify: x² - 9 = x² - 3²"},
                {"step": 3, "description": "Apply formula: (x + 3)(x - 3)"}
            ]
        },
        "topic": "algebra",
        "difficulty": "easy",
        "source": "sample_dataset"
    },
    {
        "question": "Convert 0.75 to a fraction",
        "answer": "3/4",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "Write as fraction: 0.75 = 75/100"},
                {"step": 2, "description": "Find GCD of 75 and 100: GCD = 25"},
                {"step": 3, "description": "Divide both by GCD: 75÷25 / 100÷25 = 3/4"}
            ]
        },
        "topic": "arithmetic",
        "difficulty": "easy",
        "source": "sample_dataset"
    },
    {
        "question": "What is the slope-intercept form of a linear equation?",
        "answer": "y = mx + b, where m is the slope and b is the y-intercept",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "General form: y = mx + b"},
                {"step": 2, "description": "m represents the slope (rate of change)"},
                {"step": 3, "description": "b represents the y-intercept (where line crosses y-axis)"}
            ]
        },
        "topic": "algebra",
        "difficulty": "easy",
        "source": "sample_dataset"
    },
    {
        "question": "Find the volume of a cube with side length 3 cm",
        "answer": "27 cubic centimeters",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "Use the formula: V = s³"},
                {"step": 2, "description": "Substitute s = 3: V = 3³"},
                {"step": 3, "description": "Calculate: V = 27 cm³"}
            ]
        },
        "topic": "geometry",
        "difficulty": "easy",
        "source": "sample_dataset"
    },
    {
        "question": "What is the probability of rolling a 6 on a fair die?",
        "answer": "1/6 or approximately 0.167 or 16.7%",
        "solution_steps": {
            "steps": [
                {"step": 1, "description": "Count favorable outcomes: 1 (rolling a 6)"},
                {"step": 2, "description": "Count total possible outcomes: 6 (1, 2, 3, 4, 5, 6)"},
                {"step": 3, "description": "Calculate probability: P = 1/6"},
                {"step": 4, "description": "Convert to decimal: ≈ 0.167 or 16.7%"}
            ]
        },
        "topic": "probability",
        "difficulty": "easy",
        "source": "sample_dataset"
    }
]


async def ingest_data():
    """Ingest sample data into the knowledge base."""
    print("Starting data ingestion...")
    
    try:
        vector_store = SupabaseVectorStore()
        
        print(f"Ingesting {len(SAMPLE_MATH_PROBLEMS)} mathematical problems...")
        
        inserted_ids = await vector_store.add_documents(SAMPLE_MATH_PROBLEMS)
        
        print(f"✓ Successfully ingested {len(inserted_ids)} documents")
        print(f"Document IDs: {inserted_ids}")
        
        # Get statistics
        stats = await vector_store.get_statistics()
        print(f"\nKnowledge Base Statistics:")
        print(f"Total documents: {stats['total_documents']}")
        print(f"Topics: {stats['topics']}")
        
        print("\n✓ Data ingestion completed successfully!")
        
    except Exception as e:
        print(f"✗ Error during ingestion: {e}")
        import traceback
        traceback.print_exc()


async def test_search():
    """Test the search functionality."""
    print("\n" + "="*50)
    print("Testing search functionality...")
    print("="*50 + "\n")
    
    try:
        vector_store = SupabaseVectorStore()
        
        test_queries = [
            "How do I solve a quadratic equation?",
            "What is a derivative?",
            "How to find the area of a circle?"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            results = await vector_store.similarity_search(query, k=2)
            
            if results:
                print(f"Found {len(results)} results:")
                for idx, result in enumerate(results, 1):
                    print(f"\n  Result {idx}:")
                    print(f"  Question: {result.get('question', 'N/A')}")
                    print(f"  Topic: {result.get('topic', 'N/A')}")
                    print(f"  Similarity: {result.get('similarity', 0):.3f}")
            else:
                print("  No results found")
            
            print("-" * 50)
        
    except Exception as e:
        print(f"✗ Error during search test: {e}")
        import traceback
        traceback.print_exc()


def print_sql_setup():
    """Print SQL setup instructions."""
    from app.vectorstore import MATCH_DOCUMENTS_RPC
    
    print("\n" + "="*50)
    print("SUPABASE SETUP INSTRUCTIONS")
    print("="*50 + "\n")
    
    print("1. Go to your Supabase project SQL Editor")
    print("2. Run the following SQL to set up the schema:\n")
    
    vector_store = SupabaseVectorStore()
    schema_sql = asyncio.run(vector_store.initialize_schema())
    print(schema_sql)
    
    print("\n3. Then run this SQL to create the search function:\n")
    print(MATCH_DOCUMENTS_RPC)
    
    print("\n" + "="*50)
    print("After running the SQL, you can run this script to ingest data")
    print("="*50 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--sql":
        print_sql_setup()
    else:
        print("Math Agent Knowledge Base Ingestion")
        print("="*50 + "\n")
        
        # Run ingestion
        asyncio.run(ingest_data())
        
        # Run search test
        asyncio.run(test_search())

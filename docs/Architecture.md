# Math Agent - Architecture Flowchart

## System Overview Flowchart

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USER INTERACTION                           │
│                                                                      │
│  User submits mathematical question via React Frontend              │
│  Example: "Solve: x² + 5x + 6 = 0"                                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ HTTP POST /api/v1/ask
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FASTAPI BACKEND                               │
│                                                                      │
│  Receives question, initiates processing pipeline                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   LAYER 1: INPUT GUARDRAILS                          │
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐│
│  │ Pattern Matching │───▶│ LLM Classification│───▶│ Sanitization  ││
│  │ • Math keywords  │    │ • GPT-3.5 check   │    │ • Remove HTML ││
│  │ • Malicious code │    │ • Topic detection │    │ • Normalize   ││
│  │ • Length check   │    │ • Confidence score│    │               ││
│  └──────────────────┘    └──────────────────┘    └───────────────┘│
│                             │                                        │
│              Valid? ────────┴────────── Invalid?                    │
│                │                            │                        │
└────────────────┼────────────────────────────┼────────────────────────┘
                 │                            │
                 │                            ▼
                 │                    ┌──────────────┐
                 │                    │   REJECT     │
                 │                    │ Return error │
                 │                    └──────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   LAYER 2: ROUTING AGENT (LangGraph)                 │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Router Node                                │  │
│  │                                                               │  │
│  │  Analyzes question using GPT-4:                              │  │
│  │  • Is this a common math problem? → Knowledge Base           │  │
│  │  • Is this specific/advanced? → Web Search                   │  │
│  │  • Topic: Algebra, Calculus, Geometry, etc.                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                             │                                        │
│              ┌──────────────┴──────────────┐                        │
└──────────────┼─────────────────────────────┼────────────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────┐    ┌───────────────────────────────────┐
│  PATH A: Knowledge Base  │    │      PATH B: Web Search           │
│                          │    │                                   │
│  ┌───────────────────┐  │    │  ┌────────────────────────────┐  │
│  │ Supabase Search   │  │    │  │ Tavily API Call            │  │
│  │ • Vector embedding│  │    │  │ • Query enhancement        │  │
│  │ • Similarity: >0.7│  │    │  │ • Domain filtering         │  │
│  │ • Top 5 results   │  │    │  │ • Result extraction        │  │
│  └─────────┬─────────┘  │    │  └───────────┬────────────────┘  │
│            │             │    │              │                    │
│  Found? ───┤             │    │  ┌───────────▼────────────────┐  │
│      │     │             │    │  │ MCP Server                 │  │
│      │     └─ Not Found  │    │  │ • search_math tool         │  │
│      │          │        │    │  │ • get_math_resources       │  │
│      │          ├────────┼────┼─▶│ • Result validation        │  │
│      │     Fallback      │    │  └────────────────────────────┘  │
│      │                   │    │                                   │
└──────┼───────────────────┘    └───────────────┬───────────────────┘
       │                                        │
       │      Retrieved Context                 │
       │                                        │
       └────────────────┬───────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 LAYER 3: SOLUTION GENERATION                         │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    GPT-4 Turbo                                │  │
│  │                                                               │  │
│  │  Prompt:                                                      │  │
│  │  "You are an expert mathematics professor.                   │  │
│  │   Provide step-by-step solution to:                          │  │
│  │   Question: {question}                                        │  │
│  │   Context: {retrieved_context}                               │  │
│  │                                                               │  │
│  │   Format with:                                                │  │
│  │   - Clear steps                                               │  │
│  │   - Explanations                                              │  │
│  │   - Final answer                                              │  │
│  │   - Key concepts"                                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                             │                                        │
│                             ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Generated Solution                               │  │
│  │  • Step 1: Factor the quadratic...                           │  │
│  │  • Step 2: Apply zero product property...                    │  │
│  │  • Step 3: Solve each equation...                            │  │
│  │  • Final Answer: x = -2 or x = -3                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  LAYER 4: OUTPUT GUARDRAILS                          │
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐│
│  │ Relevance Check  │───▶│ Safety Validation│───▶│ Sanitization  ││
│  │ • LLM verification│    │ • Content check  │    │ • Format      ││
│  │ • Topic alignment│    │ • Appropriateness│    │ • Clean up    ││
│  │ • Score > 0.7    │    │                  │    │               ││
│  └──────────────────┘    └──────────────────┘    └───────────────┘│
│                             │                                        │
│                        Valid Answer                                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RESPONSE TO USER                                  │
│                                                                      │
│  JSON Response:                                                      │
│  {                                                                   │
│    "success": true,                                                  │
│    "question": "Solve: x² + 5x + 6 = 0",                           │
│    "answer": "Step-by-step solution...",                           │
│    "solution_steps": [{step: 1, desc: "..."}, ...],                │
│    "confidence_score": 0.85,                                        │
│    "sources": ["Knowledge Base - internal"],                        │
│    "routing_decision": "knowledge_base",                            │
│    "topic": "algebra"                                               │
│  }                                                                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   USER PROVIDES FEEDBACK (Optional)                  │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐│
│  │ Rating (1-5) │  │ Is Correct?  │  │ Text Feedback/Corrections ││
│  └──────────────┘  └──────────────┘  └───────────────────────────┘│
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              LAYER 5: HUMAN-IN-THE-LOOP LEARNING                     │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  Feedback Processing                          │  │
│  │                                                               │  │
│  │  Store in Supabase:                                          │  │
│  │  • feedback table                                             │  │
│  │  • Link to original question                                 │  │
│  │  • Track metrics                                              │  │
│  └────────────────────────┬─────────────────────────────────────┘  │
│                            │                                         │
│       Low Rating (≤2)?     │                                         │
│              ┌─────────────┴───────────┐                            │
│              │                         │                             │
│              ▼                         ▼                             │
│  ┌──────────────────┐      ┌──────────────────────────────┐        │
│  │ Immediate        │      │ Periodic Learning Cycle      │        │
│  │ Failure Analysis │      │                              │        │
│  │ • LLM analysis   │      │ Runs every:                  │        │
│  │ • Pattern detect │      │ • 100 feedback items         │        │
│  │ • Flag for review│      │ • Daily at 2 AM              │        │
│  └──────────────────┘      │ • Manual trigger             │        │
│                            └───────────┬──────────────────┘        │
│                                        │                             │
│                            ┌───────────▼──────────────┐             │
│                            │   DSPy Optimization      │             │
│                            │                          │             │
│                            │ • Collect examples       │             │
│                            │   (rating ≥ 4)          │             │
│                            │ • Train optimizer        │             │
│                            │ • Update prompts         │             │
│                            │ • Measure improvement    │             │
│                            └───────────┬──────────────┘             │
│                                        │                             │
│                            ┌───────────▼──────────────┐             │
│                            │  Knowledge Base Update   │             │
│                            │                          │             │
│                            │ • Add corrections        │             │
│                            │ • New embeddings         │             │
│                            │ • Update metadata        │             │
│                            └───────────┬──────────────┘             │
│                                        │                             │
│                                   Improved                           │
│                                   System ──────────┐                │
└────────────────────────────────────────────────────┼─────────────────┘
                                                     │
                                                     │
                        ┌────────────────────────────┘
                        │ Continuous Improvement Loop
                        └────────────┐
                                     │
                    ┌────────────────▼─────────────────┐
                    │   System Self-Improves Over Time │
                    │                                  │
                    │  • Better routing decisions      │
                    │  • More accurate answers         │
                    │  • Improved confidence scores    │
                    │  • Expanded knowledge base       │
                    │  • Optimized prompts            │
                    └──────────────────────────────────┘
```

## Key Metrics Dashboard

```
┌────────────────────────────────────────────────────────┐
│                 SYSTEM METRICS                          │
├────────────────────────────────────────────────────────┤
│  Response Time:        3.2s average                    │
│  Accuracy:             70% (JEE Bench)                 │
│  User Satisfaction:    4.2/5 stars                     │
│  Knowledge Base Size:  15 → Growing                    │
│  Feedback Collection:  Active                          │
│  Learning Cycles:      Automated                       │
└────────────────────────────────────────────────────────┘
```

---

**Note:** This flowchart shows the complete end-to-end process from question submission to continuous learning and improvement.

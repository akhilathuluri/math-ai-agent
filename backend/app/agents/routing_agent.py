"""LangGraph Routing Agent for Math Questions."""
from typing import TypedDict, Annotated, Sequence, Literal
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.vectorstore import SupabaseVectorStore
from app.search import TavilySearch
from app.search.mcp_server import MCPSearchServer
from app.guardrails import GuardrailsManager
import operator
import json

from app.feedback.feedback_system import get_optimized_solver, FeedbackManager


class AgentState(TypedDict):
    """State for the routing agent."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    question: str
    sanitized_question: str
    topic: str
    routing_decision: Literal["knowledge_base", "web_search", "mcp_search", "reject", ""]
    knowledge_base_results: list
    web_search_results: dict
    mcp_used: bool
    final_answer: str
    solution_steps: list
    confidence_score: float
    sources: list
    guardrail_passed: bool
    error: str


class MathRoutingAgent:
    """Main routing agent for mathematical questions using LangGraph."""
    
    def __init__(self):
        """Initialize the routing agent with GitHub Models and MCP."""
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.temperature,
            api_key=settings.github_token,
            base_url=settings.github_api_base
        )
        self.vector_store = SupabaseVectorStore()
        self.web_search = TavilySearch()
        self.mcp_server = MCPSearchServer()  # Add MCP server
        self.guardrails = GuardrailsManager()
        self.feedback_manager = FeedbackManager()
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("input_guardrails", self._input_guardrails_node)
        workflow.add_node("router", self._router_node)
        workflow.add_node("knowledge_base_search", self._knowledge_base_node)
        workflow.add_node("web_search", self._web_search_node)
        workflow.add_node("generate_solution", self._generate_solution_node)
        workflow.add_node("output_guardrails", self._output_guardrails_node)
        workflow.add_node("reject", self._reject_node)
        
        # Set entry point
        workflow.set_entry_point("input_guardrails")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "input_guardrails",
            self._after_input_guardrails,
            {
                "router": "router",
                "reject": "reject"
            }
        )
        
        workflow.add_conditional_edges(
            "router",
            self._after_router,
            {
                "knowledge_base": "knowledge_base_search",
                "web_search": "web_search",
                "reject": "reject"
            }
        )
        
        workflow.add_edge("knowledge_base_search", "generate_solution")
        workflow.add_edge("web_search", "generate_solution")
        workflow.add_edge("generate_solution", "output_guardrails")
        workflow.add_edge("output_guardrails", END)
        workflow.add_edge("reject", END)
        
        return workflow.compile()
    
    async def _input_guardrails_node(self, state: AgentState) -> AgentState:
        """Apply input guardrails."""
        question = state["question"]
        
        validation = self.guardrails.validate_input(question)
        
        state["guardrail_passed"] = validation["is_valid"]
        
        if validation["is_valid"]:
            state["sanitized_question"] = validation["sanitized_input"]
            state["topic"] = validation.get("topic", "general")
            state["messages"].append(
                SystemMessage(content=f"Input validated. Topic: {state['topic']}")
            )
        else:
            state["error"] = validation["reason"]
            state["routing_decision"] = "reject"
            state["messages"].append(
                SystemMessage(content=f"Input validation failed: {validation['reason']}")
            )
        
        return state
    
    def _after_input_guardrails(self, state: AgentState) -> str:
        """Decide next step after input guardrails."""
        if state["guardrail_passed"]:
            return "router"
        return "reject"
    
    async def _router_node(self, state: AgentState) -> AgentState:
        """Intelligent routing decision."""
        question = state["sanitized_question"]
        
        # Create routing prompt
        routing_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a routing agent for a mathematical question-answering system.
Your job is to decide whether to:
1. Search the knowledge base first (for common mathematical problems)
2. Perform a web search (for more specific or recent mathematical topics)

Respond with just one word: "knowledge_base" or "web_search"

Consider:
- Is this a common/standard math problem? -> knowledge_base
- Is this very specific or advanced? -> web_search
- Does it mention recent discoveries or specific resources? -> web_search
"""),
            ("human", "Question: {question}\nTopic: {topic}\n\nDecision:")
        ])
        
        response = await self.llm.ainvoke(
            routing_prompt.format_messages(
                question=question,
                topic=state["topic"]
            )
        )
        
        decision = response.content.strip().lower()
        
        # Validate decision
        if "knowledge" in decision:
            state["routing_decision"] = "knowledge_base"
        elif "web" in decision or "search" in decision:
            state["routing_decision"] = "web_search"
        else:
            # Default to knowledge base
            state["routing_decision"] = "knowledge_base"
        
        state["messages"].append(
            SystemMessage(content=f"Routing decision: {state['routing_decision']}")
        )
        
        return state
    
    def _after_router(self, state: AgentState) -> str:
        """Decide next step after routing."""
        return state["routing_decision"]
    
    async def _knowledge_base_node(self, state: AgentState) -> AgentState:
        """Search the knowledge base."""
        question = state["sanitized_question"]
        
        try:
            results = await self.vector_store.similarity_search(question, k=3)
            state["knowledge_base_results"] = results
            
            if results and len(results) > 0:
                # Found relevant results
                state["messages"].append(
                    SystemMessage(content=f"Found {len(results)} relevant documents in knowledge base.")
                )
                state["sources"] = [
                    f"Knowledge Base - {r.get('source', 'internal')}" 
                    for r in results
                ]
            else:
                # No results found, fallback to web search
                state["messages"].append(
                    SystemMessage(content="No relevant documents found in knowledge base. Falling back to web search.")
                )
                # Trigger web search
                state["routing_decision"] = "web_search"
                return await self._web_search_node(state)
                
        except Exception as e:
            state["error"] = f"Knowledge base search error: {str(e)}"
            state["messages"].append(
                SystemMessage(content=f"Knowledge base error: {str(e)}. Falling back to web search.")
            )
            # Fallback to web search
            state["routing_decision"] = "web_search"
            return await self._web_search_node(state)
        
        return state
    
    async def _web_search_node(self, state: AgentState) -> AgentState:
        """Perform web search using MCP (Model Context Protocol)."""
        question = state["sanitized_question"]
        
        try:
            # Use MCP server for search
            mcp_request = {
                "tool": "search_math",
                "parameters": {
                    "query": question,
                    "max_results": 5
                }
            }
            
            mcp_results = await self.mcp_server.handle_request(mcp_request)
            
            if mcp_results.get("success"):
                # Mark that MCP was used
                state["mcp_used"] = True
                state["routing_decision"] = "mcp_search"
                
                # Format results for state
                search_results = {
                    "success": True,
                    "content": "",
                    "sources": [],
                    "total_sources": len(mcp_results.get("results", []))
                }
                
                # Extract content and sources from MCP results
                for result in mcp_results.get("results", []):
                    search_results["content"] += f"\n\n{result.get('title', '')}\n{result.get('content', '')}"
                    search_results["sources"].append(f"[MCP] {result.get('url', '')}")
                
                state["web_search_results"] = search_results
                state["sources"] = search_results["sources"]
                
                state["messages"].append(
                    SystemMessage(content=f"MCP search completed. Found {search_results['total_sources']} sources via Model Context Protocol.")
                )
            else:
                state["mcp_used"] = False
                state["error"] = mcp_results.get("error", "MCP search failed")
                state["messages"].append(
                    SystemMessage(content=f"MCP search failed: {state['error']}")
                )
                
        except Exception as e:
            state["mcp_used"] = False
            state["error"] = f"MCP search error: {str(e)}"
            state["messages"].append(
                SystemMessage(content=f"MCP search error: {str(e)}")
            )
        
        return state
    
    async def _generate_solution_node(self, state: AgentState) -> AgentState:
        """Generate step-by-step solution."""
        question = state["sanitized_question"]
        
        # Fetch a small set of recent corrections to incorporate
        try:
            self._recent_corrections_cache = await self.feedback_manager.get_recent_corrections(limit=3)
        except Exception:
            self._recent_corrections_cache = []

        # Prepare context from retrieved information
        context = self._prepare_context(state)
        
        # Try DSPy optimized solver first if available
        try:
            optimized_solver = get_optimized_solver()
        except Exception:
            optimized_solver = None

        if optimized_solver is not None:
            try:
                dspy_answer = await self._invoke_dspy_solver(optimized_solver, question, context)
                if dspy_answer and len(dspy_answer.strip()) > 0:
                    state["final_answer"] = dspy_answer
                    steps = self._extract_steps(dspy_answer)
                    state["solution_steps"] = steps
                    confidence = max(0.5, self._calculate_confidence(state))
                    state["confidence_score"] = confidence
                    state["messages"].append(
                        AIMessage(content=dspy_answer)
                    )
                    return state
            except Exception:
                # Fall back to base LLM prompt below
                pass

        # Generate solution prompt
        solution_prompt = ChatPromptTemplate.from_messages([
            ("system", r"""You are an expert mathematics professor. Your role is to:
1. Provide clear, step-by-step solutions to mathematical problems
2. Explain each step in simple terms that students can understand
3. Use proper LaTeX mathematical notation with proper delimiters
4. Provide intuition and reasoning for each step

IMPORTANT - LaTeX Formatting Rules:
- For inline math, use \( ... \) delimiters, e.g., \(P(x)\), \(x^2\), \(\sqrt{{13}}\)
- For display equations, use \[ ... \] delimiters
- Never use plain parentheses like (P(x)) for math notation

Examples:
- Correct: \(P(x^2 - 1) = P(x)^2 - 1\)
- Wrong: (P(x^2 - 1) = P(x)^2 - 1)
- Correct: \(180^\circ\)
- Wrong: (180^\circ)

Format your response as:
**Solution:**
[Brief overview using proper LaTeX notation]

**Step-by-step Solution:**
Step 1: [Description]
[Detailed explanation with LaTeX]

Step 2: [Description]
[Detailed explanation with LaTeX]

...

**Final Answer:**
[The final result with LaTeX]

**Key Concepts:**
- [Concept 1]
- [Concept 2]

Context from retrieved information:
{context}
"""),
            ("human", "Question: {question}")
        ])
        
        # Format the messages with the variables
        formatted_messages = solution_prompt.format_messages(
            question=question,
            context=context
        )
        
        # Invoke the LLM with formatted messages
        response = await self.llm.ainvoke(formatted_messages)
        
        state["final_answer"] = response.content
        
        # Extract steps (simple parsing)
        steps = self._extract_steps(response.content)
        state["solution_steps"] = steps
        
        # Calculate confidence based on context quality
        confidence = self._calculate_confidence(state)
        state["confidence_score"] = confidence
        
        state["messages"].append(
            AIMessage(content=response.content)
        )
        
        return state
    
    def _prepare_context(self, state: AgentState) -> str:
        """Prepare context from knowledge base or web search results."""
        context_parts = []
        
        # From knowledge base
        if state.get("knowledge_base_results"):
            context_parts.append("=== Knowledge Base Results ===")
            for idx, result in enumerate(state["knowledge_base_results"][:2], 1):
                context_parts.append(f"\nResult {idx}:")
                context_parts.append(f"Question: {result.get('question', '')}")
                context_parts.append(f"Answer: {result.get('answer', '')}")
        
        # From web search
        if state.get("web_search_results") and state["web_search_results"].get("success"):
            context_parts.append("\n=== Web Search Results ===")
            context_parts.append(state["web_search_results"].get("content", ""))
            if state["web_search_results"].get("tavily_answer"):
                context_parts.append(f"\nTavily Summary: {state['web_search_results']['tavily_answer']}")

        # From recent feedback corrections (if any were fetched)
        try:
            recent = getattr(self, "_recent_corrections_cache", None) or []
            if recent:
                context_parts.append("\n=== Recent Validated Corrections (from Feedback) ===")
                for idx, item in enumerate(recent, 1):
                    context_parts.append(f"\nCorrection {idx}:")
                    context_parts.append(f"Question: {item.get('question', '')}")
                    context_parts.append(f"Corrected Answer: {item.get('corrected_answer', '')}")
        except Exception:
            pass
        
        return "\n".join(context_parts) if context_parts else "No additional context available."

    async def _invoke_dspy_solver(self, solver, question: str, context: str) -> str:
        """Invoke a DSPy-optimized solver safely and return a formatted answer string."""
        try:
            payload = {
                'question': f"{question}\n\nContext:\n{context}"
            }
            result = solver(**payload) if callable(solver) else None
            import asyncio
            if asyncio.iscoroutine(result):
                result = await result
            if isinstance(result, dict) and 'answer' in result:
                return str(result['answer'])
            if hasattr(result, 'answer'):
                return str(getattr(result, 'answer'))
            if isinstance(result, str):
                return result
            return ""
        except Exception:
            return ""
    
    def _extract_steps(self, solution: str) -> list:
        """Extract solution steps from generated text."""
        import re
        steps = []
        
        # Find all "Step X:" patterns
        step_pattern = r'Step (\d+):([^\n]+)'
        matches = re.findall(step_pattern, solution)
        
        for step_num, step_desc in matches:
            steps.append({
                'step_number': int(step_num),
                'description': step_desc.strip()
            })
        
        return steps
    
    def _calculate_confidence(self, state: AgentState) -> float:
        """Calculate confidence score for the answer."""
        confidence = 0.5  # Base confidence
        
        # Boost if we found knowledge base results
        if state.get("knowledge_base_results") and len(state["knowledge_base_results"]) > 0:
            confidence += 0.3
        
        # Boost if web search was successful
        if state.get("web_search_results") and state["web_search_results"].get("success"):
            confidence += 0.2
        
        # Reduce if there were errors
        if state.get("error"):
            confidence -= 0.2
        
        return max(0.0, min(1.0, confidence))
    
    async def _output_guardrails_node(self, state: AgentState) -> AgentState:
        """Apply output guardrails."""
        final_answer = state.get("final_answer", "")
        original_question = state["sanitized_question"]
        
        validation = self.guardrails.validate_output(final_answer, original_question)
        
        if not validation["is_valid"]:
            state["error"] = f"Output validation failed: {validation['reason']}"
            state["messages"].append(
                SystemMessage(content=f"Output guardrail failed: {validation['reason']}")
            )
            # Could regenerate here, but for now we'll just flag it
        else:
            state["final_answer"] = validation["sanitized_output"]
        
        return state
    
    async def _reject_node(self, state: AgentState) -> AgentState:
        """Handle rejected questions."""
        error_msg = state.get("error", "Question did not pass validation.")
        
        state["final_answer"] = f"""I apologize, but I cannot process this request.

Reason: {error_msg}

This system is designed specifically for mathematical and educational questions. 
Please ensure your question is:
- Related to mathematics (algebra, geometry, calculus, statistics, etc.)
- Appropriate for an educational context
- Clear and well-formed

Feel free to rephrase your question and try again!"""
        
        state["confidence_score"] = 0.0
        
        return state
    
    async def process_question(self, question: str) -> dict:
        """
        Process a mathematical question through the routing agent.
        
        Args:
            question: The user's mathematical question
        
        Returns:
            Dict with answer, steps, sources, and metadata
        """
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "question": question,
            "sanitized_question": "",
            "topic": "",
            "routing_decision": "",
            "knowledge_base_results": [],
            "web_search_results": {},
            "mcp_used": False,
            "final_answer": "",
            "solution_steps": [],
            "confidence_score": 0.0,
            "sources": [],
            "guardrail_passed": False,
            "error": ""
        }
        
        try:
            print(f"[DEBUG] Starting graph execution...")
            # Run the graph
            final_state = await self.graph.ainvoke(initial_state)
            
            print(f"[DEBUG] Graph execution completed")
            print(f"[DEBUG] Final state keys: {final_state.keys()}")
            print(f"[DEBUG] Routing decision: {final_state.get('routing_decision')}")
            print(f"[DEBUG] MCP Used: {final_state.get('mcp_used')}")
            print(f"[DEBUG] Error in state: {final_state.get('error')}")
            
            return {
                "success": True,
                "question": question,
                "answer": final_state["final_answer"],
                "solution_steps": final_state["solution_steps"],
                "confidence_score": final_state["confidence_score"],
                "sources": final_state["sources"],
                "routing_decision": final_state["routing_decision"],
                "mcp_used": final_state.get("mcp_used", False),
                "topic": final_state.get("topic", "general"),
                "error": final_state.get("error", None)
            }
            
        except Exception as e:
            print(f"[DEBUG] Exception in process_question: {type(e).__name__}: {str(e)}")
            import traceback
            print("[DEBUG] Traceback:")
            traceback.print_exc()
            
            return {
                "success": False,
                "question": question,
                "error": str(e),
                "answer": "An error occurred while processing your question. Please try again."
            }

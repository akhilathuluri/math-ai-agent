"""MCP (Model Context Protocol) Server for Web Search."""
import json
from typing import Any, Dict
import asyncio
from tavily import TavilyClient
from app.config import settings


class MCPSearchServer:
    """
    MCP Server implementation for web search capabilities.
    
    This provides a standardized interface for search operations
    following the Model Context Protocol specification.
    """
    
    def __init__(self):
        """Initialize MCP search server."""
        self.tavily_client = TavilyClient(api_key=settings.tavily_api_key)
        self.tools = self._register_tools()
    
    def _register_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register available MCP tools."""
        return {
            "search_math": {
                "description": "Search for mathematical content on the web",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The mathematical question to search for"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                },
                "handler": self.search_math
            },
            "get_math_resources": {
                "description": "Get educational math resources for a topic",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Mathematical topic (e.g., calculus, algebra)"
                        }
                    },
                    "required": ["topic"]
                },
                "handler": self.get_math_resources
            }
        }
    
    async def search_math(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Search for mathematical content.
        
        Args:
            query: Mathematical question
            max_results: Number of results to return
        
        Returns:
            Search results in MCP format
        """
        try:
            # Enhance query for math context
            enhanced_query = f"mathematics: {query}"
            
            # Perform search using Tavily
            response = self.tavily_client.search(
                query=enhanced_query,
                max_results=max_results,
                search_depth="advanced",
                include_domains=[
                    "khanacademy.org",
                    "mathworld.wolfram.com",
                    "wikipedia.org",
                    "brilliant.org",
                    "math.stackexchange.com"
                ]
            )
            
            # Format results
            formatted_results = []
            for result in response.get('results', []):
                formatted_results.append({
                    "title": result.get('title'),
                    "url": result.get('url'),
                    "content": result.get('content'),
                    "score": result.get('score', 0.0)
                })
            
            return {
                "success": True,
                "query": query,
                "results": formatted_results,
                "total_results": len(formatted_results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_math_resources(self, topic: str) -> Dict[str, Any]:
        """
        Get educational resources for a mathematical topic.
        
        Args:
            topic: Mathematical topic name
        
        Returns:
            List of educational resources
        """
        # Predefined high-quality resources by topic
        resources = {
            "algebra": [
                {
                    "name": "Khan Academy Algebra",
                    "url": "https://www.khanacademy.org/math/algebra",
                    "description": "Comprehensive algebra course with videos and practice"
                },
                {
                    "name": "Purplemath Algebra Lessons",
                    "url": "https://www.purplemath.com/modules/index.htm",
                    "description": "Step-by-step algebra explanations"
                }
            ],
            "calculus": [
                {
                    "name": "Khan Academy Calculus",
                    "url": "https://www.khanacademy.org/math/calculus-1",
                    "description": "Calculus 1 and 2 with interactive exercises"
                },
                {
                    "name": "Paul's Online Math Notes",
                    "url": "https://tutorial.math.lamar.edu/",
                    "description": "Detailed calculus notes and examples"
                }
            ],
            "geometry": [
                {
                    "name": "Khan Academy Geometry",
                    "url": "https://www.khanacademy.org/math/geometry",
                    "description": "Complete geometry course"
                }
            ],
            "statistics": [
                {
                    "name": "Khan Academy Statistics",
                    "url": "https://www.khanacademy.org/math/statistics-probability",
                    "description": "Statistics and probability fundamentals"
                }
            ]
        }
        
        topic_lower = topic.lower()
        topic_resources = resources.get(topic_lower, [])
        
        return {
            "success": True,
            "topic": topic,
            "resources": topic_resources,
            "count": len(topic_resources)
        }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP request.
        
        Args:
            request: MCP request with tool name and parameters
        
        Returns:
            MCP response
        """
        tool_name = request.get('tool')
        parameters = request.get('parameters', {})
        
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }
        
        tool = self.tools[tool_name]
        handler = tool['handler']
        
        try:
            result = await handler(**parameters)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}"
            }
    
    def list_tools(self) -> Dict[str, Any]:
        """
        List available MCP tools.
        
        Returns:
            Dictionary of available tools and their specifications
        """
        tools_spec = {}
        for name, tool in self.tools.items():
            tools_spec[name] = {
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
        
        return {
            "tools": tools_spec,
            "count": len(tools_spec)
        }


# Example usage and testing
async def test_mcp_server():
    """Test the MCP server."""
    server = MCPSearchServer()
    
    print("Available MCP Tools:")
    print(json.dumps(server.list_tools(), indent=2))
    
    print("\n" + "="*50)
    print("Testing search_math tool...")
    result = await server.handle_request({
        "tool": "search_math",
        "parameters": {
            "query": "quadratic equation formula",
            "max_results": 3
        }
    })
    print(json.dumps(result, indent=2))
    
    print("\n" + "="*50)
    print("Testing get_math_resources tool...")
    result = await server.handle_request({
        "tool": "get_math_resources",
        "parameters": {
            "topic": "calculus"
        }
    })
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(test_mcp_server())

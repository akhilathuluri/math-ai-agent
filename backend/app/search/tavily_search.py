"""Tavily Web Search Integration for Math Agent."""
from typing import List, Dict, Any, Optional
from tavily import TavilyClient
from app.config import settings
import re


class TavilySearch:
    """Web search using Tavily API."""
    
    def __init__(self):
        """Initialize Tavily client."""
        self.client = TavilyClient(api_key=settings.tavily_api_key)
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "advanced"
    ) -> Dict[str, Any]:
        """
        Perform web search for mathematical questions.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            search_depth: "basic" or "advanced"
        
        Returns:
            Dict containing search results and metadata
        """
        try:
            # Enhance query for mathematical context
            enhanced_query = self._enhance_math_query(query)
            
            # Perform search
            response = self.client.search(
                query=enhanced_query,
                max_results=max_results,
                search_depth=search_depth,
                include_answer=True,
                include_raw_content=False,
                include_domains=[
                    "khanacademy.org",
                    "mathworld.wolfram.com",
                    "wikipedia.org",
                    "brilliant.org",
                    "mathsisfun.com",
                    "stackexchange.com",
                    "math.stackexchange.com"
                ]
            )
            
            # Extract and format results
            formatted_results = self._format_results(response)
            
            return {
                'success': True,
                'query': query,
                'enhanced_query': enhanced_query,
                'results': formatted_results,
                'answer': response.get('answer', ''),
                'total_results': len(formatted_results)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'results': []
            }
    
    def _enhance_math_query(self, query: str) -> str:
        """Enhance query with mathematical context."""
        # Add mathematical context if not present
        math_keywords = ['math', 'mathematics', 'solve', 'calculate', 'formula']
        query_lower = query.lower()
        
        has_math_context = any(keyword in query_lower for keyword in math_keywords)
        
        if not has_math_context:
            return f"mathematics: {query}"
        
        return query
    
    def _format_results(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format search results for easier processing."""
        results = response.get('results', [])
        
        formatted = []
        for result in results:
            formatted.append({
                'title': result.get('title', ''),
                'url': result.get('url', ''),
                'content': result.get('content', ''),
                'score': result.get('score', 0.0),
                'raw_content': result.get('raw_content', '')
            })
        
        return formatted
    
    async def search_and_extract(
        self,
        query: str,
        max_results: int = 3
    ) -> Dict[str, Any]:
        """
        Search and extract relevant mathematical content.
        
        Returns:
            Dict with extracted content and sources
        """
        search_results = await self.search(query, max_results=max_results)
        
        if not search_results['success']:
            return {
                'success': False,
                'error': search_results.get('error', 'Search failed'),
                'content': None
            }
        
        # Extract relevant content
        extracted_content = self._extract_mathematical_content(
            search_results['results']
        )
        
        return {
            'success': True,
            'content': extracted_content,
            'tavily_answer': search_results.get('answer', ''),
            'sources': [r['url'] for r in search_results['results']],
            'total_sources': search_results['total_results']
        }
    
    def _extract_mathematical_content(
        self,
        results: List[Dict[str, Any]]
    ) -> str:
        """Extract and combine relevant mathematical content from results."""
        content_parts = []
        
        for idx, result in enumerate(results, 1):
            content = result.get('content', '')
            if content:
                # Clean up content
                content = self._clean_content(content)
                
                # Add source reference
                source_info = f"\n[Source {idx}: {result.get('title', 'Unknown')}]\n"
                content_parts.append(source_info + content)
        
        return "\n\n".join(content_parts)
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content."""
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        # Remove special characters that might interfere
        content = re.sub(r'[^\w\s\.\,\!\?\:\;\(\)\[\]\{\}\+\-\*\/\=\^\<\>]', '', content)
        return content.strip()
    
    async def validate_search_result(
        self,
        query: str,
        search_result: str
    ) -> Dict[str, Any]:
        """
        Validate if search result is relevant and trustworthy.
        
        Returns:
            Dict with validation results
        """
        # Check if result contains mathematical content
        has_math = self._contains_mathematical_content(search_result)
        
        # Check quality indicators
        quality_score = self._assess_content_quality(search_result)
        
        is_valid = has_math and quality_score > 0.5
        
        return {
            'is_valid': is_valid,
            'has_mathematical_content': has_math,
            'quality_score': quality_score,
            'reason': 'Valid mathematical content' if is_valid else 'Low quality or non-mathematical content'
        }
    
    def _contains_mathematical_content(self, content: str) -> bool:
        """Check if content contains mathematical information."""
        math_indicators = [
            r'\d+',  # Numbers
            r'equation',
            r'formula',
            r'theorem',
            r'proof',
            r'solution',
            r'calculate',
            r'[+\-*/=]',  # Math operators
        ]
        
        content_lower = content.lower()
        matches = sum(1 for pattern in math_indicators 
                     if re.search(pattern, content_lower))
        
        return matches >= 3
    
    def _assess_content_quality(self, content: str) -> float:
        """Assess the quality of content (0.0 to 1.0)."""
        score = 0.0
        
        # Length check (too short or too long might be low quality)
        length = len(content)
        if 100 < length < 5000:
            score += 0.3
        
        # Contains explanation words
        explanation_words = ['because', 'therefore', 'thus', 'hence', 'since']
        if any(word in content.lower() for word in explanation_words):
            score += 0.2
        
        # Contains step indicators
        step_indicators = ['step', 'first', 'second', 'finally', 'next']
        if any(word in content.lower() for word in step_indicators):
            score += 0.3
        
        # Contains mathematical notation
        if re.search(r'[\d+\-*/=()]', content):
            score += 0.2
        
        return min(score, 1.0)

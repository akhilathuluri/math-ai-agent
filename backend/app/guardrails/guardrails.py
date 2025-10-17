"""Input and Output Guardrails for Math Agent."""
from typing import Dict, Any, Optional, List
from enum import Enum
import re
from openai import OpenAI
from app.config import settings


class GuardrailViolation(Enum):
    """Types of guardrail violations."""
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    NON_MATHEMATICAL = "non_mathematical"
    MALICIOUS_INPUT = "malicious_input"
    TOO_LONG = "too_long"
    UNSAFE_OUTPUT = "unsafe_output"


class InputGuardrails:
    """Input validation and safety checks."""
    
    def __init__(self):
        """Initialize input guardrails with GitHub Models."""
        self.openai_client = OpenAI(
            api_key=settings.github_token,
            base_url=settings.github_api_base
        )
        self.max_length = settings.max_question_length
        self.math_keywords = settings.allowed_topics
        
        # Patterns for malicious input detection
        self.malicious_patterns = [
            r'<script',
            r'javascript:',
            r'onerror=',
            r'eval\(',
            r'exec\(',
            r'__import__',
        ]
    
    def validate(self, user_input: str) -> Dict[str, Any]:
        """
        Validate user input against guardrails.
        
        Returns:
            Dict with keys: is_valid, reason, sanitized_input
        """
        # Check length
        if len(user_input) > self.max_length:
            return {
                'is_valid': False,
                'reason': f'Input too long. Maximum {self.max_length} characters.',
                'violation': GuardrailViolation.TOO_LONG.value,
                'sanitized_input': None
            }
        
        # Check for malicious patterns
        for pattern in self.malicious_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                return {
                    'is_valid': False,
                    'reason': 'Potentially malicious input detected.',
                    'violation': GuardrailViolation.MALICIOUS_INPUT.value,
                    'sanitized_input': None
                }
        
        # Sanitize input
        sanitized = self._sanitize_input(user_input)
        
        # Check if question is mathematical
        is_math = self._is_mathematical_question(sanitized)
        if not is_math['is_mathematical']:
            return {
                'is_valid': False,
                'reason': 'Question does not appear to be mathematical. This system only handles mathematics questions.',
                'violation': GuardrailViolation.NON_MATHEMATICAL.value,
                'sanitized_input': sanitized,
                'confidence': is_math['confidence']
            }
        
        # Check for inappropriate content using LLM
        content_check = self._check_content_appropriateness(sanitized)
        if not content_check['is_appropriate']:
            return {
                'is_valid': False,
                'reason': 'Inappropriate content detected.',
                'violation': GuardrailViolation.INAPPROPRIATE_CONTENT.value,
                'sanitized_input': sanitized
            }
        
        return {
            'is_valid': True,
            'reason': 'Input passed all guardrails.',
            'violation': None,
            'sanitized_input': sanitized,
            'topic': is_math.get('detected_topic', 'general')
        }
    
    def _sanitize_input(self, text: str) -> str:
        """Remove potentially dangerous characters and normalize text."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Trim
        text = text.strip()
        return text
    
    def _is_mathematical_question(self, text: str) -> Dict[str, Any]:
        """
        Determine if the question is mathematical using keyword matching 
        and LLM classification.
        """
        text_lower = text.lower()
        
        # Keyword-based quick check
        math_keyword_found = any(keyword in text_lower for keyword in self.math_keywords)
        
        # Look for mathematical symbols and patterns
        math_symbols = ['+', '-', '×', '÷', '=', '∫', '∑', '√', '^', 
                       'sin', 'cos', 'tan', 'log', 'derivative', 'integral']
        has_math_symbols = any(symbol in text_lower for symbol in math_symbols)
        
        # Number patterns
        has_numbers = bool(re.search(r'\d+', text))
        
        # Word problem indicators - questions with numbers and calculation intent
        word_problem_indicators = [
            'how much', 'how many', 'what is', 'calculate', 'find', 
            'total', 'cost', 'price', 'paid', 'per', 'each',
            'if', 'when', 'given', 'solve', 'prove', 'derive',
            'sum', 'difference', 'product', 'quotient', 'ratio',
            'percent', 'percentage', 'rate', 'speed', 'distance', 'time',
            'more than', 'less than', 'times as much', 'times as many'
        ]
        has_word_problem_pattern = any(indicator in text_lower for indicator in word_problem_indicators)
        
        # Quick decision for obvious cases
        if math_keyword_found or has_math_symbols:
            return {
                'is_mathematical': True,
                'confidence': 0.9,
                'detected_topic': self._detect_math_topic(text_lower)
            }
        
        # Word problems with numbers are mathematical
        if has_numbers and has_word_problem_pattern:
            return {
                'is_mathematical': True,
                'confidence': 0.85,
                'detected_topic': 'word_problem'
            }
        
        # Use LLM for ambiguous cases
        if has_numbers:
            llm_check = self._llm_classify_mathematical(text)
            return llm_check
        
        return {
            'is_mathematical': False,
            'confidence': 0.8,
            'detected_topic': None
        }
    
    def _detect_math_topic(self, text: str) -> str:
        """Detect the specific mathematical topic."""
        topic_keywords = {
            'algebra': ['equation', 'variable', 'polynomial', 'linear', 'quadratic'],
            'calculus': ['derivative', 'integral', 'limit', 'differential', 'differentiate'],
            'geometry': ['triangle', 'circle', 'angle', 'area', 'perimeter', 'volume'],
            'trigonometry': ['sin', 'cos', 'tan', 'sine', 'cosine', 'tangent'],
            'statistics': ['mean', 'median', 'standard deviation', 'probability', 'distribution'],
            'arithmetic': ['addition', 'subtraction', 'multiplication', 'division', 'fraction'],
            'word_problem': ['how much', 'how many', 'cost', 'price', 'paid', 'per', 'total', 'salary', 'earnings', 'profit', 'spend', 'buy', 'sell']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in text for keyword in keywords):
                return topic
        
        return 'general'
    
    def _llm_classify_mathematical(self, text: str) -> Dict[str, Any]:
        """Use LLM to classify if the question is mathematical."""
        prompt = f"""Determine if the following question is a mathematics question.
A mathematics question should be about topics like: algebra, geometry, calculus, 
trigonometry, statistics, probability, arithmetic, number theory, or any mathematical concept.

Question: {text}

Respond in JSON format:
{{
    "is_mathematical": true/false,
    "confidence": 0.0-1.0,
    "detected_topic": "topic name or null",
    "reasoning": "brief explanation"
}}
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            print(f"LLM classification error: {e}")
            return {
                'is_mathematical': False,
                'confidence': 0.5,
                'detected_topic': None
            }
    
    def _check_content_appropriateness(self, text: str) -> Dict[str, bool]:
        """Check if content is appropriate for educational context."""
        # Simple keyword-based check
        inappropriate_keywords = [
            'hack', 'exploit', 'crack', 'illegal', 'piracy',
            # Add more as needed
        ]
        
        text_lower = text.lower()
        for keyword in inappropriate_keywords:
            if keyword in text_lower:
                return {'is_appropriate': False, 'reason': f'Inappropriate keyword: {keyword}'}
        
        return {'is_appropriate': True, 'reason': 'Content is appropriate'}


class OutputGuardrails:
    """Output validation and safety checks."""
    
    def __init__(self):
        """Initialize output guardrails with GitHub Models."""
        self.openai_client = OpenAI(
            api_key=settings.github_token,
            base_url=settings.github_api_base
        )
    
    def validate(self, output: str, original_question: str) -> Dict[str, Any]:
        """
        Validate generated output.
        
        Returns:
            Dict with keys: is_valid, reason, sanitized_output
        """
        # Check if output is empty
        if not output or len(output.strip()) < 10:
            return {
                'is_valid': False,
                'reason': 'Output is too short or empty.',
                'violation': GuardrailViolation.UNSAFE_OUTPUT.value,
                'sanitized_output': None
            }
        
        # Check for hallucinations or off-topic responses
        relevance_check = self._check_relevance(output, original_question)
        if not relevance_check['is_relevant']:
            return {
                'is_valid': False,
                'reason': 'Output is not relevant to the question.',
                'violation': GuardrailViolation.UNSAFE_OUTPUT.value,
                'sanitized_output': output,
                'confidence': relevance_check['confidence']
            }
        
        # Check for inappropriate content in output
        content_check = self._check_output_safety(output)
        if not content_check['is_safe']:
            return {
                'is_valid': False,
                'reason': 'Output contains unsafe content.',
                'violation': GuardrailViolation.UNSAFE_OUTPUT.value,
                'sanitized_output': None
            }
        
        # Sanitize output
        sanitized = self._sanitize_output(output)
        
        return {
            'is_valid': True,
            'reason': 'Output passed all guardrails.',
            'violation': None,
            'sanitized_output': sanitized
        }
    
    def _check_relevance(self, output: str, question: str) -> Dict[str, Any]:
        """Check if output is relevant to the original question."""
        prompt = f"""Evaluate if the answer is relevant and helpful for the given mathematical question.

Question: {question}

Answer: {output[:500]}...

Respond in JSON format:
{{
    "is_relevant": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            print(f"Relevance check error: {e}")
            return {'is_relevant': True, 'confidence': 0.6}
    
    def _check_output_safety(self, output: str) -> Dict[str, bool]:
        """Check if output is safe and appropriate."""
        # Check for disclaimers about being unable to answer
        unsafe_phrases = [
            "I cannot answer",
            "I'm not able to help",
            "I don't have information about",
        ]
        
        output_lower = output.lower()
        for phrase in unsafe_phrases:
            if phrase.lower() in output_lower and len(output) < 200:
                return {'is_safe': False, 'reason': 'Model refused to answer'}
        
        return {'is_safe': True, 'reason': 'Output is safe'}
    
    def _sanitize_output(self, text: str) -> str:
        """Clean up output text."""
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Trim
        text = text.strip()
        return text


class GuardrailsManager:
    """Central manager for all guardrails."""
    
    def __init__(self):
        """Initialize guardrails manager."""
        self.input_guardrails = InputGuardrails()
        self.output_guardrails = OutputGuardrails()
    
    def validate_input(self, user_input: str) -> Dict[str, Any]:
        """Validate user input."""
        return self.input_guardrails.validate(user_input)
    
    def validate_output(self, output: str, original_question: str) -> Dict[str, Any]:
        """Validate generated output."""
        return self.output_guardrails.validate(output, original_question)

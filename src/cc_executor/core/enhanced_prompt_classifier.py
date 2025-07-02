#!/usr/bin/env python3
"""
Enhanced prompt classifier with more accurate categorization.

Categories:
- code: User asking for code/programming
- explanation: User asking for explanations/concepts
- creative: Creative writing (stories, haikus, etc.)
- calculation: Math calculations
- analysis: Code analysis, review, debugging
- architecture: System design, architecture
- data: Data processing, transformation
- general: Everything else

Complexity:
- trivial: Very simple (e.g., add two numbers, hello world)
- low: Simple but requires some thought
- medium: Standard complexity
- high: Complex logic or multiple components
- extreme: Very complex, multi-faceted
"""

import re
from typing import Dict, Tuple

class EnhancedPromptClassifier:
    def __init__(self):
        # Code-related keywords for detection
        self.code_keywords = {
            'function', 'code', 'implement', 'write', 'create', 'program',
            'script', 'class', 'method', 'algorithm', 'def', 'return',
            'python', 'javascript', 'java', 'c++', 'golang', 'rust'
        }
        
        # Trivial code patterns
        self.trivial_patterns = [
            r'add\s+(two|2)\s+numbers?',
            r'hello\s+world',
            r'sum\s+of\s+(two|2)',
            r'print\s+(a\s+)?message',
            r'reverse\s+a?\s+string',
            r'check\s+if.*even\s+or\s+odd',
            r'convert.*celsius.*fahrenheit',
            r'area\s+of\s+(a\s+)?circle'
        ]
        
        # Low complexity patterns
        self.low_patterns = [
            r'factorial',
            r'fibonacci',
            r'prime\s+number',
            r'palindrome',
            r'bubble\s+sort',
            r'linear\s+search',
            r'count\s+occurrences',
            r'remove\s+duplicates'
        ]
        
        # High complexity patterns
        self.high_patterns = [
            r'implement.*algorithm',
            r'design.*system',
            r'optimize.*performance',
            r'refactor.*complex',
            r'multi.*thread',
            r'concurrent',
            r'distributed',
            r'machine\s+learning',
            r'neural\s+network'
        ]
    
    def classify(self, prompt: str) -> Dict[str, str]:
        """
        Classify a prompt with category and complexity.
        
        Returns:
            Dictionary with category, complexity, and sub_type
        """
        prompt_lower = prompt.lower()
        
        # Determine category
        category = self._determine_category(prompt_lower)
        
        # Determine complexity
        complexity = self._determine_complexity(prompt_lower, category)
        
        # Determine sub-type for better matching
        sub_type = self._determine_sub_type(prompt_lower, category)
        
        return {
            "category": category,
            "complexity": complexity,
            "sub_type": sub_type
        }
    
    def _determine_category(self, prompt: str) -> str:
        """Determine the main category of the prompt."""
        
        # Check for code requests
        if any(keyword in prompt for keyword in self.code_keywords):
            # Further check if it's analysis vs generation
            if any(word in prompt for word in ['analyze', 'review', 'debug', 'fix', 'improve', 'refactor']):
                return "analysis"
            elif any(word in prompt for word in ['architecture', 'design', 'system', 'database schema']):
                return "architecture"
            else:
                return "code"
        
        # Check for calculations first (before explanations)
        if any(word in prompt for word in [
            'calculate', 'compute', 'solve', 'equation', 'math',
            'sum', 'product', 'result of', '+', '-', '*', '/'
        ]):
            return "calculation"
        
        # Check for explanations
        if any(phrase in prompt for phrase in [
            'what is', 'explain', 'how does', 'why', 'concept of',
            'difference between', 'when to use'
        ]):
            return "explanation"
        
        # Check for creative writing
        if any(word in prompt for word in [
            'story', 'haiku', 'poem', 'narrative', 'creative',
            'fiction', 'plot', 'character', 'scene'
        ]):
            return "creative"
        
        # Check for data operations
        if any(word in prompt for word in [
            'parse', 'extract', 'transform', 'convert', 'process',
            'csv', 'json', 'xml', 'data'
        ]):
            return "data"
        
        return "general"
    
    def _determine_complexity(self, prompt: str, category: str) -> str:
        """Determine complexity level based on prompt content."""
        
        # Check word/item counts for quick complexity hints
        count_match = re.search(r'(\d+)[-\s]*(word|item|element|function|method|haiku|question)', prompt)
        if count_match:
            count = int(count_match.group(1))
            if count <= 3:
                return "low"
            elif count <= 10:
                return "medium"
            elif count <= 50:
                return "high"
            else:
                return "extreme"
        
        # Category-specific complexity rules
        if category == "code":
            # Check trivial patterns
            for pattern in self.trivial_patterns:
                if re.search(pattern, prompt):
                    return "trivial"
            
            # Check low complexity patterns
            for pattern in self.low_patterns:
                if re.search(pattern, prompt):
                    return "low"
            
            # Check high complexity patterns
            for pattern in self.high_patterns:
                if re.search(pattern, prompt):
                    return "high"
            
            # Check for multiple requirements
            requirements = len([word for word in [
                'and', 'also', 'with', 'including', 'plus'
            ] if word in prompt])
            
            if requirements >= 3:
                return "high"
            elif requirements >= 1:
                return "medium"
            else:
                return "low"
        
        elif category == "calculation":
            # Simple calculations are trivial/low
            operations = len(re.findall(r'[\+\-\*/]', prompt))
            numbers = len(re.findall(r'\b\d+\b', prompt))
            
            if operations <= 1 or numbers <= 2:
                return "trivial"
            elif operations <= 5:
                return "low"
            else:
                return "medium"
        
        elif category == "creative":
            # Length determines complexity
            if '5000' in prompt or '10000' in prompt:
                return "extreme"
            elif '1000' in prompt or '2000' in prompt:
                return "high"
            elif '500' in prompt:
                return "medium"
            else:
                return "low"
        
        elif category == "architecture":
            # Architecture is usually complex
            if any(word in prompt for word in ['microservice', 'distributed', 'scalable']):
                return "extreme"
            elif any(word in prompt for word in ['database', 'api', 'frontend']):
                return "high"
            else:
                return "medium"
        
        # Default complexity by category
        default_complexity = {
            "explanation": "medium",
            "analysis": "high",
            "data": "medium",
            "general": "medium"
        }
        
        return default_complexity.get(category, "medium")
    
    def _determine_sub_type(self, prompt: str, category: str) -> str:
        """Determine sub-type for more precise matching."""
        
        if category == "code":
            if 'function' in prompt:
                return "function"
            elif 'class' in prompt:
                return "class"
            elif 'script' in prompt:
                return "script"
            elif 'algorithm' in prompt:
                return "algorithm"
            else:
                return "snippet"
        
        elif category == "explanation":
            if 'concept' in prompt:
                return "concept"
            elif 'difference' in prompt:
                return "comparison"
            elif 'how' in prompt:
                return "how_to"
            else:
                return "definition"
        
        elif category == "creative":
            if 'haiku' in prompt:
                return "haiku"
            elif 'story' in prompt:
                return "story"
            elif 'poem' in prompt:
                return "poem"
            else:
                return "writing"
        
        return "general"


# Testing
if __name__ == "__main__":
    classifier = EnhancedPromptClassifier()
    
    test_prompts = [
        # Trivial code
        "What is code to add two numbers?",
        "What is a hello world program in Python?",
        
        # Low complexity code
        "What is a Python function to calculate factorial?",
        "What is code to check if a number is prime?",
        
        # Medium complexity
        "What is a Python class for a binary search tree?",
        "What is code for 5 utility functions?",
        
        # High complexity
        "What is a distributed rate limiter implementation?",
        "What is code to optimize this algorithm for performance?",
        
        # Other categories
        "What is the concept of recursion?",
        "What is 15 + 27 - 8 * 3?",
        "What is a 500-word story about AI?",
        "What is the architecture for a todo app?",
    ]
    
    print("Enhanced Prompt Classification")
    print("=" * 60)
    
    for prompt in test_prompts:
        result = classifier.classify(prompt)
        print(f"\nPrompt: {prompt}")
        print(f"Category: {result['category']}")
        print(f"Complexity: {result['complexity']}")
        print(f"Sub-type: {result['sub_type']}")
    
    print("\n" + "=" * 60)
    print("Key improvements:")
    print("- 'code' category for programming requests")
    print("- 'trivial' complexity for add two numbers")
    print("- More nuanced complexity levels")
    print("- Sub-types for better similarity matching")
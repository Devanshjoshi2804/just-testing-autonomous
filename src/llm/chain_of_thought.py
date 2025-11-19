"""
Chain-of-Thought Prompting
Improves LLM reasoning by eliciting step-by-step thinking
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from loguru import logger


@dataclass
class CoTResponse:
    """Response from chain-of-thought prompting"""
    reasoning_steps: List[str]
    final_answer: str
    confidence: float
    tokens_used: int


class ChainOfThoughtPrompt:
    """
    Chain-of-Thought prompting strategies
    
    Techniques:
    - Zero-shot CoT: "Let's think step by step"
    - Few-shot CoT: Provide examples with reasoning
    - Self-consistency: Multiple reasoning paths
    """

    @staticmethod
    def zero_shot_cot(question: str) -> str:
        """
        Zero-shot Chain-of-Thought
        
        Simply append "Let's think step by step" to elicit reasoning
        """
        return f"""{question}

Let's think step by step and break this down:
1. First, identify the key requirements
2. Then, consider each aspect carefully
3. Finally, synthesize a comprehensive answer

Please show your reasoning process before providing the final answer."""

    @staticmethod
    def few_shot_cot(question: str, examples: List[Dict[str, str]]) -> str:
        """
        Few-shot Chain-of-Thought
        
        Provide examples that show reasoning process
        """
        prompt = "Here are some examples showing step-by-step reasoning:\n\n"
        
        for i, example in enumerate(examples, 1):
            prompt += f"Example {i}:\n"
            prompt += f"Question: {example['question']}\n"
            prompt += f"Reasoning: {example['reasoning']}\n"
            prompt += f"Answer: {example['answer']}\n\n"
        
        prompt += f"Now solve this problem using the same approach:\n\n"
        prompt += f"Question: {question}\n"
        prompt += "Reasoning: Let's break this down step by step:\n"
        
        return prompt

    @staticmethod
    def self_consistency_cot(question: str, num_paths: int = 3) -> str:
        """
        Self-Consistency CoT
        
        Generate multiple reasoning paths and aggregate
        """
        return f"""{question}

Please provide {num_paths} different reasoning approaches:

Approach 1:
- Step 1:
- Step 2:
- Step 3:
- Conclusion:

Approach 2:
- Step 1:
- Step 2:
- Step 3:
- Conclusion:

Approach 3:
- Step 1:
- Step 2:
- Step 3:
- Conclusion:

Final Answer (synthesized from all approaches):"""

    @staticmethod
    def structured_cot(question: str, structure: Dict[str, str]) -> str:
        """
        Structured Chain-of-Thought
        
        Provide specific structure for reasoning
        """
        prompt = f"{question}\n\nPlease analyze this using the following structure:\n\n"
        
        for step_name, step_desc in structure.items():
            prompt += f"{step_name}: {step_desc}\n"
        
        prompt += "\nProvide your analysis following this structure:"
        
        return prompt


class TestGenerationCoT:
    """
    Chain-of-Thought prompting specifically for test generation
    
    Improves test quality by making LLM reason about:
    - Edge cases
    - Boundary conditions
    - Security implications
    - Error scenarios
    """

    @staticmethod
    def generate_test_with_cot(endpoint_spec: Dict[str, Any]) -> str:
        """Generate test with chain-of-thought reasoning"""
        
        endpoint_path = endpoint_spec.get('path', 'unknown')
        method = endpoint_spec.get('method', 'GET')
        parameters = endpoint_spec.get('parameters', [])
        
        return f"""Generate comprehensive API tests for this endpoint:

Endpoint: {method} {endpoint_path}
Parameters: {parameters}

Let's think through this systematically:

1. UNDERSTAND THE ENDPOINT
   - What is the purpose of this endpoint?
   - What data does it accept?
   - What are the expected responses?

2. IDENTIFY TEST SCENARIOS
   - Happy path: What should work?
   - Edge cases: What boundary conditions exist?
   - Error cases: What could go wrong?
   - Security: What attacks should we prevent?

3. PARAMETER ANALYSIS
   For each parameter, consider:
   - Valid values (examples)
   - Invalid values (what breaks it?)
   - Boundary values (min, max, null)
   - Type mismatches
   - Injection attempts

4. GENERATE TEST CASES
   Based on the analysis above, create test cases that cover:
   - All positive scenarios
   - All negative scenarios
   - All boundary conditions
   - All security concerns

Please provide your reasoning for each test case, then generate the test code.
"""

    @staticmethod
    def analyze_api_doc_with_cot(api_doc: str) -> str:
        """Analyze API documentation with reasoning"""
        
        return f"""Analyze this API documentation and extract endpoint information:

Documentation:
{api_doc}

Let's analyze this step by step:

1. IDENTIFY ENDPOINTS
   - What endpoints are described?
   - What HTTP methods are used?
   - What are the URL patterns?

2. EXTRACT PARAMETERS
   For each endpoint:
   - What parameters does it accept?
   - Are they required or optional?
   - What are the data types?
   - What are the constraints (min, max, format)?

3. UNDERSTAND AUTHENTICATION
   - Does the endpoint require authentication?
   - What authentication method is used?
   - Are there any special headers needed?

4. IDENTIFY RESPONSES
   - What are the success responses?
   - What are the error responses?
   - What status codes are used?

5. EXTRACT EXAMPLES
   - Are there example requests?
   - Are there example responses?
   - Can we infer data formats from examples?

Based on this analysis, please extract structured endpoint information.
"""


# Few-shot examples for test generation
TEST_GENERATION_EXAMPLES = [
    {
        "question": "Generate tests for POST /users endpoint that accepts {name: string, email: string}",
        "reasoning": """
Let me think through this:
1. Required fields: name and email
2. Email must be valid format
3. Name should have length constraints
4. Should test duplicate emails
5. Should test SQL injection attempts
6. Should test XSS in name field
        """,
        "answer": """
Test cases:
1. Valid user creation (happy path)
2. Missing name (validation)
3. Missing email (validation)
4. Invalid email format
5. Name too long (>255 chars)
6. Duplicate email
7. SQL injection in name
8. XSS in name field
        """
    },
    {
        "question": "Generate tests for GET /users/{id} endpoint",
        "reasoning": """
Analysis:
1. {id} is path parameter
2. Should test valid IDs
3. Should test invalid IDs (non-existent, malformed)
4. Should test boundary values
5. Should test authorization (can user access this ID?)
        """,
        "answer": """
Test cases:
1. Get existing user (200)
2. Get non-existent user (404)
3. Get with invalid ID format (400)
4. Get with negative ID (400)
5. Get with ID = 0 (boundary)
6. Get with huge ID (overflow check)
7. Get without auth token (401)
        """
    }
]


def create_cot_prompt_for_agent(agent_name: str, task: str, context: Dict[str, Any] = None) -> str:
    """
    Create chain-of-thought prompt for any agent
    
    Args:
        agent_name: Name of the agent (test_generator, doc_analyzer, etc.)
        task: Task description
        context: Additional context
        
    Returns:
        CoT-enhanced prompt
    """
    prompt = f"""You are a {agent_name}. Your task is:

{task}

"""
    
    if context:
        prompt += "Context:\n"
        for key, value in context.items():
            prompt += f"- {key}: {value}\n"
        prompt += "\n"
    
    prompt += """Before providing your answer, please think through this step by step:

1. UNDERSTAND: What is being asked?
2. ANALYZE: What information do I have?
3. PLAN: What approach should I take?
4. EXECUTE: What is my step-by-step solution?
5. VERIFY: Does my solution make sense?

Show your reasoning process, then provide your final answer.
"""
    
    return prompt


# CoT templates for common tasks
COT_TEMPLATES = {
    "test_generation": TestGenerationCoT.generate_test_with_cot,
    "api_analysis": TestGenerationCoT.analyze_api_doc_with_cot,
    "zero_shot": ChainOfThoughtPrompt.zero_shot_cot,
    "few_shot": ChainOfThoughtPrompt.few_shot_cot,
    "self_consistency": ChainOfThoughtPrompt.self_consistency_cot,
    "structured": ChainOfThoughtPrompt.structured_cot,
}


def get_cot_template(template_name: str) -> callable:
    """Get CoT template by name"""
    if template_name not in COT_TEMPLATES:
        logger.warning(f"Unknown CoT template: {template_name}, using zero_shot")
        return COT_TEMPLATES["zero_shot"]
    
    return COT_TEMPLATES[template_name]

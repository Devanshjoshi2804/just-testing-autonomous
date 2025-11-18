"""
Base Agent Class
Common functionality for all LLM-powered agents
"""
from typing import Optional, Dict, Any
from loguru import logger

from src.config import get_llm_client, settings


class BaseAgent:
    """
    Base class for all LLM agents
    Provides common LLM interaction methods
    """

    def __init__(self, agent_name: str, use_fast_llm: bool = False):
        """
        Initialize base agent

        Args:
            agent_name: Name of the agent (for logging)
            use_fast_llm: Use fast LLM model instead of primary
        """
        self.agent_name = agent_name
        self.use_fast_llm = use_fast_llm

        # Get LLM client - pass provider and model directly to avoid settings mutation
        if use_fast_llm:
            self.llm = get_llm_client(
                provider=settings.FAST_LLM_PROVIDER,
                model=settings.FAST_LLM_MODEL
            )
            self.llm_provider = settings.FAST_LLM_PROVIDER
            self.llm_model = settings.FAST_LLM_MODEL

            logger.info(
                f"{agent_name} initialized with FAST LLM: "
                f"{self.llm_provider}/{self.llm_model}"
            )
        else:
            self.llm = get_llm_client()
            self.llm_provider = settings.LLM_PROVIDER
            self.llm_model = settings.LLM_MODEL

            logger.info(
                f"{agent_name} initialized with LLM: "
                f"{self.llm_provider}/{self.llm_model}"
            )

    def invoke(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Invoke LLM with prompt

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            LLM response text
        """
        try:
            # For Ollama, combine system and user prompts
            if self.llm_provider == "ollama":
                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"

                response = self.llm.invoke(full_prompt)
                result = response if isinstance(response, str) else str(response)

            else:
                # For chat models (OpenAI, Anthropic, Groq)
                messages = []
                if system_prompt:
                    messages.append(("system", system_prompt))
                messages.append(("human", prompt))

                response = self.llm.invoke(messages)
                result = response.content

            logger.debug(f"{self.agent_name} response length: {len(result)} chars")
            return result

        except Exception as e:
            logger.error(f"{self.agent_name} LLM invocation failed: {e}")
            raise

    async def ainvoke(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Asynchronously invoke LLM (non-blocking)

        Runs synchronous LLM invocation in a thread pool executor to avoid
        blocking the async event loop.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt for context

        Returns:
            LLM response text
        """
        import asyncio
        from functools import partial

        try:
            # Prepare the synchronous function call
            loop = asyncio.get_event_loop()

            # For Ollama, combine system and user prompts
            if self.llm_provider == "ollama":
                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"

                # Run in executor to avoid blocking event loop
                response = await loop.run_in_executor(
                    None,  # Uses default ThreadPoolExecutor
                    partial(self.llm.invoke, full_prompt)
                )
                result = response if isinstance(response, str) else str(response)

            else:
                # For chat models (OpenAI, Anthropic, Groq)
                messages = []
                if system_prompt:
                    messages.append(("system", system_prompt))
                messages.append(("human", prompt))

                # Run in executor to avoid blocking event loop
                response = await loop.run_in_executor(
                    None,  # Uses default ThreadPoolExecutor
                    partial(self.llm.invoke, messages)
                )
                result = response.content

            logger.debug(f"{self.agent_name} async response length: {len(result)} chars")
            return result

        except Exception as e:
            logger.error(f"{self.agent_name} async LLM invocation failed: {e}")
            raise

    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown code blocks

        Args:
            response: LLM response text

        Returns:
            Parsed JSON dict

        Raises:
            ValueError: If JSON parsing fails
        """
        import json
        import re

        # Remove markdown code blocks if present
        cleaned = response.strip()

        # Remove ```json and ``` markers
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

        # Try to parse JSON
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response[:500]}...")

            # Try to extract JSON from text using regex
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except:
                    pass

            raise ValueError(f"Could not parse JSON from response: {response[:200]}...")

    def clean_markdown(self, text: str) -> str:
        """
        Remove markdown formatting from text

        Args:
            text: Text with potential markdown

        Returns:
            Cleaned text
        """
        # Remove code blocks
        import re

        text = re.sub(r'```[\w]*\n', '', text)
        text = re.sub(r'```', '', text)

        # Remove bold/italic
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)

        # Remove headers
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

        return text.strip()

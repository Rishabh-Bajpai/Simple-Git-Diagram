import os
from openai import OpenAI

import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.api_key = os.getenv("LLM_API_KEY") or "dummy-key"  # Handle empty string
        self.model = os.getenv("LLM_MODEL_NAME", "gpt-3.5-turbo")
        
        logger.info(f"LLMService initialized with URL: {self.base_url}, Model: {self.model}")
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def generate_diagram(self, system_prompt: str, user_content: str) -> str:
        """
        Generates a response from the LLM.
        """
        try:
            logger.info(f"Sending request to LLM. Prompt length: {len(user_content)} chars")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.2,
                max_tokens=8000, 
            )
            content = response.choices[0].message.content or ""
            logger.info(f"Received LLM response. Length: {len(content)} chars")
            return content
        except Exception as e:
            import traceback
            import sys
            error_msg = f"LLM Error: {e}"
            logger.error(error_msg)
            # Still write to stderr for immediate visibility in case logger fails
            sys.stderr.write(f"{error_msg}\n")
            sys.stderr.write(traceback.format_exc())
            sys.stderr.flush()
            return f"Error generating diagram (URL: {self.base_url}): {str(e)}"

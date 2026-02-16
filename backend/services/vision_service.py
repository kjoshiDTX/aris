"""
Vision service for analyzing canvas images using GPT-4o-mini.
"""

import os
import base64
from typing import Optional
from openai import AsyncOpenAI


class VisionService:
    """Service for analyzing images using GPT-4o-mini vision capabilities."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        self.model = "gpt-4o-mini"

    def is_available(self) -> bool:
        """Check if the vision service is properly configured."""
        return self.client is not None and self.api_key is not None

    async def analyze_image(self, image_base64: str, prompt: str) -> str:
        """
        Analyze an image using GPT-4o-mini vision.
        
        Args:
            image_base64: Base64 encoded image (PNG)
            prompt: System prompt for analysis
            
        Returns:
            Text response from the model
        """
        if not self.is_available():
            raise RuntimeError("Vision service not configured. Set OPENAI_API_KEY.")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high"
                                }
                            },
                            {
                                "type": "text",
                                "text": "Please analyze this student's work."
                            }
                        ]
                    }
                ],
                max_tokens=300,
                temperature=0.7
            )

            return response.choices[0].message.content or "I couldn't analyze the image."

        except Exception as e:
            print(f"Vision analysis error: {e}")
            raise RuntimeError(f"Vision analysis failed: {str(e)}")

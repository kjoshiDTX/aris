"""
Speech service with OpenAI TTS/Whisper (functional) and Mini-Omni2 (placeholder).

Set USE_MINI_OMNI=true to switch to Mini-Omni2 when available.
"""

import os
import base64
import tempfile
from typing import Dict, Optional

from openai import AsyncOpenAI

from prompts import SPEECH_SYSTEM_PROMPT


class SpeechService:
    """
    Speech service with two backends:
    1. OpenAI (default) - Uses TTS and Whisper APIs
    2. Mini-Omni2 (placeholder) - For local inference when configured
    
    Set USE_MINI_OMNI=true to use Mini-Omni2 instead of OpenAI.
    """

    def __init__(self):
        # OpenAI configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = AsyncOpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
        self.tts_voice = os.getenv("OPENAI_TTS_VOICE", "nova")  # Options: alloy, echo, fable, onyx, nova, shimmer
        
        # Mini-Omni2 configuration (placeholder)
        self.use_mini_omni = os.getenv("USE_MINI_OMNI", "false").lower() == "true"
        self.mini_omni_host = os.getenv("MINI_OMNI_HOST", "localhost")
        self.mini_omni_port = int(os.getenv("MINI_OMNI_PORT", "50000"))
        self.mini_omni_url = f"http://{self.mini_omni_host}:{self.mini_omni_port}"

    def is_available(self) -> bool:
        """Check if any speech backend is available."""
        if self.use_mini_omni:
            return self._check_mini_omni_available()
        return self.openai_client is not None

    def _check_mini_omni_available(self) -> bool:
        """Check if Mini-Omni2 is configured and reachable."""
        # TODO: Implement actual health check when Mini-Omni2 is set up
        # Example:
        # try:
        #     response = httpx.get(f"{self.mini_omni_url}/health", timeout=2)
        #     return response.status_code == 200
        # except:
        #     return False
        return False

    async def text_to_speech(self, text: str) -> Optional[str]:
        """
        Convert text to speech.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Base64 encoded audio (MP3), or None if unavailable
        """
        if not text or not self.is_available():
            return None

        if self.use_mini_omni:
            return await self._mini_omni_tts(text)
        return await self._openai_tts(text)

    async def _openai_tts(self, text: str) -> Optional[str]:
        """Text-to-Speech using OpenAI TTS API."""
        try:
            response = await self.openai_client.audio.speech.create(
                model="tts-1",
                voice=self.tts_voice,
                input=text,
                response_format="mp3"
            )
            
            audio_bytes = response.content
            return base64.b64encode(audio_bytes).decode('utf-8')
            
        except Exception as e:
            print(f"OpenAI TTS error: {e}")
            return None

    async def _mini_omni_tts(self, text: str) -> Optional[str]:
        """Text-to-Speech using Mini-Omni2 (placeholder)."""
        # TODO: Implement when Mini-Omni2 is configured
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{self.mini_omni_url}/tts",
        #         json={"text": text, "voice": "default"}
        #     )
        #     if response.status_code == 200:
        #         return base64.b64encode(response.content).decode('utf-8')
        return None

    async def speech_to_text(self, audio_base64: str) -> str:
        """
        Transcribe speech to text.
        
        Args:
            audio_base64: Base64 encoded audio
            
        Returns:
            Transcribed text
        """
        if not audio_base64 or not self.is_available():
            return ""

        if self.use_mini_omni:
            return await self._mini_omni_stt(audio_base64)
        return await self._openai_stt(audio_base64)

    async def _openai_stt(self, audio_base64: str) -> str:
        """Speech-to-Text using OpenAI Whisper API."""
        try:
            audio_bytes = base64.b64decode(audio_base64)
            
            # Write to temp file (Whisper API requires file)
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name
            
            try:
                with open(temp_path, "rb") as audio_file:
                    transcript = await self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                return transcript.text
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            print(f"OpenAI STT error: {e}")
            return ""

    async def _mini_omni_stt(self, audio_base64: str) -> str:
        """Speech-to-Text using Mini-Omni2 (placeholder)."""
        # TODO: Implement when Mini-Omni2 is configured
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     audio_bytes = base64.b64decode(audio_base64)
        #     response = await client.post(
        #         f"{self.mini_omni_url}/stt",
        #         files={"audio": audio_bytes}
        #     )
        #     if response.status_code == 200:
        #         return response.json().get("text", "")
        return ""

    async def speech_to_speech(self, audio_base64: str) -> Dict[str, str]:
        """
        Full speech-to-speech pipeline: STT -> LLM -> TTS
        
        Args:
            audio_base64: Base64 encoded audio from user
            
        Returns:
            Dict with 'text' (response text) and 'audio' (base64 encoded)
        """
        if not self.is_available():
            return {
                "text": "Speech service not configured. Set OPENAI_API_KEY.",
                "audio": ""
            }

        if self.use_mini_omni:
            return await self._mini_omni_s2s(audio_base64)
        return await self._openai_s2s(audio_base64)

    async def _openai_s2s(self, audio_base64: str) -> Dict[str, str]:
        """Speech-to-Speech using OpenAI (Whisper + GPT + TTS)."""
        try:
            # 1. Transcribe user speech
            user_text = await self._openai_stt(audio_base64)
            if not user_text:
                return {"text": "I couldn't hear you clearly. Could you repeat that?", "audio": ""}

            # 2. Generate Socratic response via GPT
            chat_response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SPEECH_SYSTEM_PROMPT},
                    {"role": "user", "content": user_text}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            response_text = chat_response.choices[0].message.content or ""

            # 3. Convert response to speech
            audio_base64_response = await self._openai_tts(response_text)

            return {
                "text": response_text,
                "audio": audio_base64_response or ""
            }

        except Exception as e:
            print(f"OpenAI S2S error: {e}")
            return {
                "text": f"Sorry, I encountered an error: {str(e)}",
                "audio": ""
            }

    async def _mini_omni_s2s(self, audio_base64: str) -> Dict[str, str]:
        """Speech-to-Speech using Mini-Omni2 (placeholder)."""
        # TODO: Implement when Mini-Omni2 is configured
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     audio_bytes = base64.b64decode(audio_base64)
        #     response = await client.post(
        #         f"{self.mini_omni_url}/s2s",
        #         files={"audio": audio_bytes},
        #         data={"system_prompt": SPEECH_SYSTEM_PROMPT}
        #     )
        #     if response.status_code == 200:
        #         result = response.json()
        #         return {
        #             "text": result.get("text", ""),
        #             "audio": result.get("audio", "")
        #         }
        return {
            "text": "Mini-Omni2 is not configured yet.",
            "audio": ""
        }


# =============================================================================
# Configuration Notes
# =============================================================================
#
# OpenAI Backend (default):
#   - OPENAI_API_KEY: Required
#   - OPENAI_TTS_VOICE: Optional (default: nova)
#     Options: alloy, echo, fable, onyx, nova, shimmer
#
# Mini-Omni2 Backend (when ready):
#   - USE_MINI_OMNI=true: Switch to Mini-Omni2
#   - MINI_OMNI_HOST: Host (default: localhost)
#   - MINI_OMNI_PORT: Port (default: 50000)
#
# =============================================================================

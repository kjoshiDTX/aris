"""
ARIS - Socratic Tutor Backend
FastAPI server with vision analysis and speech-to-speech endpoints.
"""

import os
import base64
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()  # Load .env file

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.vision_service import VisionService
from services.speech_service import SpeechService
from prompts import SOCRATIC_ANALYSIS_PROMPT, PASSIVE_ANALYSIS_PROMPT


# Initialize services
vision_service = VisionService()
speech_service = SpeechService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    print("🎓 ARIS Socratic Tutor Backend starting...")
    print(f"   Vision Service: {'✓ Ready' if vision_service.is_available() else '✗ API key missing'}")
    print(f"   Speech Service: {'✓ Ready (placeholder)' if speech_service.is_available() else '✗ Not configured'}")
    yield
    print("🎓 ARIS Backend shutting down...")


app = FastAPI(
    title="ARIS Socratic Tutor",
    description="AI-powered tutoring assistant with vision and speech capabilities",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class AnalyzeRequest(BaseModel):
    """Request model for canvas analysis endpoint."""
    image: str  # Base64 encoded image
    mode: str = "manual"  # "manual" or "passive"
    quality: str = "high"  # "high" or "low"


class AnalyzeResponse(BaseModel):
    """Response model for canvas analysis."""
    response: str
    intervention_needed: bool = False
    audio: Optional[str] = None  # Base64 encoded audio


# Health Check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "vision": vision_service.is_available(),
            "speech": speech_service.is_available(),
        }
    }


# Talk Request/Response Models  
class TalkRequest(BaseModel):
    """Request model for voice interaction."""
    audio: str  # Base64 encoded audio (webm)
    canvas_image: str = ""  # Base64 encoded canvas image (optional)


class TalkResponse(BaseModel):
    """Response model for voice interaction."""
    text: str  # ARIS response text
    audio: Optional[str] = None  # Base64 encoded audio response


# Talk to ARIS - Voice interaction with canvas context
@app.post("/talk", response_model=TalkResponse)
async def talk_to_aris(request: TalkRequest):
    """
    Voice-based interaction with ARIS.
    
    1. Transcribes user's audio
    2. Analyzes canvas image for context (if provided)
    3. Generates Socratic response
    4. Returns response as audio
    """
    if not speech_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Speech service unavailable. Check OPENAI_API_KEY."
        )

    try:
        # 1. Transcribe user's audio
        user_text = await speech_service.speech_to_text(request.audio)
        if not user_text:
            return TalkResponse(
                text="I couldn't hear you clearly. Could you try again?",
                audio=await speech_service.text_to_speech("I couldn't hear you clearly. Could you try again?")
            )

        print(f"📝 Student said: {user_text}")

        # 2. Get canvas context if available
        canvas_context = ""
        if request.canvas_image and vision_service.is_available():
            canvas_context = await vision_service.analyze_image(
                request.canvas_image,
                "Briefly describe what you see on this student's canvas/whiteboard. Focus on any math, diagrams, or written work."
            )
            print(f"🖼️ Canvas context: {canvas_context[:100]}...")

        # 3. Generate Socratic response
        from prompts import SPEECH_SYSTEM_PROMPT
        
        # Build context-aware message
        if canvas_context:
            full_message = f"[Canvas shows: {canvas_context}]\n\nStudent says: {user_text}"
        else:
            full_message = f"Student says: {user_text}"

        # Use OpenAI to generate response
        from openai import AsyncOpenAI
        client = AsyncOpenAI()
        
        chat_response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SPEECH_SYSTEM_PROMPT},
                {"role": "user", "content": full_message}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        response_text = chat_response.choices[0].message.content or "I'm not sure how to help with that."
        print(f"🤖 ARIS response: {response_text}")

        # 4. Convert to speech
        audio_response = await speech_service.text_to_speech(response_text)

        return TalkResponse(
            text=response_text,
            audio=audio_response
        )

    except Exception as e:
        print(f"Talk error: {e}")
        error_msg = "Sorry, I had trouble processing that. Could you try again?"
        return TalkResponse(
            text=error_msg,
            audio=await speech_service.text_to_speech(error_msg)
        )


# Canvas Analysis Endpoint
@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_canvas(request: AnalyzeRequest):
    """
    Analyze the student's canvas and return a Socratic response.
    
    - Manual mode: High-res analysis, always returns a response
    - Passive mode: Low-res analysis, only responds if frustration detected
    """
    if not request.image:
        raise HTTPException(status_code=400, detail="No image provided")

    if not vision_service.is_available():
        raise HTTPException(
            status_code=503, 
            detail="Vision service unavailable. Check OPENAI_API_KEY."
        )

    try:
        # Select prompt based on mode
        if request.mode == "passive":
            # Passive mode: Check for frustration/stuck states
            analysis = await vision_service.analyze_image(
                request.image,
                PASSIVE_ANALYSIS_PROMPT
            )
            
            # Parse if intervention is needed
            intervention_needed = "INTERVENTION_NEEDED" in analysis.upper()
            
            if not intervention_needed:
                return AnalyzeResponse(
                    response="",
                    intervention_needed=False,
                    audio=None
                )
            
            # Remove the marker from response
            response_text = analysis.replace("INTERVENTION_NEEDED:", "").strip()
        else:
            # Manual mode: Full Socratic analysis
            response_text = await vision_service.analyze_image(
                request.image,
                SOCRATIC_ANALYSIS_PROMPT
            )
            intervention_needed = True

        # Generate audio response if speech service is available
        audio_base64 = None
        if speech_service.is_available():
            audio_base64 = await speech_service.text_to_speech(response_text)

        return AnalyzeResponse(
            response=response_text,
            intervention_needed=intervention_needed,
            audio=audio_base64
        )

    except Exception as e:
        print(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket for Speech-to-Speech
@app.websocket("/stream")
async def audio_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time speech-to-speech interaction.
    
    Receives audio chunks from client, processes through Mini-Omni2,
    and streams back audio responses.
    """
    await websocket.accept()
    print("🎙️ Audio stream connected")

    audio_buffer = []

    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                import json
                message = json.loads(data)
                
                if message.get("type") == "audio_chunk":
                    # Accumulate audio chunks
                    audio_buffer.append(message.get("data", ""))
                
                elif message.get("type") == "end_stream":
                    # Process complete audio
                    if audio_buffer:
                        full_audio = "".join(audio_buffer)
                        
                        # Process through speech service
                        # (Mini-Omni2 placeholder - returns mock response)
                        response = await speech_service.speech_to_speech(full_audio)
                        
                        await websocket.send_json({
                            "text": response.get("text", ""),
                            "audio": response.get("audio", "")
                        })
                        
                        audio_buffer = []
                
            except json.JSONDecodeError:
                # Handle non-JSON audio data if needed
                pass

    except WebSocketDisconnect:
        print("🎙️ Audio stream disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close(code=1011)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

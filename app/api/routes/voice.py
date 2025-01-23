"""Voice API routes - STT, TTS, and voice chat."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Transcribe audio to text using Whisper."""
    from app.dependencies import get_voice_service
    svc = get_voice_service()
    audio_bytes = await audio.read()
    result = await svc.transcribe(audio_bytes)
    return {
        "text": result.text,
        "language": result.language,
        "confidence": result.confidence,
        "duration_seconds": result.duration_seconds,
    }


@router.post("/synthesize")
async def synthesize(text: str = Form(...)):
    """Convert text to speech."""
    from app.dependencies import get_voice_service
    svc = get_voice_service()
    result = await svc.synthesize(text)
    return Response(
        content=result.audio_bytes,
        media_type="audio/wav",
        headers={"X-Duration": str(result.duration_seconds)},
    )


@router.post("/chat")
async def voice_chat(
    audio: UploadFile = File(...),
    session_id: str = Form(default=None),
):
    """Full voice round-trip: audio → text → LLM → audio."""
    from app.dependencies import get_voice_service, chat_service
    svc = get_voice_service()
    sid = session_id or str(uuid.uuid4())
    audio_bytes = await audio.read()
    reply_text, reply_audio = await svc.voice_chat(audio_bytes, chat_service, sid)
    return Response(
        content=reply_audio,
        media_type="audio/wav",
        headers={"X-Reply-Text": reply_text, "X-Session-Id": sid},
    )

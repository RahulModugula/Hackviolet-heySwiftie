"""Voice service - wraps voice pipeline for the API layer."""

from __future__ import annotations

import logging

from app.core.voice import SpeechToText, TextToSpeech, TranscriptionResult, SynthesisResult

logger = logging.getLogger(__name__)


class VoiceService:
    def __init__(self, stt: SpeechToText, tts: TextToSpeech):
        self.stt = stt
        self.tts = tts

    async def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        return await self.stt.transcribe(audio_bytes)

    async def synthesize(self, text: str) -> SynthesisResult:
        return await self.tts.synthesize(text)

    async def voice_chat(self, audio_bytes: bytes, chat_service, session_id: str) -> tuple[str, bytes]:
        """Full voice round-trip: audio in -> text -> LLM -> audio out."""
        transcription = await self.stt.transcribe(audio_bytes)
        logger.info("STT: %s", transcription.text)

        reply_text = await chat_service.respond(session_id, transcription.text)

        synthesis = await self.tts.synthesize(reply_text)
        return reply_text, synthesis.audio_bytes

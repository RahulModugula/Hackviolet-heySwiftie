"""Tests for voice pipeline (mock-based)."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.voice import SpeechToText, TextToSpeech, VoicePipeline, TranscriptionResult, SynthesisResult


@pytest.mark.asyncio
async def test_voice_pipeline_end_to_end():
    """Test that voice pipeline calls STT -> handler -> TTS in order."""
    stt = MagicMock(spec=SpeechToText)
    tts = MagicMock(spec=TextToSpeech)

    stt.transcribe = AsyncMock(return_value=TranscriptionResult(
        text="hello world", language="en", confidence=0.9, duration_seconds=1.5
    ))
    tts.synthesize = AsyncMock(return_value=SynthesisResult(
        audio_bytes=b"fake_audio", sample_rate=22050, duration_seconds=0.5
    ))

    pipeline = VoicePipeline(stt, tts)

    handler = AsyncMock(return_value="Hello! How can I help?")

    transcription, response_text, synthesis = await pipeline.process(b"audio_bytes", handler)

    assert transcription.text == "hello world"
    assert response_text == "Hello! How can I help?"
    assert synthesis.audio_bytes == b"fake_audio"
    handler.assert_called_once_with("hello world")


@pytest.mark.asyncio
async def test_stt_called_with_audio():
    stt = MagicMock(spec=SpeechToText)
    tts = MagicMock(spec=TextToSpeech)

    stt.transcribe = AsyncMock(return_value=TranscriptionResult(
        text="test", language="en", confidence=0.8, duration_seconds=0.5
    ))
    tts.synthesize = AsyncMock(return_value=SynthesisResult(
        audio_bytes=b"x", sample_rate=16000, duration_seconds=0.1
    ))

    pipeline = VoicePipeline(stt, tts)
    fake_audio = b"\x00" * 1024
    handler = AsyncMock(return_value="ok")

    await pipeline.process(fake_audio, handler)
    stt.transcribe.assert_called_once_with(fake_audio)


@pytest.mark.asyncio
async def test_transcription_result_fields():
    result = TranscriptionResult(
        text="hello", language="en", confidence=0.95, duration_seconds=2.0
    )
    assert result.text == "hello"
    assert result.language == "en"
    assert 0 <= result.confidence <= 1


@pytest.mark.asyncio
async def test_synthesis_result_fields():
    result = SynthesisResult(
        audio_bytes=b"data", sample_rate=22050, duration_seconds=1.0
    )
    assert result.sample_rate == 22050
    assert len(result.audio_bytes) > 0

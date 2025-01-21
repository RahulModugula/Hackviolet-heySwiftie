"""Voice AI - speech-to-text (Whisper) and text-to-speech (Piper)."""

from __future__ import annotations

import asyncio
import io
import logging
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    text: str
    language: str
    confidence: float
    duration_seconds: float


@dataclass
class SynthesisResult:
    audio_bytes: bytes
    sample_rate: int
    duration_seconds: float


class SpeechToText:
    """Whisper-based speech recognition using faster-whisper."""

    def __init__(self, model_size: str = "base.en", device: str = "auto"):
        self.model_size = model_size
        self.device = device
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel

            compute_type = "int8" if self.device == "cpu" else "float16"
            self._model = WhisperModel(
                self.model_size, device=self.device, compute_type=compute_type
            )
            logger.info("Whisper model loaded: %s", self.model_size)
        except ImportError:
            raise RuntimeError("faster-whisper not installed. pip install faster-whisper")

    async def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        """Transcribe audio bytes (WAV format) to text."""
        self._load()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
            f.write(audio_bytes)
            f.flush()
            segments, info = await asyncio.to_thread(
                self._model.transcribe,
                f.name,
                beam_size=5,
                vad_filter=True,
            )
            segments_list = await asyncio.to_thread(list, segments)

        text = " ".join(seg.text.strip() for seg in segments_list)
        avg_confidence = (
            sum(seg.avg_logprob for seg in segments_list) / len(segments_list)
            if segments_list
            else 0
        )

        return TranscriptionResult(
            text=text,
            language=info.language,
            confidence=min(max(avg_confidence + 1, 0), 1),  # normalize logprob
            duration_seconds=info.duration,
        )

    async def transcribe_file(self, file_path: str | Path) -> TranscriptionResult:
        """Transcribe from file path."""
        audio = await asyncio.to_thread(Path(file_path).read_bytes)
        return await self.transcribe(audio)


class TextToSpeech:
    """Piper TTS for natural speech synthesis."""

    def __init__(self, model: str = "en_US-lessac-medium", speaker: int = 0):
        self.model_name = model
        self.speaker = speaker
        self._voice = None

    def _load(self):
        if self._voice is not None:
            return
        try:
            from piper import PiperVoice

            self._voice = PiperVoice.load(self.model_name)
            logger.info("Piper TTS loaded: %s", self.model_name)
        except ImportError:
            raise RuntimeError("piper-tts not installed. pip install piper-tts")

    async def synthesize(self, text: str) -> SynthesisResult:
        """Convert text to speech, returns WAV bytes."""
        self._load()

        buf = io.BytesIO()
        wav_file = wave.open(buf, "wb")
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        sample_rate = self._voice.config.sample_rate
        wav_file.setframerate(sample_rate)

        await asyncio.to_thread(
            self._voice.synthesize, text, wav_file, speaker_id=self.speaker
        )
        wav_file.close()

        audio_bytes = buf.getvalue()
        n_frames = len(audio_bytes) // 2  # 16-bit
        duration = n_frames / sample_rate

        return SynthesisResult(
            audio_bytes=audio_bytes,
            sample_rate=sample_rate,
            duration_seconds=duration,
        )


class VoicePipeline:
    """End-to-end voice pipeline: STT -> process -> TTS."""

    def __init__(self, stt: SpeechToText, tts: TextToSpeech):
        self.stt = stt
        self.tts = tts

    async def process(
        self, audio_bytes: bytes, handler
    ) -> tuple[TranscriptionResult, str, SynthesisResult]:
        """
        Full voice pipeline:
        1. Transcribe audio input
        2. Process text through handler (e.g., chat service)
        3. Synthesize response to speech
        """
        transcription = await self.stt.transcribe(audio_bytes)
        logger.info("Transcribed: %s (%.1fs)", transcription.text, transcription.duration_seconds)

        response_text = await handler(transcription.text)

        synthesis = await self.tts.synthesize(response_text)
        logger.info("Synthesized: %.1fs of audio", synthesis.duration_seconds)

        return transcription, response_text, synthesis

"""QwenTTS FastAPI server — OpenAI-compatible /v1/audio/speech endpoint."""

import io
import logging
import os
import time
from contextlib import asynccontextmanager

import soundfile as sf
import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from transformers import pipeline

logger = logging.getLogger("qwen-tts")
logging.basicConfig(level=logging.INFO)

MODEL_ID = os.getenv("QWEN_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-Base")
HF_TOKEN = os.getenv("HF_TOKEN") or None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

tts_pipe = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global tts_pipe
    if not HF_TOKEN:
        logger.warning("HF_TOKEN is not set. Set it if the model requires authentication.")
    logger.info("Loading model: %s on %s", MODEL_ID, DEVICE)
    tts_pipe = pipeline(
        "text-to-speech",
        model=MODEL_ID,
        token=HF_TOKEN,
        torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
        device=0 if DEVICE == "cuda" else -1,
    )
    logger.info("Model loaded.")
    yield
    tts_pipe = None


app = FastAPI(
    title="Qwen TTS",
    description="Qwen3-TTS — OpenAI-compatible text-to-speech API",
    version="2.0.0",
    lifespan=lifespan,
)


class SpeechRequest(BaseModel):
    model: str = MODEL_ID
    input: str
    voice: str = "default"
    response_format: str = "wav"
    speed: float = 1.0


def synthesize(text: str) -> bytes:
    """テキストを WAV バイト列に変換する。"""
    output = tts_pipe(text)
    audio = output["audio"]
    sampling_rate = output["sampling_rate"]

    # (channels, samples) or (samples,) の両方に対応
    if hasattr(audio, "ndim") and audio.ndim == 2:
        audio = audio[0]

    buf = io.BytesIO()
    sf.write(buf, audio, sampling_rate, format="WAV")
    return buf.getvalue()


@app.get("/health")
async def health():
    return {
        "status": "ok" if tts_pipe is not None else "loading",
        "model": MODEL_ID,
        "device": DEVICE,
    }


@app.post("/v1/audio/speech")
async def create_speech(req: SpeechRequest):
    """OpenAI 互換 TTS エンドポイント。"""
    if tts_pipe is None:
        raise HTTPException(status_code=503, detail="Model is still loading")
    if not req.input:
        raise HTTPException(status_code=400, detail="input text is required")

    start = time.monotonic()
    try:
        audio_bytes = synthesize(req.input)
    except Exception as e:
        logger.exception("Synthesis failed")
        raise HTTPException(status_code=500, detail=str(e)) from e

    elapsed = time.monotonic() - start
    logger.info("Synthesized %d chars in %.2fs", len(req.input), elapsed)

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"X-Synthesis-Time": f"{elapsed:.3f}s"},
    )

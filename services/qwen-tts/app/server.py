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
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

logger = logging.getLogger("qwen-tts")
logging.basicConfig(level=logging.INFO)

MODEL_ID = os.getenv("QWEN_TTS_MODEL", "Qwen/Qwen2.5-TTS-3B")
HF_TOKEN = os.getenv("HF_TOKEN") or None  # required for gated models
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
SAMPLE_RATE = 24000

model = None
processor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, processor
    if not HF_TOKEN:
        logger.warning(
            "HF_TOKEN is not set. Gated models (e.g. Qwen2.5-TTS) will fail to download. "
            "Set HF_TOKEN in .env or environment."
        )
    logger.info("Loading model: %s on %s", MODEL_ID, DEVICE)
    processor = AutoProcessor.from_pretrained(MODEL_ID, token=HF_TOKEN)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
        device_map=DEVICE,
        token=HF_TOKEN,
    )
    logger.info("Model loaded.")
    yield
    model = None
    processor = None


app = FastAPI(
    title="Qwen TTS",
    description="QwenTTS — OpenAI-compatible text-to-speech API",
    version="1.0.0",
    lifespan=lifespan,
)


class SpeechRequest(BaseModel):
    model: str = MODEL_ID
    input: str
    voice: str = "default"
    response_format: str = "wav"
    speed: float = 1.0


def synthesize(text: str, speed: float = 1.0) -> bytes:
    """テキストを WAV バイト列に変換する。"""
    inputs = processor(text=text, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        output = model.generate(**inputs)
    audio = output[0].float().cpu().numpy()
    buf = io.BytesIO()
    sf.write(buf, audio, SAMPLE_RATE, format="WAV")
    return buf.getvalue()


@app.get("/health")
async def health():
    return {
        "status": "ok" if model is not None else "loading",
        "model": MODEL_ID,
        "device": DEVICE,
    }


@app.post("/v1/audio/speech")
async def create_speech(req: SpeechRequest):
    """OpenAI 互換 TTS エンドポイント。"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model is still loading")
    if not req.input:
        raise HTTPException(status_code=400, detail="input text is required")

    start = time.monotonic()
    try:
        audio_bytes = synthesize(req.input, req.speed)
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

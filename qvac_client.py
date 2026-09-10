"""Thin sync wrapper around the QVAC SDK: connect once, load models once, reuse."""
import asyncio
import os
import threading
from pathlib import Path

from tetherto.qvac_sdk import (
    Client,
    TranscribeRequest,
    WorkerNotFoundError,
    completion,
    load_model,
    transcribe,
)
from tetherto.qvac_sdk import models as qvac_models

_state: dict = {"client": None, "llm_id": None, "whisper_id": None, "vlm_id": None}

_WORKER_HINT = (
    "QVAC worker not found. Run `python -m tetherto.qvac_sdk install-worker` "
    "in this repo's venv, then retry."
)

# ponytail: the RPC transport is bound to the event loop that created it, so
# every call must run on the SAME loop (asyncio.run() per call closes the
# loop afterward and orphans the transport -> "RPC is closed"). One loop,
# reused for the process lifetime, is enough for a single-user hackathon app.
_loop = asyncio.new_event_loop()

# ponytail: Streamlit runs each interaction's script on its own thread, so two
# overlapping clicks (e.g. an impatient double-click) can call into the same
# loop concurrently -> "This event loop is already running" (observed live).
# A lock serializes them into a queue instead of racing.
_lock = threading.Lock()


def _run(coro, err_prefix: str):
    try:
        with _lock:
            return _loop.run_until_complete(coro)
    except Exception as e:
        raise RuntimeError(f"{err_prefix}: {e}") from e


# ponytail: on some npm versions `install-worker` hoists bare-runtime-* to
# the top-level node_modules instead of nesting it under @qvac/sdk, so the
# SDK's default path lookup misses it even though the binary is right there.
# One glob, tried only after the default Client() fails, fixes it for every
# teammate who hits the same npm layout.
def _find_hoisted_bare_binary() -> str | None:
    worker_home = Path(os.environ.get("QVAC_WORKER_HOME") or (Path.home() / ".cache" / "qvac" / "worker"))
    exe = "bare.exe" if os.name == "nt" else "bare"
    matches = sorted(worker_home.glob(f"*/node_modules/bare-runtime-*/bin/{exe}"))
    return str(matches[-1]) if matches else None


async def _connect() -> None:
    if _state["client"] is None:
        try:
            client = Client()
        except WorkerNotFoundError:
            bare_path = _find_hoisted_bare_binary()
            if bare_path is None:
                raise
            client = Client(bare_path=bare_path)
        await client.connect()
        _state["client"] = client


async def _connect_and_load() -> None:
    await _connect()
    transport = _state["client"].transport

    if _state["llm_id"] is None:
        try:
            _state["llm_id"] = await load_model(transport, model_src=qvac_models.QWEN3_1_7B_INST_Q4)
        except Exception:
            _state["llm_id"] = await load_model(transport, model_src=qvac_models.LLAMA_3_2_1B_INST_Q4_0)

    if _state["whisper_id"] is None:
        _state["whisper_id"] = await load_model(transport, model_src=qvac_models.WHISPER_SMALL_Q8_0)


async def _connect_and_load_vlm() -> None:
    await _connect()
    if _state["vlm_id"] is None:
        transport = _state["client"].transport
        # ponytail: a multimodal llama.cpp model is two files -- the LLM
        # weights (model_src) plus the vision projector (mmproj), loaded
        # together via model_config.projectionModelSrc, not a second
        # load_model() call.
        _state["vlm_id"] = await load_model(
            transport,
            model_src=qvac_models.VISIONPSY_NANO_460M_MULTIMODAL_Q4_K_M,
            model_config={"projectionModelSrc": qvac_models.MMPROJ_VISIONPSY_NANO_460M_MULTIMODAL_Q8_0.src},
        )


def ensure_ready_sync() -> None:
    if _state["llm_id"] is not None and _state["whisper_id"] is not None:
        return
    try:
        with _lock:
            _loop.run_until_complete(_connect_and_load())
    except WorkerNotFoundError as e:
        raise RuntimeError(_WORKER_HINT) from e
    except Exception as e:
        raise RuntimeError(f"QVAC setup failed: {e}") from e


def ensure_vlm_ready_sync() -> None:
    if _state["vlm_id"] is not None:
        return
    try:
        with _lock:
            _loop.run_until_complete(_connect_and_load_vlm())
    except WorkerNotFoundError as e:
        raise RuntimeError(_WORKER_HINT) from e
    except Exception as e:
        raise RuntimeError(f"QVAC VLM setup failed: {e}") from e


async def _extract(text: str, json_schema: dict, system_prompt: str | None) -> str:
    transport = _state["client"].transport
    history = []
    if system_prompt:
        history.append({"role": "system", "content": system_prompt})
    history.append({"role": "user", "content": text})
    run = completion(
        transport,
        model_id=_state["llm_id"],
        history=history,
        stream=False,
        response_format={"type": "json_schema", "json_schema": {"name": "observation", "schema": json_schema}},
    )
    return await run.text()


def extract_sync(text: str, json_schema: dict, system_prompt: str | None = None) -> str:
    ensure_ready_sync()
    return _run(_extract(text, json_schema, system_prompt), "QVAC completion failed")


async def _transcribe(audio_file_path: str) -> str:
    transport = _state["client"].transport
    # ponytail: `type` has a pydantic default, but the SDK builds the wire
    # payload with exclude_unset=True, which drops any field the caller
    # didn't pass explicitly -- including a defaulted one. Omitting it here
    # strips the payload's routing discriminator, so the worker never opens
    # the transcription stream ("expected a response stream", observed live).
    req = TranscribeRequest(
        modelId=_state["whisper_id"],
        type="transcribe",
        audioChunk={"type": "filePath", "value": audio_file_path},
    )
    last_text = ""
    async for resp in transcribe(transport, req):
        if resp.text:
            last_text = resp.text
    return last_text or ""


def transcribe_sync(audio_file_path: str) -> str:
    ensure_ready_sync()
    return _run(_transcribe(audio_file_path), "QVAC transcription failed")


_IMAGE_PROMPT = (
    "Look at this photo of a piece of medical equipment. Describe it factually: "
    "the type of equipment, and any brand, manufacturer, or model number visible "
    "on labels or the equipment body. Read text exactly as printed. If something "
    "is not visible or not legible, do not guess it."
)


async def _describe_image(image_path: str) -> str:
    transport = _state["client"].transport
    run = completion(
        transport,
        model_id=_state["vlm_id"],
        history=[{"role": "user", "content": _IMAGE_PROMPT, "attachments": [{"path": image_path}]}],
        stream=False,
    )
    return await run.text()


def describe_image_sync(image_path: str) -> str:
    ensure_vlm_ready_sync()
    return _run(_describe_image(image_path), "QVAC image description failed")

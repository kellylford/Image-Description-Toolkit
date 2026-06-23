"""
Florence-2 provider — Microsoft's vision model, runs locally via HuggingFace.
No API key needed. Requires a GPU (or CPU fallback, slow).

Supported tasks used here:
  - "<DETAILED_CAPTION>" — richest description, what we use by default
  - "<CAPTION>"          — brief one-liner
  - "<MORE_DETAILED_CAPTION>" — middle ground

Florence-2 doesn't accept arbitrary prompts the way Claude/GPT-4o do.
We map the prompt_name to the closest Florence task; free-text prompts
are ignored (Florence is a structured-task model, not instruction-following).

Models available on HuggingFace:
  microsoft/Florence-2-large        — best quality, ~1.5GB
  microsoft/Florence-2-base         — smaller, faster
  microsoft/Florence-2-large-ft     — fine-tuned variant
  microsoft/Florence-2-base-ft
"""
from __future__ import annotations

import io
from typing import Optional

from .base import BaseProvider, DescriptionResult

DEFAULT_MODEL = "microsoft/Florence-2-large"

# Map IDT prompt names to Florence task tokens
_TASK_MAP = {
    "detailed":   "<DETAILED_CAPTION>",
    "brief":      "<CAPTION>",
    "technical":  "<MORE_DETAILED_CAPTION>",
    "social":     "<CAPTION>",
    "document":   "<OCR_WITH_REGION>",
    "news":       "<DETAILED_CAPTION>",
}
_DEFAULT_TASK = "<DETAILED_CAPTION>"


class FlorenceProvider(BaseProvider):
    """
    Run Florence-2 locally. The model is downloaded on first use (~1.5GB for large).
    Subsequent uses load from the HuggingFace cache (~/.cache/huggingface/).
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        device: Optional[str] = None,
        task: Optional[str] = None,
    ):
        """
        model:  HuggingFace model ID (e.g. "microsoft/Florence-2-base")
        device: "cuda", "mps", or "cpu". Auto-detected if None.
        task:   Florence task token override (e.g. "<CAPTION>"). If None,
                the task is inferred from the prompt_name passed to describe().
        """
        self._model_id = model
        self._task_override = task
        self._device = device or _auto_device()
        self._model = None
        self._processor = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoProcessor, AutoModelForCausalLM
        except ImportError:
            raise ImportError(
                "Florence-2 requires 'transformers' and 'torch': "
                "pip install transformers torch"
            )
        import torch
        from transformers import AutoProcessor, AutoModelForCausalLM

        dtype = torch.float16 if self._device in ("cuda", "mps") else torch.float32
        self._processor = AutoProcessor.from_pretrained(
            self._model_id, trust_remote_code=True
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            self._model_id,
            torch_dtype=dtype,
            trust_remote_code=True,
        ).to(self._device)
        self._model.eval()

    @property
    def provider_name(self) -> str:
        return "florence"

    @property
    def model_name(self) -> str:
        return self._model_id

    def describe(self, image_bytes: bytes, mime_type: str, prompt: str) -> DescriptionResult:
        import torch
        from PIL import Image

        self._ensure_loaded()

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Resolve task from prompt text or use override
        task = self._task_override or _task_from_prompt(prompt)

        inputs = self._processor(text=task, images=img, return_tensors="pt").to(self._device)

        with torch.no_grad():
            ids = self._model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=1024,
                num_beams=3,
                early_stopping=False,
            )

        raw = self._processor.batch_decode(ids, skip_special_tokens=False)[0]
        parsed = self._processor.post_process_generation(
            raw,
            task=task,
            image_size=(img.width, img.height),
        )

        text = _extract_text(parsed, task)
        return DescriptionResult(
            text=text,
            model=self._model_id,
            provider="florence",
        )


def _task_from_prompt(prompt: str) -> str:
    """Infer a Florence task token from a prompt string or name."""
    lower = prompt.lower()
    if "brief" in lower or "one sentence" in lower or "short" in lower:
        return "<CAPTION>"
    if "text" in lower or "transcribe" in lower or "ocr" in lower:
        return "<OCR_WITH_REGION>"
    return _DEFAULT_TASK


def _extract_text(parsed: dict, task: str) -> str:
    """Pull the plain-text description out of Florence's structured output."""
    if isinstance(parsed, dict):
        if task in parsed:
            val = parsed[task]
            if isinstance(val, str):
                return val.strip()
            if isinstance(val, dict) and "labels" in val:
                return " ".join(val["labels"]).strip()
        # Fallback: concatenate all string values
        parts = [str(v) for v in parsed.values() if isinstance(v, str)]
        return " ".join(parts).strip()
    return str(parsed).strip()


def _auto_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"

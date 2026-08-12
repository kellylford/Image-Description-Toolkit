"""MLX chat — Apple Silicon local inference.

Split out of ``providers.py`` for one honest reason: none of this can run
anywhere except macOS on Apple Silicon, so it is dead weight in every coverage
measurement taken on Windows or CI. Keeping it here means ``providers.py``
reports the coverage of code that is actually exercised, and this module can
carry a low floor without pretending otherwise.

Ported from ``ChatProcessingWorker._chat_with_mlx`` in
``imagedescriber/workers_wx.py``, which was deleted with the rest of that class.
"""
from __future__ import annotations

from typing import Iterator

from ..providers.base import ChatDelta, ChatProvider, ChatRequest, ChatUsage, ChatYield
from .providers import _conversation_turns

__all__ = ["MLXChatProvider"]


class MLXChatProvider(ChatProvider):
    """Apple Silicon local inference. macOS only, and does not stream.

    Yields one :class:`ChatDelta` with the whole reply, so consumers cannot
    tell it apart from a streaming provider.

    **Known layering wart.** The MLX model loading, Metal memory management and
    JPEG conversion all live in ``imagedescriber/ai_providers.py``, so this
    class imports them from there. That is the wrong direction — ``idt_core``
    should not reach into the GUI package — and the proper fix is to move the
    MLX machinery into ``idt_core/providers/mlx.py``. That move is deliberately
    not attempted here: it cannot be exercised on a non-Apple-Silicon machine,
    and rewriting untestable model-loading code is how the batch path gets
    broken. The import is lazy and only runs when someone selects MLX, so no
    other provider or platform is affected.
    """

    #: MLX accepts a single image per conversation.
    MAX_IMAGES = 1

    def __init__(self, model: str):
        self._model = model

    @property
    def provider_name(self) -> str:
        return "mlx"

    @property
    def model_name(self) -> str:
        return self._model

    @staticmethod
    def _load_mlx():
        try:
            from imagedescriber.ai_providers import (  # type: ignore
                HAS_MLX_VLM, _mlx_apply_chat_template, _mlx_generate, _mlx_provider,
            )
        except ImportError:
            try:
                from ai_providers import (  # type: ignore
                    HAS_MLX_VLM, _mlx_apply_chat_template, _mlx_generate, _mlx_provider,
                )
            except ImportError as exc:
                raise RuntimeError(
                    "MLX support is not available in this build."
                ) from exc
        return HAS_MLX_VLM, _mlx_provider, _mlx_generate, _mlx_apply_chat_template

    def chat(self, request: ChatRequest) -> Iterator[ChatYield]:
        from pathlib import Path as _Path

        has_mlx, provider, generate, apply_template = self._load_mlx()
        if not has_mlx:
            raise RuntimeError(
                "mlx-vlm is not installed. Install it with: pip install mlx-vlm"
            )
        if not provider.is_available():
            raise RuntimeError(
                "MLX is not available. Requires macOS with Apple Silicon."
            )

        model = request.model or self._model
        provider._ensure_model_loaded(model)
        processor = provider._processor
        config = provider._mlx_config

        images = [a for m in request.messages for a in m.attachments if a.is_image]
        temp_jpeg = None
        if images:
            source = images[0].path
            if source:
                temp_jpeg = provider._to_jpeg_tempfile(source)

        # MLX silently ignores extra images, so say so rather than let the
        # user assume all of them were considered.
        warning = ""
        if len(images) > self.MAX_IMAGES:
            warning = (
                "[Note: MLX only supports 1 image per conversation. "
                "Only the first image was used.]\n\n"
            )

        try:
            # HuggingFace-style messages; the image goes in the first user turn.
            hf_messages = []
            if request.system_prompt:
                hf_messages.append(
                    {"role": "system", "content": request.system_prompt}
                )
            image_assigned = False
            for msg in _conversation_turns(request.messages):
                if msg.role == "user" and not image_assigned and temp_jpeg:
                    hf_messages.append({
                        "role": "user",
                        "content": [
                            {"type": "image"},
                            {"type": "text", "text": msg.content},
                        ],
                    })
                    image_assigned = True
                else:
                    hf_messages.append({"role": msg.role, "content": msg.content})

            try:
                prompt = processor.apply_chat_template(
                    hf_messages, tokenize=False, add_generation_prompt=True
                )
            except Exception:
                # Fall back to the single-prompt helper, which loses history.
                last_user = next(
                    (m.content for m in reversed(list(request.messages))
                     if m.role == "user"),
                    "",
                )
                prompt = apply_template(
                    processor, config,
                    f"Please respond in English only. {last_user}",
                    num_images=1 if temp_jpeg else 0,
                )

            output = generate(
                provider._model,
                processor,
                prompt,
                image=[temp_jpeg] if temp_jpeg else [],
                max_tokens=request.max_output_tokens or provider.MAX_TOKENS,
                verbose=False,
            )

            text = getattr(output, "text", None) or str(output)
            response = text.strip() if text else "MLX returned an empty response."
            yield ChatDelta(warning + response)
            yield ChatUsage(
                input_tokens=getattr(output, "prompt_tokens", 0) or 0,
                output_tokens=getattr(output, "generation_tokens", 0) or 0,
            )
        finally:
            if temp_jpeg:
                try:
                    _Path(temp_jpeg).unlink()
                except OSError:
                    pass

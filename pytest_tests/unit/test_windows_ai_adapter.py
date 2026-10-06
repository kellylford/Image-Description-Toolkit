"""ImageDescriber's Windows AI adapter (``imagedescriber/ai_providers.py``).

The contract suite (test_provider_contract.py) checks what every adapter must do. These check
what is particular to this one: which failures stop a batch, which are retried, which are one
picture's refusal; that a PC without the model gets it prepared first; that a model name from
another provider can't reach the helper; and where it is offered. The helper itself is replaced
by a stand-in for its ``request``; the provider's own tests run the real protocol.
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "imagedescriber")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ai_providers  # noqa: E402
from idt_core.providers import windows_ai  # noqa: E402
from idt_core.providers.windows_ai import WindowsAIError, error_for_code  # noqa: E402

pytestmark = pytest.mark.unit


class FakeHelper:
    """Answers each request with the next outcome: text, or a WindowsAIError to raise."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.kinds = []

    def request(self, kind, mime_type, image_bytes, timeout=None):
        self.kinds.append(kind)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def picture(tmp_path):
    from PIL import Image

    path = tmp_path / "photo.jpg"
    Image.new("RGB", (16, 16), (200, 120, 40)).save(path, format="JPEG")
    return str(path)


@pytest.fixture
def pc(monkeypatch):
    """A ready Copilot+ PC. Returns a function that installs a helper with given outcomes."""
    state = {"state": "Ready", "prepared": 0, "prepare_fails": None}

    def check_ready(force=False):
        return {"state": state["state"]}

    def prepare():
        if state["state"] == "Ready":
            return {"state": "Ready"}
        if state["prepare_fails"]:
            raise state["prepare_fails"]
        state["prepared"] += 1
        state["state"] = "Ready"
        return {"state": "Ready"}

    monkeypatch.setattr(windows_ai, "check_ready", check_ready)
    monkeypatch.setattr(windows_ai, "prepare", prepare)
    monkeypatch.setattr(ai_providers.time, "sleep", lambda _s: None)

    def install(*outcomes):
        fake = FakeHelper(*outcomes)
        monkeypatch.setattr(windows_ai, "_helper", fake)
        return fake

    install.state = state
    return install


def _fails(picture, model="accessible"):
    with pytest.raises(ai_providers.ProviderError) as caught:
        ai_providers.WindowsAIProvider().describe_image(picture, "a prompt", model)
    return caught.value


def test_a_description_comes_back_with_no_usage_to_report(pc, picture):
    helper = pc("A mug on a desk.")
    provider = ai_providers.WindowsAIProvider()
    assert provider.describe_image(picture, "ignored", "Brief") == "A mug on a desk."
    assert helper.kinds == ["brief"]
    assert provider.last_usage is None


def test_a_model_from_another_provider_becomes_the_default_kind(pc, picture):
    helper = pc("text")
    ai_providers.WindowsAIProvider().describe_image(picture, "", "llama3.2-vision")
    assert helper.kinds == ["accessible"]


def test_a_pc_without_the_model_gets_it_prepared_first(pc, picture):
    pc.state["state"] = "NotReady"
    helper = pc("text")
    ai_providers.WindowsAIProvider().describe_image(picture, "", "detailed")
    assert pc.state["prepared"] == 1
    assert helper.kinds == ["detailed"]


def test_a_model_that_cant_be_got_ready_stops_the_batch_at_once(pc, picture):
    """Getting it ready can take 15 minutes; a retry must not double that, on every picture."""
    pc.state["state"] = "NotReady"
    pc.state["prepare_fails"] = WindowsAIError(
        "Windows couldn't get its image description model ready. It may still be downloading.",
        code="not_ready", status_code=503)
    helper = pc("never asked")
    err = _fails(picture)
    assert err.kind == ai_providers.ErrorKind.UNAVAILABLE
    assert "still be downloading" in str(err), "the reason reaches the person"
    assert helper.kinds == []


def test_a_model_windows_dropped_after_being_ready_is_got_ready_again(pc, picture, monkeypatch):
    """The Ready report is cached for the process; a not_ready answer means it went stale."""
    asked_afresh = []
    cached = windows_ai.check_ready

    def check_ready(force=False):
        if force:
            asked_afresh.append(True)
            pc.state["state"] = "NotReady"
        return cached(force)

    monkeypatch.setattr(windows_ai, "check_ready", check_ready)
    helper = pc(error_for_code("not_ready", "The model isn't ready."), "Described after all.")
    assert ai_providers.WindowsAIProvider().describe_image(picture, "", "brief") == "Described after all."
    assert asked_afresh and pc.state["prepared"] == 1
    assert len(helper.kinds) == 2


@pytest.mark.parametrize("code", ["not_supported", "disabled_by_user", "blocked_by_policy"])
def test_a_pc_that_cant_run_it_stops_the_batch_without_retrying(pc, picture, code):
    helper = pc(error_for_code(code, "Windows' AI features are turned off."))
    err = _fails(picture)
    assert err.kind == ai_providers.ErrorKind.UNAVAILABLE
    assert "turned off" in str(err)
    assert len(helper.kinds) == 1


def test_a_missing_helper_stops_the_batch(monkeypatch, picture):
    monkeypatch.setattr(windows_ai, "_on_windows", lambda: True)
    monkeypatch.setattr(windows_ai, "_windows_build", lambda: 26200)
    monkeypatch.setattr(windows_ai, "_helper_command", lambda: None)
    assert _fails(picture).kind == ai_providers.ErrorKind.UNAVAILABLE


@pytest.mark.parametrize("code", ["content_filtered", "too_much_text", "decode_failed"])
def test_a_refusal_of_one_picture_is_not_retried_and_says_so(pc, picture, code):
    helper = pc(error_for_code(code, "Windows' content filter declined this picture."))
    err = _fails(picture)
    assert err.kind == ai_providers.ErrorKind.UNKNOWN and not err.is_retryable
    assert len(helper.kinds) == 1
    # The batch reads per_image from the exception this was raised from.
    assert getattr(err.__context__, "per_image", False) is True


def test_a_helper_that_restarted_is_tried_once_more(pc, picture):
    helper = pc(error_for_code("internal_error", "InternalError"), "Second time lucky.")
    assert ai_providers.WindowsAIProvider().describe_image(picture, "", "brief") == "Second time lucky."
    assert len(helper.kinds) == 2


def test_a_helper_failing_twice_is_reported_as_a_server_error(pc, picture):
    helper = pc(WindowsAIError("The Windows AI helper stopped unexpectedly.", status_code=503),
                WindowsAIError("The Windows AI helper stopped unexpectedly.", status_code=503))
    err = _fails(picture)
    assert err.kind == ai_providers.ErrorKind.SERVER_ERROR
    assert len(helper.kinds) == 2


def test_a_timeout_is_a_timeout(pc, picture):
    slow = WindowsAIError("Windows AI didn't describe the picture within 180 seconds.", timeout=True)
    pc(slow, slow)
    assert _fails(picture).kind == ai_providers.ErrorKind.TIMEOUT


# ---------------------------------------------------------------------------
# Where it is offered
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def other_providers_answer_at_once(monkeypatch):
    """The others' availability checks reach Ollama's port and look for SDKs and CLIs, which
    costs seconds a test. Their answers don't matter here: say the ungated ones are available."""
    for key, instance in ai_providers.get_all_providers().items():
        if key != "windows-ai":
            monkeypatch.setattr(instance, "is_available", lambda k=key: k not in ai_providers._GATED_PROVIDERS)


def _offered(**kwargs):
    return [key for key, _ in ai_providers.provider_picker_choices(**kwargs)]


def test_offered_only_where_it_can_run(monkeypatch):
    monkeypatch.setattr(ai_providers._windows_ai_provider, "is_available", lambda: False)
    assert "windows-ai" not in _offered()
    monkeypatch.setattr(ai_providers._windows_ai_provider, "is_available", lambda: True)
    assert "windows-ai" in _offered()
    assert ("windows-ai", "Windows AI") in ai_providers.provider_picker_choices()


def test_never_offered_where_only_a_prompt_matters(monkeypatch):
    monkeypatch.setattr(ai_providers._windows_ai_provider, "is_available", lambda: True)
    with_prompt = _offered(needs_prompt=True)
    assert "windows-ai" not in with_prompt
    assert set(_offered()) - set(with_prompt) == {"windows-ai"}


def test_only_windows_ai_takes_no_prompt():
    assert not ai_providers.provider_uses_prompt("windows-ai")
    assert not ai_providers.provider_uses_prompt("Windows AI")
    for key, _ in ai_providers._PICKER_PROVIDERS:
        if key != "windows-ai":
            assert ai_providers.provider_uses_prompt(key), key


def test_no_models_listed_when_it_cant_run(monkeypatch):
    monkeypatch.setattr(windows_ai, "is_available", lambda: False)
    assert ai_providers.WindowsAIProvider().get_available_models() == []
    monkeypatch.setattr(windows_ai, "is_available", lambda: True)
    assert ai_providers.WindowsAIProvider().get_available_models() == ["accessible", "detailed", "brief", "diagram"]


def test_registered_with_both_provider_lookups(monkeypatch):
    assert ai_providers.get_all_providers()["windows-ai"] is ai_providers._windows_ai_provider
    monkeypatch.setattr(ai_providers._windows_ai_provider, "is_available", lambda: True)
    assert "windows-ai" in ai_providers.get_available_providers()
    assert ai_providers.provider_key("Windows AI") == "windows-ai"

"""The Windows AI provider (``idt_core/providers/windows_ai.py``) against a stand-in helper.

The real helper is a packaged C# app that needs a Copilot+ PC's NPU, so these tests run the
provider's own code -- finding the helper, readiness, the long-lived ``--serve`` process, the
protocol, the failure codes -- against a small Python script that speaks the same protocol
and does whatever each test tells it to. Nothing here needs Windows: the platform check is a
function the tests replace. The C# side has its own tests (windows_ai_helper/IdtWindowsAI.Tests).
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from idt_core.providers import windows_ai  # noqa: E402
from idt_core.providers.windows_ai import WindowsAIError, WindowsAIProvider  # noqa: E402

pytestmark = pytest.mark.unit

#: The stand-in helper. Its behaviour comes from a JSON file named by FAKE_CONFIG; it appends
#: every request it receives to the file named by FAKE_LOG, and logs each start. The ``serve``
#: steps are numbered across restarts, so a step that kills the helper happens once.
FAKE_HELPER = r'''
import json, os, sys, time
cfg = json.load(open(os.environ["FAKE_CONFIG"], encoding="utf-8"))
def log(entry):
    with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
mode = sys.argv[1]
log({"start": mode})
if mode in ("--check", "--prepare"):
    state = cfg.get("prepared_state", "Ready") if mode == "--prepare" else cfg.get("state", "Ready")
    report = {"protocol": cfg.get("protocol", 1), "version": "1.0.0", "identity": cfg.get("identity", True),
              "state": state, "kinds": ["accessible", "detailed", "brief", "diagram"]}
    if cfg.get("message"):
        report["message"] = cfg["message"]
    print(cfg.get("check_prefix", "") + json.dumps(report), flush=True)
    sys.exit(0)
script = cfg.get("serve", [])
# The script runs across restarts: a helper started after one that died carries on from where it left off.
n = sum(1 for e in open(os.environ["FAKE_LOG"], encoding="utf-8") if '"start"' not in e)
for line in sys.stdin:
    request = json.loads(line)
    log({k: v for k, v in request.items() if k != "image"} | {"image_bytes": len(request.get("image", ""))})
    step = script[n] if n < len(script) else "ok"
    n += 1
    if step == "die":
        sys.exit(3)
    if step == "sleep":
        time.sleep(30)
    if step == "array":
        print("[]", flush=True)
        continue
    if step == "empty":
        print(json.dumps({"id": request["id"], "ok": True, "text": "  "}), flush=True)
        continue
    if step == "garbage":
        print("<html>not json</html>", flush=True)
        continue
    if step == "wrong_id":
        print(json.dumps({"id": request["id"] + 100, "ok": True, "text": "?"}), flush=True)
        continue
    if step.startswith("code:"):
        print(json.dumps({"id": request["id"], "ok": False, "code": step[5:], "message": "said the helper"}), flush=True)
        continue
    print(json.dumps({"id": request["id"], "ok": True, "kind": request["kind"],
                      "text": f"{request['kind']} description {n}", "seconds": 0.01}), flush=True)
'''


class FakeHelper:
    def __init__(self, tmp_path: Path):
        self.script = tmp_path / "fake_helper.py"
        self.script.write_text(FAKE_HELPER, encoding="utf-8")
        self.config_path = tmp_path / "fake_config.json"
        self.log_path = tmp_path / "fake_log.jsonl"
        self.configure()

    def configure(self, **cfg):
        self.config_path.write_text(json.dumps(cfg), encoding="utf-8")

    def entries(self):
        if not self.log_path.exists():
            return []
        return [json.loads(line) for line in self.log_path.read_text(encoding="utf-8").splitlines()]

    def starts(self, mode):
        return sum(1 for e in self.entries() if e.get("start") == mode)

    def requests(self):
        return [e for e in self.entries() if "start" not in e]


@pytest.fixture
def helper(tmp_path, monkeypatch):
    """A Windows PC with the helper installed, as far as the provider can tell."""
    fake = FakeHelper(tmp_path)
    monkeypatch.setenv("FAKE_CONFIG", str(fake.config_path))
    monkeypatch.setenv("FAKE_LOG", str(fake.log_path))
    monkeypatch.setattr(windows_ai, "_on_windows", lambda: True)
    monkeypatch.setattr(windows_ai, "_windows_build", lambda: 26200)
    monkeypatch.setattr(windows_ai, "_helper_command", lambda: [sys.executable, str(fake.script)])
    monkeypatch.setattr(windows_ai, "_ready_report", None)
    windows_ai.shutdown_helper()
    yield fake
    windows_ai.shutdown_helper()


JPEG = b"\xff\xd8\xff\xe0 pretend jpeg"


# ---------------------------------------------------------------------------
# Models, codes, availability
# ---------------------------------------------------------------------------


def test_the_models_are_the_kinds_and_accessible_comes_first():
    assert windows_ai.WINDOWS_AI_MODELS == ["accessible", "detailed", "brief", "diagram"]
    assert windows_ai.DEFAULT_MODEL == "accessible"
    assert windows_ai.WINDOWS_AI_MODEL_METADATA["accessible"]["recommended"] is True


@pytest.mark.parametrize("given,expected", [(None, "accessible"), ("Brief", "brief"), (" DIAGRAM ", "diagram")])
def test_kinds_are_read_whatever_their_case(given, expected):
    assert windows_ai.normalise_kind(given) == expected


def test_a_model_that_isnt_a_kind_names_the_kinds():
    with pytest.raises(ValueError, match="accessible, detailed, brief, diagram"):
        windows_ai.normalise_kind("moondream")


@pytest.mark.parametrize("code", ["content_filtered", "too_much_text", "unsupported_format", "decode_failed", "too_large"])
def test_a_refusal_for_one_picture_is_per_image(code):
    err = windows_ai.error_for_code(code, "x")
    assert (err.per_image, err.setup, err.code) == (True, False, code)


@pytest.mark.parametrize("code", ["not_supported", "disabled_by_user", "blocked_by_policy"])
def test_a_problem_with_the_pc_is_setup(code):
    err = windows_ai.error_for_code(code, "x")
    assert (err.setup, err.per_image) == (True, False)


@pytest.mark.parametrize("code", ["not_ready", "internal_error"])
def test_a_transient_problem_is_worth_retrying(code):
    assert windows_ai.error_for_code(code, "x").status_code == 503


def test_an_unknown_code_is_neither_setup_nor_per_image():
    err = windows_ai.error_for_code("bad_request", "x")
    assert (err.setup, err.per_image, err.status_code) == (False, False, None)


def test_available_only_on_windows_24h2_with_the_helper(monkeypatch):
    monkeypatch.setattr(windows_ai, "_helper_command", lambda: ["helper"])
    monkeypatch.setattr(windows_ai, "_windows_build", lambda: 26100)
    monkeypatch.setattr(windows_ai, "_on_windows", lambda: True)
    assert windows_ai.is_available()
    monkeypatch.setattr(windows_ai, "_windows_build", lambda: 22631)
    assert not windows_ai.is_available()
    monkeypatch.setattr(windows_ai, "_windows_build", lambda: 26100)
    monkeypatch.setattr(windows_ai, "_helper_command", lambda: None)
    assert not windows_ai.is_available()
    monkeypatch.setattr(windows_ai, "_helper_command", lambda: ["helper"])
    monkeypatch.setattr(windows_ai, "_on_windows", lambda: False)
    assert not windows_ai.is_available()


def test_the_helper_is_found_in_windowsapps_even_off_path(tmp_path, monkeypatch):
    apps = tmp_path / "Microsoft" / "WindowsApps"
    apps.mkdir(parents=True)
    (apps / windows_ai.HELPER_ALIAS).write_bytes(b"")
    monkeypatch.setattr(windows_ai.shutil, "which", lambda _name: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert windows_ai.find_helper() == str(apps / windows_ai.HELPER_ALIAS)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "elsewhere"))
    assert windows_ai.find_helper() is None


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("on_windows,build,has_helper,fragment", [
    (False, 26200, True, "only on Windows"),
    (True, 22631, True, "build 22631"),
    (True, 26200, False, "isn't installed"),
])
def test_check_ready_says_what_is_missing(monkeypatch, on_windows, build, has_helper, fragment):
    monkeypatch.setattr(windows_ai, "_on_windows", lambda: on_windows)
    monkeypatch.setattr(windows_ai, "_windows_build", lambda: build)
    monkeypatch.setattr(windows_ai, "_helper_command", lambda: ["helper"] if has_helper else None)
    with pytest.raises(WindowsAIError, match=fragment) as caught:
        windows_ai.check_ready()
    assert caught.value.setup


@pytest.mark.parametrize("cfg,fragment", [
    ({"identity": False}, "isn't installed as a package"),
    ({"protocol": 2}, "protocol 2"),
    ({"state": "NotSupportedOnCurrentSystem"}, "Copilot\\+ PC"),
    ({"state": "DisabledByUser"}, "turned off"),
    ({"state": "SomethingNew"}, "SomethingNew"),
])
def test_a_pc_that_cant_run_it_is_a_setup_error(helper, cfg, fragment):
    helper.configure(**cfg)
    with pytest.raises(WindowsAIError, match=fragment) as caught:
        windows_ai.check_ready()
    assert caught.value.setup


def test_a_ready_report_is_remembered_so_pickers_dont_start_a_process_each_time(helper):
    windows_ai.check_ready()
    windows_ai.check_ready()
    assert helper.starts("--check") == 1
    windows_ai.check_ready(force=True)
    assert helper.starts("--check") == 2


def test_a_model_not_yet_downloaded_passes_check_ready_and_isnt_remembered(helper):
    helper.configure(state="NotReady")
    assert windows_ai.check_ready()["state"] == "NotReady"
    windows_ai.check_ready()
    assert helper.starts("--check") == 2


def test_a_report_after_warnings_is_still_found(helper):
    helper.configure(check_prefix="WARNING: something first\n")
    assert windows_ai.check_ready()["state"] == "Ready"


def test_prepare_downloads_a_model_that_isnt_ready(helper):
    helper.configure(state="NotReady", prepared_state="Ready")
    assert windows_ai.prepare()["state"] == "Ready"
    assert helper.starts("--prepare") == 1


def test_prepare_that_fails_is_retryable_and_says_why(helper):
    helper.configure(state="NotReady", prepared_state="NotReady", message="still downloading")
    with pytest.raises(WindowsAIError, match="still downloading") as caught:
        windows_ai.prepare()
    assert (caught.value.code, caught.value.status_code) == ("not_ready", 503)


def test_prepare_does_nothing_when_already_ready(helper):
    windows_ai.prepare()
    assert helper.starts("--prepare") == 0


# ---------------------------------------------------------------------------
# Describing
# ---------------------------------------------------------------------------


def test_a_description_comes_back_with_the_kind_as_its_model(helper):
    result = WindowsAIProvider("Detailed").describe(JPEG, "image/jpeg", "a prompt")
    assert result.text == "detailed description 1"
    assert (result.provider, result.model) == ("windows-ai", "detailed")
    assert (result.input_tokens, result.output_tokens) == (None, None)


def test_the_prompt_never_reaches_the_helper(helper):
    WindowsAIProvider().describe(JPEG, "image/jpeg", "Describe this as a pirate would")
    request = helper.requests()[0]
    assert set(request) == {"id", "kind", "mime", "image_bytes"}
    assert request["kind"] == "accessible"


def test_one_helper_serves_every_picture_and_every_provider_instance(helper):
    for kind in ("brief", "detailed"):
        WindowsAIProvider(kind).describe(JPEG, "image/jpeg", "")
    assert helper.starts("--serve") == 1
    first, second = (r["id"] for r in helper.requests())
    assert second == first + 1


@pytest.mark.parametrize("code,flag", [("content_filtered", "per_image"), ("not_supported", "setup")])
def test_a_refusal_carries_its_meaning_and_the_helpers_message(helper, code, flag):
    helper.configure(serve=[f"code:{code}"])
    with pytest.raises(WindowsAIError, match="said the helper") as caught:
        WindowsAIProvider().describe(JPEG, "image/jpeg", "")
    assert getattr(caught.value, flag)
    assert caught.value.code == code


def test_after_a_refusal_the_same_helper_carries_on(helper):
    helper.configure(serve=["code:content_filtered", "ok"])
    provider = WindowsAIProvider()
    with pytest.raises(WindowsAIError):
        provider.describe(JPEG, "image/jpeg", "")
    assert provider.describe(JPEG, "image/jpeg", "").text.startswith("accessible")
    assert helper.starts("--serve") == 1


def test_a_helper_that_dies_is_retryable_and_the_next_picture_starts_another(helper):
    helper.configure(serve=["die"])
    provider = WindowsAIProvider()
    with pytest.raises(WindowsAIError, match="stopped unexpectedly") as caught:
        provider.describe(JPEG, "image/jpeg", "")
    assert caught.value.status_code == 503
    assert provider.describe(JPEG, "image/jpeg", "").text
    assert helper.starts("--serve") == 2


def test_a_helper_that_takes_too_long_is_stopped_and_reported_as_a_timeout(helper):
    helper.configure(serve=["sleep"])
    with pytest.raises(WindowsAIError) as caught:
        windows_ai.helper().request("brief", "image/jpeg", JPEG, timeout=1.0)
    assert caught.value.timeout
    assert not windows_ai.helper().is_running()


@pytest.mark.parametrize("step,fragment", [
    ("garbage", "can't read"), ("array", "can't read"), ("wrong_id", "different request"),
])
def test_an_answer_out_of_step_restarts_the_helper(helper, step, fragment):
    helper.configure(serve=[step])
    with pytest.raises(WindowsAIError, match=fragment) as caught:
        WindowsAIProvider().describe(JPEG, "image/jpeg", "")
    assert caught.value.status_code == 503
    assert not windows_ai.helper().is_running()


def test_a_missing_helper_is_a_setup_error_at_construction(monkeypatch):
    monkeypatch.setattr(windows_ai, "_on_windows", lambda: True)
    monkeypatch.setattr(windows_ai, "_windows_build", lambda: 26200)
    monkeypatch.setattr(windows_ai, "_helper_command", lambda: None)
    with pytest.raises(WindowsAIError) as caught:
        WindowsAIProvider()
    assert caught.value.setup


def test_a_type_the_helper_doesnt_take_is_converted_to_jpeg(helper):
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGBA", (8, 8), (255, 0, 0, 128)).save(out, format="WEBP")
    WindowsAIProvider().describe(out.getvalue(), "image/webp", "")
    assert helper.requests()[0]["mime"] == "image/jpeg"


def test_shutting_down_stops_the_helper(helper):
    WindowsAIProvider().describe(JPEG, "image/jpeg", "")
    assert windows_ai.helper().is_running()
    windows_ai.shutdown_helper()
    assert not windows_ai.helper().is_running()


# ---------------------------------------------------------------------------
# Registry, catalog and chat
# ---------------------------------------------------------------------------


def test_registered_as_local_keyless_and_unable_to_chat():
    from idt_core.providers import registry

    caps = registry.capabilities_for("Windows AI")
    assert (caps.provider, caps.display_name, caps.is_local, caps.requires_api_key, caps.chat) == (
        "windows-ai", "Windows AI", True, False, False)
    assert not caps.supports_attachments
    assert "windows-ai" in registry.list_providers()
    assert "windows-ai" not in registry.chat_providers()
    assert registry.can_chat("claude") and not registry.can_chat("windows_ai")


def test_every_other_registered_provider_can_still_chat():
    from idt_core.providers import registry

    assert set(registry.list_providers()) - set(registry.chat_providers()) == {"windows-ai"}


def test_the_catalog_lists_the_kinds_with_accessible_recommended():
    from idt_core.providers import catalog

    entries = catalog.curated_models("windows-ai")
    assert [e.id for e in entries] == windows_ai.WINDOWS_AI_MODELS
    assert entries[0].recommended
    assert all(e.context_window is None and e.cost == "free" for e in entries)


@pytest.mark.parametrize("name", ["windows-ai", "Windows AI", "windowsai"])
def test_chat_refuses_it_plainly(name):
    from idt_core.chat.providers import create_chat_provider

    with pytest.raises(ValueError, match="describes pictures but can't chat"):
        create_chat_provider(name, "accessible")


# ---------------------------------------------------------------------------
# A whole `idt describe` run
# ---------------------------------------------------------------------------


def test_idt_describe_records_the_kind_and_no_prompt(helper, tmp_path, monkeypatch, capsys):
    """End to end through the CLI: the run uses the stand-in helper, records the kind as the
    model and "none" as the prompt, and leaves the workspace's own default prompt alone."""
    import shutil

    from cli import main as cli_main
    from idt_core import config
    from idt_core.workspace import Workspace

    monkeypatch.setattr(config, "_CONFIG_FILE", tmp_path / "config.json")
    pictures = tmp_path / "pictures"
    pictures.mkdir()
    shutil.copy(_ROOT / "testimages" / "coffee_desk.jpg", pictures)
    bundle = tmp_path / "pictures.idtw"
    args = cli_main.build_parser().parse_args([
        "describe", str(pictures), "--workspace", str(bundle), "--provider", "windows-ai",
        "--model", "Brief", "--prompt", "narrative", "--no-export", "--no-video",
    ])
    args.func(args)

    captured = capsys.readouterr()
    assert "takes no prompt" in captured.err
    assert "not used (Windows AI describes with its brief kind)" in captured.out
    workspace = Workspace.open(bundle)
    (item,) = [i for i in workspace.items() if i.descriptions]
    description = item.descriptions[-1]
    assert (description.provider, description.model, description.prompt_name) == ("windows-ai", "brief", "none")
    assert description.text == "brief description 1"
    assert workspace.defaults.prompt_name == "detailed", "the workspace's own prompt is left alone"
    assert [r["kind"] for r in helper.requests()] == ["brief"]


def test_an_empty_description_is_never_returned(helper):
    helper.configure(serve=["empty"])
    with pytest.raises(WindowsAIError, match="empty description") as caught:
        WindowsAIProvider().describe(JPEG, "image/jpeg", "")
    assert caught.value.status_code == 503


def test_a_large_picture_is_scaled_down_rather_than_refused(helper):
    import os as _os

    from PIL import Image

    out = io.BytesIO()
    Image.frombytes("RGB", (3000, 3000), _os.urandom(3000 * 3000 * 3)).save(out, format="PNG")
    assert len(out.getvalue()) > windows_ai.MAX_IMAGE_BYTES
    WindowsAIProvider().describe(out.getvalue(), "image/png", "")
    request = helper.requests()[0]
    assert request["mime"] == "image/jpeg"
    assert request["image_bytes"] * 3 / 4 <= windows_ai.MAX_IMAGE_BYTES


def test_stop_doesnt_wait_for_a_picture_and_the_request_says_it_was_stopped(helper):
    """A GUI's Stop, and exit, must not hang behind a describe that takes minutes."""
    import threading
    import time

    helper.configure(serve=["sleep"])
    outcome = {}

    def describe():
        try:
            WindowsAIProvider().describe(JPEG, "image/jpeg", "")
        except WindowsAIError as exc:
            outcome["error"] = exc

    worker = threading.Thread(target=describe)
    worker.start()
    deadline = time.time() + 10
    while not helper.requests() and time.time() < deadline:
        time.sleep(0.05)
    started = time.time()
    assert windows_ai.helper().is_running(), "checking must not wait for the picture either"
    windows_ai.shutdown_helper()
    worker.join(10)
    assert time.time() - started < 8
    assert "stopped before it finished" in str(outcome["error"])
    assert outcome["error"].status_code is None, "stopped on purpose: not to be retried"


# ---------------------------------------------------------------------------
# guideme
# ---------------------------------------------------------------------------


def test_guideme_running_the_command_prints_no_prompt_note(capsys):
    from types import SimpleNamespace

    from cli.main import _resolve_prompt

    assert _resolve_prompt(SimpleNamespace(prompt="none", prompt_text=None), None, "windows-ai") == ("none", "")
    assert capsys.readouterr().err == ""


def test_guideme_command_has_no_prompt_for_windows_ai():
    from cli.guide import _build_command

    parts = _build_command("dir", "C:/pics", "windows-ai", "brief", "none", True, False, {})
    assert "--prompt" not in parts
    assert parts[parts.index("--model") + 1] == "brief"


def test_guideme_declining_to_prepare_doesnt_claim_it_is_ready(helper, monkeypatch, capsys):
    from cli import guide

    helper.configure(state="NotReady")
    monkeypatch.setattr(guide, "get_yes_no", lambda *a, **k: False)
    assert guide._check_windows_ai()
    out = capsys.readouterr().out
    assert "when the first picture is described" in out
    assert "is ready" not in out
    assert helper.starts("--prepare") == 0


def test_guideme_reads_each_kind_once(monkeypatch, capsys):
    from cli import guide

    seen = {}
    monkeypatch.setattr(guide, "get_choice", lambda _q, labels, **k: seen.setdefault("labels", labels) and "BACK")
    guide._step_model("windows-ai")
    assert seen["labels"][0] == "Accessible  (recommended)"


def test_only_windows_ai_takes_no_prompt():
    from idt_core.providers import registry

    assert not registry.uses_prompt("windows-ai") and not registry.uses_prompt("Windows AI")
    assert [p for p in registry.list_providers() if not registry.uses_prompt(p)] == ["windows-ai"]
    assert registry.uses_prompt("something-new"), "an unknown provider is assumed to take a prompt"

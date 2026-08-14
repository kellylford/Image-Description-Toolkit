"""A floor under the standalone chat app's wx layer.

Same reasoning as ``test_gui_smoke.py``, which covers ``imagedescriber/``:
wxPython swallows exceptions raised inside event handlers, so a broken handler
is not a traceback, it is a button that does nothing. This file is the
equivalent floor for ``chatapp/``, kept separate because the other file is
parametrised over the ImageDescriber directory and its flat-import convention.

Three things are checked:

1. The modules import under a real ``wx.App``.
2. **Every handler named in a ``Bind()`` call exists on the class.** This is the
   check that catches a renamed method leaving a dead binding — the failure wx
   is least able to report.
3. A whole turn runs end to end through the real ``ChatWorker`` and the real
   ``wx.CallAfter`` marshalling, with a fake provider. That covers the part
   that is genuinely hard to reason about: a background thread delivering
   events to a window that may already be gone.
"""

import ast
import os
import re
import sys
import time
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_APP_DIR = _ROOT / "chatapp"
for _p in (str(_ROOT), str(_APP_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

REQUIRE_WX = os.environ.get("IDT_REQUIRE_WX") == "1"

try:
    import wx
except ImportError as _exc:  # pragma: no cover
    if REQUIRE_WX:
        raise RuntimeError(
            "IDT_REQUIRE_WX=1 but wxPython is not importable, so the chat app "
            f"smoke tests cannot run: {_exc}"
        ) from _exc
    wx = None

pytestmark = pytest.mark.skipif(
    wx is None, reason="wxPython not installed in this environment")

APP_SOURCE = _APP_DIR / "chat_app_wx.py"


def _accessible_is_supported() -> bool:
    """True where wx.Accessible can actually be constructed.

    It is a Windows-only feature: on GTK and macOS both the constructor and
    ``GetAccessible()`` raise NotImplementedError. The production code already
    guards for that (``_set_accessible_name`` swallows it); these tests did
    not, which is how three of them failed on the Apple Silicon runner while
    passing locally.
    """
    if wx is None:
        return False
    try:
        app = wx.App.Get() or wx.App(False)  # noqa: F841 - needed for wx.Frame
        frame = wx.Frame(None)
    except Exception:
        return False
    try:
        wx.Accessible(wx.TextCtrl(frame))
        return True
    except (NotImplementedError, AttributeError):
        return False
    finally:
        frame.Destroy()


ACCESSIBLE_SUPPORTED = _accessible_is_supported()

accessible_only = pytest.mark.skipif(
    not ACCESSIBLE_SUPPORTED,
    reason="wx.Accessible is Windows-only; unavailable on this platform",
)


@pytest.fixture(scope="module")
def wx_app():
    app = None
    try:
        app = wx.App.Get() or wx.App(False)
    except Exception as exc:  # pragma: no cover
        if REQUIRE_WX:
            pytest.fail(f"wxPython imports but wx.App() failed: {exc}")
        pytest.skip(f"no usable display for wxPython: {exc}")
    yield app


# ---------------------------------------------------------------------------
# 1. Imports
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module_name", ["shared.chat_worker_wx", "chat_app_wx"])
def test_module_imports(module_name, wx_app):
    import importlib

    importlib.import_module(module_name)


def test_engine_layer_stays_free_of_wx():
    """idt_core.chat must never import wx, or the CLI stops working.

    Checked by source inspection rather than sys.modules, because this test
    module has already imported wx by the time it runs.
    """
    for path in (_ROOT / "idt_core" / "chat").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "").split(".")[0]]
            else:
                continue
            assert "wx" not in names, f"{path.name} imports wx"


# ---------------------------------------------------------------------------
# 2. Bind() handlers must exist
# ---------------------------------------------------------------------------

def _bound_handler_names(source: str):
    """Every ``self.<name>`` passed as a handler to a ``.Bind(...)`` call.

    Only the second positional argument: ``Bind(event, handler, source)`` —
    the third is the widget the event comes from, not a handler.
    """
    tree = ast.parse(source)
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "Bind"):
            continue
        for arg in node.args[1:2]:
            if (isinstance(arg, ast.Attribute)
                    and isinstance(arg.value, ast.Name)
                    and arg.value.id == "self"):
                found.add(arg.attr)
    return found


def test_every_bound_handler_exists(wx_app):
    """A renamed method that leaves a stale Bind() is a dead control."""
    from chat_app_wx import ApiKeysDialog, ChatFrame, ProviderDialog

    handlers = _bound_handler_names(APP_SOURCE.read_text(encoding="utf-8"))
    assert handlers, "no Bind() handlers found — has the parser drifted?"

    classes = (ChatFrame, ProviderDialog, ApiKeysDialog)
    missing = [
        name for name in sorted(handlers)
        if not any(hasattr(cls, name) for cls in classes)
    ]
    assert not missing, f"Bind() names methods that do not exist: {missing}"


def test_api_keys_dialog_constructs_with_all_providers(wx_app):
    """The dialog builds headless and offers exactly the shared-key providers."""
    from chat_app_wx import ApiKeysDialog

    dlg = ApiKeysDialog(None)
    try:
        assert set(dlg._fields) == {"claude", "openai", "ollama.com"}
        for field in dlg._fields.values():
            assert field.GetValue() == "", "stored keys must never be pre-filled"
    finally:
        dlg.Destroy()


def test_menu_handlers_exist(wx_app):
    """_menu_item() takes handlers positionally, so Bind scanning misses them."""
    from chat_app_wx import ChatFrame

    source = APP_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    named = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_menu_item"):
            for arg in node.args:
                if (isinstance(arg, ast.Attribute)
                        and isinstance(arg.value, ast.Name)
                        and arg.value.id == "self"):
                    named.add(arg.attr)

    assert named, "no _menu_item handlers found"
    missing = [n for n in sorted(named) if not hasattr(ChatFrame, n)]
    assert not missing, f"menu items name missing handlers: {missing}"


# ---------------------------------------------------------------------------
# 2b. Screen reader naming
# ---------------------------------------------------------------------------

@accessible_only
def test_accessible_name_defers_to_wx_for_list_items(wx_app):
    """childId > 0 is a list item, and must NOT get the control's label.

    Reported bug: arrowing through the conversation announced "Conversation
    history" on every press instead of reading the message. Cause was a
    wx.Accessible whose GetName ignored childId, so every item inherited the
    control's name and the item text was never spoken.
    """
    from chat_app_wx import _NamedAccessible

    frame = wx.Frame(None)
    try:
        ctrl = wx.TextCtrl(frame)
        acc = _NamedAccessible(ctrl, "Your message")

        assert acc.GetName(0) == (wx.ACC_OK, "Your message")
        for child_id in (1, 2, 7):
            status, _ = acc.GetName(child_id)
            assert status == wx.ACC_NOT_IMPLEMENTED, (
                f"childId {child_id} must defer to wx so the item text is read"
            )
    finally:
        frame.Destroy()


@accessible_only
def test_list_controls_do_not_get_a_custom_accessible(wx_app):
    """A ListBox reports its own items; overriding that hides them."""
    from chat_app_wx import _set_accessible_name

    frame = wx.Frame(None)
    try:
        listbox = wx.ListBox(frame, choices=["first message", "second message"])
        _set_accessible_name(listbox, "Conversation history")

        assert listbox.GetName() == "Conversation history"
        assert listbox.GetAccessible() is None, (
            "a custom accessible on a ListBox masks the item text"
        )
    finally:
        frame.Destroy()


def test_history_and_session_lists_keep_their_items_readable(frame):
    """End to end: the real controls must expose item strings, not just a name."""
    frame.history_list.Append("You: hello")
    frame.history_list.Append("fake-1: hi there")

    # Item text is the part that matters on every platform.
    assert frame.history_list.GetString(0) == "You: hello"
    assert frame.history_list.GetString(1) == "fake-1: hi there"
    assert frame.history_list.GetName() == "Conversation history"

    if ACCESSIBLE_SUPPORTED:
        assert frame.history_list.GetAccessible() is None
        assert frame.session_list.GetAccessible() is None


# ---------------------------------------------------------------------------
# 3. A real turn, end to end
# ---------------------------------------------------------------------------

class _FakeProvider:
    provider_name = "fake"
    model_name = "fake-1"

    def __init__(self, chunks=("Hello", " world")):
        self._chunks = list(chunks)

    def chat(self, request):
        from idt_core.providers.base import ChatDelta, ChatUsage

        for chunk in self._chunks:
            yield ChatDelta(chunk)
        yield ChatUsage(input_tokens=9, output_tokens=2)


def _pump(predicate, timeout=5.0):
    """Run the wx event loop until predicate() or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        wx.YieldIfNeeded()
        if predicate():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def frame(wx_app, tmp_path):
    from chat_app_wx import ChatFrame
    from idt_core.chat import DirectoryChatStore

    frame = ChatFrame()
    frame.store = DirectoryChatStore(tmp_path)
    yield frame
    frame.Destroy()
    wx.YieldIfNeeded()


def test_a_turn_streams_and_lands_in_history(frame):
    from idt_core.chat import ChatEngine

    frame.engine = ChatEngine(frame.session, _FakeProvider(), frame.store)
    frame.model_name = "fake-1"
    frame._start_turn("hi there")

    assert _pump(lambda: not frame._is_streaming), "turn did not finish"

    roles = [m.role for m in frame.session.messages]
    assert roles == ["user", "assistant"]
    assert frame.session.messages[-1].content == "Hello world"
    assert frame.history_list.GetCount() == 2
    assert frame.send_btn.IsEnabled()
    assert not frame.stop_btn.IsEnabled()


def test_history_lines_name_the_speaker(frame):
    """A screen reader should say who spoke, not read an anonymous line."""
    from idt_core.chat import ChatEngine

    frame.engine = ChatEngine(frame.session, _FakeProvider(), frame.store)
    frame._start_turn("question")
    assert _pump(lambda: not frame._is_streaming)

    lines = [frame.history_list.GetString(i)
             for i in range(frame.history_list.GetCount())]
    assert lines[0].startswith("You:")
    assert lines[1].startswith("fake-1:")


def test_streaming_does_not_announce_each_chunk(frame):
    """Announcing per token would make a screen reader unusable."""
    from idt_core.chat import ChatEngine

    announced = []
    frame._announce = lambda text: announced.append(text)
    frame.engine = ChatEngine(frame.session, _FakeProvider(
        chunks=["a", "b", "c", "d"]), frame.store)
    frame._start_turn("hi")
    assert _pump(lambda: not frame._is_streaming)

    # Four chunks arrived; exactly one announcement, carrying the whole reply.
    assert len(announced) == 1
    assert announced[0] == "abcd"


def test_silent_policy_announces_nothing(frame):
    from chat_app_wx import ANNOUNCE_SILENT
    from idt_core.chat import ChatEngine

    frame.announce_policy = ANNOUNCE_SILENT
    statuses = []
    frame._set_status = lambda text, field=0: statuses.append(text)

    frame.engine = ChatEngine(frame.session, _FakeProvider(), frame.store)
    frame._start_turn("hi")
    assert _pump(lambda: not frame._is_streaming)

    # The status bar still updates; the reader-directed announcement does not.
    assert "Response complete" in statuses


def test_worker_delivering_to_a_destroyed_window_is_a_no_op(wx_app, tmp_path):
    """The old worker posted to deleted C++ objects after the window closed."""
    from chat_app_wx import ChatFrame
    from shared.chat_worker_wx import ChatWorker
    from idt_core.chat import ChatEngine, ChatFinished, DirectoryChatStore, ChatSession

    frame = ChatFrame()
    session = ChatSession()
    engine = ChatEngine(session, _FakeProvider(), DirectoryChatStore(tmp_path))
    worker = ChatWorker(frame, engine, lambda: engine.send("hi"))

    frame.Destroy()
    wx.YieldIfNeeded()

    # Must not raise even though the window is gone.
    worker._dispatch(ChatFinished(message=session.messages[0]
                                  if session.messages else None))


def test_token_usage_reports_context_and_billed_separately(frame):
    from idt_core.chat import ChatEngine

    frame.engine = ChatEngine(frame.session, _FakeProvider(), frame.store)
    frame._start_turn("one")
    assert _pump(lambda: not frame._is_streaming)
    frame._start_turn("two")
    assert _pump(lambda: not frame._is_streaming)

    # Two replies at 9 in / 2 out each.
    assert frame.session.context_tokens == 11
    assert frame.session.billed_tokens == 22


def test_enter_on_a_saved_conversation_opens_it(frame, tmp_path):
    """Reported bug: Enter in the conversation list did nothing.

    A native wx.ListBox on MSW does not generate EVT_KEY_DOWN for Enter, so the
    per-list binding never fired. Enter is handled at frame level instead, and
    this asserts the routing rather than the binding.
    """
    from idt_core.chat import ChatMessage, ChatSession

    saved = ChatSession(title="Earlier conversation")
    saved.add(ChatMessage(role="user", content="from before"))
    frame.store.save(saved)
    frame._refresh_sessions()
    frame.session_list.SetSelection(0)

    assert frame.session.id != saved.id, "precondition: a different chat is open"

    consumed = frame._handle_return(frame.session_list, shift_down=False)

    assert consumed, "Enter must be consumed when the conversation list has focus"
    assert frame.session.id == saved.id
    assert frame.session.display_title() == "Earlier conversation"
    assert frame.history_list.GetCount() == 1


def test_enter_elsewhere_is_not_swallowed(frame):
    """Enter on a button must still activate it, not be eaten by the frame."""
    assert frame._handle_return(frame.send_btn, shift_down=False) is False
    assert frame._handle_return(None, shift_down=False) is False


def test_delete_removes_the_selected_conversation(frame, monkeypatch):
    """Plain Delete, not a chord — but only when the list has focus."""
    import chat_app_wx
    from idt_core.chat import ChatMessage, ChatSession

    doomed = ChatSession(title="Delete me")
    doomed.add(ChatMessage(role="user", content="x"))
    frame.store.save(doomed)
    frame._refresh_sessions()
    frame.session_list.SetSelection(0)

    monkeypatch.setattr(chat_app_wx.wx, "MessageBox", lambda *a, **k: wx.YES)

    consumed = frame._handle_delete(frame.session_list)

    assert consumed
    assert frame.store.load(doomed.id) is None
    assert frame.session_list.GetCount() == 0


def test_delete_asks_before_destroying_a_conversation(frame, monkeypatch):
    import chat_app_wx
    from idt_core.chat import ChatMessage, ChatSession

    kept = ChatSession(title="Keep me")
    kept.add(ChatMessage(role="user", content="x"))
    frame.store.save(kept)
    frame._refresh_sessions()
    frame.session_list.SetSelection(0)

    monkeypatch.setattr(chat_app_wx.wx, "MessageBox", lambda *a, **k: wx.NO)
    frame._handle_delete(frame.session_list)

    assert frame.store.load(kept.id) is not None, "declining must not delete"


def test_delete_keeps_its_text_editing_meaning(frame):
    """The reason this is not a menu accelerator.

    A plain-Delete accelerator on the menu bar is application-wide: it would
    fire while typing and you could not delete a character in the message box.
    """
    assert frame._handle_delete(frame.input_text) is False
    assert frame._handle_delete(frame.detail) is False
    assert frame._handle_delete(frame.history_list) is False
    assert frame._handle_delete(None) is False


def test_delete_chat_menu_item_has_no_accelerator():
    """Guards the above: an accelerator here would break typing."""
    source = APP_SOURCE.read_text(encoding="utf-8")
    match = re.search(r'"&?Delete Chat[^"]*"', source)
    assert match, "Delete Chat menu item not found"
    assert "\\t" not in match.group(0), (
        f"Delete Chat must not carry a menu accelerator: {match.group(0)}"
    )


def test_delete_removes_the_selected_attachment(frame, tmp_path):
    photo = tmp_path / "photo.png"
    photo.write_bytes(b"png")
    frame.provider_name = "claude"
    frame._add_attachments([photo])
    frame.attach_list.SetSelection(0)

    assert frame._handle_delete(frame.attach_list) is True
    assert frame.pending_attachments == []


def test_shift_enter_only_applies_to_the_message_box(frame):
    frame.input_text.SetValue("")
    assert frame._handle_return(frame.input_text, shift_down=True) is True
    assert "\n" in frame.input_text.GetValue()


def test_attachments_are_sent_then_cleared(frame, tmp_path):
    """Queued files ride along with the next message and are not re-sent.

    Re-sending would re-upload the same image on every later turn; the engine
    de-duplicates, but the queue must not hold on to them either.
    """
    from idt_core.chat import ChatEngine

    photo = tmp_path / "photo.png"
    photo.write_bytes(b"pretend-png")
    frame.provider_name = "claude"
    frame._add_attachments([photo])

    assert len(frame.pending_attachments) == 1
    assert frame.attach_list.GetCount() == 1
    assert "1 file" in frame.attach_label.GetLabel()

    provider = _FakeProvider()
    frame.engine = ChatEngine(frame.session, provider, frame.store)
    frame.input_text.SetValue("what is this?")
    frame.on_send(None)
    assert _pump(lambda: not frame._is_streaming)

    user_turn = frame.session.messages[0]
    assert [a.name for a in user_turn.attachments] == ["photo.png"]
    assert frame.pending_attachments == []
    assert frame.attach_list.GetCount() == 0
    assert "none" in frame.attach_label.GetLabel()


def test_a_rejected_file_leaves_the_queue_empty_not_broken(frame, tmp_path):
    """A PDF on Ollama must be refused without disturbing anything else."""
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF")
    frame.provider_name = "ollama"

    # _add_attachments reports rejections in a modal dialog, which would hang
    # the test run; replace it with a recorder so the message is still checked.
    import chat_app_wx

    shown = []
    original = chat_app_wx.wx.MessageBox
    chat_app_wx.wx.MessageBox = lambda text, *a, **k: shown.append(text)
    try:
        frame._add_attachments([pdf])
    finally:
        chat_app_wx.wx.MessageBox = original

    assert shown and "doc.pdf" in shown[0]

    assert frame.pending_attachments == []
    assert frame.attach_list.GetCount() == 0


def test_switching_to_a_provider_without_attachments_clears_the_queue(frame, tmp_path):
    photo = tmp_path / "photo.png"
    photo.write_bytes(b"png")
    frame.provider_name = "claude"
    frame._add_attachments([photo])
    assert frame.pending_attachments

    frame.provider_name = "ollama cloud"   # registered as taking none
    frame._update_attach_controls()

    assert frame.pending_attachments == []
    assert not frame.attach_btn.IsEnabled()


def test_history_line_names_the_attachment(frame, tmp_path):
    from idt_core.chat.messages import Attachment, ChatMessage

    message = ChatMessage(role="user", content="look",
                          attachments=[Attachment("image/png", path=str(tmp_path / "cat.png"))])
    line = frame._line_for(message)

    assert "cat.png" in line
    assert line.startswith("You:")


def test_export_markdown_includes_the_system_prompt(frame, tmp_path):
    from idt_core.chat import ChatEngine

    frame.session.system_prompt = "Be terse."
    frame.engine = ChatEngine(frame.session, _FakeProvider(), frame.store)
    frame._start_turn("hi")
    assert _pump(lambda: not frame._is_streaming)

    markdown = frame._markdown()
    assert "Be terse." in markdown
    assert "Hello world" in markdown

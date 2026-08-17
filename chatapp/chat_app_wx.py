"""IDT Chat — a keyboard-first, screen-reader-first chat client.

A standalone application rather than a window inside ImageDescriber, because
chat is not about images. Discoverability is itself an accessibility feature:
an app named for what it does beats a menu item three levels into an image
tool.

Accessibility decisions, and why
--------------------------------
* **The conversation is a ``wx.ListBox``**, not a rich text control or a tree.
  One tab stop, arrow-key navigation, and every item is a string a screen
  reader announces reliably. Each line names its speaker and model, so the
  reader says "Claude Opus 5" rather than leaving an anonymous response.
* **A separate, editable detail pane** holds the full text of the selected
  message. Editable so it can be selected, arrowed through and copied; edits
  are never saved.
* **Streaming does not narrate.** Text accumulates silently and is announced
  once, complete, according to the announcement policy. Announcing every
  token would make a screen reader unusable — this is the main reason the
  policy exists at all.
* **Every action has a keyboard accelerator** and appears in the menu bar.
* **State changes that used to be silent now speak**: truncation, retries,
  errors, and the arrival of a response.

Run directly with ``python chatapp/chat_app_wx.py``.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Make idt_core importable both from a source checkout and a frozen build.
if getattr(sys, "frozen", False):
    _ROOT = Path(sys.executable).parent
else:
    _ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import wx  # noqa: E402

from idt_core.chat import (  # noqa: E402
    ChatCancelled,
    ChatDelta,
    ChatEngine,
    ChatFailed,
    ChatFinished,
    ChatOptions,
    ChatRetrying,
    ChatSession,
    ChatStarted,
    ChatThinking,
    ChatToolCall,
    ChatToolResult,
    ChatUsage,
    DirectoryChatStore,
    prepare_attachments,
)
from idt_core.chat.messages import Attachment  # noqa: E402
from idt_core.chat.providers import create_chat_provider  # noqa: E402
from idt_core.keys import (  # noqa: E402
    ENV_VARS,
    credential_store_name,
    delete_api_key,
    key_source,
    missing_key_message,
    requires_api_key,
    resolve_api_key,
    store_api_key,
)
from idt_core.providers.registry import (  # noqa: E402
    attachment_wildcard,
    capabilities_for,
    list_providers,
    supports_attachments,
)

from shared.chat_worker_wx import ChatWorker  # noqa: E402
from shared.mac_accessibility import (  # noqa: E402
    clear_command_key_equivalents,
    install_dialog_naming,
    set_accessible_name as _set_mac_accessible_name,
)
from shared.speech_engine import (  # noqa: E402
    RATE_PRESET_LABELS,
    SpeechSettings,
    default_options,
    list_speech_options,
    speaker,
)

APP_NAME = "IDT Chat"

#: True on macOS. wx maps every "Ctrl+" accelerator to Command here, so the
#: same accelerator string has to clear two sets of platform conventions.
_MAC = wx.Platform == "__WXMAC__"

#: How much a screen reader should say when a response arrives.
ANNOUNCE_FULL = "full"
ANNOUNCE_SUMMARY = "summary"
ANNOUNCE_SILENT = "silent"

ANNOUNCE_LABELS = {
    ANNOUNCE_FULL: "Announce the full response",
    ANNOUNCE_SUMMARY: "Announce a summary (first sentence and length)",
    ANNOUNCE_SILENT: "Announce nothing",
}


def _version() -> str:
    try:
        from idt_core import __version__

        return __version__
    except Exception:
        return "unknown"


class _NamedAccessible(wx.Accessible):
    """Give a control a name VoiceOver will actually read.

    ``SetName()`` does not reach NSAccessibility for text controls on macOS, so
    the name has to come from an overridden ``GetName``.

    **childId matters.** childId 0 is the control itself; anything above 0 is
    the Nth child — the individual items of a list. Returning the control's
    label for every childId makes a screen reader announce "Conversation
    history" on every arrow key instead of reading the message under the
    cursor. Children must defer to wx's own implementation, which supplies the
    item text.
    """

    def __init__(self, window: wx.Window, label: str):
        super().__init__(window)
        self._label = label

    def GetName(self, childId):
        if childId:
            return (wx.ACC_NOT_IMPLEMENTED, None)
        return (wx.ACC_OK, self._label)


def _set_accessible_name(control: wx.Window, label: str) -> None:
    """Name a control for screen readers, on both platforms.

    Three mechanisms, because no one of them works everywhere:

    * ``SetName`` — what wx itself carries, and what NVDA and Narrator read for
      most Windows controls.
    * ``wx.Accessible`` — needed on Windows for text controls, whose name does
      not otherwise reach MSAA. **Only** text controls get one: item-bearing
      controls such as wx.ListBox already report their items correctly, and a
      custom accessible on those risks masking the item text — which is the
      whole point of using a ListBox for the conversation.
    * ``NSAccessibility`` — the macOS route, and it applies to *every* control
      type, because there wx names none of them. This is the fix for tabbing to
      a field and hearing its contents but never its label: VoiceOver was
      reading the value because there was no name to read.
    """
    control.SetName(label)
    _set_mac_accessible_name(control, label)    # no-op off macOS
    if not isinstance(control, wx.TextCtrl):
        return
    try:
        control.SetAccessible(_NamedAccessible(control, label))
    except (NotImplementedError, AttributeError):
        pass  # wx.Accessible is Windows-only in some builds


def _first_sentence(text: str) -> str:
    stripped = " ".join(text.split())
    for end in (". ", "? ", "! "):
        index = stripped.find(end)
        if 0 < index < 200:
            return stripped[: index + 1]
    return stripped[:200]


class ProviderDialog(wx.Dialog):
    """Pick a provider and model."""

    def __init__(self, parent, provider: str = "ollama", model: str = ""):
        super().__init__(parent, title="Choose Provider and Model",
                         size=(460, 220))
        self._initial_model = model

        sizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(2, 2, 8, 8)
        grid.AddGrowableCol(1, 1)

        grid.Add(wx.StaticText(self, label="&Provider:"), 0,
                 wx.ALIGN_CENTER_VERTICAL)
        # wx.Choice rather than wx.ComboBox: ComboBox crashes VoiceOver on
        # macOS, a defect already documented in the ImageDescriber chat window.
        self.provider_choice = wx.Choice(self, choices=self._provider_names())
        _set_accessible_name(self.provider_choice, "Provider")
        grid.Add(self.provider_choice, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label="&Model:"), 0,
                 wx.ALIGN_CENTER_VERTICAL)
        self.model_choice = wx.Choice(self, choices=[])
        _set_accessible_name(self.model_choice, "Model")
        grid.Add(self.model_choice, 1, wx.EXPAND)

        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)

        self.status = wx.StaticText(self, label="")
        sizer.Add(self.status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizer(sizer)

        self.provider_choice.Bind(wx.EVT_CHOICE, self._on_provider)
        index = self.provider_choice.FindString(provider)
        self.provider_choice.SetSelection(max(index, 0))
        self._populate_models()

    @staticmethod
    def _mlx_is_usable() -> bool:
        """True only where MLX chat can actually run.

        Platform is not enough. This app's PyInstaller spec excludes mlx and
        mlx_vlm to keep the binary small, so on a packaged macOS build the
        machine can be Apple Silicon and the option still fail. Offering a
        provider that raises the moment it is chosen is worse than not
        offering it, so the check is "can we import it", not "what OS is this".
        """
        if sys.platform != "darwin":
            return False
        try:
            import mlx_vlm  # noqa: F401
        except Exception:
            return False
        return True

    @classmethod
    def _provider_names(cls):
        names = [p for p in list_providers() if p != "ollama cloud"]
        if not cls._mlx_is_usable():
            names = [p for p in names if p != "mlx"]
        return names

    def _on_provider(self, _event):
        self._populate_models()

    def _populate_models(self):
        provider = self.provider_choice.GetStringSelection()
        self.model_choice.Clear()
        self.status.SetLabel("")

        if provider == "ollama":
            # Off the UI thread: listing asks /api/show once per installed
            # model, so with 20-30 models pulled this froze the window for
            # seconds — and far longer against a remote host or a stopped
            # daemon, where every probe waits out its own timeout.
            self._start_ollama_listing()
            return

        if provider in ("claude", "openai"):
            # Painted synchronously from the model catalog, which never touches
            # the network: with no cache and no key this is exactly the curated
            # list, so the picker is filled the instant the dialog opens and is
            # never empty. The live refresh happens behind it (issue #267).
            try:
                from idt_core.providers import catalog

                # `keep` so a model the account no longer lists — but which the
                # user has selected — cannot silently vanish and leave them on
                # whatever happens to be first.
                entries = catalog.cached_models(
                    provider, keep=[self._initial_model] if self._initial_model else []
                )
                for entry in entries:
                    # Display name shown, API id kept as client data. Reading
                    # the client data is what makes pre-selection work.
                    self.model_choice.Append(entry.display(), entry.id)
            except Exception as exc:                        # noqa: BLE001
                self.status.SetLabel(f"Could not list models: {exc}")

            if requires_api_key(provider) and not resolve_api_key(provider):
                self.status.SetLabel(missing_key_message(provider))
            self._select_model(self._initial_model)
            self._start_catalog_refresh(provider)
            return

        self._select_model(self._initial_model)

    # -- Ollama -----------------------------------------------------------

    def _start_ollama_listing(self):
        """List Ollama chat models on a worker thread, fill the picker after.

        The generation token guards two races: the user switching provider
        while a listing is in flight (a late result must not repopulate the
        picker for a different provider), and the dialog being closed before
        the thread finishes.
        """
        import threading

        self._load_token = getattr(self, "_load_token", 0) + 1
        token = self._load_token
        self.status.SetLabel("Looking for Ollama models…")

        def work():
            try:
                from idt_core.providers.ollama import OllamaProvider, DEFAULT_MODEL

                # Chat listing, not the describe listing: chat needs the
                # `completion` capability, and filtering on vision here hid
                # every text-only model — often the best chat models installed.
                found = OllamaProvider(model=DEFAULT_MODEL).list_chat_models()
                error = ""
            except Exception as exc:                        # noqa: BLE001
                found, error = [], str(exc)
            wx.CallAfter(self._finish_ollama_listing, token, found, error)

        threading.Thread(target=work, daemon=True).start()

    def _finish_ollama_listing(self, token, models, error):
        if token != getattr(self, "_load_token", 0):
            return                      # superseded by a newer request
        if not self:
            return                      # dialog closed while we were listing

        for model_id in models:
            self.model_choice.Append(model_id, model_id)

        if error:
            self.status.SetLabel(f"Could not list models: {error}")
        elif not models:
            self.status.SetLabel("No Ollama models found. Is Ollama running?")
        else:
            self.status.SetLabel("")
        self._select_model(self._initial_model)

    # -- Claude / OpenAI ---------------------------------------------------

    def _displayed_ids(self):
        return [self.model_choice.GetClientData(i)
                for i in range(self.model_choice.GetCount())]

    def _start_catalog_refresh(self, provider):
        """Ask the provider's API for its current model list, on a worker.

        Only when the cached list has actually expired, so opening this dialog
        repeatedly does not mean an API call each time.
        """
        import threading

        self._load_token = getattr(self, "_load_token", 0) + 1
        token = self._load_token
        # What was selected when we painted. If it differs by the time the
        # refresh lands, the user has been working in the control and must not
        # have it rebuilt underneath them.
        painted_selection = self._selected_id()

        def work():
            try:
                from idt_core.providers import catalog

                if not catalog.is_stale(provider):
                    return
                entries = catalog.refresh_if_stale(provider)
                if entries is None:
                    return              # nothing changed, or the fetch failed
                found = [(e.display(), e.id) for e in entries]
            except Exception:           # noqa: BLE001
                # A refresh is an improvement on what is already shown, never a
                # prerequisite for it. Failing quietly leaves the cached list in
                # place, which is the correct outcome and already on screen.
                return
            wx.CallAfter(self._finish_catalog_refresh, token, provider,
                         painted_selection, found)

        threading.Thread(target=work, daemon=True).start()

    def _finish_catalog_refresh(self, token, provider, painted_selection, found):
        """Fold a refreshed list into the picker, or decline to.

        Rebuilding a wx.Choice underneath someone is not a neutral act: it moves
        the selection and makes a screen reader re-announce the control. So the
        list is only rebuilt when doing so is both necessary and safe, and the
        rest of the time the news goes to the status line, which is polite text
        rather than an interruption.
        """
        if token != getattr(self, "_load_token", 0):
            return                      # superseded by a newer request
        if not self:
            return                      # dialog closed while we were listing
        if self.provider_choice.GetStringSelection() != provider:
            return                      # user switched provider meanwhile

        new_ids = [model_id for _label, model_id in found]
        if new_ids == self._displayed_ids():
            return                      # identical — do not touch the control

        added = [m for m in new_ids if m not in set(self._displayed_ids())]

        if self._selected_id() != painted_selection:
            # They have started choosing. Tell them, do not rebuild.
            self.status.SetLabel(
                "Model list updated — reopen this dialog to see the changes."
            )
            return

        keep = self._selected_id() or self._initial_model
        self.model_choice.Clear()
        for label, model_id in found:
            self.model_choice.Append(label, model_id)
        self._select_model(keep)

        if added:
            count = len(added)
            plural = "" if count == 1 else "s"
            self.status.SetLabel(f"Model list updated — {count} new model{plural}.")
        else:
            self.status.SetLabel("Model list updated.")

    def _selected_id(self):
        index = self.model_choice.GetSelection()
        if index == wx.NOT_FOUND:
            return ""
        return self.model_choice.GetClientData(index) or ""

    def _select_model(self, wanted: str):
        if wanted:
            for i in range(self.model_choice.GetCount()):
                data = self.model_choice.GetClientData(i)
                if (data or self.model_choice.GetString(i)) == wanted:
                    self.model_choice.SetSelection(i)
                    return
        if self.model_choice.GetCount():
            self.model_choice.SetSelection(0)

    def get_selection(self):
        provider = self.provider_choice.GetStringSelection()
        index = self.model_choice.GetSelection()
        if index == wx.NOT_FOUND:
            return provider, ""
        data = self.model_choice.GetClientData(index)
        return provider, (data or self.model_choice.GetString(index))


class SettingsDialog(wx.Dialog):
    """Application settings, one notebook tab per area.

    Speech is the first tab; the notebook is the point — the next settings
    area gets a tab here, not another one-off dialog.
    """

    def __init__(self, parent, speech: SpeechSettings, options):
        super().__init__(parent, title="Settings", size=(660, 420))
        self._options = list(options)

        outer = wx.BoxSizer(wx.VERTICAL)
        notebook = wx.Notebook(self, name="Settings sections")
        _set_accessible_name(notebook, "Settings sections")

        # ---- Speech tab --------------------------------------------------
        page = wx.Panel(notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.auto_read = wx.CheckBox(
            page, label="&Read responses aloud when they finish streaming",
            name="Read responses aloud")
        self.auto_read.SetValue(speech.enabled)
        sizer.Add(self.auto_read, 0, wx.ALL, 10)

        grid = wx.FlexGridSizer(rows=2, cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1, 1)

        grid.Add(wx.StaticText(page, label="Speech &engine:"), 0,
                 wx.ALIGN_CENTER_VERTICAL)
        self.engine_choice = wx.Choice(
            page, choices=[option.label for option in self._options],
            name="Speech engine")
        _set_accessible_name(self.engine_choice, "Speech engine")
        grid.Add(self.engine_choice, 1, wx.EXPAND)

        grid.Add(wx.StaticText(page, label="Speaking r&ate:"), 0,
                 wx.ALIGN_CENTER_VERTICAL)
        self.rate_choice = wx.Choice(
            page, choices=[label.capitalize() for label in RATE_PRESET_LABELS],
            name="Speaking rate")
        _set_accessible_name(self.rate_choice, "Speaking rate")
        grid.Add(self.rate_choice, 0)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        self.rate_note = wx.StaticText(page, label="")
        sizer.Add(self.rate_note, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        page.SetSizer(sizer)
        notebook.AddPage(page, "Speech")
        outer.Add(notebook, 1, wx.EXPAND | wx.ALL, 8)

        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self, wx.ID_OK)
        buttons.AddButton(ok)
        buttons.AddButton(wx.Button(self, wx.ID_CANCEL))
        buttons.Realize()
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(outer)
        ok.SetDefault()

        # Pre-select the saved engine/voice, falling back to the first entry.
        selected = 0
        for i, option in enumerate(self._options):
            if option.engine == speech.engine and option.voice == speech.voice:
                selected = i
                break
        self.engine_choice.SetSelection(selected)

        try:
            self.rate_choice.SetSelection(
                RATE_PRESET_LABELS.index(speech.rate_preset))
        except ValueError:
            self.rate_choice.SetSelection(0)

        self.engine_choice.Bind(wx.EVT_CHOICE, lambda e: self._update_rate_state())
        self._update_rate_state()
        wx.CallAfter(self.auto_read.SetFocus)

    def _selected_option(self):
        index = self.engine_choice.GetSelection()
        if index == wx.NOT_FOUND or index >= len(self._options):
            return self._options[0]
        return self._options[index]

    def _update_rate_state(self):
        option = self._selected_option()
        self.rate_choice.Enable(option.has_rate)
        if option.is_screen_reader:
            # Deliberately no voice/rate control for screen-reader routes:
            # those belong to the reader's own settings.
            self.rate_note.SetLabel(
                "Voice and rate follow your screen reader's own settings.")
        elif option.has_rate:
            self.rate_note.SetLabel("")
        else:
            self.rate_note.SetLabel("This engine uses its default rate.")
        self.Layout()

    def get_settings(self) -> SpeechSettings:
        option = self._selected_option()
        index = self.rate_choice.GetSelection()
        preset = (RATE_PRESET_LABELS[index]
                  if 0 <= index < len(RATE_PRESET_LABELS) else "default")
        return SpeechSettings(
            enabled=self.auto_read.GetValue(),
            engine=option.engine,
            voice=option.voice,
            rate_preset=preset,
        )


class ApiKeysDialog(wx.Dialog):
    """Set API keys for the whole toolkit, not just this app.

    Keys are written to the operating system's credential store (Windows
    Credential Manager / macOS Keychain), where every IDT surface — this app,
    ImageDescriber, and the ``idt`` command line — resolves them through
    ``idt_core.keys``. The dialog never displays a stored key: each provider
    shows *where* its current key comes from, and takes a new value.
    """

    PROVIDERS = (
        ("claude", "Claude (Anthropic)"),
        ("openai", "OpenAI"),
        ("ollama.com", "Ollama web search"),
    )

    _SOURCE_TEXT = {
        "credential store": "stored in {store}",
        "config file": "stored in the config file",
        "legacy file": "stored in a legacy key file",
    }

    def __init__(self, parent):
        super().__init__(parent, title="API Keys", size=(620, 360))
        self._fields = {}
        self._status_labels = {}

        panel = wx.Panel(self)
        outer = wx.BoxSizer(wx.VERTICAL)

        store = credential_store_name()
        intro = wx.StaticText(panel, label=(
            f"Keys are saved to {store or 'the configuration file'} and used "
            f"by IDT Chat, ImageDescriber, and the idt command line. "
            f"Existing keys are never shown; enter a value to replace one."
        ))
        intro.Wrap(580)
        outer.Add(intro, 0, wx.ALL, 10)

        grid = wx.FlexGridSizer(rows=len(self.PROVIDERS), cols=4,
                                vgap=8, hgap=8)
        grid.AddGrowableCol(1, 1)
        for provider, label in self.PROVIDERS:
            grid.Add(wx.StaticText(panel, label=f"{label}:"), 0,
                     wx.ALIGN_CENTER_VERTICAL)
            field = wx.TextCtrl(panel, style=wx.TE_PASSWORD,
                                name=f"{label} API key")
            _set_accessible_name(field, f"{label} API key")
            self._fields[provider] = field
            grid.Add(field, 1, wx.EXPAND)

            remove = wx.Button(panel, label="&Remove",
                               name=f"Remove {label} key")
            remove.Bind(wx.EVT_BUTTON,
                        lambda e, p=provider: self.on_remove(p))
            grid.Add(remove, 0)

            status = wx.StaticText(panel, label="")
            self._status_labels[provider] = status
            grid.Add(status, 0, wx.ALIGN_CENTER_VERTICAL)
        outer.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        buttons = wx.StdDialogButtonSizer()
        save = wx.Button(panel, wx.ID_OK, "&Save")
        buttons.AddButton(save)
        buttons.AddButton(wx.Button(panel, wx.ID_CANCEL))
        buttons.Realize()
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(outer)
        save.Bind(wx.EVT_BUTTON, self.on_save)
        save.SetDefault()

        self._refresh_status()
        first = self._fields[self.PROVIDERS[0][0]]
        wx.CallAfter(first.SetFocus)

    def _refresh_status(self):
        store = credential_store_name() or "the credential store"
        for provider, _label in self.PROVIDERS:
            source = key_source(provider)
            if source == "environment":
                text = (f"using the {ENV_VARS.get(provider, '?')} environment "
                        f"variable (overrides stored keys)")
            elif source in self._SOURCE_TEXT:
                text = self._SOURCE_TEXT[source].format(store=store)
            else:
                text = "not set"
            self._status_labels[provider].SetLabel(text)
        self.Layout()

    def on_remove(self, provider):
        removed = delete_api_key(provider)
        self._refresh_status()
        remaining = key_source(provider)
        if removed and remaining is None:
            message = "Key removed."
        elif removed:
            # The store entry is gone but resolution still finds one — say
            # so, or the user will believe the remaining key is deleted.
            message = (f"Removed from the credential store, but a key from "
                       f"the {remaining} still applies.")
        elif remaining:
            message = (f"Nothing stored in the credential store to remove; "
                       f"the current key comes from the {remaining}.")
        else:
            message = "No stored key to remove."
        wx.MessageBox(message, "Remove key", wx.OK | wx.ICON_INFORMATION, self)

    def on_save(self, event):
        entered = {p: f.GetValue().strip() for p, f in self._fields.items()}
        entered = {p: v for p, v in entered.items() if v}
        if not entered:
            self.EndModal(wx.ID_OK)
            return

        # store_api_key prefers the OS store and falls back to the config
        # file — same path ImageDescriber's settings use, so a platform
        # without a credential store can still save keys.
        failed = [p for p, v in entered.items() if not store_api_key(p, v)]
        if failed:
            labels = {p: label for p, label in self.PROVIDERS}
            names = ", ".join(labels.get(p, p) for p in failed)
            wx.MessageBox(
                f"Could not save the key for: {names} — neither the "
                f"credential store nor the configuration file accepted it.",
                "Save failed", wx.OK | wx.ICON_ERROR, self)
            self._refresh_status()
            return
        self.EndModal(wx.ID_OK)


class ChatFrame(wx.Frame):
    """The main window."""

    def __init__(self):
        super().__init__(None, title=APP_NAME, size=(1000, 720))

        self.store = DirectoryChatStore()
        self.session = ChatSession()
        self.engine = None
        self.worker = None
        self.provider_name = "ollama"
        self.model_name = ""
        self.announce_policy = ANNOUNCE_FULL
        self._streaming_chunks = []
        self._is_streaming = False
        self.pending_attachments = []   # Attachment objects queued for the next turn
        self._temp_dir = None           # Holds HEIC conversions and pasted images
        self._web_search = False        # Per-window, not persisted with the session

        self.speech_settings = SpeechSettings.load()
        # Probing for engines/voices runs PowerShell (or `say`) and takes a
        # few seconds; do it now in the background so the Settings dialog
        # opens instantly with real choices.
        self._speech_options = None
        import threading
        threading.Thread(target=self._probe_speech, daemon=True).start()

        self._build_menu()
        self._build_ui()
        self._bind_keys()

        # Take back the Command chords wx hands to buttons with a "&" in their
        # label. Until this ran, "&Attach Files..." owned Cmd+A -- and a
        # control in the window beats the menu bar, so Cmd+A opened the file
        # picker instead of selecting text in the message box.
        stolen = clear_command_key_equivalents(self)
        if stolen:
            print(f"reclaimed Command chords from controls: {stolen}",
                  file=sys.stderr)

        self.CreateStatusBar(2)
        self.SetStatusWidths([-3, -1])
        self._set_status("Ready")

        self._refresh_sessions()
        self._refresh_attachments()
        self._update_attach_controls()
        self._update_title()
        self.input_text.SetFocus()

    # ---- construction ----------------------------------------------------

    def _build_menu(self):
        """The menu bar, and the accelerators it must not steal.

        Every "Ctrl+" below is Command on macOS, so each accelerator has to
        clear both platforms' conventions. Three rules came out of that:

        * **Never take a system chord.** Cmd+M is Minimize (wx puts it on the
          automatic Window menu), Cmd+W is Close, Cmd+Q is Quit, Cmd+, is
          Settings. Change Model moved off Ctrl+M for the first, and Web Search
          off Ctrl+Shift+W for the second; Quit and Settings are handled by id
          rather than by binding the key a second time.
        * **Standard editing keys belong to the focused control.** Ctrl+C used
          to mean "copy the selected transcript message" application-wide,
          which meant you could not copy a selection out of the message box.
          It is now a normal Copy that falls back to the transcript, and the
          rest of the standard Edit menu exists for the first time — on macOS
          that menu is what makes Cmd+A, Cmd+V and Cmd+Z work *at all*, since
          Cocoa routes those through menu items and there was no Edit menu.
        * **wx.ID_PREFERENCES / wx.ID_ABOUT / wx.ID_EXIT are wiring, not
          decoration.** macOS puts Settings, About and Quit on the application
          menu, and those entries reach these handlers only when the items
          carry the standard ids. They also must not repeat the accelerator
          the application menu already supplies, or two menu items answer to
          the same chord.
        """
        bar = wx.MenuBar()

        file_menu = wx.Menu()
        self._menu_item(file_menu, "&New Chat\tCtrl+N", self.on_new_chat)
        # No accelerator on purpose. A menu accelerator is application-wide, so
        # binding plain Delete here would steal the key from every text field
        # in the window -- you could not delete a character while typing. It is
        # handled contextually in on_char_hook instead, which can see focus.
        self._menu_item(file_menu, "&Delete Chat", self.on_delete_chat)
        file_menu.AppendSeparator()
        # Ctrl+Shift+E, not Ctrl+E: Cmd+E is "use selection for find" on macOS,
        # and Cmd+Shift+E is what Mac apps use for Export.
        self._menu_item(file_menu, "&Export Conversation...\tCtrl+Shift+E",
                        self.on_export)
        file_menu.AppendSeparator()
        self._menu_item(file_menu, self._accel("&Settings...", "Ctrl+,"),
                        self.on_settings, wx.ID_PREFERENCES)
        self._menu_item(file_menu, "API &Keys...", self.on_api_keys)
        file_menu.AppendSeparator()
        if _MAC:
            # Cmd+W closes the window on macOS whether an app implements it or
            # not; with one window that is the same as quitting.
            self._menu_item(file_menu, "&Close Window\tCtrl+W", self.on_exit,
                            wx.ID_CLOSE)
        self._menu_item(file_menu, self._accel("E&xit", "Ctrl+Q"),
                        self.on_exit, wx.ID_EXIT)
        bar.Append(file_menu, "&File")

        edit_menu = wx.Menu()
        self._menu_item(edit_menu, "&Undo\tCtrl+Z", self.on_undo, wx.ID_UNDO)
        redo = "Ctrl+Shift+Z" if _MAC else "Ctrl+Y"
        self._menu_item(edit_menu, f"&Redo\t{redo}", self.on_redo, wx.ID_REDO)
        edit_menu.AppendSeparator()
        self._menu_item(edit_menu, "Cu&t\tCtrl+X", self.on_cut, wx.ID_CUT)
        self._menu_item(edit_menu, "&Copy\tCtrl+C", self.on_copy, wx.ID_COPY)
        self._menu_item(edit_menu, "&Paste\tCtrl+V", self.on_paste, wx.ID_PASTE)
        self._menu_item(edit_menu, "Select &All\tCtrl+A", self.on_select_all,
                        wx.ID_SELECTALL)
        edit_menu.AppendSeparator()
        # No accelerator: Copy already does this when the transcript has focus.
        # The item is here so the command is discoverable, and so it works from
        # anywhere in the window.
        self._menu_item(edit_menu, "Copy &Message", self.on_copy_message)
        self._menu_item(edit_menu, "Copy W&hole Conversation\tCtrl+Shift+C",
                        self.on_copy_all)
        bar.Append(edit_menu, "&Edit")

        chat_menu = wx.Menu()
        self._menu_item(chat_menu, "&Send Message\tCtrl+Return", self.on_send)
        self.stop_menu_item = self._menu_item(
            chat_menu, "S&top Response\tCtrl+." , self.on_stop)
        self._menu_item(chat_menu, "&Regenerate Response\tCtrl+R",
                        self.on_regenerate)
        chat_menu.AppendSeparator()
        self.attach_menu_item = self._menu_item(
            chat_menu, "&Attach Files...\tCtrl+Shift+A", self.on_attach_files)
        # A paste variant, and safe as one: nothing in this app is rich text,
        # so there is no "paste and match style" for it to displace.
        self._menu_item(chat_menu, "&Paste Image\tCtrl+Shift+V",
                        self.on_paste_image)
        chat_menu.AppendSeparator()
        # Ctrl+Shift+M, not Ctrl+M: Cmd+M minimises the window on macOS.
        self._menu_item(chat_menu, "Change &Model...\tCtrl+Shift+M",
                        self.on_change_model)
        self._menu_item(chat_menu, "Set S&ystem Prompt...\tCtrl+Shift+P",
                        self.on_system_prompt)
        chat_menu.AppendSeparator()
        # A check item, not a command: web search is a mode for the whole
        # conversation, and the checkmark is what a screen reader reports.
        # Ctrl+Shift+K, not Ctrl+Shift+W: Cmd+W and Cmd+Shift+W are the
        # close-window family on macOS.
        self.web_search_item = chat_menu.AppendCheckItem(
            wx.ID_ANY, "Use &Web Search\tCtrl+Shift+K",
            "Let the model search the web (Ollama models with tool support)")
        self.Bind(wx.EVT_MENU, self.on_toggle_web_search, self.web_search_item)
        bar.Append(chat_menu, "&Chat")

        view_menu = wx.Menu()
        self._menu_item(view_menu, "&Read Last Response\tCtrl+Shift+R",
                        self.on_read_last)
        self._menu_item(view_menu, "&Token Usage\tCtrl+T", self.on_token_usage)
        view_menu.AppendSeparator()
        self._announce_items = {}
        for policy in (ANNOUNCE_FULL, ANNOUNCE_SUMMARY, ANNOUNCE_SILENT):
            item = view_menu.AppendRadioItem(wx.ID_ANY, ANNOUNCE_LABELS[policy])
            self.Bind(wx.EVT_MENU,
                      lambda e, p=policy: self._set_announce_policy(p), item)
            self._announce_items[policy] = item
        self._announce_items[ANNOUNCE_FULL].Check(True)
        bar.Append(view_menu, "&View")

        help_menu = wx.Menu()
        # F1 is the Windows help key; on macOS it is a hardware key and the
        # convention is Cmd+? instead.
        shortcuts_key = "Ctrl+?" if _MAC else "F1"
        self._menu_item(help_menu, f"&Keyboard Shortcuts\t{shortcuts_key}",
                        self.on_shortcuts)
        self._menu_item(help_menu, "&About", self.on_about, wx.ID_ABOUT)
        bar.Append(help_menu, "&Help")

        self.SetMenuBar(bar)

    @staticmethod
    def _accel(label: str, key: str) -> str:
        """`label` with `key` attached, except where macOS supplies the key.

        Settings and Quit already answer to Cmd+, and Cmd+Q from the
        application menu. Spelling the accelerator out again would put two menu
        items on one chord.
        """
        return label if _MAC else f"{label}\t{key}"

    def _menu_item(self, menu, label, handler, item_id=wx.ID_ANY):
        item = menu.Append(item_id, label)
        self.Bind(wx.EVT_MENU, handler, item)
        return item

    def _build_ui(self):
        panel = wx.Panel(self)
        outer = wx.BoxSizer(wx.HORIZONTAL)

        # --- left: saved conversations ---
        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(panel, label="&Conversations:"), 0, wx.ALL, 4)
        self.session_list = wx.ListBox(panel, style=wx.LB_SINGLE,
                                       name="Saved conversations")
        _set_accessible_name(self.session_list, "Saved conversations")
        left.Add(self.session_list, 1, wx.EXPAND | wx.ALL, 4)
        outer.Add(left, 0, wx.EXPAND)
        self.session_list.SetMinSize((240, -1))

        # --- right: the conversation ---
        right = wx.BoxSizer(wx.VERTICAL)

        right.Add(wx.StaticText(panel, label="Conversation &history:"), 0,
                  wx.LEFT | wx.TOP, 4)
        self.history_list = wx.ListBox(panel, style=wx.LB_SINGLE,
                                       name="Conversation history")
        _set_accessible_name(self.history_list, "Conversation history")
        right.Add(self.history_list, 2, wx.EXPAND | wx.ALL, 4)

        right.Add(wx.StaticText(panel, label="Selected &message:"), 0,
                  wx.LEFT, 4)
        self.detail = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_RICH2, name="Selected message"
        )
        _set_accessible_name(self.detail, "Selected message")
        self.detail.SetMinSize((-1, 180))
        right.Add(self.detail, 1, wx.EXPAND | wx.ALL, 4)

        right.Add(
            wx.StaticText(
                panel,
                label="&Your message (Enter sends, Shift+Enter starts a new line):",
            ),
            0, wx.LEFT, 4,
        )
        self.input_text = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER,
            name="Your message"
        )
        _set_accessible_name(self.input_text, "Your message")
        self.input_text.SetMinSize((-1, 90))
        right.Add(self.input_text, 0, wx.EXPAND | wx.ALL, 4)

        # Pending attachments. Kept visible even when empty rather than shown
        # and hidden: a control that appears and disappears is disorienting
        # with a screen reader, and the count in the label carries the state.
        self.attach_label = wx.StaticText(panel, label="Atta&chments: none")
        right.Add(self.attach_label, 0, wx.LEFT, 4)
        self.attach_list = wx.ListBox(panel, style=wx.LB_SINGLE,
                                      name="Pending attachments")
        _set_accessible_name(self.attach_list, "Pending attachments")
        self.attach_list.SetMinSize((-1, 54))
        right.Add(self.attach_list, 0, wx.EXPAND | wx.ALL, 4)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.send_btn = wx.Button(panel, label="&Send")
        self.stop_btn = wx.Button(panel, label="S&top")
        self.stop_btn.Enable(False)
        self.attach_btn = wx.Button(panel, label="&Attach Files...")
        self.remove_attach_btn = wx.Button(panel, label="&Remove Attachment")
        self.remove_attach_btn.Enable(False)
        buttons.Add(self.send_btn, 0, wx.RIGHT, 6)
        buttons.Add(self.stop_btn, 0, wx.RIGHT, 6)
        buttons.Add(self.attach_btn, 0, wx.RIGHT, 6)
        buttons.Add(self.remove_attach_btn, 0)
        right.Add(buttons, 0, wx.ALL, 4)

        outer.Add(right, 1, wx.EXPAND)
        panel.SetSizer(outer)

        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send)
        self.stop_btn.Bind(wx.EVT_BUTTON, self.on_stop)
        self.attach_btn.Bind(wx.EVT_BUTTON, self.on_attach_files)
        self.remove_attach_btn.Bind(wx.EVT_BUTTON, self.on_remove_attachment)
        self.attach_list.Bind(wx.EVT_LISTBOX, self.on_attachment_selected)
        self.history_list.Bind(wx.EVT_LISTBOX, self.on_history_selected)
        self.session_list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open_session)
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def _bind_keys(self):
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    # ---- helpers ---------------------------------------------------------

    def _set_status(self, text, field=0):
        self.SetStatusText(text, field)

    def _update_title(self):
        title = self.session.display_title()
        model = f" — {self.provider_name}/{self.model_name}" if self.model_name else ""
        self.SetTitle(f"{title}{model} — {APP_NAME}")

    def _set_announce_policy(self, policy):
        self.announce_policy = policy
        self._set_status(ANNOUNCE_LABELS[policy])

    def _ensure_engine(self) -> bool:
        """Build the engine, prompting for a provider the first time."""
        if self.engine is not None:
            return True
        if not self.model_name:
            if not self._choose_provider():
                return False
        try:
            api_key = resolve_api_key(self.provider_name)
            if requires_api_key(self.provider_name) and not api_key:
                wx.MessageBox(missing_key_message(self.provider_name),
                              "API key needed", wx.OK | wx.ICON_WARNING, self)
                return False
            provider = create_chat_provider(
                self.provider_name, self.model_name, api_key
            )
        except Exception as exc:
            wx.MessageBox(str(exc), "Could not start chat",
                          wx.OK | wx.ICON_ERROR, self)
            return False
        self.engine = ChatEngine(self.session, provider, self.store)
        self._update_title()
        self._update_attach_controls()
        return True

    def _choose_provider(self) -> bool:
        dlg = ProviderDialog(self, self.provider_name, self.model_name)
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return False
            provider, model = dlg.get_selection()
        finally:
            dlg.Destroy()
        if not model:
            wx.MessageBox("No model selected.", "Choose a model",
                          wx.OK | wx.ICON_WARNING, self)
            return False
        self.provider_name = capabilities_for(provider).provider or provider
        self.model_name = model
        return True

    # ---- rendering -------------------------------------------------------

    def _line_for(self, message) -> str:
        """One history line. Names the speaker so a reader announces who spoke."""
        if message.role == "user":
            speaker = "You"
        elif message.role == "system":
            speaker = "System"
        else:
            speaker = message.model or "Assistant"
        text = " ".join(message.content.split())
        if message.attachments:
            names = ", ".join(a.name for a in message.attachments)
            text = f"{text} [attached: {names}]" if text else f"[attached: {names}]"
        if message.error:
            text = f"[{message.error}] {text}" if text else f"[{message.error}]"
        # The FULL text, not a preview. The window clips it visually, but a
        # screen reader arrowing the list reads the entire item — same
        # convention as ImageDescriber's description lists. The 120-char
        # preview this replaces meant a reader could never hear a whole
        # response from the transcript list itself.
        return f"{speaker}: {text}"

    def _reload_history(self):
        self.history_list.Clear()
        for message in self.session.messages:
            self.history_list.Append(self._line_for(message))
        if self.history_list.GetCount():
            self.history_list.SetSelection(self.history_list.GetCount() - 1)
            self._show_detail(len(self.session.messages) - 1)
        else:
            self.detail.SetValue("")
        self._update_title()

    def _show_detail(self, index):
        if 0 <= index < len(self.session.messages):
            message = self.session.messages[index]
            body = message.content
            if message.error:
                body = f"{body}\n\n[{message.error}]" if body else f"[{message.error}]"
            self.detail.SetValue(body)

    def _announce(self, text):
        """Make a screen reader speak `text` without stealing the caret.

        Writing into the detail pane and bouncing focus is what reliably
        produces an announcement across NVDA, Narrator and VoiceOver; wx has no
        portable live-region equivalent.
        """
        if self.announce_policy == ANNOUNCE_SILENT or not text:
            return
        if self.announce_policy == ANNOUNCE_SUMMARY:
            words = len(text.split())
            text = f"{_first_sentence(text)} Response complete, {words} words."
        focused = wx.Window.FindFocus()
        self.history_list.SetFocus()
        wx.CallLater(120, lambda: focused.SetFocus() if focused else None)
        self._set_status(text[:120], 0)

    # ---- sessions --------------------------------------------------------

    def _refresh_sessions(self):
        self.session_list.Clear()
        self._sessions = self.store.list_sessions()
        for session in self._sessions:
            turns = sum(1 for m in session.messages if m.role == "user")
            self.session_list.Append(f"{session.display_title()} ({turns})",
                                     session.id)

    def on_open_session(self, _event):
        index = self.session_list.GetSelection()
        if index == wx.NOT_FOUND:
            return
        session = self.store.load(self.session_list.GetClientData(index))
        if session is None:
            return
        self.session = session
        self.provider_name = session.provider or self.provider_name
        self.model_name = session.model or self.model_name
        self.engine = None
        self._reload_history()
        self._set_status(f"Opened {session.display_title()}")
        self.input_text.SetFocus()

    def on_new_chat(self, _event):
        self.session = ChatSession()
        self.engine = None
        self._reload_history()
        self._set_status("New chat")
        self.input_text.SetFocus()

    def on_delete_chat(self, _event):
        index = self.session_list.GetSelection()
        if index == wx.NOT_FOUND:
            self._set_status("Select a conversation to delete")
            return
        session_id = self.session_list.GetClientData(index)
        title = self.session_list.GetString(index)
        if wx.MessageBox(f"Delete “{title}”? This cannot be undone.",
                         "Delete conversation",
                         wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
            return
        self.store.delete(session_id)
        if session_id == self.session.id:
            self.on_new_chat(None)
        self._refresh_sessions()
        self._set_status("Conversation deleted")

    # ---- attachments -----------------------------------------------------

    def _workdir(self) -> Path:
        """Scratch directory for HEIC conversions and pasted images."""
        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="idtchat_"))
        return self._temp_dir

    def _refresh_attachments(self):
        self.attach_list.Clear()
        for att in self.pending_attachments:
            size = ""
            try:
                if att.path:
                    size = f"  ({Path(att.path).stat().st_size / 1024:.0f} KB)"
            except OSError:
                # The file moved or vanished since it was attached. Show the
                # name without a size; sending validates existence properly
                # and reports it there.
                pass
            self.attach_list.Append(f"{att.name or Path(att.path or '').name}{size}")

        count = len(self.pending_attachments)
        if count == 0:
            self.attach_label.SetLabel("Atta&chments: none")
        elif count == 1:
            self.attach_label.SetLabel("Atta&chments: 1 file")
        else:
            self.attach_label.SetLabel(f"Atta&chments: {count} files")
        self.remove_attach_btn.Enable(count > 0)

    def _attachments_supported(self) -> bool:
        return supports_attachments(self.provider_name)

    def _add_attachments(self, paths):
        """Prepare and queue files, reporting anything rejected."""
        attachments, _converted, errors = prepare_attachments(
            paths, self.provider_name, self._workdir()
        )
        self.pending_attachments.extend(attachments)
        self._refresh_attachments()

        if errors:
            wx.MessageBox("\n\n".join(errors), "Some files were not attached",
                          wx.OK | wx.ICON_WARNING, self)
        if attachments:
            names = ", ".join(a.name for a in attachments)
            message = (f"Attached {len(attachments)} file"
                       f"{'s' if len(attachments) != 1 else ''}: {names}")
            self._set_status(message)
            self._announce(message)

    def on_attach_files(self, _event):
        if not self._attachments_supported():
            wx.MessageBox(
                f"{self.provider_name} does not accept attachments.",
                "Attachments unavailable", wx.OK | wx.ICON_INFORMATION, self)
            return

        wildcard = attachment_wildcard(self.provider_name)
        # HEIC is offered even though no provider reads it: it is converted to
        # JPEG on the way in, so refusing to list it would be unhelpful on a
        # machine full of iPhone photos.
        if "heic" not in wildcard.lower():
            wildcard += "|HEIC/HEIF images (*.heic;*.heif)|*.heic;*.heif"

        with wx.FileDialog(
            self, "Attach files", wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            paths = dlg.GetPaths()
        self._add_attachments(paths)

    def on_paste_image(self, _event):
        """Queue a bitmap sitting on the clipboard."""
        if not self._attachments_supported():
            self._set_status(f"{self.provider_name} does not accept attachments")
            return
        if not wx.TheClipboard.Open():
            self._set_status("Could not read the clipboard")
            return
        try:
            if not wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP)):
                self._set_status("No image on the clipboard")
                return
            data = wx.BitmapDataObject()
            if not wx.TheClipboard.GetData(data):
                self._set_status("Could not read the image from the clipboard")
                return
        finally:
            wx.TheClipboard.Close()

        target = self._workdir() / f"pasted_{len(self.pending_attachments) + 1}.png"
        if not data.GetBitmap().ConvertToImage().SaveFile(
                str(target), wx.BITMAP_TYPE_PNG):
            self._set_status("Could not save the pasted image")
            return

        self.pending_attachments.append(
            Attachment(media_type="image/png", path=str(target)))
        self._refresh_attachments()
        self._set_status("Pasted image attached")
        self._announce("Pasted image attached")

    def on_remove_attachment(self, _event):
        index = self.attach_list.GetSelection()
        if index == wx.NOT_FOUND or index >= len(self.pending_attachments):
            self._set_status("Select an attachment to remove")
            return
        removed = self.pending_attachments.pop(index)
        self._refresh_attachments()
        self._set_status(f"Removed {removed.name}")
        self._announce(f"Removed {removed.name}")
        if self.pending_attachments:
            self.attach_list.SetSelection(min(index, len(self.pending_attachments) - 1))

    def on_attachment_selected(self, _event):
        self.remove_attach_btn.Enable(self.attach_list.GetSelection() != wx.NOT_FOUND)

    def _update_attach_controls(self):
        """Reflect whether the current provider takes attachments."""
        enabled = self._attachments_supported()
        self.attach_btn.Enable(enabled)
        self.attach_menu_item.Enable(enabled)
        if not enabled and self.pending_attachments:
            # Switching to a provider that cannot take them would otherwise
            # leave files queued that silently never get sent.
            self.pending_attachments = []
            self._refresh_attachments()
            self._set_status(
                f"{self.provider_name} does not accept attachments; queue cleared")
        self._update_web_search_controls()

    # ---- web search ------------------------------------------------------

    def _update_web_search_controls(self):
        """Web search rides on tool calling, which only the Ollama chat
        provider implements; on other providers the item is disabled so its
        state cannot quietly mean nothing."""
        supported = self.provider_name == "ollama"
        self.web_search_item.Enable(supported)
        if not supported and self._web_search:
            self._web_search = False
            self.web_search_item.Check(False)
            self._set_status("Web search is off: only Ollama supports it")

    def on_toggle_web_search(self, _event):
        if not self.web_search_item.IsChecked():
            self._web_search = False
            self._set_status("Web search off")
            self._announce("Web search off")
            return

        from idt_core.chat.tools import missing_web_key_message, web_search_available

        if not web_search_available():
            # Veto rather than let every search fail mid-answer.
            self.web_search_item.Check(False)
            self._web_search = False
            wx.MessageBox(missing_web_key_message(), "Web search needs a key",
                          wx.OK | wx.ICON_INFORMATION, self)
            return

        # Warn (but allow) when the model does not report tool support: the
        # capability probe fails open, and a wrong "no" here would block a
        # feature that actually works.
        try:
            from idt_core.providers.ollama import model_capabilities

            caps = model_capabilities(self.model_name) if self.model_name else None
            if caps is not None and "tools" not in caps:
                wx.MessageBox(
                    f"{self.model_name} does not report tool support, so it "
                    f"may answer without searching. Models tagged 'tools' on "
                    f"ollama.com work best.",
                    "Model may not search", wx.OK | wx.ICON_INFORMATION, self)
        except Exception:
            # The capability probe is advisory; a probe failure must not
            # block enabling web search (fail open, like the probe itself).
            pass

        self._web_search = True
        self._set_status("Web search on")
        self._announce("Web search on")

    def _cleanup_temp_files(self):
        if self._temp_dir is None:
            return
        import shutil

        shutil.rmtree(self._temp_dir, ignore_errors=True)
        self._temp_dir = None

    # ---- sending ---------------------------------------------------------

    def on_send(self, _event):
        if self._is_streaming:
            self._set_status("Still waiting for the current response")
            return
        text = self.input_text.GetValue().strip()
        if not text and not self.pending_attachments:
            return
        if not self._ensure_engine():
            return

        # Validate late: a file can be moved or deleted between attaching and
        # sending, and the failure would otherwise surface as an opaque
        # provider error.
        missing = [a for a in self.pending_attachments if not a.exists()]
        if missing:
            names = ", ".join(a.name for a in missing)
            wx.MessageBox(f"These attachments no longer exist:\n{names}",
                          "Missing files", wx.OK | wx.ICON_ERROR, self)
            self.pending_attachments = [
                a for a in self.pending_attachments if a.exists()]
            self._refresh_attachments()
            return

        attachments = list(self.pending_attachments)
        self.pending_attachments = []
        self._refresh_attachments()
        self.input_text.SetValue("")
        self._start_turn(text, attachments=attachments)

    def on_regenerate(self, _event):
        if self._is_streaming or self.engine is None:
            return
        if not any(m.role == "assistant" for m in self.session.messages):
            self._set_status("Nothing to regenerate")
            return
        self._start_turn("", regenerate=True)

    def _start_turn(self, text, regenerate=False, attachments=()):
        speaker.stop()  # a new question should silence the previous answer
        self._is_streaming = True
        self._streaming_chunks = []
        self.stop_btn.Enable(True)
        self.send_btn.Enable(False)
        self._set_status("Waiting for a response…")

        engine, options = self.engine, ChatOptions(web_search=self._web_search)
        queued = list(attachments)
        if regenerate:
            start = lambda: engine.regenerate(options)  # noqa: E731
        else:
            start = lambda: engine.send(text, queued, options)  # noqa: E731
        self.worker = ChatWorker(self, engine, start)
        self.worker.start()

    def on_stop(self, _event):
        speaker.stop()  # Ctrl+. also silences a response being read aloud
        if self.worker is not None and self._is_streaming:
            self.worker.cancel()
            self._set_status("Stopping…")

    # ---- engine events (UI thread) ---------------------------------------

    def on_chat_event(self, event):
        if isinstance(event, ChatStarted):
            self._reload_history()
            if event.dropped_messages:
                note = (f"Dropped the {event.dropped_messages} oldest turns to "
                        f"stay within the context window.")
                self._set_status(note)
                self._announce(note)
            return

        if isinstance(event, ChatDelta):
            # Accumulate silently. Announcing per chunk would flood the reader.
            self._streaming_chunks.append(event.text)
            self.detail.SetValue("".join(self._streaming_chunks))
            self.detail.ShowPosition(self.detail.GetLastPosition())
            return

        if isinstance(event, ChatThinking):
            # Status only, never the text: reasoning models produce pages of
            # scratch work, and narrating it would bury the actual answer.
            self._set_status("Model is thinking…")
            return

        if isinstance(event, ChatRetrying):
            self._set_status(f"{event.error} — retrying ({event.attempt})")
            return

        if isinstance(event, ChatToolCall):
            # The note joins the streaming view so the wait is explained, but
            # never the saved message — the engine commits only model text.
            note = event.describe()
            self._streaming_chunks.append(f"\n[{note}]\n")
            self.detail.SetValue("".join(self._streaming_chunks))
            self.detail.ShowPosition(self.detail.GetLastPosition())
            self._set_status(note + "…")
            return

        if isinstance(event, ChatToolResult):
            if event.summary:
                self._set_status(event.summary)
            return

        if isinstance(event, ChatUsage):
            self._set_status(
                f"context {self.session.context_tokens:,} · "
                f"billed {self.session.billed_tokens:,}", 1)
            return

        if isinstance(event, (ChatFinished, ChatCancelled, ChatFailed)):
            self._finish_turn(event)

    def _finish_turn(self, event):
        self._is_streaming = False
        self.stop_btn.Enable(False)
        self.send_btn.Enable(True)
        self.worker = None
        self._reload_history()
        self._refresh_sessions()

        if isinstance(event, ChatFinished):
            self._set_status("Response complete")
            if self.speech_settings.enabled and speaker.speak(
                    event.message.content, self.speech_settings):
                # The speech engine is reading it; the focus-flip
                # announcement on top would say everything twice.
                pass
            else:
                self._announce(event.message.content)
        elif isinstance(event, ChatCancelled):
            self._set_status("Stopped — partial response kept")
            self._announce("Stopped. Partial response kept.")
        else:
            self._set_status(f"Error: {event.error}")
            self._announce(f"Error. {event.error}")
        self.input_text.SetFocus()

    # ---- commands --------------------------------------------------------

    def on_history_selected(self, _event):
        self._show_detail(self.history_list.GetSelection())

    def on_change_model(self, _event):
        if self._is_streaming:
            return
        if not self._choose_provider():
            return
        # Rebuild against the new provider; history is preserved.
        self.engine = None
        if self._ensure_engine():
            self._set_status(f"Now using {self.provider_name}/{self.model_name}")

    def _probe_speech(self):
        """Background thread: enumerate speech engines and voices once."""
        try:
            self._speech_options = list_speech_options()
        except Exception:
            self._speech_options = default_options()

    def on_settings(self, _event):
        options = self._speech_options
        if options is None:
            # The startup probe is still running. Never re-probe on the UI
            # thread — the PowerShell probe can take up to 25 s, which is a
            # frozen window, and a second concurrent probe besides. Offer
            # the static engines now; the full voice list is one reopen away.
            options = default_options()
            self._set_status(
                "Still detecting installed voices — reopen Settings in a "
                "moment for the full list")

        dlg = SettingsDialog(self, self.speech_settings, options)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self.speech_settings = dlg.get_settings()
                try:
                    self.speech_settings.save()
                except OSError:
                    self._set_status("Could not save settings to disk")
                    return
                state = "on" if self.speech_settings.enabled else "off"
                self._set_status(f"Settings saved — automatic reading {state}")
                self._announce(f"Automatic reading {state}")
        finally:
            dlg.Destroy()

    def on_api_keys(self, _event):
        dlg = ApiKeysDialog(self)
        try:
            dlg.ShowModal()
        finally:
            dlg.Destroy()
        # A key may have just appeared (or vanished) for the active provider.
        if requires_api_key(self.provider_name) and not resolve_api_key(
                self.provider_name):
            self._set_status(missing_key_message(self.provider_name))
        else:
            self._set_status("API keys updated")

    def on_system_prompt(self, _event):
        dlg = wx.TextEntryDialog(
            self, "System prompt for this conversation:", "System Prompt",
            self.session.system_prompt, style=wx.TE_MULTILINE | wx.OK | wx.CANCEL
        )
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self.session.system_prompt = dlg.GetValue().strip()
                self.store.save(self.session)
                self._set_status("System prompt updated")
        finally:
            dlg.Destroy()

    def on_read_selected(self, _event):
        """Announce the message currently highlighted in the transcript."""
        index = self.history_list.GetSelection()
        if 0 <= index < len(self.session.messages):
            message = self.session.messages[index]
            self.detail.SetValue(message.content)
            self._announce(message.content)

    def on_read_last(self, _event):
        for message in reversed(self.session.messages):
            if message.role == "assistant":
                self.detail.SetValue(message.content)
                self._announce(message.content)
                return
        self._set_status("No response yet")

    def on_token_usage(self, _event):
        wx.MessageBox(
            f"Context window in use: {self.session.context_tokens:,} tokens\n"
            f"Billed this conversation: {self.session.billed_tokens:,} tokens\n\n"
            "Context is the most recent exchange, which is what occupies the "
            "model's window. Billed is the sum across every turn.",
            "Token Usage", wx.OK | wx.ICON_INFORMATION, self)

    # ---- standard editing -------------------------------------------------
    #
    # These exist because a menu accelerator is application-wide. Ctrl+C bound
    # straight to "copy the selected transcript message" meant Ctrl+C did that
    # *everywhere*, including in the message box, so a selection could not be
    # copied out of it. Each command now asks who has focus first.
    #
    # On macOS most of these never run: Cocoa dispatches cut:/copy:/paste:/
    # selectAll:/undo: to the focused NSTextView before wx sees a menu command,
    # which is the behaviour we want and the reason the Edit menu has to exist
    # there at all -- without it, Cmd+A and Cmd+V do nothing in any text field,
    # including the API key box. wx only falls back to sending the command
    # event when nothing native claimed it, i.e. exactly when focus is on a
    # list, which is where the transcript fallback belongs.
    #
    # On Windows the accelerator reaches the frame first, so the routing below
    # is what makes the standard keys behave normally.

    @staticmethod
    def _focused():
        """The control with focus. A seam, so the routing can be tested.

        Same reason ``_handle_return`` takes its focused window as an argument:
        driving real focus in a test is unreliable, and the routing is the part
        worth asserting.
        """
        return wx.Window.FindFocus()

    @staticmethod
    def _text_command(focused, method: str) -> bool:
        """Run a standard edit command on a focused text control.

        True when it was run, so the caller knows not to fall back. A command
        the control cannot currently do (Copy with no selection, Paste with an
        empty clipboard) counts as not run.
        """
        if not isinstance(focused, wx.TextCtrl):
            return False
        can = getattr(focused, "Can" + method, None)   # SelectAll has no Can*
        if can is not None and not can():
            return False
        getattr(focused, method)()
        return True

    def on_undo(self, event):
        if not self._text_command(self._focused(), "Undo"):
            event.Skip()

    def on_redo(self, event):
        if not self._text_command(self._focused(), "Redo"):
            event.Skip()

    def on_cut(self, event):
        if not self._text_command(self._focused(), "Cut"):
            event.Skip()

    def on_copy(self, event):
        """Copy the selection, or the selected message when there is none.

        The fallback is deliberate: on the transcript there is no text
        selection to copy, and "copy what I am pointing at" is the only useful
        reading of Copy there. It also covers the detail pane with nothing
        selected, where copying the message being displayed is what was meant.
        """
        if self._text_command(self._focused(), "Copy"):
            return
        self.on_copy_message(event)

    def on_paste(self, event):
        """Paste text, or queue an image from the clipboard as an attachment."""
        if self._text_command(self._focused(), "Paste"):
            return
        if self._clipboard_has_image():
            self.on_paste_image(event)

    def on_select_all(self, event):
        if not self._text_command(self._focused(), "SelectAll"):
            event.Skip()

    @staticmethod
    def _clipboard_has_image() -> bool:
        if not wx.TheClipboard.Open():
            return False
        try:
            return wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP))
        finally:
            wx.TheClipboard.Close()

    def _copy(self, text):
        if not text:
            return
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
            self._set_status("Copied")

    def on_copy_message(self, _event):
        index = self.history_list.GetSelection()
        if 0 <= index < len(self.session.messages):
            self._copy(self.session.messages[index].content)

    def on_copy_all(self, _event):
        self._copy(self._transcript())

    def _transcript(self) -> str:
        lines = []
        for message in self.session.messages:
            speaker = "You" if message.role == "user" else (
                message.model or message.role.title())
            lines.append(f"[{speaker}]\n{message.content}\n")
        return "\n".join(lines)

    def on_export(self, _event):
        if not self.session.messages:
            self._set_status("Nothing to export")
            return
        with wx.FileDialog(
            self, "Export conversation",
            defaultFile=f"{self.session.display_title()[:40]}.md",
            wildcard=("Markdown (*.md)|*.md|Text (*.txt)|*.txt|"
                      "JSON (*.json)|*.json"),
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            path = Path(dlg.GetPath())

        try:
            if path.suffix.lower() == ".json":
                import json

                path.write_text(
                    json.dumps(self.session.to_dict(), indent=2, ensure_ascii=False),
                    encoding="utf-8")
            elif path.suffix.lower() == ".md":
                path.write_text(self._markdown(), encoding="utf-8")
            else:
                path.write_text(self._transcript(), encoding="utf-8")
        except OSError as exc:
            wx.MessageBox(str(exc), "Export failed", wx.OK | wx.ICON_ERROR, self)
            return
        self._set_status(f"Exported to {path.name}")

    def _markdown(self) -> str:
        lines = [f"# {self.session.display_title()}", ""]
        if self.session.system_prompt:
            lines += ["> **System prompt:** " + self.session.system_prompt, ""]
        for message in self.session.messages:
            speaker = "You" if message.role == "user" else (
                message.model or message.role.title())
            lines.append(f"## {speaker}")
            lines.append("")
            lines.append(message.content)
            if message.error:
                lines.append("")
                lines.append(f"*{message.error}*")
            lines.append("")
        return "\n".join(lines)

    def _shortcut_lines(self):
        """The shortcut list, named for the platform the user is on.

        wx turns every "Ctrl+" accelerator into Command on macOS, so a list
        that says Ctrl there is simply wrong -- and unusable read aloud.
        """
        mod = "Cmd" if _MAC else "Ctrl"
        rows = [
            ("Enter", "Send message"),
            ("Shift+Enter", "New line in the message box"),
            (f"{mod}+Return", "Send message (from anywhere in the window)"),
            ("", ""),
            ("Enter", "In the conversation list: open it."),
            ("", "In the transcript: read the message again."),
            ("Delete", "In the conversation list: delete it."),
            ("", "In the attachments list: remove it."),
            ("", ""),
            (f"{mod}+N", "New chat"),
            (f"{mod}+Shift+M", "Change model"),
            (f"{mod}+Shift+P", "Set system prompt"),
            (f"{mod}+Shift+K", "Web search on/off (Ollama)"),
            (f"{mod}+R", "Regenerate response"),
            (f"{mod}+.", "Stop the current response (and speech)"),
            ("", ""),
            (f"{mod}+Shift+A", "Attach files"),
            (f"{mod}+Shift+V", "Paste image from clipboard"),
            ("", ""),
            (f"{mod}+X / {mod}+C / {mod}+V", "Cut, copy, paste"),
            (f"{mod}+A", "Select all"),
            (f"{mod}+Z", "Undo"),
            (f"{mod}+Shift+Z" if _MAC else "Ctrl+Y", "Redo"),
            (f"{mod}+C", "In the transcript: copy the selected message"),
            (f"{mod}+Shift+C", "Copy the whole conversation"),
            ("", ""),
            (f"{mod}+Shift+R", "Read the last response again"),
            (f"{mod}+T", "Token usage"),
            (f"{mod}+Shift+E", "Export conversation"),
            (f"{mod}+?" if _MAC else "F1", "This list"),
        ]
        width = max(len(keys) for keys, _text in rows) + 2
        return "\n".join(
            f"{keys.ljust(width)}{text}".rstrip() for keys, text in rows)

    def on_shortcuts(self, _event):
        wx.MessageBox(self._shortcut_lines(), "Keyboard Shortcuts",
                      wx.OK | wx.ICON_INFORMATION, self)

    def on_about(self, _event):
        wx.MessageBox(
            f"{APP_NAME} {_version()}\n\n"
            "An accessible, keyboard-first chat client for Ollama, Claude and "
            "OpenAI.\n\nPart of the Image Description Toolkit.",
            f"About {APP_NAME}", wx.OK | wx.ICON_INFORMATION, self)

    # ---- keys ------------------------------------------------------------

    def _handle_return(self, focused, shift_down: bool) -> bool:
        """Act on Enter for whichever control has focus. True if consumed.

        Split out so it can be tested without driving real focus.
        """
        if focused is self.input_text:
            if shift_down:
                self.input_text.WriteText("\n")
            else:
                self.on_send(None)
            return True
        if focused is self.session_list:
            self.on_open_session(None)
            return True
        if focused is self.history_list:
            # Re-announce the selected message: Enter on a transcript line is a
            # natural "say that again".
            self.on_read_selected(None)
            return True
        return False

    def _handle_delete(self, focused) -> bool:
        """Act on the Delete key for whichever list has focus. True if consumed.

        Deliberately narrow: only the two list controls. Anywhere else --
        crucially the message box and the detail pane -- Delete must keep its
        ordinary text-editing meaning, which is why this is not a menu
        accelerator.
        """
        if focused is self.session_list:
            self.on_delete_chat(None)
            return True
        if focused is self.attach_list:
            self.on_remove_attachment(None)
            return True
        return False

    def on_char_hook(self, event):
        """Frame-level key handling.

        Enter is handled here rather than in each control's EVT_KEY_DOWN
        because a native wx.ListBox on MSW does not generate EVT_KEY_DOWN for
        Enter at all -- the control ignores it and the key goes to frame-level
        default-button handling. A per-list EVT_KEY_DOWN binding for Enter
        therefore never fires, which is exactly how pressing Enter on a saved
        conversation silently did nothing.
        """
        key = event.GetKeyCode()
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            if self._handle_return(wx.Window.FindFocus(), event.ShiftDown()):
                return
        elif key == wx.WXK_DELETE:
            if self._handle_delete(wx.Window.FindFocus()):
                return
        elif key == wx.WXK_F1 and _MAC:
            # The Mac help key is Cmd+?, which is what the menu carries. F1 is
            # honoured too for anyone arriving from the Windows build whose
            # keyboard actually sends it.
            self.on_shortcuts(None)
            return
        event.Skip()

    # ---- shutdown --------------------------------------------------------

    def on_exit(self, _event):
        self.Close()

    def on_close(self, event):
        speaker.stop()
        # The engine persists after every turn, so there is nothing to save
        # here -- a lost close handler cannot lose the conversation.
        if self.worker is not None and self._is_streaming:
            self.worker.cancel()
        self._cleanup_temp_files()
        event.Skip()
        self.Destroy()


class ChatApp(wx.App):
    def OnInit(self):
        self.SetAppName(APP_NAME)
        # Belt and braces for the dialogs: each one already names its controls
        # as it builds them, and this names anything added later that forgets.
        install_dialog_naming(wx)
        frame = ChatFrame()
        frame.Show()
        self.SetTopWindow(frame)
        return True


def main():
    app = ChatApp(False)
    app.MainLoop()


if __name__ == "__main__":
    main()

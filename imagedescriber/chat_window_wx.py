#!/usr/bin/env python3
"""
chat_window_wx.py - Accessible Chat Interface for ImageDescriber

Provides a fully accessible chat window with:
- ListBox for conversation history (better screen reader support)
- Automatic announcement of new messages
- Tab/Shift+Tab navigation between history and input
- Session persistence and multi-turn conversations
- Image preview during conversation
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

import wx
import wx.lib.newevent

# Add project root to sys.path for shared module imports
# Works in both development mode (running script) and frozen mode (PyInstaller exe)
if getattr(sys, 'frozen', False):
    # Frozen mode - executable directory is base
    _project_root = Path(sys.executable).parent
    _imagedescriber_dir = _project_root  # In frozen mode, all modules are at exe level
else:
    # Development mode - use __file__ relative path
    _project_root = Path(__file__).parent.parent
    _imagedescriber_dir = Path(__file__).parent

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_imagedescriber_dir) not in sys.path:
    sys.path.insert(0, str(_imagedescriber_dir))

# Import shared utilities (sys.path already configured above)
from shared.wx_common import show_error, show_warning, show_info

# Import workers and events - simple imports work since sys.path includes both
# the project root and the imagedescriber directory
from workers_wx import (
    ChatProcessingWorker,
    EVT_CHAT_UPDATE,
    EVT_CHAT_COMPLETE,
    EVT_CHAT_ERROR
)
from data_models import ImageItem, ImageWorkspace, ImageDescription

# Import provider attachment capabilities (models/ added to sys.path for frozen compat)
try:
    if getattr(sys, 'frozen', False):
        _models_path = Path(sys.executable).parent / 'models'
    else:
        _models_path = Path(__file__).parent.parent / 'models'
    if str(_models_path) not in sys.path:
        sys.path.insert(0, str(_models_path))
    from provider_configs import get_supported_attachments, supports_attachments, get_attachment_wildcard
except ImportError:
    def get_supported_attachments(p): return []
    def supports_attachments(p): return False
    def get_attachment_wildcard(p): return "All files (*.*)|*.*"


class _NamedTextAccessible(wx.Accessible):
    """Provides an accessible name for wx.TextCtrl so VoiceOver reads the label.

    On macOS, wx.TextCtrl.SetName() does not map to NSAccessibility label, so
    VoiceOver announces every text field as just "edit".  Subclassing
    wx.Accessible and overriding GetName() feeds the correct label through the
    Cocoa NSAccessibility bridge.
    """

    def __init__(self, win: wx.TextCtrl, label: str):
        super().__init__(win)
        self._label = label

    def GetName(self, childId):
        return (wx.ACC_OK, self._label)


class ChatDialog(wx.Dialog):
    """Simple dialog to select AI provider and model for chat session
    
    Provides quick provider/model selection before opening the main chat window.
    Follows same design pattern as ProcessingOptionsDialog.
    """
    
    def __init__(self, parent, config: dict, cached_ollama_models=None):
        """Initialize chat settings dialog
        
        Args:
            parent: Parent window
            config: Application configuration dictionary
            cached_ollama_models: Optional cached Ollama models list for performance
        """
        super().__init__(parent, title="Chat Settings", 
                        style=wx.DEFAULT_DIALOG_STYLE)
        
        self.config = config
        self.cached_ollama_models = cached_ollama_models
        self._create_ui()
        self.Centre()
        
    def _create_ui(self):
        """Create dialog UI"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Instructions
        intro_text = wx.StaticText(self, 
            label="Select AI provider and model for your chat session:")
        main_sizer.Add(intro_text, 0, wx.ALL, 10)
        
        # Provider selection
        provider_sizer = wx.BoxSizer(wx.HORIZONTAL)
        provider_label = wx.StaticText(self, label="Provider:")
        provider_label.SetMinSize((100, -1))
        provider_sizer.Add(provider_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        
        self.provider_choice = wx.Choice(self, choices=['Ollama', 'OpenAI', 'Claude', 'MLX'])
        self.provider_choice.SetSelection(0)  # Default to Ollama
        self.provider_choice.Bind(wx.EVT_CHOICE, self.on_provider_changed)
        provider_sizer.Add(self.provider_choice, 1, wx.ALL | wx.EXPAND, 5)
        
        main_sizer.Add(provider_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        
        # Model selection
        model_sizer = wx.BoxSizer(wx.HORIZONTAL)
        model_label = wx.StaticText(self, label="Model:")
        model_label.SetMinSize((100, -1))
        model_sizer.Add(model_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        
        # ACCESSIBILITY FIX: Use wx.Choice instead of wx.ComboBox to avoid macOS VoiceOver crash
        self.model_combo = wx.Choice(self)
        model_sizer.Add(self.model_combo, 1, wx.ALL | wx.EXPAND, 5)
        
        main_sizer.Add(model_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        
        # Buttons
        btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        main_sizer.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        
        # Load default provider models
        self.on_provider_changed(None)
        
    def on_provider_changed(self, event):
        """Update model list when provider changes - uses dynamic detection"""
        # Initialize with default to prevent NameError in exception handlers
        provider = 'ollama'
        
        try:
            selected = self.provider_choice.GetStringSelection()
            if selected:  # Guard against empty selection
                provider = selected.lower()
        except Exception:
            pass  # Use default 'ollama'
        
        # Clear current models
        self.model_combo.Clear()
        
        try:
            if provider == 'ollama':
                # Use cached models if available, otherwise query Ollama dynamically
                models = None
                if self.cached_ollama_models is not None:
                    # Use cached models for instant loading
                    models = self.cached_ollama_models
                else:
                    # Auto-populate cache on first use (slower, but only happens once)
                    try:
                        from ai_providers import get_available_providers
                    except ImportError:
                        from imagedescriber.ai_providers import get_available_providers
                    
                    providers = get_available_providers()
                    if 'ollama' in providers:
                        ollama_provider = providers['ollama']
                        models = ollama_provider.get_available_models()
                        # Cache for next time
                        self.cached_ollama_models = models
                
                if models:
                    for model in models:
                        self.model_combo.Append(model, model)
                    # Set first model as default
                    self.model_combo.SetSelection(0)
                else:
                    # Fallback if no models found
                    self.model_combo.Append('llava:latest', 'llava:latest')
                    self.model_combo.SetSelection(0)
                    
            elif provider == 'openai':
                # Load from canonical list - supports both frozen and dev mode
                try:
                    from ai_providers import DEV_OPENAI_MODELS
                except ImportError:
                    from imagedescriber.ai_providers import DEV_OPENAI_MODELS
                for model in DEV_OPENAI_MODELS:
                    self.model_combo.Append(model, model)
                self.model_combo.SetStringSelection('gpt-4o')
                
            elif provider == 'claude':
                # Import the official Claude models list with friendly display names
                from ai_providers import DEV_CLAUDE_MODELS, CLAUDE_MODEL_METADATA
                for model in DEV_CLAUDE_MODELS:
                    display = CLAUDE_MODEL_METADATA.get(model, {}).get('name', model)
                    self.model_combo.Append(display, model)  # client data = API ID
                # Set to first available model (list is ordered by recommendation)
                if self.model_combo.GetCount() > 0:
                    self.model_combo.SetSelection(0)
                
            elif provider == 'mlx':
                # Apple MLX Metal GPU inference (macOS only) — no API key required
                try:
                    from imagedescriber.ai_providers import MLXProvider
                except ImportError:
                    from ai_providers import MLXProvider
                for model in MLXProvider.KNOWN_MODELS:
                    self.model_combo.Append(model, model)
                if MLXProvider.KNOWN_MODELS:
                    self.model_combo.SetSelection(0)

        except Exception as e:
            print(f"Error populating models for {provider}: {e}")
            # Set a reasonable fallback
            if provider == 'ollama':
                self.model_combo.Append('llava:latest', 'llava:latest')
                self.model_combo.SetSelection(0)
            elif provider == 'openai':
                self.model_combo.Append('gpt-4o', 'gpt-4o')
                self.model_combo.SetSelection(0)
            elif provider == 'claude':
                # Use first model from official Claude models list with friendly display name
                from ai_providers import DEV_CLAUDE_MODELS, CLAUDE_MODEL_METADATA
                if DEV_CLAUDE_MODELS:
                    api_id = DEV_CLAUDE_MODELS[0]
                    display = CLAUDE_MODEL_METADATA.get(api_id, {}).get('name', api_id)
                    self.model_combo.Append(display, api_id)
                    self.model_combo.SetSelection(0)
        
    def get_selections(self) -> Dict[str, str]:
        """Get selected provider and model.
        Returns the API model ID (client data for Claude models), not the friendly display name."""
        selection = self.model_combo.GetSelection()
        if selection != wx.NOT_FOUND:
            client_data = self.model_combo.GetClientData(selection)
            model = client_data if client_data is not None else self.model_combo.GetStringSelection()
        else:
            model = self.model_combo.GetStringSelection()
        return {
            'provider': self.provider_choice.GetStringSelection().lower(),
            'model': model
        }


class ChatWindow(wx.Dialog):
    """Accessible chat interface with conversation history
    
    Features:
    - wx.ListBox for chat history (superior screen reader support)
    - Automatic announcement of new AI responses
    - Tab/Shift+Tab navigation between history and input
    - Image thumbnail preview
    - Persistent sessions with full message history
    - Real-time streaming responses
    """
    
    def __init__(self, parent, workspace: ImageWorkspace, image_item: Optional[ImageItem], 
                 provider: str, model: str, session_id: Optional[str] = None,
                 chat_item: Optional[ImageItem] = None):
        """Initialize chat window
        
        Args:
            parent: Parent window
            workspace: ImageWorkspace instance for persistence
            image_item: Optional ImageItem being discussed (None for general chat)
            provider: AI provider name (ollama, openai, claude)
            model: Model name
            session_id: Optional legacy session ID (deprecated; prefer chat_item)
            chat_item: Optional ImageItem with item_type='chat' that stores this session
        """
        # Set window title based on whether we have a named chat item or image
        if chat_item and chat_item.display_name:
            title = f"Chat: {chat_item.display_name}"
        elif image_item:
            title = f"Chat: {Path(image_item.file_path).name}"
        else:
            title = f"Chat with AI: {provider.title()} ({model})"
        
        super().__init__(parent, title=title,
                        size=(800, 700), 
                        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
        
        self.workspace = workspace
        self.image_item = image_item
        self.provider = provider
        self.model = model
        self.chat_item = chat_item  # workspace item storing this chat (new flow)
        
        # Try to get config and cache from parent (ImageDescriber)
        self.config = getattr(parent, 'config', {})
        self.cached_ollama_models = getattr(parent, 'cached_ollama_models', None)
        
        self.current_response_chunks = []  # Buffer for streaming response
        self.is_processing = False
        self.pending_attachments: List[Dict[str, str]] = []  # [{path, media_type}, ...]
        # Temp file tracking for HEIC conversion and clipboard paste cleanup
        self._temp_files: List[str] = []
        self._temp_dirs: List[str] = []
        # Token/context window tracking
        self._session_input_tokens = 0
        self._session_output_tokens = 0
        self._context_window_size = 0   # Populated async; 0 = not yet known
        self._compact_pending = False   # Set True during Summarize & Compact
        
        if chat_item is not None:
            # New flow: chat_item stores the session in workspace.items
            self.session_id = chat_item.file_path.replace('chat:', '')
            # Build runtime session dict from chat_item and rebuild message history
            self.session = {
                'id': self.session_id,
                'name': chat_item.display_name or title,
                'image_path': str(image_item.file_path) if image_item else None,
                'provider': provider,
                'model': model,
                'created': datetime.now().isoformat(),
                'modified': datetime.now().isoformat(),
                'messages': self._build_messages_from_descriptions(chat_item)
            }
        else:
            # Legacy flow: use workspace.chat_sessions dict
            self.session_id = session_id or self._create_session_id()
            if self.session_id in workspace.chat_sessions:
                self.session = workspace.chat_sessions[self.session_id]
            else:
                self.session = self._create_new_session()
                workspace.chat_sessions[self.session_id] = self.session
        
        self._create_ui()
        self._bind_events()
        self._load_history()

        self.Centre()
        wx.CallAfter(self._init_token_tracking)
        
    def _create_session_id(self) -> str:
        """Create unique session ID"""
        return f"chat_{int(time.time() * 1000)}"

    def _build_messages_from_descriptions(self, chat_item: ImageItem) -> list:
        """Reconstruct conversation messages list from ImageDescription objects.

        Used when resuming an existing chat session so the AI worker receives
        the full conversation history for context.
        Attachments are not restored (path may not exist anymore) — only text.
        """
        messages = []
        for desc in chat_item.descriptions:
            if desc.prompt_style == 'user_question':
                messages.append({
                    'role': 'user',
                    'content': desc.text,
                    'timestamp': desc.created
                })
            elif desc.prompt_style == 'ai_response':
                messages.append({
                    'role': 'assistant',
                    'content': desc.text,
                    'timestamp': desc.created,
                    'metadata': desc.metadata
                })
        return messages
        
    def _create_new_session(self) -> dict:
        """Create new chat session data structure"""
        # Name and path depend on whether we have an image
        if self.image_item:
            name = f"Chat: {Path(self.image_item.file_path).name}"
            image_path = str(self.image_item.file_path)
        else:
            name = f"Chat: {self.provider.title()} ({self.model})"
            image_path = None
        
        return {
            'id': self.session_id,
            'name': name,
            'image_path': image_path,  # None for general chat
            'provider': self.provider,
            'model': self.model,
            'created': datetime.now().isoformat(),
            'modified': datetime.now().isoformat(),
            'messages': []
        }
        
    def _create_ui(self):
        """Create accessible UI with ListBox for history"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Header with image preview and session info
        header_sizer = self._create_header(panel)
        main_sizer.Add(header_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Token / context window strip — thin bar showing session usage vs model limit
        self._token_strip_panel = wx.Panel(panel)
        _ts_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.token_gauge = wx.Gauge(self._token_strip_panel, range=100, size=(-1, 8))
        _ts_sizer.Add(self.token_gauge, 1, wx.EXPAND | wx.RIGHT, 8)
        self.token_label = wx.StaticText(self._token_strip_panel, label="Tokens: —",
                                         name="Token usage")
        _ts_sizer.Add(self.token_label, 0, wx.ALIGN_CENTER_VERTICAL)
        self._token_strip_panel.SetSizer(_ts_sizer)
        main_sizer.Add(self._token_strip_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Conversation history (ListBox for accessibility)
        history_label = wx.StaticText(panel, label="Conversation History:")
        main_sizer.Add(history_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        self.history_list = wx.ListBox(panel,
                                       style=wx.LB_SINGLE | wx.LB_NEEDED_SB,
                                       name="Conversation history")
        self.history_list.SetMinSize((-1, 180))
        main_sizer.Add(self.history_list, 1, wx.EXPAND | wx.ALL, 10)

        # Message detail — shows full text of the selected history item.
        # Editable so the user can select/copy text and navigate with cursor keys.
        # Changes are intentionally not saved back to the session.
        detail_label = wx.StaticText(panel, label="Selected message:")
        main_sizer.Add(detail_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.message_detail = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_WORDWRAP | wx.TE_RICH2,
            name="Selected message"
        )
        try:
            self.message_detail.SetAccessible(_NamedTextAccessible(self.message_detail, "Selected message"))
        except NotImplementedError:
            pass  # wx.Accessible not supported on this platform (macOS)
        self.message_detail.SetMinSize((-1, 200))
        main_sizer.Add(self.message_detail, 0, wx.EXPAND | wx.ALL, 10)

        # Status/typing indicator
        self.status_text = wx.StaticText(panel, label="")
        main_sizer.Add(self.status_text, 0, wx.LEFT | wx.RIGHT, 10)
        
        # Input area
        input_label = wx.StaticText(panel, label="Your message:")
        main_sizer.Add(input_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        self.input_text = wx.TextCtrl(panel, 
                                      style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER,
                                      name="Your message",
                                      size=(-1, 100))
        try:
            self.input_text.SetAccessible(_NamedTextAccessible(self.input_text, "Your message"))
        except NotImplementedError:
            pass  # wx.Accessible not supported on this platform (macOS)
        main_sizer.Add(self.input_text, 0, wx.EXPAND | wx.ALL, 10)
        
        # Pending attachments panel — hidden until files are queued
        self.attach_panel = wx.Panel(panel)
        attach_panel_sizer = wx.BoxSizer(wx.VERTICAL)

        attach_label = wx.StaticText(self.attach_panel, label="Attachments:")
        attach_panel_sizer.Add(attach_label, 0, wx.LEFT | wx.TOP, 5)

        self.attach_list = wx.ListBox(self.attach_panel,
                                      style=wx.LB_SINGLE | wx.LB_NEEDED_SB,
                                      name="Pending attachments",
                                      size=(-1, 60))
        attach_panel_sizer.Add(self.attach_list, 0, wx.EXPAND | wx.ALL, 5)

        self.remove_attach_btn = wx.Button(self.attach_panel, label="Remove Selected")
        attach_panel_sizer.Add(self.remove_attach_btn, 0, wx.LEFT | wx.BOTTOM, 5)

        self.attach_panel.SetSizer(attach_panel_sizer)
        self.attach_panel.Show(False)
        main_sizer.Add(self.attach_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.send_btn = wx.Button(panel, label="Send (Enter)")
        self.send_btn.SetDefault()
        button_sizer.Add(self.send_btn, 0, wx.ALL, 5)
        
        self.clear_btn = wx.Button(panel, label="Clear Input")
        button_sizer.Add(self.clear_btn, 0, wx.ALL, 5)

        self.attach_btn = wx.Button(panel, label="Attach Files...")
        button_sizer.Add(self.attach_btn, 0, wx.ALL, 5)

        self.commands_btn = wx.Button(panel, label="Session ▾")
        button_sizer.Add(self.commands_btn, 0, wx.ALL, 5)

        button_sizer.AddStretchSpacer()
        
        self.close_btn = wx.Button(panel, wx.ID_CLOSE, label="Close")
        button_sizer.Add(self.close_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(main_sizer)
        
        # Set initial focus to input
        wx.CallAfter(self.input_text.SetFocus)
        
        # Set initial attach button state based on provider
        self._update_attach_button_state()
        
    def _create_header(self, parent) -> wx.BoxSizer:
        """Create header with image thumbnail and session info"""
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Image preview (150x150 thumbnail) - only if image_item exists
        if self.image_item is not None:
            img_bitmap = self._load_image_thumbnail(self.image_item.file_path, size=(150, 150))
            if img_bitmap:
                img_preview = wx.StaticBitmap(parent, bitmap=img_bitmap)
                header_sizer.Add(img_preview, 0, wx.ALL, 5)
        
        # Session info
        info_sizer = wx.BoxSizer(wx.VERTICAL)
        
        provider_text = f"Provider: {self.session['provider']} ({self.session['model']})"
        self.provider_label = wx.StaticText(parent, label=provider_text)
        info_sizer.Add(self.provider_label, 0, wx.ALL, 2)
        
        # Change Model button
        change_model_btn = wx.Button(parent, label="Change Model...", size=(-1, 24))
        change_model_btn.Bind(wx.EVT_BUTTON, self.on_change_model)
        info_sizer.Add(change_model_btn, 0, wx.ALL, 2)
        
        session_text = f"Session: {self.session['name']}"
        session_label = wx.StaticText(parent, label=session_text)
        info_sizer.Add(session_label, 0, wx.ALL, 2)
        
        msg_count = len(self.session['messages'])
        count_text = f"Messages: {msg_count}"
        self.message_count_label = wx.StaticText(parent, label=count_text)
        info_sizer.Add(self.message_count_label, 0, wx.ALL, 2)
        
        header_sizer.Add(info_sizer, 1, wx.EXPAND | wx.ALL, 5)
        
        return header_sizer
        
    def _load_image_thumbnail(self, image_path: str, size: tuple) -> Optional[wx.Bitmap]:
        """Load and resize image thumbnail"""
        try:
            from PIL import Image
            
            img = Image.open(image_path)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Convert PIL image to wx.Bitmap
            width, height = img.size
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            wx_img = wx.Image(width, height)
            wx_img.SetData(img.tobytes())
            
            return wx_img.ConvertToBitmap()
            
        except Exception as e:
            print(f"Error loading thumbnail: {e}")
            return None
        
    def _load_history(self):
        """Load conversation history into ListBox.

        When a chat_item is available (new flow), reads from chat_item.descriptions
        to show 'You' / 'AI' labels and token counts.
        Falls back to session['messages'] for legacy sessions.
        """
        self.history_list.Clear()

        if self.chat_item is not None:
            # New flow: read from ImageDescription objects
            for desc in self.chat_item.descriptions:
                role = "You" if desc.prompt_style == "user_question" else "AI"
                time_str = ""
                try:
                    dt = datetime.fromisoformat(desc.created)
                    hour = dt.hour % 12 or 12
                    ampm = "A" if dt.hour < 12 else "P"
                    time_str = f"{hour}:{dt.minute:02d}{ampm}"
                except Exception:
                    pass
                token_str = ""
                if desc.prompt_style == "ai_response" and desc.token_usage:
                    ct = (desc.token_usage.get('output_tokens')
                          or desc.token_usage.get('completion_tokens', 0))
                    if ct:
                        token_str = f" [\u2199 {ct:,} tok]"
                display_text = f"{role} ({time_str}){token_str}: {desc.text}"
                self.history_list.Append(display_text)
        else:
            # Legacy flow: read from session messages dict
            for msg in self.session['messages']:
                timestamp = msg.get('timestamp', '')
                role = "You" if msg['role'] == 'user' else "AI"
                time_str = ""
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        time_str = dt.strftime("%I:%M %p")
                    except Exception:
                        pass
                display_text = f"{role} ({time_str}): {msg['content']}"
                attachments = msg.get('attachments', [])
                if attachments:
                    filenames = ', '.join(Path(a['path']).name for a in attachments)
                    display_text += f"\n[Attachments: {filenames}]"
                self.history_list.Append(display_text)

        # Scroll to bottom (most recent message)
        if self.history_list.GetCount() > 0:
            last_idx = self.history_list.GetCount() - 1
            self.history_list.SetSelection(last_idx)
            self._update_message_detail(last_idx)

    def on_history_selected(self, event):
        """Update message detail when the user clicks or arrows to a history item."""
        self._update_message_detail()

    def _update_message_detail(self, idx: Optional[int] = None):
        """Populate message_detail with the full text of the currently selected
        history item.

        Args:
            idx: Explicit list index to display. When None, reads GetSelection().
                 Callers that just called SetSelection() should pass the index
                 directly because GetSelection() can return a stale value on macOS
                 when the ListBox does not have focus.

        Source priority:
          1. chat_item.descriptions[idx].text  (new flow - full untruncated text)
          2. session['messages'][idx]['content'] (legacy flow)

        Changes the user makes in message_detail are intentionally not persisted.
        """
        if idx is None:
            idx = self.history_list.GetSelection()
        if idx == wx.NOT_FOUND or idx < 0:
            return
        try:
            if self.chat_item is not None:
                descs = self.chat_item.descriptions
                if idx < len(descs):
                    self.message_detail.SetValue(descs[idx].text)
            else:
                msgs = self.session.get('messages', [])
                if idx < len(msgs):
                    self.message_detail.SetValue(msgs[idx].get('content', ''))
        except Exception:
            pass  # Best-effort; guard against race conditions

    def _bind_events(self):
        """Bind event handlers"""
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send_message)
        self.clear_btn.Bind(wx.EVT_BUTTON, self.on_clear_input)
        self.close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        self.input_text.Bind(wx.EVT_TEXT_ENTER, self.on_send_message)
        self.attach_btn.Bind(wx.EVT_BUTTON, self.on_attach_files)
        self.remove_attach_btn.Bind(wx.EVT_BUTTON, self.on_remove_attachment)
        self.commands_btn.Bind(wx.EVT_BUTTON, self.on_commands_menu)
        # History list selection drives the message detail area
        self.history_list.Bind(wx.EVT_LISTBOX, self.on_history_selected)
        # Intercept Ctrl/Cmd+V at window level for clipboard image paste
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down)
        
        # Bind chat worker events
        self.Bind(EVT_CHAT_UPDATE, self.on_chat_update)
        self.Bind(EVT_CHAT_COMPLETE, self.on_chat_complete)
        self.Bind(EVT_CHAT_ERROR, self.on_chat_error)
        
    def on_send_message(self, event):
        """Send user message and start AI processing"""
        message = self.input_text.GetValue().strip()
        if not message:
            return
            
        if self.is_processing:
            show_warning(self, "Please wait for the AI response to complete.")
            return
        
        # Validate any queued attachments still exist on disk
        missing = [a for a in self.pending_attachments if not Path(a['path']).exists()]
        if missing:
            names = ', '.join(Path(a['path']).name for a in missing)
            show_error(self, f"Attachment file(s) not found and cannot be sent:\n{names}")
            return

        # Add user message to session (with any pending attachments)
        timestamp = datetime.now().isoformat()
        user_msg = {
            'role': 'user',
            'content': message,
            'timestamp': timestamp
        }
        if self.pending_attachments:
            user_msg['attachments'] = list(self.pending_attachments)
        self.session['messages'].append(user_msg)

        # New flow: persist user turn to chat_item as an ImageDescription
        if self.chat_item is not None:
            user_desc = ImageDescription(
                text=message,
                prompt_style="user_question",
                provider=self.provider,
                model=self.model,
                created=timestamp
            )
            self.chat_item.add_description(user_desc)
            self.workspace.mark_modified()
        
        # Display in history ListBox
        time_str = datetime.fromisoformat(timestamp).strftime("%I:%M %p")
        display_text = f"You ({time_str}): {message}"
        if self.pending_attachments:
            filenames = ', '.join(Path(a['path']).name for a in self.pending_attachments)
            display_text += f"\n[Attachments: {filenames}]"
        self.history_list.Append(display_text)
        
        # Clear pending attachments now that they are part of the message
        self.pending_attachments = []
        self._refresh_attachment_panel()
        
        # Scroll to show new message
        last_idx = self.history_list.GetCount() - 1
        self.history_list.SetSelection(last_idx)
        self._update_message_detail(last_idx)

        # Clear input
        self.input_text.Clear()
        
        # Show status
        self.status_text.SetLabel("AI is typing...")
        self.is_processing = True
        
        # Disable input while processing
        self.input_text.Enable(False)
        self.send_btn.Enable(False)
        
        # Initialize response buffer
        self.current_response_chunks = []
        
        # Start worker thread
        self._start_ai_processing()
        
    def _start_ai_processing(self):
        """Start ChatProcessingWorker with full message history"""
        # Get image path if available (None for text-only chat)
        image_path = str(self.image_item.file_path) if self.image_item else None
        
        # Get API key from config if provider needs one
        api_key = self._get_api_key_for_provider(self.provider)
        
        worker = ChatProcessingWorker(
            parent_window=self,
            image_path=image_path,  # None for text-only mode
            provider=self.provider,
            model=self.model,
            messages=self.session['messages'],
            api_key=api_key
        )
        worker.start()
    
    def _get_api_key_for_provider(self, provider: str) -> Optional[str]:
        """Load API key for the specified provider from various sources
        
        Check order:
        1. Environment variables
        2. Local text files (legacy support)
        3. Configuration file (via config_loader)
        
        Args:
            provider: Provider name (ollama, openai, claude, huggingface)
            
        Returns:
            API key string or None if not found/not needed
        """
        # Ollama doesn't need API key (runs locally)
        if provider.lower() == 'ollama':
            return None
        
        provider_key = provider.lower()
        
        # 1. Environment Variables
        env_map = {
            'openai': 'OPENAI_API_KEY',
            'claude': 'ANTHROPIC_API_KEY',
            'huggingface': 'HUGGINGFACE_API_KEY'
        }
        if provider_key in env_map:
            env_val = os.getenv(env_map[provider_key])
            if env_val:
                return env_val

        # 2. Local Text Files (Legacy support)
        # Common filenames used in this project
        file_map = {
            'openai': ['openai_api_key.txt', 'openai.txt'],
            'claude': ['claude.txt', 'anthropic.txt'],
            'huggingface': ['huggingface_api_key.txt', 'hf_key.txt']
        }
        
        if provider_key in file_map:
            filenames = file_map[provider_key]
            # Search locations: CWD, Exe dir, Script dir
            search_paths = [Path.cwd()]
            if getattr(sys, 'frozen', False):
                search_paths.append(Path(sys.executable).parent)
            else:
                search_paths.append(Path(__file__).parent)         # imagedescriber/
                search_paths.append(Path(__file__).parent.parent)  # project root/
            
            for sp in search_paths:
                for fn in filenames:
                    fp = sp / fn
                    if fp.exists():
                        try:
                            with open(fp, 'r', encoding='utf-8') as f:
                                val = f.read().strip()
                                if val:
                                    return val
                        except Exception:
                            pass

        # 3. Configuration File (Standard method)
        try:
            # Robust configuration loading (matching ai_providers.py logic)
            load_json_config_func = None

            # Try imports
            try:
                from idt_core.config_loader import load_json_config
                load_json_config_func = load_json_config
            except ImportError:
                pass

            config = None
            if load_json_config_func:
                try:
                    config, config_path, source = load_json_config_func('image_describer_config.json')
                except Exception:
                    pass

            # Manual Fallback if config loader failed
            if not config:
                import json
                candidates = []
                if getattr(sys, 'frozen', False):
                    base_dir = Path(sys.executable).parent
                    candidates.append(base_dir / 'image_describer_config.json')
                    candidates.append(base_dir / 'scripts' / 'image_describer_config.json')
                    if hasattr(sys, '_MEIPASS'):
                        candidates.append(Path(sys._MEIPASS) / 'scripts' / 'image_describer_config.json')
                else:
                    base_dir = Path(__file__).parent.parent
                    candidates.append(base_dir / 'scripts' / 'image_describer_config.json')

                candidates.append(Path.cwd() / 'image_describer_config.json')

                for path in candidates:
                    if path.exists():
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                config = json.load(f)
                                break
                        except Exception:
                            continue

            if not config:
                return None

            # Get API keys dict
            api_keys = config.get('api_keys', {})
            
            # Match provider name (case-insensitive)
            # Check exact match first
            if provider_key in api_keys:
                return api_keys[provider_key]
                
            # Check case-insensitive
            for key_provider, api_key in api_keys.items():
                if key_provider.lower() == provider_key:
                    return api_key
            
            # Check standard capitalization mappings
            provider_map = {
                'openai': ['OpenAI', 'open_ai'],
                'claude': ['Claude', 'Anthropic', 'anthropic'],
                'huggingface': ['HuggingFace', 'Hugging Face', 'HF']
            }
            
            if provider_key in provider_map:
                for variant in provider_map[provider_key]:
                    if variant in api_keys and api_keys[variant]:
                        return api_keys[variant]
            
            return None
            
        except Exception as e:
            print(f"Error loading API key for {provider}: {e}")
            return None

    def on_chat_update(self, event):
        """Handle streaming response chunks"""
        chunk = event.message_chunk
        self.current_response_chunks.append(chunk)
        
        # Update status to show we're receiving data
        chunk_count = len(self.current_response_chunks)
        self.status_text.SetLabel(f"Receiving response... ({chunk_count} chunks)")
        
    def on_chat_complete(self, event):
        """Handle completed AI response"""
        full_response = event.full_response

        # Compact mode: replace history with the summary instead of appending
        if self._compact_pending:
            self._compact_pending = False
            self._apply_compact(full_response)
            self.is_processing = False
            self.input_text.Enable(True)
            self.send_btn.Enable(True)
            self.input_text.SetFocus()
            self.status_text.SetLabel("")
            return
        
        # Save AI response to session
        timestamp = datetime.now().isoformat()
        ai_msg = {
            'role': 'assistant',
            'content': full_response,
            'timestamp': timestamp,
            'metadata': event.metadata
        }
        self.session['messages'].append(ai_msg)
        
        # New flow: persist AI turn to chat_item as an ImageDescription
        if self.chat_item is not None:
            token_usage = getattr(event, 'token_usage', {}) or {}
            output_tok = (token_usage.get('output_tokens')
                          or token_usage.get('completion_tokens', 0))
            ai_desc = ImageDescription(
                text=full_response,
                prompt_style="ai_response",
                provider=self.provider,
                model=self.model,
                created=timestamp,
                completion_tokens=output_tok,
                metadata=event.metadata,
                token_usage=token_usage
            )
            self.chat_item.add_description(ai_desc)
            self.workspace.mark_modified()

        # Accumulate session token totals and refresh the strip
        token_usage = getattr(event, 'token_usage', {}) or {}
        self._session_input_tokens += (token_usage.get('input_tokens')
                                        or token_usage.get('prompt_tokens', 0))
        self._session_output_tokens += (token_usage.get('output_tokens')
                                         or token_usage.get('completion_tokens', 0))
        self._update_token_strip()
        
        # Update session modified time
        self.session['modified'] = timestamp
        
        # Display in history ListBox with token count for new flow
        time_str = datetime.fromisoformat(timestamp).strftime("%I:%M %p")
        token_usage_for_display = getattr(event, 'token_usage', {}) or {}
        if self.chat_item is not None:
            # New flow: use consistent "You/AI" format with token count
            dt = datetime.fromisoformat(timestamp)
            hour = dt.hour % 12 or 12
            ampm = "A" if dt.hour < 12 else "P"
            time_str_new = f"{hour}:{dt.minute:02d}{ampm}"
            token_str = ""
            ct = (token_usage_for_display.get('output_tokens')
                  or token_usage_for_display.get('completion_tokens', 0))
            if ct:
                token_str = f" [\u2199 {ct:,} tok]"
            display_text = f"AI ({time_str_new}){token_str}: {full_response}"
        else:
            display_text = f"AI ({time_str}): {full_response}"
        self.history_list.Append(display_text)
        
        # Select the new message (screen readers will announce it)
        last_idx = self.history_list.GetCount() - 1
        self.history_list.SetSelection(last_idx)
        self._update_message_detail(last_idx)

        # Force screen reader announcement by setting focus briefly then returning it
        wx.CallAfter(self._announce_new_message, display_text)
        
        # Update message count
        msg_count = len(self.session['messages'])
        self.message_count_label.SetLabel(f"Messages: {msg_count}")
        
        # Clear status
        self.status_text.SetLabel("")
        
        # Auto-save workspace
        try:
            self.workspace.save()
        except Exception as e:
            print(f"Warning: Failed to auto-save workspace: {e}")
        
        # Re-enable input
        self.is_processing = False
        self.input_text.Enable(True)
        self.send_btn.Enable(True)
        self.input_text.SetFocus()
        
    def _announce_new_message(self, message_text: str):
        """Force screen reader to announce new AI message
        
        This is done by briefly moving focus to the history list,
        then returning it to the input field.
        """
        # Temporarily move focus to history list (triggers announcement)
        self.history_list.SetFocus()
        
        # Return focus to input after brief delay
        wx.CallLater(100, self.input_text.SetFocus)
        
    def on_chat_error(self, event):
        """Handle chat processing error"""
        error_msg = event.error
        
        # Show error to user
        show_error(self, f"Chat error:\n{error_msg}")
        
        # Add error to history
        timestamp = datetime.now().isoformat()
        time_str = datetime.fromisoformat(timestamp).strftime("%I:%M %p")
        error_text = f"System ({time_str}): Error - {error_msg}"
        self.history_list.Append(error_text)
        self.history_list.SetSelection(self.history_list.GetCount() - 1)
        
        # Clear status
        self.status_text.SetLabel("")
        
        # Re-enable input
        self.is_processing = False
        self.input_text.Enable(True)
        self.send_btn.Enable(True)
        self.input_text.SetFocus()
        
    def on_clear_input(self, event):
        """Clear the input field"""
        self.input_text.Clear()
        self.input_text.SetFocus()

    def on_change_model(self, event):
        """Change the AI provider and model for this session"""
        chat_dialog = ChatDialog(self, self.config, cached_ollama_models=self.cached_ollama_models)
        
        # Pre-select current
        for i in range(chat_dialog.provider_choice.GetCount()):
            if chat_dialog.provider_choice.GetString(i).lower() == self.provider.lower():
                chat_dialog.provider_choice.SetSelection(i)
                chat_dialog.on_provider_changed(None) # Trigger model update
                break
        
        # Try to select current model
        if self.model:
            # Find the model in the list
            for i in range(chat_dialog.model_combo.GetCount()):
                if chat_dialog.model_combo.GetString(i) == self.model:
                    chat_dialog.model_combo.SetSelection(i)
                    break
        
        if chat_dialog.ShowModal() == wx.ID_OK:
            selections = chat_dialog.get_selections()
            self.provider = selections['provider']
            self.model = selections['model']
            
            # Update session data
            self.session['provider'] = self.provider
            self.session['model'] = self.model
            
            # Update UI
            provider_text = f"Provider: {self.provider} ({self.model})"
            self.provider_label.SetLabel(provider_text)
            
            # Clear pending attachments — they may not be valid for the new provider
            self.pending_attachments = []
            self._refresh_attachment_panel()
            self._update_attach_button_state()
            
            # Add system message to history
            timestamp = datetime.now().isoformat()
            time_str = datetime.fromisoformat(timestamp).strftime("%I:%M %p")
            sys_msg = f"System ({time_str}): Switched to {self.provider} - {self.model}"
            self.history_list.Append(sys_msg)
            self.history_list.SetSelection(self.history_list.GetCount() - 1)
            self.workspace.save()
            
        chat_dialog.Destroy()

    # ------------------------------------------------------------------
    # File attachment support
    # ------------------------------------------------------------------

    def _infer_media_type(self, path: str) -> str:
        """Infer MIME type from file extension."""
        ext = Path(path).suffix.lower()
        _ext_to_mime = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.tif': 'image/tiff', '.tiff': 'image/tiff',
            '.pdf': 'application/pdf',
        }
        return _ext_to_mime.get(ext, 'application/octet-stream')

    def _update_attach_button_state(self):
        """Show/hide the attach button based on whether the current provider supports attachments."""
        can_attach = supports_attachments(self.provider)
        self.attach_btn.Show(can_attach)
        # Ensure layout reflects visibility change
        self.attach_btn.GetParent().Layout()

    def on_attach_files(self, event):
        """Open file picker and queue selected files as pending attachments."""
        # Build wildcard: start with provider-specific images, then add HEIC
        wildcard = get_attachment_wildcard(self.provider)
        # Add HEIC/HEIF to the wildcard if not already present
        if 'heic' not in wildcard.lower():
            wildcard = wildcard.rstrip('|') + '|HEIC/HEIF images (*.heic;*.heif)|*.heic;*.heif'
        with wx.FileDialog(self, "Attach files",
                           wildcard=wildcard,
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                for path in dlg.GetPaths():
                    # Convert HEIC/HEIF to JPEG before attaching (providers can't read HEIC directly)
                    if Path(path).suffix.lower() in ('.heic', '.heif'):
                        try:
                            from idt_core.converter import convert_heic_to_jpg
                            import tempfile
                            tmp_dir = tempfile.mkdtemp(prefix="idt_chat_")
                            jpg_path = str(Path(tmp_dir) / (Path(path).stem + ".jpg"))
                            convert_heic_to_jpg(path, jpg_path)
                            self._temp_files.append(jpg_path)
                            self._temp_dirs.append(tmp_dir)
                            path = jpg_path
                            media_type = 'image/jpeg'
                            self.status_text.SetLabel(
                                f"HEIC converted to JPEG: {Path(jpg_path).name}"
                            )
                        except Exception as e:
                            show_error(self, f"Could not convert HEIC file: {e}")
                            continue
                    else:
                        media_type = self._infer_media_type(path)
                    # Guard: enforce per-provider file size limits before queuing
                    try:
                        size_bytes = Path(path).stat().st_size
                        if self.provider == 'claude':
                            if media_type == 'application/pdf' and size_bytes > 32 * 1024 * 1024:
                                show_error(self, f"PDF exceeds Claude's 32 MB limit:\n{Path(path).name}")
                                continue
                            elif media_type.startswith('image/') and size_bytes > 5 * 1024 * 1024:
                                show_error(self, f"Image exceeds Claude's 5 MB limit:\n{Path(path).name}")
                                continue
                    except Exception:
                        pass  # Size check is best-effort; let the API report errors
                    self.pending_attachments.append({'path': path, 'media_type': media_type})
                self._refresh_attachment_panel()

    def on_remove_attachment(self, event):
        """Remove the selected attachment from the pending queue."""
        idx = self.attach_list.GetSelection()
        if idx != wx.NOT_FOUND and idx < len(self.pending_attachments):
            self.pending_attachments.pop(idx)
            self._refresh_attachment_panel()

    def _refresh_attachment_panel(self):
        """Repopulate the pending attachments ListBox and show/hide the panel."""
        self.attach_list.Clear()
        for att in self.pending_attachments:
            label = f"{Path(att['path']).name}  ({att['media_type']})"
            self.attach_list.Append(label)
        show = bool(self.pending_attachments)
        self.attach_panel.Show(show)
        self.Layout()

    def on_key_down(self, event):
        """Handle Ctrl/Cmd+V to paste a clipboard image as an attachment."""
        # Let the normal event chain run for everything except Ctrl+V
        is_ctrl = event.ControlDown() or event.CmdDown()
        if is_ctrl and event.GetKeyCode() == ord('V'):
            if wx.TheClipboard.Open():
                if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP)):
                    bmp_data = wx.BitmapDataObject()
                    if wx.TheClipboard.GetData(bmp_data):
                        wx.TheClipboard.Close()
                        # Save bitmap to a temp PNG file and queue it
                        try:
                            import tempfile
                            tmp_dir = tempfile.mkdtemp(prefix="idt_paste_")
                            self._temp_dirs.append(tmp_dir)
                            png_path = str(Path(tmp_dir) / "pasted_image.png")
                            img = bmp_data.GetBitmap().ConvertToImage()
                            img.SaveFile(png_path, wx.BITMAP_TYPE_PNG)
                            self._temp_files.append(png_path)
                            self.pending_attachments.append(
                                {'path': png_path, 'media_type': 'image/png'}
                            )
                            self._refresh_attachment_panel()
                            self.status_text.SetLabel("Clipboard image added as attachment.")
                            return  # Consumed — don't propagate further
                        except Exception as e:
                            wx.TheClipboard.Close() if wx.TheClipboard.IsOpened() else None
                            self.status_text.SetLabel(f"Clipboard paste failed: {e}")
                            return
                wx.TheClipboard.Close()
        event.Skip()  # Let normal Ctrl+V text paste work in TextCtrl

    def on_close(self, event):
        """Handle close — guard if AI is mid-response, then cleanup and save."""
        if self.is_processing:
            dlg = wx.MessageDialog(
                self,
                "The AI is still responding. Close anyway and lose the current response?",
                "Close Chat",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
            )
            result = dlg.ShowModal()
            dlg.Destroy()
            if result != wx.ID_YES:
                return
        self._cleanup_temp_files()
        try:
            self.workspace.save()
        except Exception as e:
            print(f"Warning: Failed to save workspace on close: {e}")
        self.EndModal(wx.ID_CLOSE)

    # ------------------------------------------------------------------
    # Token / context window tracking
    # ------------------------------------------------------------------

    def _init_token_tracking(self):
        """Sum tokens from existing descriptions (resumed session) and start context fetch."""
        if self.chat_item is not None:
            for desc in self.chat_item.descriptions:
                if desc.prompt_style == 'ai_response' and desc.token_usage:
                    tu = desc.token_usage
                    self._session_input_tokens += (
                        tu.get('input_tokens') or tu.get('prompt_tokens', 0)
                    )
                    self._session_output_tokens += (
                        tu.get('output_tokens') or tu.get('completion_tokens', 0)
                    )
        self._update_token_strip()
        import threading
        t = threading.Thread(target=self._fetch_context_window_bg, daemon=True)
        t.start()

    def _fetch_context_window_bg(self):
        """Background thread: look up context window size for the current model."""
        size = 0
        try:
            if self.provider == 'claude':
                from idt_core.providers.claude import CLAUDE_MODEL_METADATA
                size = CLAUDE_MODEL_METADATA.get(self.model, {}).get('context_window', 200_000)
            elif self.provider == 'openai':
                from idt_core.providers.openai_provider import OPENAI_MODEL_METADATA
                size = OPENAI_MODEL_METADATA.get(self.model, {}).get('context_window', 128_000)
            elif self.provider == 'ollama':
                try:
                    import ollama
                    info = ollama.show(self.model)
                    # Newer Ollama versions expose model_info with architecture-prefixed keys
                    model_info = getattr(info, 'model_info', None) or {}
                    for key, val in model_info.items():
                        if 'context_length' in key.lower() or 'context_window' in key.lower():
                            size = int(val)
                            break
                    # Fall back to parsing the parameters string (num_ctx N)
                    if not size:
                        params_str = getattr(info, 'parameters', '') or ''
                        for line in params_str.splitlines():
                            parts = line.strip().lower().split()
                            if parts and parts[0] == 'num_ctx' and len(parts) >= 2:
                                size = int(parts[1])
                                break
                except Exception:
                    size = 32_768
            elif self.provider == 'mlx':
                size = 32_768
        except Exception:
            pass
        wx.CallAfter(self._on_context_window_fetched, size)

    def _on_context_window_fetched(self, size: int):
        if not self or not self.IsShown():
            return
        self._context_window_size = size
        self._update_token_strip()

    def _update_token_strip(self):
        """Refresh the token gauge and label."""
        if not hasattr(self, 'token_gauge'):
            return
        total = self._session_input_tokens + self._session_output_tokens
        if self._context_window_size > 0:
            pct = min(100, round(total * 100 / self._context_window_size))
            if pct < 60:
                colour = wx.Colour(34, 139, 34)    # green
            elif pct < 85:
                colour = wx.Colour(200, 150, 0)    # amber
            else:
                colour = wx.Colour(200, 30, 30)    # red
            self.token_gauge.SetForegroundColour(colour)
            self.token_gauge.SetValue(pct)
            self.token_label.SetLabel(
                f"Tokens: {total:,} / {self._context_window_size:,} ({pct}%)"
            )
        else:
            self.token_gauge.SetValue(0)
            self.token_label.SetLabel(f"Tokens: {total:,}" if total else "Tokens: —")
        self._token_strip_panel.Layout()

    # ------------------------------------------------------------------
    # Session commands menu
    # ------------------------------------------------------------------

    def on_commands_menu(self, event):
        """Show the Session commands popup menu."""
        menu = wx.Menu()
        compact_item = menu.Append(wx.ID_ANY, "Summarize && Compact",
                                    "Ask AI to summarize, then replace context with summary")
        export_item = menu.Append(wx.ID_ANY, "Export Conversation...",
                                   "Save full conversation history to a text file")
        self.Bind(wx.EVT_MENU, self.on_summarize_compact, compact_item)
        self.Bind(wx.EVT_MENU, self.on_export_conversation, export_item)
        self.PopupMenu(menu)
        menu.Destroy()

    def on_summarize_compact(self, event):
        """Ask the AI to summarize; on response, replace context with that summary."""
        if self.is_processing:
            show_warning(self, "Please wait for the current response to complete.")
            return
        if len(self.session['messages']) < 2:
            show_info(self, "Nothing to compact yet — start chatting first.")
            return

        msg_count = len(self.session['messages'])
        dlg = wx.MessageDialog(
            self,
            f"This sends a summarization request to the AI ({msg_count} messages in context), "
            "then replaces the active context with that summary to free up token budget.\n\n"
            "Your full history is preserved in the workspace file.\n\nContinue?",
            "Summarize & Compact",
            wx.YES_NO | wx.ICON_QUESTION,
        )
        result = dlg.ShowModal()
        dlg.Destroy()
        if result != wx.ID_YES:
            return

        self._compact_pending = True
        summarize_msg = (
            "Please provide a comprehensive summary of our entire conversation so far. "
            "Include all topics discussed, decisions made, questions asked and answered, "
            "and any important context or conclusions. Be thorough — this summary will "
            "replace the full conversation history."
        )
        self.session['messages'].append({
            'role': 'user',
            'content': summarize_msg,
            'timestamp': datetime.now().isoformat(),
        })

        self.status_text.SetLabel("Summarizing conversation…")
        self.send_btn.Enable(False)
        self.input_text.Enable(False)
        self.is_processing = True

        api_key = self.config.get('api_keys', {}).get(self.provider, '')
        worker = ChatProcessingWorker(
            parent_window=self,
            image_path=None,
            provider=self.provider,
            model=self.model,
            messages=self.session['messages'],
            api_key=api_key,
        )
        worker.start()

    def _apply_compact(self, summary: str):
        """Replace active context with the given summary; preserve full history on disk."""
        timestamp = datetime.now().isoformat()
        self.session['messages'] = [
            {
                'role': 'user',
                'content': f'[Conversation summary — full history preserved in workspace]:\n{summary}',
                'timestamp': timestamp,
            },
            {
                'role': 'assistant',
                'content': 'Got it. How can I continue helping you?',
                'timestamp': timestamp,
            },
        ]
        self.session['modified'] = timestamp

        if self.chat_item is not None:
            compact_desc = ImageDescription(
                text=f"[COMPACT] {summary}",
                prompt_style='compact_summary',
                provider=self.provider,
                model=self.model,
                created=timestamp,
            )
            self.chat_item.add_description(compact_desc)
            self.workspace.mark_modified()

        self._session_input_tokens = 0
        self._session_output_tokens = 0
        self._update_token_strip()

        self.history_list.Append("─── Conversation compacted ───")
        last_idx = self.history_list.GetCount() - 1
        self.history_list.SetSelection(last_idx)
        self._update_message_detail(last_idx)
        self.message_count_label.SetLabel(f"Messages: {len(self.session['messages'])}")

        try:
            self.workspace.save()
        except Exception:
            pass

    def on_export_conversation(self, event):
        """Save full conversation history to a plain-text file."""
        default_name = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with wx.FileDialog(
            self, "Export Conversation",
            wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            defaultFile=default_name,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            path = dlg.GetPath()

        try:
            lines = [f"Chat Export: {self.session.get('name', 'Chat Session')}", ""]
            if self.chat_item is not None:
                for desc in self.chat_item.descriptions:
                    if desc.prompt_style not in ('user_question', 'ai_response'):
                        continue
                    role = "You" if desc.prompt_style == "user_question" else "AI"
                    try:
                        dt = datetime.fromisoformat(desc.created)
                        m, d, y = dt.month, dt.day, dt.year
                        hr = dt.hour % 12 or 12
                        ampm = "A" if dt.hour < 12 else "P"
                        time_str = f"{m}/{d}/{y} {hr}:{dt.minute:02d}{ampm}"
                    except Exception:
                        time_str = desc.created
                    lines += [f"[{role} — {time_str}]", desc.text, ""]
            else:
                for msg in self.session['messages']:
                    role = "You" if msg['role'] == 'user' else "AI"
                    lines += [f"[{role}]", msg['content'], ""]

            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            self.status_text.SetLabel(f"Exported to {Path(path).name}")
        except Exception as e:
            show_error(self, f"Export failed:\n{e}")

    def _cleanup_temp_files(self):
        """Remove any temp files created for HEIC conversion or clipboard paste."""
        import shutil
        for f in list(self._temp_files):
            try:
                Path(f).unlink(missing_ok=True)
            except Exception:
                pass
        for d in list(self._temp_dirs):
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass
        self._temp_files = []
        self._temp_dirs = []

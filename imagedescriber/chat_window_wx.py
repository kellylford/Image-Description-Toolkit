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
if getattr(sys, 'frozen', False):
    _project_root = Path(sys.executable).parent
else:
    _project_root = Path(__file__).parent.parent

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Import shared utilities
from shared.wx_common import show_error, show_warning, show_info

# Import workers and events
from imagedescriber.workers_wx import (
    ChatProcessingWorker,
    EVT_CHAT_UPDATE,
    EVT_CHAT_COMPLETE,
    EVT_CHAT_ERROR
)

# Import data models
from imagedescriber.data_models import ImageItem, ImageWorkspace


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
        
        self.provider_choice = wx.Choice(self, choices=['Ollama', 'OpenAI', 'Claude', 'HuggingFace'])
        self.provider_choice.SetSelection(0)  # Default to Ollama
        self.provider_choice.Bind(wx.EVT_CHOICE, self.on_provider_changed)
        provider_sizer.Add(self.provider_choice, 1, wx.ALL | wx.EXPAND, 5)
        
        main_sizer.Add(provider_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        
        # Model selection
        model_sizer = wx.BoxSizer(wx.HORIZONTAL)
        model_label = wx.StaticText(self, label="Model:")
        model_label.SetMinSize((100, -1))
        model_sizer.Add(model_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        
        self.model_combo = wx.ComboBox(self, style=wx.CB_DROPDOWN)
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
        provider = self.provider_choice.GetStringSelection().lower()
        
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
                        self.model_combo.Append(model)
                    # Set first model as default
                    self.model_combo.SetValue(models[0])
                else:
                    # Fallback if no models found
                    self.model_combo.SetValue('llava:latest')
                    
            elif provider == 'openai':
                # Common OpenAI models
                models = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4']
                for model in models:
                    self.model_combo.Append(model)
                self.model_combo.SetValue('gpt-4o')
                
            elif provider == 'claude':
                # Claude models
                models = ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229']
                for model in models:
                    self.model_combo.Append(model)
                self.model_combo.SetValue('claude-3-5-sonnet-20241022')
                
            elif provider == 'huggingface':
                # HuggingFace models
                models = ['Salesforce/blip-image-captioning-large', 'microsoft/git-large-coco']
                for model in models:
                    self.model_combo.Append(model)
                if models:
                    self.model_combo.SetValue(models[0])
                    
        except Exception as e:
            print(f"Error populating models for {provider}: {e}")
            # Set a reasonable fallback
            if provider == 'ollama':
                self.model_combo.SetValue('llava:latest')
            elif provider == 'openai':
                self.model_combo.SetValue('gpt-4o')
            elif provider == 'claude':
                self.model_combo.SetValue('claude-3-5-sonnet-20241022')
        
    def get_selections(self) -> Dict[str, str]:
        """Get selected provider and model
        
        Returns:
            Dictionary with 'provider' and 'model' keys
        """
        return {
            'provider': self.provider_choice.GetStringSelection().lower(),
            'model': self.model_combo.GetValue()
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
                 provider: str, model: str, session_id: Optional[str] = None):
        """Initialize chat window
        
        Args:
            parent: Parent window
            workspace: ImageWorkspace instance for persistence
            image_item: Optional ImageItem (None for general chat)
            provider: AI provider name (ollama, openai, claude)
            model: Model name
            session_id: Optional existing session ID to resume
        """
        # Set window title based on whether we have an image
        if image_item:
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
        self.session_id = session_id or self._create_session_id()
        self.current_response_chunks = []  # Buffer for streaming response
        self.is_processing = False
        
        # Load or create session
        if self.session_id in workspace.chat_sessions:
            self.session = workspace.chat_sessions[self.session_id]
        else:
            self.session = self._create_new_session()
            workspace.chat_sessions[self.session_id] = self.session
        
        self._create_ui()
        self._bind_events()
        self._load_history()
        
        self.Centre()
        
    def _create_session_id(self) -> str:
        """Create unique session ID"""
        return f"chat_{int(time.time() * 1000)}"
        
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
        
        # Conversation history (ListBox for accessibility)
        history_label = wx.StaticText(panel, label="Conversation History:")
        main_sizer.Add(history_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        self.history_list = wx.ListBox(panel, 
                                       style=wx.LB_SINGLE | wx.LB_NEEDED_SB | wx.LB_HSCROLL,
                                       name="Conversation history")
        self.history_list.SetMinSize((-1, 300))
        main_sizer.Add(self.history_list, 1, wx.EXPAND | wx.ALL, 10)
        
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
        main_sizer.Add(self.input_text, 0, wx.EXPAND | wx.ALL, 10)
        
        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.send_btn = wx.Button(panel, label="Send (Enter)")
        self.send_btn.SetDefault()
        button_sizer.Add(self.send_btn, 0, wx.ALL, 5)
        
        self.clear_btn = wx.Button(panel, label="Clear Input")
        button_sizer.Add(self.clear_btn, 0, wx.ALL, 5)
        
        button_sizer.AddStretchSpacer()
        
        self.close_btn = wx.Button(panel, wx.ID_CLOSE, label="Close")
        button_sizer.Add(self.close_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(main_sizer)
        
        # Set initial focus to input
        wx.CallAfter(self.input_text.SetFocus)
        
    def _create_header(self, parent) -> wx.BoxSizer:
        """Create header with image thumbnail and session info"""
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Image preview (150x150 thumbnail)
        img_bitmap = self._load_image_thumbnail(self.image_item.file_path, size=(150, 150))
        if img_bitmap:
            img_preview = wx.StaticBitmap(parent, bitmap=img_bitmap)
            header_sizer.Add(img_preview, 0, wx.ALL, 5)
        
        # Session info
        info_sizer = wx.BoxSizer(wx.VERTICAL)
        
        provider_text = f"Provider: {self.session['provider']} ({self.session['model']})"
        provider_label = wx.StaticText(parent, label=provider_text)
        info_sizer.Add(provider_label, 0, wx.ALL, 2)
        
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
        """Load conversation history into ListBox"""
        self.history_list.Clear()
        
        for msg in self.session['messages']:
            timestamp = msg.get('timestamp', '')
            role = "You" if msg['role'] == 'user' else "AI"
            
            # Format timestamp (show time only)
            time_str = ""
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%I:%M %p")
                except:
                    pass
            
            # Format message for ListBox display
            # Each message is a single list item for screen reader friendliness
            display_text = f"{role} ({time_str}): {msg['content']}"
            self.history_list.Append(display_text)
        
        # Scroll to bottom (most recent message)
        if self.history_list.GetCount() > 0:
            self.history_list.SetSelection(self.history_list.GetCount() - 1)
            
    def _bind_events(self):
        """Bind event handlers"""
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send_message)
        self.clear_btn.Bind(wx.EVT_BUTTON, self.on_clear_input)
        self.close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        self.input_text.Bind(wx.EVT_TEXT_ENTER, self.on_send_message)
        
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
        
        # Add user message to session
        timestamp = datetime.now().isoformat()
        user_msg = {
            'role': 'user',
            'content': message,
            'timestamp': timestamp
        }
        self.session['messages'].append(user_msg)
        
        # Display in history ListBox
        time_str = datetime.fromisoformat(timestamp).strftime("%I:%M %p")
        display_text = f"You ({time_str}): {message}"
        self.history_list.Append(display_text)
        
        # Scroll to show new message
        self.history_list.SetSelection(self.history_list.GetCount() - 1)
        
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
        
        worker = ChatProcessingWorker(
            parent_window=self,
            image_path=image_path,  # None for text-only mode
            provider=self.provider,
            model=self.model,
            messages=self.session['messages']
        )
        worker.start()
        
    def on_chat_update(self, event):
        """Handle streaming response chunks"""
        chunk = event.message_chunk
        self.current_response_chunks.append(chunk)
        
        # Update status to show we're receiving data
        chunk_count = len(self.current_response_chunks)
        self.status_text.SetLabel(f"Receiving response... ({chunk_count} chunks)")
        
    def on_chat_complete(self, event):
        """Handle completed AI response"""
        # Get full response
        full_response = event.full_response
        
        # Save AI response to session
        timestamp = datetime.now().isoformat()
        ai_msg = {
            'role': 'assistant',
            'content': full_response,
            'timestamp': timestamp,
            'metadata': event.metadata
        }
        self.session['messages'].append(ai_msg)
        
        # Update session modified time
        self.session['modified'] = timestamp
        
        # Display in history ListBox
        time_str = datetime.fromisoformat(timestamp).strftime("%I:%M %p")
        display_text = f"AI ({time_str}): {full_response}"
        self.history_list.Append(display_text)
        
        # Select the new message (screen readers will announce it)
        self.history_list.SetSelection(self.history_list.GetCount() - 1)
        
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
        
    def on_close(self, event):
        """Handle window close"""
        # Save workspace before closing
        try:
            self.workspace.save()
        except Exception as e:
            print(f"Warning: Failed to save workspace on close: {e}")
        
        self.EndModal(wx.ID_CLOSE)

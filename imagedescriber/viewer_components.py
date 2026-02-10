#!/usr/bin/env python3
"""
viewer_components.py - Reusable Viewer Components for ImageDescriber

Contains:
- WorkflowMonitor: Logic for parsing description files and monitoring changes
- ViewerPanel: The main UI panel for the Viewer mode (description-centric view)
"""

import sys
import os
import time
import threading
from pathlib import Path
from typing import List, Dict, Optional, Any
import wx
import wx.lib.newevent

# Custom events for live updates
LiveUpdateEvent, EVT_LIVE_UPDATE = wx.lib.newevent.NewEvent()

# Import shared components
try:
    from shared.wx_common import (
        DescriptionListBox,
        show_warning,
        show_info,
        ask_yes_no
    )
    from shared.exif_utils import extract_exif_date_string
except ImportError:
    # Fallback for dev/frozen paths
    DescriptionListBox = wx.ListBox # Fallback
    show_warning = wx.MessageBox
    show_info = wx.MessageBox
    def ask_yes_no(parent, message, caption):
        return wx.MessageBox(message, caption, wx.YES_NO) == wx.YES

class WorkflowMonitor(threading.Thread):
    """Background thread for monitoring workflow progress"""
    
    def __init__(self, callback_window, workflow_dir):
        super().__init__(daemon=True)
        self.callback_window = callback_window
        self.workflow_dir = Path(workflow_dir)
        self.running = True
        
        # Check multiple possible locations for the descriptions file
        possible_locations = [
            self.workflow_dir / "descriptions" / "image_descriptions.txt",
            self.workflow_dir / "descriptions.txt",
            self.workflow_dir / "image_descriptions.txt",
        ]
        self.descriptions_file = None
        for loc in possible_locations:
            if loc.exists():
                self.descriptions_file = loc
                break
        
        if not self.descriptions_file:
            # Default to most likely location even if it doesn't exist yet
            self.descriptions_file = self.workflow_dir / "descriptions" / "image_descriptions.txt"
            
        self.last_modified = 0
    
    def run(self):
        """Monitor descriptions file for changes"""
        while self.running:
            try:
                if self.descriptions_file and self.descriptions_file.exists():
                    stat = self.descriptions_file.stat()
                    if stat.st_mtime > self.last_modified:
                        self.last_modified = stat.st_mtime
                        # Notify window to refresh via thread-safe event
                        wx.PostEvent(self.callback_window, LiveUpdateEvent())
            except:
                pass
            
            time.sleep(2)  # Check every 2 seconds
    
    def stop(self):
        """Stop monitoring"""
        self.running = False


class WorkflowParser:
    """Helper class for parsing description files"""
    
    @staticmethod
    def parse_file(file_path):
        """Parse the descriptions.txt file"""
        descriptions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            separator = '-' * 80
            sections = content.split(separator)
            
            for section in sections:
                if not section.strip():
                    continue
                
                # Skip header-only sections
                section_lower = section.lower()
                if ('image descriptions generated' in section_lower and 'file:' not in section_lower):
                    continue
                
                desc = WorkflowParser.parse_entry(section.strip())
                if desc:
                    descriptions.append(desc)
        
        except Exception as e:
            print(f"Error parsing descriptions: {e}")
        
        return descriptions
    
    @staticmethod
    def parse_entry(section):
        """Parse a single description entry"""
        lines = section.split('\n')
        entry = {
            'file_path': '',
            'relative_path': '',
            'description': '',
            'model': '',
            'prompt_style': '',
            'photo_date': '',
            'camera': '',
            'source': '',
            'provider': ''
        }
        
        description_started = False
        description_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped:
                if description_started:
                    description_lines.append('')
                continue
            
            # Parse metadata fields
            if line_stripped.startswith('File: '):
                entry['relative_path'] = line_stripped[6:].strip()
            elif line_stripped.startswith('Path: '):
                entry['file_path'] = line_stripped[6:].strip()
            elif line_stripped.startswith('Model: '):
                entry['model'] = line_stripped[7:].strip()
            elif line_stripped.startswith('Prompt Style: '):
                entry['prompt_style'] = line_stripped[14:].strip()
            elif line_stripped.startswith('Photo Date: '):
                entry['photo_date'] = line_stripped[12:].strip()
            elif line_stripped.startswith('Camera: '):
                entry['camera'] = line_stripped[8:].strip()
            elif line_stripped.startswith('Source: '):
                entry['source'] = line_stripped[8:].strip()
            elif line_stripped.startswith('Provider: '):
                entry['provider'] = line_stripped[10:].strip()
            elif line_stripped.startswith('Timestamp: '):
                pass
            elif line_stripped.startswith('Description: '):
                description_started = True
                desc_text = line_stripped[13:].strip()
                if desc_text:
                    description_lines.append(desc_text)
            elif line_stripped.startswith('[') and line_stripped.endswith(']'):
                continue
            elif description_started and not line_stripped.startswith(('Timestamp:', 'File:', 'Path:', 'Source:', 'Model:', 'Prompt Style:', 'Photo Date:', 'Camera:', 'Provider:')):
                description_lines.append(line_stripped)
        
        if description_lines:
            entry['description'] = '\n'.join(description_lines).strip()
            return entry
        
        return None


class ViewerPanel(wx.Panel):
    """
    Description-centric viewer panel.
    Displays a list of descriptions on the left, and details/preview on the right.
    Compatible with both directory-based Workflows and memory-based Workspaces.
    """
    
    def __init__(self, parent, main_window=None):
        super().__init__(parent)
        self.main_window = main_window # Reference to main frame for callbacks
        
        self.current_dir = None
        self.workflow_name = None
        self.monitor_thread = None
        self.is_live = False
        self.workspace_source_dirs = []  # Track workspace source directories for path resolution
        
        # Data storage
        self.descriptions = []
        self.entries = [] # Full entry dicts
        
        self.setup_ui()
        self.bind_events()
        
    def setup_ui(self):
        """Create the UI layout"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Splitter window
        self.splitter = wx.SplitterWindow(self, style=wx.SP_3D | wx.SP_LIVE_UPDATE)
        
        # --- LEFT PANEL: List ---
        left_panel = wx.Panel(self.splitter)
        left_panel.SetCanFocus(False)  # Prevent panel from receiving focus
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Controls area
        controls_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.refresh_btn = wx.Button(left_panel, label="Refresh")
        controls_sizer.Add(self.refresh_btn, 0, wx.ALL, 5)
        
        self.live_checkbox = wx.CheckBox(left_panel, label="Live Monitoring")
        controls_sizer.Add(self.live_checkbox, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        left_sizer.Add(controls_sizer, 0, wx.EXPAND | wx.ALL, 2)
        
        # List label
        desc_list_label = wx.StaticText(left_panel, label="Descriptions:")
        desc_list_label.SetCanFocus(False)  # Prevent tab stop on label
        left_sizer.Add(desc_list_label, 0, wx.ALL, 5)
        
        # Description ListBox (Accessible)
        self.desc_list = DescriptionListBox(left_panel, style=wx.LB_SINGLE)
        left_sizer.Add(self.desc_list, 1, wx.EXPAND | wx.ALL, 5)
        
        left_panel.SetSizer(left_sizer)
        
        # --- RIGHT PANEL: Details ---
        right_panel = wx.Panel(self.splitter)
        right_panel.SetCanFocus(False)  # Prevent panel from receiving focus
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Image Preview (Top Right)
        self.image_preview_panel = wx.Panel(right_panel, size=(-1, 300))
        self.image_preview_panel.SetBackgroundColour(wx.Colour(200, 200, 200)) # Placeholder gray
        self.image_preview_bitmap = None
        self.image_preview_panel.Bind(wx.EVT_PAINT, self.on_paint_preview)
        
        right_sizer.Add(self.image_preview_panel, 0, wx.EXPAND | wx.ALL, 5)
        
        # Metadata Label
        self.metadata_label = wx.StaticText(right_panel, label="")
        self.metadata_label.SetCanFocus(False)  # Prevent tab stop on label
        font = self.metadata_label.GetFont()
        font.MakeBold()
        self.metadata_label.SetFont(font)
        right_sizer.Add(self.metadata_label, 0, wx.EXPAND | wx.ALL, 5)
        
        # Full Description Text
        desc_label = wx.StaticText(right_panel, label="Description:")
        desc_label.SetCanFocus(False)  # Prevent tab stop on label
        right_sizer.Add(desc_label, 0, wx.ALL, 5)
        self.desc_text = wx.TextCtrl(right_panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        right_sizer.Add(self.desc_text, 1, wx.EXPAND | wx.ALL, 5)
        
        # Action Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.copy_btn = wx.Button(right_panel, label="Copy Text")
        self.copy_btn.Bind(wx.EVT_BUTTON, self.on_copy_text)
        btn_sizer.Add(self.copy_btn, 0, wx.ALL, 5)
        
        right_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        right_panel.SetSizer(right_sizer)
        
        # Splitter setup
        self.splitter.SplitVertically(left_panel, right_panel)
        self.splitter.SetSashGravity(0.4)
        self.splitter.SetMinimumPaneSize(200)
        
        main_sizer.Add(self.splitter, 1, wx.EXPAND | wx.ALL, 0)
        self.SetSizer(main_sizer)
        
    def bind_events(self):
        """Bind events"""
        self.desc_list.Bind(wx.EVT_LISTBOX, self.on_selection_changed)
        self.refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)
        self.live_checkbox.Bind(wx.EVT_CHECKBOX, self.on_live_toggle)
        self.Bind(EVT_LIVE_UPDATE, self.on_live_update_event)
        
        # Global key hook for navigation (optional, might conflict with parent)
        self.desc_list.Bind(wx.EVT_KEY_DOWN, self.on_list_key)

    def load_from_directory(self, directory):
        """Load data from a workflow directory"""
        self.current_dir = Path(directory)
        self.live_checkbox.Enable(True)
        
        # Find descriptions file
        possible_locations = [
            self.current_dir / "descriptions" / "image_descriptions.txt",
            self.current_dir / "descriptions.txt",
            self.current_dir / "image_descriptions.txt",
        ]
        
        desc_file = None
        for location in possible_locations:
            if location.exists():
                desc_file = location
                break
        
        if not desc_file:
            wx.MessageBox(f"No descriptions found in {directory}", "Error", wx.ICON_ERROR)
            return
            
        # Parse
        self.entries = WorkflowParser.parse_file(desc_file)
        self.refresh_list()
        
    def load_from_workspace(self, workspace):
        """Load data from an active ImageWorkspace object (Flattening)"""
        self.current_dir = None
        # Store workspace source directories for image path resolution
        self.workspace_source_dirs = workspace.get_all_directories() if hasattr(workspace, 'get_all_directories') else []
        self.live_checkbox.SetValue(False)
        self.live_checkbox.Enable(False) # Live monitoring meaningless for memory workspace
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread = None
            
        self.entries = []
        
        # Flatten workspace items into viewer entries
        for file_path, item in workspace.items.items():
            for desc in item.descriptions:
                entry = {
                    'file_path': str(item.file_path),
                    'relative_path': Path(item.file_path).name,
                    'description': desc.text,
                    'model': desc.model,
                    'prompt_style': desc.prompt_style,
                    'created': desc.created,
                    'provider': desc.provider,
                    'metadata': desc.metadata
                }
                self.entries.append(entry)
        
        # Sort by creation time if possible, or filename
        # Workspace is usually unsorted dict, so sorting helps consistency
        self.entries.sort(key=lambda x: x.get('file_path', ''))
        
        self.refresh_list()
        
    def refresh_list(self):
        """Update the UI list from self.entries"""
        # Prepare data for Accessible ListBox
        display_data = []
        for entry in self.entries:
            # Matches existing Viewer logic: truncated text visually + full metadata
            full_text = entry.get('description', '')
            truncated = (full_text[:100] + "...") if len(full_text) > 100 else full_text
            
            # Format metadata for accessibility
            meta_str = f"Model: {entry.get('model','')}, Prompt: {entry.get('prompt_style','')}"
            
            display_data.append({
                'description': full_text, # Screen reader reads this
                'model': entry.get('model', ''),
                'prompt_style': entry.get('prompt_style', ''),
                'created': entry.get('created', ''),
                'label': truncated # Visual label
            })
            
        self.desc_list.LoadDescriptions(display_data)
        
        if self.entries:
            self.desc_list.SetSelection(0)
            self.on_selection_changed(None)
        else:
            self.clear_details()

    def on_selection_changed(self, event):
        """Handle selection"""
        sel = self.desc_list.GetSelection()
        if sel != wx.NOT_FOUND and sel < len(self.entries):
            entry = self.entries[sel]
            self.show_details(entry)

    def show_details(self, entry):
        """Display details for an entry"""
        # Reconstruct full description with metadata like original format
        description = entry.get('description', '')
        
        # Build metadata footer
        metadata_parts = []
        if entry.get('camera'):
            metadata_parts.append(f"Camera: {entry['camera']}")
        if entry.get('photo_date'):
            metadata_parts.append(f"Photo Date: {entry['photo_date']}")
        if entry.get('model'):
            metadata_parts.append(f"Model: {entry['model']}")
        if entry.get('prompt_style'):
            metadata_parts.append(f"Prompt Style: {entry['prompt_style']}")
        
        # Add metadata footer if available
        if metadata_parts:
            full_text = description + "\n\n" + " | ".join(metadata_parts)
        else:
            full_text = description
        
        self.desc_text.SetValue(full_text)
        
        # Header metadata (filename and model info)
        fname = Path(entry.get('file_path', '')).name
        model = entry.get('model', 'Unknown')
        prompt = entry.get('prompt_style', 'Unknown')
        self.metadata_label.SetLabel(f"{fname}\nModel: {model} | Prompt: {prompt}")
        
        # Image Preview with robust path resolution (only if previews enabled)
        if self.main_window and hasattr(self.main_window, 'show_image_previews') and self.main_window.show_image_previews:
            file_path = entry.get('file_path', '')
            resolved_path = self.resolve_image_path(file_path)
            self.load_image_preview(str(resolved_path))
        else:
            # Clear preview if disabled
            self.image_preview_bitmap = None
            self.image_preview_panel.Refresh()
    
    def resolve_image_path(self, file_path_str):
        """Resolve image path handling relative paths and moved workspaces"""
        path = Path(file_path_str)
        
        # Try original path first
        if path.exists():
            return path
        
        # Try relative to current workflow directory
        if self.current_dir:
            # Try relative to workflow root
            try_rel = self.current_dir / file_path_str
            if try_rel.exists():
                return try_rel
            
            # Try filename in workflow dir
            try_flat = self.current_dir / path.name
            if try_flat.exists():
                return try_flat
            
            # Try common subfolders
            for sub in ['images', 'input_images', 'testimages', 'img']:
                try_sub = self.current_dir / sub / path.name
                if try_sub.exists():
                    return try_sub
        
        # Try workspace source directories (for .idw files)
        if self.workspace_source_dirs:
            filename = path.name
            for source_dir in self.workspace_source_dirs:
                # Try direct filename match
                try_direct = Path(source_dir) / filename
                if try_direct.exists():
                    return try_direct
                
                # Try common subfolders within source directory
                for sub in ['images', 'input_images', 'testimages', 'img', 'photos']:
                    try_sub = Path(source_dir) / sub / filename
                    if try_sub.exists():
                        return try_sub
        
        # Return original path (will fail but at least we tried)
        return path

    def load_image_preview(self, path):
        """Load and scale image for preview"""
        # Skip if previews disabled in main window
        if self.main_window and hasattr(self.main_window, 'show_image_previews') and not self.main_window.show_image_previews:
            return
        
        if not path or not os.path.exists(path):
            # Create a placeholder bitmap with error message
            try:
                w, h = self.image_preview_panel.GetSize()
                if w > 0 and h > 0:
                    # Create a gray placeholder bitmap with text
                    bitmap = wx.Bitmap(w, h)
                    dc = wx.MemoryDC(bitmap)
                    dc.SetBackground(wx.Brush(wx.Colour(220, 220, 220)))
                    dc.Clear()
                    dc.SetTextForeground(wx.Colour(100, 100, 100))
                    dc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                    
                    text = "Image not found" if path else "No image"
                    if path:
                        filename = Path(path).name
                        text_lines = [
                            "Image not found:",
                            filename,
                            "",
                            "Check that the image exists in",
                            "the workspace source directory"
                        ]
                    else:
                        text_lines = ["No image selected"]
                    
                    y_offset = (h - len(text_lines) * 20) // 2
                    for line in text_lines:
                        text_w, text_h = dc.GetTextExtent(line)
                        x = (w - text_w) // 2
                        dc.DrawText(line, x, y_offset)
                        y_offset += 20
                    
                    dc.SelectObject(wx.NullBitmap)
                    self.image_preview_bitmap = bitmap
                else:
                    self.image_preview_bitmap = None
            except:
                self.image_preview_bitmap = None
            
            self.image_preview_panel.Refresh()
            return
            
        try:
            img = wx.Image(path, wx.BITMAP_TYPE_ANY)
            
            # Scale to fit panel
            w, h = self.image_preview_panel.GetSize()
            if w <= 0 or h <= 0: return
            
            img_w, img_h = img.GetWidth(), img.GetHeight()
            
            # Aspect ratio scaling
            ratio = min(w / img_w, h / img_h)
            new_w, new_h = int(img_w * ratio), int(img_h * ratio)
            
            img = img.Scale(new_w, new_h, wx.IMAGE_QUALITY_HIGH)
            self.image_preview_bitmap = wx.Bitmap(img)
            self.image_preview_panel.Refresh()
        except:
            self.image_preview_bitmap = None
            self.image_preview_panel.Refresh()

    def on_paint_preview(self, event):
        """Paint image preview"""
        dc = wx.PaintDC(self.image_preview_panel)
        dc.Clear()
        if self.image_preview_bitmap:
            # Center it
            w, h = self.image_preview_panel.GetSize()
            img_w, img_h = self.image_preview_bitmap.GetSize()
            x = (w - img_w) // 2
            y = (h - img_h) // 2
            dc.DrawBitmap(self.image_preview_bitmap, x, y)
    
    def on_refresh(self, event):
        """Reload current source"""
        if self.current_dir:
            self.load_from_directory(self.current_dir)
        elif self.main_window and hasattr(self.main_window, 'workspace'):
            # Reload from active workspace
            self.load_from_workspace(self.main_window.workspace)

    def on_live_toggle(self, event):
        """Toggle connection to monitor thread"""
        self.is_live = self.live_checkbox.GetValue()
        if self.is_live and self.current_dir:
            if not self.monitor_thread:
                self.monitor_thread = WorkflowMonitor(self, self.current_dir)
                self.monitor_thread.start()
        else:
            if self.monitor_thread:
                self.monitor_thread.stop()
                self.monitor_thread = None

    def on_live_update_event(self, event):
        """Handle background thread update"""
        if self.current_dir:
            # Remember selection
            sel = self.desc_list.GetSelection()
            self.load_from_directory(self.current_dir)
            if sel != wx.NOT_FOUND and sel < self.desc_list.GetCount():
                self.desc_list.SetSelection(sel)

    def on_list_key(self, event):
        """Keyboard navigation support"""
        keycode = event.GetKeyCode()
        
        # Handle Tab traversal explicitly
        if keycode == wx.WXK_TAB and not event.ShiftDown():
            if self.desc_text:
                self.desc_text.SetFocus()
            return
            
        # Pass standard navigation keys to native handler
        event.Skip()

    def clear_details(self):
        self.desc_text.SetValue("")
        self.metadata_label.SetLabel("")
        self.image_preview_bitmap = None
        self.image_preview_panel.Refresh()
    
    def on_copy_text(self, event):
        """Copy description to clipboard"""
        text = self.desc_text.GetValue()
        if text:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text))
                wx.TheClipboard.Close()


"""
Batch Progress Dialog for ImageDescriber

Phase 3: Real-time batch processing progress dialog with pause/resume/stop controls.

This modeless dialog shows:
- Processing statistics (current/total, average time)
- Current image being processed
- Progress bar
- Control buttons (Pause/Resume, Stop, Close)

Accessibility:
- Uses wx.ListBox for single tab stop stats display
- Named controls for screen reader context
- Large click targets for buttons
"""

import wx
from pathlib import Path
from typing import Optional


class BatchProgressDialog(wx.Dialog):
    """Modeless dialog showing batch processing progress and controls"""
    
    def __init__(self, parent, total_images: int):
        """Initialize batch progress dialog
        
        Args:
            parent: Parent window (ImageDescriberFrame)
            total_images: Total number of images to process
        """
        wx.Dialog.__init__(
            self,
            parent,
            title="Batch Processing Progress",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.STAY_ON_TOP  # Modeless, resizable, always visible
        )
        
        self.parent_window = parent
        self.total_images = total_images
        
        # Create UI
        self._create_ui()
        
        # Set initial size
        self.SetSize((500, 350))
        self.CenterOnParent()
    
    def _create_ui(self):
        """Create dialog UI components"""
        # Main panel
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title label
        title_label = wx.StaticText(
            panel,
            label="Processing Statistics:",
            name="Processing statistics title"
        )
        title_font = title_label.GetFont()
        title_font.PointSize += 2
        title_font = title_font.Bold()
        title_label.SetFont(title_font)
        main_sizer.Add(title_label, 0, wx.ALL, 10)
        
        # Stats list box (read-only, single-selection for accessibility)
        # Includes current image as last item for keyboard navigation
        self.stats_list = wx.ListBox(
            panel,
            style=wx.LB_SINGLE,
            name="Processing statistics and current image"
        )
        self.stats_list.SetMinSize((450, 100))
        # Bind key handler to skip separator line during navigation
        self.stats_list.Bind(wx.EVT_KEY_DOWN, self._on_stats_key)
        main_sizer.Add(self.stats_list, 0, wx.ALL | wx.EXPAND, 10)
        
        # Progress label
        progress_label = wx.StaticText(
            panel,
            label="Progress:",
            name="Progress label"
        )
        main_sizer.Add(progress_label, 0, wx.LEFT | wx.RIGHT, 10)
        
        # Progress bar
        self.progress_bar = wx.Gauge(
            panel,
            range=100,
            name="Batch progress percentage"
        )
        self.progress_bar.SetMinSize((-1, 25))
        main_sizer.Add(self.progress_bar, 0, wx.ALL | wx.EXPAND, 10)
        
        # Button sizer
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Pause/Resume button
        self.pause_button = wx.Button(panel, label="Pause", size=(100, -1))
        self.pause_button.Bind(wx.EVT_BUTTON, self.on_pause_clicked)
        button_sizer.Add(self.pause_button, 0, wx.ALL, 5)
        
        # Stop button
        self.stop_button = wx.Button(panel, label="Stop", size=(100, -1))
        self.stop_button.Bind(wx.EVT_BUTTON, self.on_stop_clicked)
        button_sizer.Add(self.stop_button, 0, wx.ALL, 5)
        
        # Close button
        self.close_button = wx.Button(panel, label="Close", size=(100, -1))
        self.close_button.Bind(wx.EVT_BUTTON, lambda e: self.Hide())
        button_sizer.Add(self.close_button, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        # Set panel sizer
        panel.SetSizer(main_sizer)
        
        # Dialog sizer
        dialog_sizer = wx.BoxSizer(wx.VERTICAL)
        dialog_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(dialog_sizer)
    
    def update_progress(self, current: int, total: int, 
                       file_path: str = None, avg_time: float = 0.0,
                       image_name: str = None, provider: str = None, model: str = None):
        """Update progress display
        
        Args:
            current: Current image number (1-based)
            total: Total number of images
            file_path: Path to current image being processed (optional)
            avg_time: Average processing time per image in seconds (optional)
            image_name: Display name override (for video extraction, optional)
            provider: AI provider name (for video extraction, optional)
            model: AI model name (for video extraction, optional)
        """
        # Update stats list (including current image as last item)
        self.stats_list.Clear()
        self.stats_list.Append(f"Items Processed: {current} / {total}")
        
        # Show average time only if available (not during video extraction)
        if avg_time > 0:
            self.stats_list.Append(f"Average Processing Time: {avg_time:.1f} seconds")
        
        # Calculate estimated time remaining
        if avg_time > 0 and current < total:
            remaining_images = total - current
            estimated_seconds = remaining_images * avg_time
            
            # Format time nicely
            if estimated_seconds < 60:
                time_str = f"{estimated_seconds:.0f} seconds"
            elif estimated_seconds < 3600:
                minutes = estimated_seconds / 60
                time_str = f"{minutes:.1f} minutes"
            else:
                hours = estimated_seconds / 3600
                time_str = f"{hours:.1f} hours"
            
            self.stats_list.Append(f"Estimated Time Remaining: {time_str}")
        
        # Add separator line
        self.stats_list.Append("─" * 40)
        # Track separator index for keyboard navigation
        self.separator_index = self.stats_list.GetCount() - 1
        
        # Add current image/video being processed
        if image_name:
            # Video extraction or custom name
            self.stats_list.Append(f"Current: {image_name}")
            if provider and model:
                self.stats_list.Append(f"Provider: {provider}")
                self.stats_list.Append(f"Model: {model}")
        elif file_path:
            # Regular image processing
            filename = Path(file_path).name
            self.stats_list.Append(f"Current Image: {filename}")
        
        # Update progress bar
        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.SetValue(percentage)
        
        # Force refresh
        self.Layout()
    
    def on_pause_clicked(self, event):
        """Toggle pause/resume"""
        if self.pause_button.GetLabel() == "Pause":
            # Call parent's pause handler
            if hasattr(self.parent_window, 'on_pause_batch'):
                self.parent_window.on_pause_batch()
            self.pause_button.SetLabel("Resume")
        else:
            # Call parent's resume handler
            if hasattr(self.parent_window, 'on_resume_batch'):
                self.parent_window.on_resume_batch()
            self.pause_button.SetLabel("Pause")
    
    def on_stop_clicked(self, event):
        """Stop processing"""
        # Import here to avoid circular dependency
        from shared.wx_common import ask_yes_no
        
        # Confirm before stopping
        result = ask_yes_no(
            self,
            "Stop batch processing?\n\n"
            "Progress will be saved. You can resume later by reopening this workspace."
        )
        
        if result:
            # Call parent's stop handler
            if hasattr(self.parent_window, 'on_stop_batch'):
                self.parent_window.on_stop_batch()
    
    def reset_pause_button(self):
        """Reset pause button to 'Pause' state"""
        self.pause_button.SetLabel("Pause")
    
    def _on_stats_key(self, event):
        """Handle keyboard navigation in stats list to skip separator line"""
        keycode = event.GetKeyCode()
        current_selection = self.stats_list.GetSelection()
        
        # Skip separator line when navigating with arrow keys
        if keycode == wx.WXK_DOWN:
            if current_selection != wx.NOT_FOUND:
                next_index = current_selection + 1
                # Skip separator line if next item is separator
                if hasattr(self, 'separator_index') and next_index == self.separator_index:
                    next_index += 1
                # Don't go past last item
                if next_index < self.stats_list.GetCount():
                    self.stats_list.SetSelection(next_index)
                    return  # Don't propagate event
        
        elif keycode == wx.WXK_UP:
            if current_selection != wx.NOT_FOUND:
                prev_index = current_selection - 1
                # Skip separator line if previous item is separator
                if hasattr(self, 'separator_index') and prev_index == self.separator_index:
                    prev_index -= 1
                # Don't go before first item
                if prev_index >= 0:
                    self.stats_list.SetSelection(prev_index)
                    return  # Don't propagate event
        
        # For all other keys, use default behavior
        event.Skip()

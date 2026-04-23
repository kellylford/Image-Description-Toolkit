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

SEP_LINE = "─" * 44  # reused in mark_complete()


class BatchProgressDialog(wx.Dialog):
    """Modeless dialog showing batch processing progress and controls"""
    
    def __init__(self, parent, total_images: int,
                 batch_provider: str = '', batch_model: str = '', batch_prompt: str = ''):
        """Initialize batch progress dialog
        
        Args:
            parent: Parent window (ImageDescriberFrame)
            total_images: Total number of images to process
            batch_provider: AI provider name shown in Job Settings section
            batch_model: AI model name shown in Job Settings section
            batch_prompt: Prompt style shown in Job Settings section
        """
        wx.Dialog.__init__(
            self,
            parent,
            title="Batch Processing Progress",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.STAY_ON_TOP  # Modeless, resizable, always visible
        )
        
        self.parent_window = parent
        self.total_images = total_images
        self.batch_provider = batch_provider
        self.batch_model = batch_model
        self.batch_prompt = batch_prompt
        self._is_complete = False  # Set by mark_complete(); changes Stop→Close

        # Create UI
        self._create_ui()
        
        # Set initial size
        self.SetSize((500, 420))
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
        self.stats_list.SetMinSize((450, 160))
        # Bind key handler to skip separator lines during navigation
        self.stats_list.Bind(wx.EVT_KEY_DOWN, self._on_stats_key)
        # Bind selection-change handler so mouse clicks on separators jump away
        self.stats_list.Bind(wx.EVT_LISTBOX, self._on_stats_selection)
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
                       image_name: str = None, provider: str = None, model: str = None,
                       last_image: str = None, last_description: str = None,
                       token_stats: dict = None,
                       batch_provider: str = None, batch_model: str = None,
                       batch_prompt: str = None):
        """Update progress display
        
        Args:
            current: Current image number (1-based)
            total: Total number of images
            file_path: Path to current image being processed (optional)
            avg_time: Average processing time per image in seconds (optional)
            image_name: Display name override (for video extraction, optional)
            provider: AI provider name (for video extraction, optional)
            model: AI model name (for video extraction, optional)
            last_image: Last image that was described (optional)
            last_description: Full description text of last image (optional, not clipped)
            token_stats: Dict with avg_input, avg_output, avg_total, total,
                         peak_total, peak_name (optional, shown when non-None)
            batch_provider: Override stored batch provider (optional)
            batch_model: Override stored batch model (optional)
            batch_prompt: Override stored batch prompt (optional)
        """
        # Allow callers to update stored batch settings
        if batch_provider is not None:
            self.batch_provider = batch_provider
        if batch_model is not None:
            self.batch_model = batch_model
        if batch_prompt is not None:
            self.batch_prompt = batch_prompt

        # Save selection before clearing so we can restore it after rebuild
        saved_selection = self.stats_list.GetSelection()

        # Track separator row indices for keyboard navigation skip logic
        self.separator_indices = set()

        # Rebuild stats list
        self.stats_list.Clear()

        # ── Processing Progress section ──────────────────────────────────────
        self.stats_list.Append(f"Items Processed:            {current} / {total}")

        if avg_time > 0:
            self.stats_list.Append(f"Average Processing Time:    {avg_time:.1f} seconds")

        if avg_time > 0 and current < total:
            remaining_images = total - current
            estimated_seconds = remaining_images * avg_time
            if estimated_seconds < 60:
                time_str = f"{estimated_seconds:.0f} seconds"
            elif estimated_seconds < 3600:
                time_str = f"{estimated_seconds / 60:.1f} minutes"
            else:
                time_str = f"{estimated_seconds / 3600:.1f} hours"
            self.stats_list.Append(f"Estimated Time Remaining:   {time_str}")

        # ── Separator ────────────────────────────────────────────────────────
        self.stats_list.Append("─" * 44)
        self.separator_indices.add(self.stats_list.GetCount() - 1)

        # ── Job Settings section ─────────────────────────────────────────────
        if self.batch_provider or self.batch_model or self.batch_prompt:
            if self.batch_provider:
                self.stats_list.Append(f"Provider:                   {self.batch_provider.title()}")
            if self.batch_model:
                self.stats_list.Append(f"Model:                      {self.batch_model}")
            if self.batch_prompt:
                self.stats_list.Append(f"Prompt Style:               {self.batch_prompt}")

        # ── Token Usage section (only when data is available) ────────────────
        if token_stats:
            self.stats_list.Append("─" * 44)
            self.separator_indices.add(self.stats_list.GetCount() - 1)
            self.stats_list.Append("Token Usage")
            self.stats_list.Append(f"  Average Input Tokens:     {token_stats['avg_input']:,}")
            self.stats_list.Append(f"  Average Output Tokens:    {token_stats['avg_output']:,}")
            self.stats_list.Append(f"  Average Total Tokens:     {token_stats['avg_total']:,}")
            self.stats_list.Append(f"  Total Tokens:             {token_stats['total']:,}")
            peak_label = f"{token_stats['peak_total']:,} ({token_stats['peak_name']})"
            self.stats_list.Append(f"  Largest Token Use:        {peak_label}")

        # ── Separator ────────────────────────────────────────────────────────
        self.stats_list.Append("─" * 44)
        self.separator_indices.add(self.stats_list.GetCount() - 1)

        # ── Last completed + current image ───────────────────────────────────
        if last_image and last_description:
            self.stats_list.Append(f"Last Image Described:       {last_image}")
            self.stats_list.Append(f"Last Description:           {last_description}")

        if image_name:
            self.stats_list.Append(f"Current:                    {image_name}")
            if provider and model:
                self.stats_list.Append(f"Provider:                   {provider}")
                self.stats_list.Append(f"Model:                      {model}")
        elif file_path:
            self.stats_list.Append(f"Current Image:              {Path(file_path).name}")

        # Update progress bar
        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.SetValue(percentage)

        # Restore the previously selected row (skip separators if needed)
        count = self.stats_list.GetCount()
        if saved_selection != wx.NOT_FOUND and count > 0:
            idx = min(saved_selection, count - 1)
            # Scan forward past any separator, then backward if still on one
            while idx < count - 1 and idx in self.separator_indices:
                idx += 1
            while idx > 0 and idx in self.separator_indices:
                idx -= 1
            if idx not in self.separator_indices:
                self.stats_list.SetSelection(idx)
                self.stats_list.EnsureVisible(idx)

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
        """Stop processing — or close the dialog when batch is already complete."""
        if self._is_complete:
            self.Destroy()
            return

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

    def mark_complete(self, summary: str = ""):
        """
        Called when batch processing finishes naturally — keeps dialog open
        so the user can review stats before dismissing.

        Changes Pause→disabled, Stop→Close, updates title to show completion.
        """
        self._is_complete = True

        # Append completion notice to the live stats list
        self.stats_list.Append(SEP_LINE)
        self.separator_indices.add(self.stats_list.GetCount() - 1)
        self.stats_list.Append("\u2713  Batch Complete!")
        if summary:
            self.stats_list.Append(f"     {summary}")
        self.stats_list.EnsureVisible(self.stats_list.GetCount() - 1)

        # Fill progress bar
        self.progress_bar.SetValue(100)

        # Update controls
        self.pause_button.SetLabel("Pause")
        self.pause_button.Enable(False)
        self.stop_button.SetLabel("Close")
        self.stop_button.Enable(True)

        # Hide the redundant original Close button (Stop is now the only Close)
        self.close_button.Hide()
        self.Layout()

        # Update window title so screen readers announce completion
        self.SetTitle("Batch Complete  —  Review stats then close")
    
    def reset_pause_button(self):
        """Reset pause button to 'Pause' state"""
        self.pause_button.SetLabel("Pause")
    
    def _on_stats_selection(self, event):
        """Prevent separator lines from holding keyboard/mouse selection.

        wx.EVT_LISTBOX fires on every selection change (arrow key, mouse click,
        or programmatic SetSelection). If the newly selected index is a
        separator, move focus to the nearest selectable item instead.
        """
        idx = self.stats_list.GetSelection()
        separators = getattr(self, 'separator_indices', set())
        if idx == wx.NOT_FOUND or idx not in separators:
            event.Skip()
            return

        count = self.stats_list.GetCount()
        # Try moving forward first, then backward
        for delta, rng in [(1, range(idx + 1, count)), (-1, range(idx - 1, -1, -1))]:
            for candidate in rng:
                if candidate not in separators:
                    self.stats_list.SetSelection(candidate)
                    return

        # No selectable item at all — deselect
        self.stats_list.SetSelection(wx.NOT_FOUND)

    def _on_stats_key(self, event):
        """Handle keyboard navigation in stats list to skip all separator lines"""
        keycode = event.GetKeyCode()
        current_selection = self.stats_list.GetSelection()
        separators = getattr(self, 'separator_indices', set())

        if keycode == wx.WXK_DOWN:
            if current_selection != wx.NOT_FOUND:
                next_index = current_selection + 1
                # Advance past any consecutive separators
                while next_index in separators and next_index < self.stats_list.GetCount():
                    next_index += 1
                if next_index < self.stats_list.GetCount():
                    self.stats_list.SetSelection(next_index)
                    return

        elif keycode == wx.WXK_UP:
            if current_selection != wx.NOT_FOUND:
                prev_index = current_selection - 1
                # Step back past any consecutive separators
                while prev_index in separators and prev_index >= 0:
                    prev_index -= 1
                if prev_index >= 0:
                    self.stats_list.SetSelection(prev_index)
                    return

        event.Skip()

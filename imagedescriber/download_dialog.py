#!/usr/bin/env python3
"""
Download Settings Dialog for ImageDescriber

Provides a dialog for configuring web image download settings.
"""

import wx
import re
from pathlib import Path


class DownloadSettingsDialog(wx.Dialog):
    """
    Dialog for configuring web image download settings.
    
    Allows users to specify:
    - URL to download from
    - Minimum image dimensions
    - Maximum number of images
    - Auto-add to workspace option
    """
    
    def __init__(self, parent, url: str = ""):
        """
        Initialize download settings dialog.
        
        Args:
            parent: Parent window
            url: Optional pre-filled URL
        """
        super().__init__(parent, title="Download Images From URL",
                        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        
        self.SetSize((550, 400))
        
        # Create main panel
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(panel, label="Download Images From Web Page")
        title_font = title.GetFont()
        title_font.PointSize += 2
        title_font = title_font.Bold()
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # URL input
        url_label = wx.StaticText(panel, label="&URL:")
        main_sizer.Add(url_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        self.url_input = wx.TextCtrl(panel, value=url, name="URL input field")
        main_sizer.Add(self.url_input, 0, wx.ALL | wx.EXPAND, 10)
        
        # Settings group
        settings_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Download Settings")
        
        # Minimum size
        size_sizer = wx.BoxSizer(wx.HORIZONTAL)
        size_label = wx.StaticText(panel, label="Minimum image size:")
        size_sizer.Add(size_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        self.min_width = wx.SpinCtrl(panel, value="0", min=0, max=10000,
                                      name="Minimum width")
        size_sizer.Add(self.min_width, 0, wx.RIGHT, 5)
        size_sizer.Add(wx.StaticText(panel, label="×"), 0, 
                      wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        self.min_height = wx.SpinCtrl(panel, value="0", min=0, max=10000,
                                       name="Minimum height")
        size_sizer.Add(self.min_height, 0, wx.RIGHT, 5)
        size_sizer.Add(wx.StaticText(panel, label="pixels"), 0,
                      wx.ALIGN_CENTER_VERTICAL)
        
        settings_box.Add(size_sizer, 0, wx.ALL, 10)
        
        # Maximum images
        max_sizer = wx.BoxSizer(wx.HORIZONTAL)
        max_label = wx.StaticText(panel, label="Maximum images to download:")
        max_sizer.Add(max_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        self.max_images = wx.SpinCtrl(panel, value="100", min=-1, max=10000,
                                       name="Maximum images")
        max_sizer.Add(self.max_images, 0, wx.RIGHT, 5)
        max_sizer.Add(wx.StaticText(panel, label="(-1 for unlimited)"), 0,
                     wx.ALIGN_CENTER_VERTICAL)
        
        settings_box.Add(max_sizer, 0, wx.ALL, 10)
        
        # Process after download checkbox
        self.process_after = wx.CheckBox(panel,
                                        label="&Process images after download",
                                        name="Process after download checkbox")
        self.process_after.SetValue(True)
        settings_box.Add(self.process_after, 0, wx.ALL, 10)
        
        main_sizer.Add(settings_box, 0, wx.ALL | wx.EXPAND, 10)
        
        # Help text
        help_text = wx.StaticText(panel, 
            label="This will download all images found on the web page.\n"
                  "Images are parsed from <img> tags and linked image files.\n"
                  "Duplicate images (by content hash) are automatically skipped.")
        help_text.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        main_sizer.Add(help_text, 0, wx.ALL, 10)
        
        # Buttons
        button_sizer = wx.StdDialogButtonSizer()
        
        ok_btn = wx.Button(panel, wx.ID_OK)
        ok_btn.SetDefault()
        button_sizer.AddButton(ok_btn)
        
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        button_sizer.AddButton(cancel_btn)
        
        button_sizer.Realize()
        main_sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        
        panel.SetSizer(main_sizer)
        
        # Bind events
        ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        
        # Set focus to URL field
        wx.CallAfter(self.url_input.SetFocus)
    
    def on_ok(self, event):
        """Validate settings before accepting."""
        url = self.url_input.GetValue().strip()
        
        # Validate URL
        if not url:
            wx.MessageBox("Please enter a URL.", "Invalid URL",
                         wx.OK | wx.ICON_WARNING, self)
            self.url_input.SetFocus()
            return
        
        # Smart URL normalization - add https:// if missing (like CLI does)
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            self.url_input.SetValue(url)  # Update the display
        
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            wx.MessageBox(
                "Please enter a valid URL.",
                "Invalid URL Format",
                wx.OK | wx.ICON_WARNING, self)
            self.url_input.SetFocus()
            return
        
        # Accept dialog
        self.EndModal(wx.ID_OK)
    
    def get_settings(self) -> dict:
        """
        Get download settings from dialog.
        
        Returns:
            dict with keys: url, min_width, min_height, max_images, process_after
        """
        max_imgs = self.max_images.GetValue()
        if max_imgs == -1:
            max_imgs = None  # Unlimited
        
        return {
            'url': self.url_input.GetValue().strip(),
            'min_width': self.min_width.GetValue(),
            'min_height': self.min_height.GetValue(),
            'max_images': max_imgs,
            'process_after': self.process_after.GetValue()
        }

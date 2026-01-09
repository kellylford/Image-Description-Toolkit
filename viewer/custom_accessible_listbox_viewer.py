"""
Drop-in replacement for wx.ListBox in your viewer_wx.py
Provides full descriptions to screen readers while showing truncated text visually
"""

import wx


class AccessibleDescriptionListBox(wx.Accessible):
    """Custom accessible object that provides full descriptions to screen readers"""
    
    def __init__(self, listbox, descriptions):
        super().__init__()
        self.listbox = listbox
        self.descriptions = descriptions  # Reference to the full descriptions list
    
    def GetName(self, childId):
        """Override to return full description text for screen readers"""
        if childId == wx.ACC_SELF:
            # Return the listbox label itself
            return wx.ACC_OK, "Image Descriptions"
        
        # childId is 1-based for list items
        if childId > 0 and childId <= len(self.descriptions):
            idx = childId - 1
            entry = self.descriptions[idx]
            
            # Build full accessible string with all metadata
            full_text = entry.get('description', '')
            filename = entry.get('filename', '')
            
            # Return filename + full description for screen readers
            accessible_text = f"{filename}. {full_text}"
            return wx.ACC_OK, accessible_text
        
        return wx.ACC_NOT_IMPLEMENTED, ""
    
    def GetValue(self, childId):
        """Return full description as value"""
        if childId > 0 and childId <= len(self.descriptions):
            idx = childId - 1
            return wx.ACC_OK, self.descriptions[idx].get('description', '')
        return wx.ACC_NOT_IMPLEMENTED, ""
    
    def GetDescription(self, childId):
        """Return full description"""
        if childId > 0 and childId <= len(self.descriptions):
            idx = childId - 1
            return wx.ACC_OK, self.descriptions[idx].get('description', '')
        return wx.ACC_NOT_IMPLEMENTED, ""


class DescriptionListBox(wx.ListBox):
    """
    Custom ListBox for image descriptions that shows truncated text visually
    but provides full descriptions to screen readers.
    
    Drop-in replacement for wx.ListBox in viewer_wx.py
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.descriptions = []  # Will hold references to full description dicts
        self.custom_accessible = None
    
    def LoadDescriptions(self, descriptions_list):
        """
        Load descriptions and setup custom accessibility.
        
        Args:
            descriptions_list: List of description dicts from viewer_wx.py
                             Each dict has 'description', 'filename', etc.
        """
        self.Clear()
        self.descriptions = descriptions_list
        
        # Add items with truncated text for visual display
        for entry in descriptions_list:
            description = entry.get('description', '')
            # Truncate to 100 chars for display (matching viewer_wx.py)
            truncated = description[:100] + ("..." if len(description) > 100 else "")
            self.Append(truncated)
        
        # Create custom accessible that provides full text
        self.custom_accessible = AccessibleDescriptionListBox(self, self.descriptions)
        self.SetAccessible(self.custom_accessible)
    
    def GetFullDescription(self, index):
        """Get the full description dict for an item"""
        if 0 <= index < len(self.descriptions):
            return self.descriptions[index]
        return {}


# INSTRUCTIONS FOR INTEGRATING INTO viewer_wx.py:
# ================================================
# 
# 1. Add this import at the top of viewer_wx.py:
#    from custom_accessible_listbox_viewer import DescriptionListBox
# 
# 2. In __init__ method, change this line:
#    OLD: self.desc_list = wx.ListBox(left_panel, style=wx.LB_SINGLE)
#    NEW: self.desc_list = DescriptionListBox(left_panel, style=wx.LB_SINGLE)
# 
# 3. In load_descriptions method, replace the list population code:
#    
#    OLD CODE:
#    --------
#    self.desc_list.Clear()
#    for i, entry in enumerate(entries):
#        description = entry.get('description', '')
#        truncated = description[:100] + ("..." if len(description) > 100 else "")
#        self.desc_list.Append(truncated)
#    
#    NEW CODE:
#    --------
#    self.desc_list.LoadDescriptions(entries)
# 
# That's it! Now screen readers will announce full descriptions while
# the list shows truncated text visually.

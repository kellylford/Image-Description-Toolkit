"""
UI Components for Image Describer

This module contains custom UI components with enhanced accessibility support.
"""

from PyQt6.QtWidgets import QTreeWidget, QLineEdit, QPlainTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator, QDoubleValidator


class AccessibleTreeWidget(QTreeWidget):
    """Enhanced QTreeWidget with better accessibility support"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccessibilityMode(True)
    
    def setAccessibilityMode(self, enabled=True):
        """Enable enhanced accessibility features"""
        if enabled:
            # Ensure proper focus policy
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            
            # Enable better keyboard navigation
            self.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
            self.setUniformRowHeights(True)
            
            # Connect to selection changes for better announcements
            self.itemSelectionChanged.connect(self._announce_selection)
            
            # Connect to expand/collapse signals for state announcements
            self.itemExpanded.connect(self._announce_expanded)
            self.itemCollapsed.connect(self._announce_collapsed)
    
    def _announce_selection(self):
        """Provide enhanced announcements for screen readers"""
        current = self.currentItem()
        if current:
            # Get accessible description from the item
            accessible_desc = current.data(0, Qt.ItemDataRole.AccessibleDescriptionRole)
            if accessible_desc:
                # Set it as the widget's accessible description for immediate announcement
                self.setAccessibleDescription(f"Selected: {accessible_desc}")

    def _announce_expanded(self, item):
        """Provide announcement when an item is expanded."""
        if item:
            original_desc = item.data(0, Qt.ItemDataRole.AccessibleDescriptionRole) or item.text(0)
            # Clean up any previous state text
            if original_desc.startswith("Collapsed: "):
                original_desc = original_desc[11:]
            elif original_desc.startswith("Expanded: "):
                original_desc = original_desc[10:]
            
            # Prepend state to the description
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, f"Expanded: {original_desc}")
            # Announce the change more forcefully by also updating the widget's description
            child_count = item.childCount()
            if child_count > 0:
                self.setAccessibleDescription(f"{original_desc} expanded, {child_count} items visible")
            else:
                self.setAccessibleDescription(f"{original_desc} expanded")

    def _announce_collapsed(self, item):
        """Provide announcement when an item is collapsed."""
        if item:
            original_desc = item.data(0, Qt.ItemDataRole.AccessibleDescriptionRole) or item.text(0)
            # Clean up previous state text before adding the new one
            if original_desc.startswith("Expanded: "):
                original_desc = original_desc[10:]
            elif original_desc.startswith("Collapsed: "):
                original_desc = original_desc[11:]
            
            # Prepend state to the description
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, f"Collapsed: {original_desc}")
            # Announce the change with additional context
            child_count = item.childCount()
            if child_count > 0:
                self.setAccessibleDescription(f"{original_desc} collapsed, {child_count} items hidden")
            else:
                self.setAccessibleDescription(f"{original_desc} collapsed")

    def keyPressEvent(self, event):
        """Override to handle keyboard navigation for accessibility"""
        current = self.currentItem()
        
        if current and event.key() == Qt.Key.Key_Space:
            # Space bar toggles expand/collapse
            if current.childCount() > 0:
                if self.isItemExpanded(current):
                    self.collapseItem(current)
                else:
                    self.expandItem(current)
                event.accept()
                return
        elif current and event.key() == Qt.Key.Key_Return:
            # Enter key also toggles expand/collapse (alternative to space)
            if current.childCount() > 0:
                if self.isItemExpanded(current):
                    self.collapseItem(current)
                else:
                    self.expandItem(current)
                event.accept()
                return
        
        # For all other keys, use default behavior
        super().keyPressEvent(event)


class AccessibleNumericInput(QLineEdit):
    """Accessible numeric input that replaces QSpinBox/QDoubleSpinBox"""
    
    def __init__(self, parent=None, is_integer=False, minimum=None, maximum=None, suffix=""):
        super().__init__(parent)
        self.is_integer = is_integer
        self.suffix = suffix
        self._setup_validation(minimum, maximum)
        self._setup_accessibility()
        
    def _setup_validation(self, minimum, maximum):
        """Setup input validation"""
        if self.is_integer:
            validator = QIntValidator()
            if minimum is not None:
                validator.setBottom(int(minimum))
            if maximum is not None:
                validator.setTop(int(maximum))
        else:
            validator = QDoubleValidator()
            if minimum is not None:
                validator.setBottom(minimum)
            if maximum is not None:
                validator.setTop(maximum)
            validator.setDecimals(2)
        
        self.setValidator(validator)
        
    def _setup_accessibility(self):
        """Setup accessibility features"""
        # Improve focus policy and keyboard handling
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Add placeholder text to help users understand the format
        if self.is_integer:
            self.setPlaceholderText(f"Enter number{self.suffix}")
        else:
            self.setPlaceholderText(f"Enter decimal number{self.suffix}")
    
    def setValue(self, value):
        """Set the numeric value"""
        if self.is_integer:
            self.setText(str(int(value)))
        else:
            self.setText(f"{value:.1f}")
    
    def value(self):
        """Get the numeric value"""
        text = self.text()
        if not text:
            return 0.0 if not self.is_integer else 0
        
        try:
            if self.is_integer:
                return int(text)
            else:
                return float(text)
        except ValueError:
            return 0.0 if not self.is_integer else 0


class AccessibleTextEdit(QPlainTextEdit):
    """Text edit with proper Tab key handling for accessibility"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_accessibility()
    
    def _setup_accessibility(self):
        """Setup accessibility and keyboard handling"""
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def keyPressEvent(self, event):
        """Override to handle Tab key properly for accessibility"""
        if event.key() == Qt.Key.Key_Tab:
            # Tab should move to next widget, not insert tab character
            # Use the parent widget's focus navigation
            parent = self.parent()
            if parent:
                parent.focusNextPrevChild(True)  # True = forward
            else:
                self.focusNextChild()
            event.accept()
        elif event.key() == Qt.Key.Key_Backtab:
            # Shift+Tab should move to previous widget
            parent = self.parent()
            if parent:
                parent.focusNextPrevChild(False)  # False = backward
            else:
                self.focusPreviousChild()
            event.accept()
        else:
            # For all other keys, use default behavior
            super().keyPressEvent(event)
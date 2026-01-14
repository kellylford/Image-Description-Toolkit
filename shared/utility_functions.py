"""
Shared utility functions for IDT applications.

This module consolidates common utility functions used across multiple applications
to reduce code duplication and improve maintainability.

Functions:
    - sanitize_name(): Convert strings to filesystem-safe names
    - format_timestamp_standard(): Format timestamps to M/D/YYYY H:MMP format
"""

import re
from typing import Optional
from datetime import datetime


def sanitize_name(name: str, preserve_case: bool = True) -> str:
    """Convert strings to filesystem-safe names.
    
    This function removes or replaces characters that are invalid in filenames
    across different platforms while preserving alphanumeric characters and
    common separators.
    
    Removes: All characters except letters, numbers, underscore, hyphen, period
    Replaces: Nothing (removes non-allowed characters)
    Preserves: Case by default, can lowercase if needed
    
    This function is used to sanitize:
    - Model names (e.g., "GPT-4 Vision" → "GPT-4Vision")
    - Provider names (e.g., "OpenAI (API)" → "OpenAIAPI")
    - Prompt style names
    - Custom workflow names
    
    Args:
        name: The string to sanitize
        preserve_case: If True, preserve the original case. If False, convert to lowercase.
                      Default: True
    
    Returns:
        Sanitized string safe for filesystem use. Returns "unknown" if input is empty
        after sanitization.
        
    Examples:
        >>> sanitize_name("GPT-4 Vision")
        'GPT-4Vision'
        >>> sanitize_name("GPT-4 Vision", preserve_case=False)
        'gpt-4vision'
        >>> sanitize_name("Model (v2.1)")
        'Modelv2.1'
        >>> sanitize_name("")
        'unknown'
        >>> sanitize_name("OpenAI:API/Key")
        'OpenAIAPIKey'
    
    Raises:
        None - Function handles all input gracefully
    
    Notes:
        - Empty strings after sanitization return "unknown"
        - The function removes spaces entirely (doesn't replace with underscores)
        - Common abbreviations and version numbers are preserved (e.g., "GPT-4")
        - This behavior is tested extensively in pytest_tests/unit/test_sanitization.py
    """
    if not name:
        return "unknown"
    
    # Remove characters that are not letters, numbers, underscore, hyphen, or dot
    # Spaces and punctuation are removed (not replaced) to match expected behavior
    safe_name = re.sub(r'[^A-Za-z0-9_\-.]', '', str(name))
    
    # Convert to lowercase unless case preservation is requested
    return safe_name if preserve_case else safe_name.lower()


def sanitize_filename(filename: str, preserve_case: bool = True) -> str:
    """Remove invalid characters from filename for cross-platform compatibility.
    
    This function removes characters that are invalid in filenames across different
    platforms including Windows, macOS, and Linux.
    
    Removes: Windows invalid chars (< > : " / \\ | ? *) + control characters
    Replaces: Whitespace with empty string
    Preserves: Alphanumeric, underscore, hyphen, period
    
    Args:
        filename: Filename to sanitize
        preserve_case: If True, preserve case; if False, lowercase. Default: True
        
    Returns:
        Sanitized filename. Returns "file" if input becomes empty after sanitization.
        
    Example:
        >>> sanitize_filename("My File: (1).txt")
        'MyFile1.txt'
    """
    # Remove invalid characters from different platforms
    # Windows: < > : " / \ | ? *
    # All platforms: control characters
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    
    # Replace spaces and other whitespace with nothing
    cleaned = re.sub(r'\s+', '', cleaned)
    
    # Remove any remaining non-alphanumeric except . - _
    cleaned = re.sub(r'[^a-zA-Z0-9._-]', '', cleaned)
    
    if not preserve_case:
        cleaned = cleaned.lower()
    
    # Ensure not empty
    if not cleaned:
        cleaned = "file"
    
    return cleaned


def format_timestamp_standard(timestamp_input: Optional[datetime] = None) -> str:
    """Format datetime to M/D/YYYY H:MMP format (no leading zeros).
    
    This function provides a standardized timestamp format used throughout IDT
    for display in window titles, logs, and UI elements.
    
    Format: M/D/YYYY H:MMP (example: "3/25/2025 7:35P", "10/16/2025 8:03A")
    Features:
    - No leading zeros on month, day, or hour
    - Uppercase A/P suffix for AM/PM
    - 12-hour format (not 24-hour)
    
    Args:
        timestamp_input: datetime object to format. If None, uses current time.
                        Default: None
    
    Returns:
        Formatted timestamp string in M/D/YYYY H:MMP format
        
    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 3, 25, 7, 35, 0)
        >>> format_timestamp_standard(dt)
        '3/25/2025 7:35P'
        >>> dt2 = datetime(2025, 10, 16, 8, 3, 0)
        >>> format_timestamp_standard(dt2)
        '10/16/2025 8:03A'
        >>> format_timestamp_standard()  # Current time
        '1/14/2026 2:30P'
    
    Notes:
        - Used throughout IDT for consistent timestamp display
        - Matches format used in window titles and workflow metadata
        - Replaces the format_timestamp() function from wx_common.py for core utility
    """
    if timestamp_input is None:
        timestamp_input = datetime.now()
    
    # Format: M/D/YYYY H:MMP (no leading zeros)
    # Use %-m, %-d on Unix, %#m, %#d on Windows (Python handles this automatically)
    month = timestamp_input.month
    day = timestamp_input.day
    year = timestamp_input.year
    
    # Get hour (1-12 for 12-hour format)
    hour = timestamp_input.hour
    if hour == 0:
        hour = 12
    elif hour > 12:
        hour -= 12
    
    minute = timestamp_input.minute
    am_pm = "A" if timestamp_input.hour < 12 else "P"
    
    return f"{month}/{day}/{year} {hour}:{minute:02d}{am_pm}"

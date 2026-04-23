"""
Window Title Builder Module

Provides standardized window title building for IDT applications.
Used for both console windows and GUI applications to display:
- Progress percentage and image counts
- Workflow context (name, prompt style, model)
- Operation type (Describing, Extracting, etc.)
- Optional status suffixes (error, validation, etc.)

Examples:
    >>> title = build_window_title(
    ...     progress_percent=50,
    ...     current=5,
    ...     total=10,
    ...     operation="Describing Images",
    ...     suffix=" - Processing"
    ... )
    >>> print(title)
    IDT - Describing Images (50%, 5 of 10) - Processing

    >>> title = build_window_title(
    ...     progress_percent=0,
    ...     current=0,
    ...     total=0,
    ...     operation="Extracting Video Frames"
    ... )
    >>> print(title)
    IDT - Extracting Video Frames (0%, 0 of 0)

    >>> title = build_window_title(
    ...     progress_percent=100,
    ...     current=20,
    ...     total=20,
    ...     operation="Describing Images",
    ...     context_parts=["my_workflow", "detailed", "gpt-4o"],
    ...     suffix=" - Complete"
    ... )
    >>> print(title)
    IDT - Describing Images (100%, 20 of 20) - Complete - my_workflow - detailed - gpt-4o
"""

from typing import List, Optional


def build_window_title(
    progress_percent: int,
    current: int,
    total: int,
    operation: str = "Processing",
    context_parts: Optional[List[str]] = None,
    suffix: str = ""
) -> str:
    """
    Build a standardized window title for IDT applications.

    Constructs a window title showing progress statistics and workflow context.
    Used for both console window titles (Windows) and GUI application titles.

    Args:
        progress_percent: Progress as integer percentage (0-100)
        current: Current item count
        total: Total item count
        operation: Operation description (e.g., "Describing Images", "Extracting Video Frames")
        context_parts: Optional list of context strings to append (e.g., [workflow_name, prompt_style, model_name])
        suffix: Optional suffix to append (e.g., " - Skipped", " - Validation Failed", " - Complete")

    Returns:
        Formatted window title string following pattern:
        "IDT - {operation} ({progress}%, {current} of {total})[suffix][ - {context_parts}]"

    Examples:
        >>> build_window_title(50, 5, 10, "Describing Images")
        'IDT - Describing Images (50%, 5 of 10)'

        >>> build_window_title(50, 5, 10, "Describing Images", ["my_workflow"])
        'IDT - Describing Images (50%, 5 of 10) - my_workflow'

        >>> build_window_title(50, 5, 10, "Describing Images", ["wf", "detailed", "gpt-4o"], " - Live")
        'IDT - Describing Images (50%, 5 of 10) - Live - wf - detailed - gpt-4o'
    """
    # Build base progress title
    base_title = f"IDT - {operation} ({progress_percent}%, {current} of {total})"

    # Add suffix if provided (e.g., " - Skipped", " - Validation Failed")
    if suffix:
        base_title += suffix

    # Add workflow context parts if provided
    if context_parts:
        # Filter out empty strings and None values
        valid_parts = [str(part).strip() for part in context_parts if part]
        if valid_parts:
            base_title += f" - {' - '.join(valid_parts)}"

    return base_title


def build_window_title_from_context(
    progress_percent: int,
    current: int,
    total: int,
    operation: str,
    workflow_name: Optional[str] = None,
    prompt_style: Optional[str] = None,
    model_name: Optional[str] = None,
    suffix: str = ""
) -> str:
    """
    Build a standardized window title with explicit context parameters.

    Convenience function for building titles when context is provided as separate parameters
    rather than as a list.

    Args:
        progress_percent: Progress as integer percentage (0-100)
        current: Current item count
        total: Total item count
        operation: Operation description (e.g., "Describing Images")
        workflow_name: Optional workflow name to display
        prompt_style: Optional prompt style to display
        model_name: Optional model name to display
        suffix: Optional suffix to append (e.g., " - Complete")

    Returns:
        Formatted window title string

    Examples:
        >>> build_window_title_from_context(
        ...     50, 5, 10, "Describing Images",
        ...     workflow_name="my_workflow",
        ...     prompt_style="detailed",
        ...     model_name="gpt-4o"
        ... )
        'IDT - Describing Images (50%, 5 of 10) - my_workflow - detailed - gpt-4o'
    """
    # Collect context parts, filtering out None/empty values
    context_parts = []
    for part in [workflow_name, prompt_style, model_name]:
        if part:
            context_parts.append(part)

    return build_window_title(
        progress_percent=progress_percent,
        current=current,
        total=total,
        operation=operation,
        context_parts=context_parts if context_parts else None,
        suffix=suffix
    )

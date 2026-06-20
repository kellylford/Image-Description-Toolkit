"""
idt_core — Image Description Toolkit engine

Public API surface for use by CLI and future GUI integration.
"""
from .project import Project
from .pipeline import Pipeline, RunOptions, PipelineEvent, WorkspacePipeline, WorkspaceEvent
from .image_item import ImageItem, Description
from .scanner import scan_images, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from .config import UserConfig, BUILT_IN_PROMPTS, DEFAULT_PROMPT_NAME
from .metadata import MetadataExtractor, NominatimGeocoder, ImageMetadata
from .downloader import Downloader, DownloadResult
from .video import VideoExtractor, VideoExtractionOptions, VideoExtractionResult, scan_videos
from .embedder import Embedder, embed_image_file
from .exporter import (
    export_html, export_csv, export_txt,
    export_workspace_html, export_workspace_csv, export_workspace_txt,
)
from .progress import Progress
from .workspace import Workspace, WorkspaceItem, WorkspaceDescription, BUNDLE_EXT
from .gui_bridge import gui_workspace_to_bundle, bundle_to_gui_workspace_dict

__version__ = "4.5.0"

__all__ = [
    "Project",
    "Pipeline", "RunOptions", "PipelineEvent",
    "WorkspacePipeline", "WorkspaceEvent",
    "ImageItem", "Description",
    "scan_images", "scan_videos", "IMAGE_EXTENSIONS", "VIDEO_EXTENSIONS",
    "UserConfig", "BUILT_IN_PROMPTS", "DEFAULT_PROMPT_NAME",
    "MetadataExtractor", "NominatimGeocoder", "ImageMetadata",
    "Downloader", "DownloadResult",
    "VideoExtractor", "VideoExtractionOptions", "VideoExtractionResult",
    "Embedder", "embed_image_file",
    "export_html", "export_csv", "export_txt",
    "export_workspace_html", "export_workspace_csv", "export_workspace_txt",
    "Progress",
    "Workspace", "WorkspaceItem", "WorkspaceDescription", "BUNDLE_EXT",
    "gui_workspace_to_bundle", "bundle_to_gui_workspace_dict",
]

#!/usr/bin/env python3
"""
Embed AI-generated descriptions into image file metadata.

Supports two sources:
  - CLI workflow directory (reads image_descriptions.txt + file_path_mapping.json)
  - GUI workspace dict (reads ImageItem data from deserialized .idw JSON)

Two write modes:
  - Copy mode (default): copies each original to output_dir, embeds into the copy
  - In-place mode: embeds directly into the original file

Usage:
    python embed_descriptions.py <workflow_dir> [--output-dir <dir>] [--in-place] [--dry-run]
"""

import argparse
import json
import logging
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    from exif_embedder import ExifEmbedder, UnsupportedFormatError
except ImportError:
    from scripts.exif_embedder import ExifEmbedder, UnsupportedFormatError

try:
    from descriptions_to_html import DescriptionsParser
except ImportError:
    from scripts.descriptions_to_html import DescriptionsParser

# idt_core provides better embedding (EXIF + XMP dc:description) when available.
# Falls back to the piexif-only ExifEmbedder otherwise.
try:
    from idt_core.embedder import embed_image_file as _idt_embed_image_file
except ImportError:
    _idt_embed_image_file = None

logger = logging.getLogger(__name__)

HEIC_SUFFIXES = {'.heic', '.heif'}


@dataclass
class EmbedResult:
    embedded: int = 0
    skipped_format: List[str] = field(default_factory=list)
    skipped_no_original: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False

    @property
    def total_attempted(self):
        return self.embedded + len(self.skipped_format) + len(self.skipped_no_original) + len(self.errors)

    def summary(self) -> str:
        prefix = "[DRY RUN] Would have embedded" if self.dry_run else "Embedded"
        lines = [f"{prefix} {self.embedded} image(s)."]
        if self.skipped_format:
            lines.append(f"  Skipped (unsupported format): {len(self.skipped_format)}")
        if self.skipped_no_original:
            lines.append(f"  Skipped (original not found): {len(self.skipped_no_original)}")
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
        return '\n'.join(lines)


class EmbedDescriptions:
    """Embed AI descriptions from IDT workflow or workspace into image metadata."""

    def embed_from_workflow_dir(self, workflow_dir: Path, output_dir: Optional[Path] = None,
                                in_place: bool = False, dry_run: bool = False) -> EmbedResult:
        """
        Embed descriptions from a completed workflow directory into images.

        Reads descriptions/image_descriptions.txt and descriptions/file_path_mapping.json
        to locate and embed descriptions into true original image files.

        Args:
            workflow_dir: Path to the wf_* workflow output directory.
            output_dir: Where to write embedded copies (copy mode). Defaults to
                        workflow_dir/embedded_images/. Ignored when in_place=True.
            in_place: If True, embed directly into original files (modifies originals).
            dry_run: Report what would happen without writing anything.

        Returns:
            EmbedResult with counts and skipped/error lists.
        """
        workflow_dir = Path(workflow_dir)
        result = EmbedResult(dry_run=dry_run)

        descriptions_file = workflow_dir / 'descriptions' / 'image_descriptions.txt'
        mapping_file = workflow_dir / 'descriptions' / 'file_path_mapping.json'

        if not descriptions_file.exists():
            raise FileNotFoundError(f"Descriptions file not found: {descriptions_file}")

        # Parse descriptions
        parser = DescriptionsParser(descriptions_file)
        entries = parser.parse()
        if not entries:
            logger.warning("No description entries found in %s", descriptions_file)
            return result

        # Load file path mapping (maps relative temp path → absolute original path)
        path_mapping: Dict[str, str] = {}
        basename_mapping: Dict[str, str] = {}
        if mapping_file.exists():
            with open(mapping_file, 'r', encoding='utf-8') as f:
                path_mapping = json.load(f)
            for rel_key, orig_path in path_mapping.items():
                basename_mapping[Path(rel_key).name] = orig_path
        else:
            logger.warning("file_path_mapping.json not found; will use Path: field as fallback")

        if not in_place:
            if output_dir is None:
                output_dir = workflow_dir / 'embedded_images'
            if not dry_run:
                output_dir.mkdir(parents=True, exist_ok=True)

        embedder = ExifEmbedder()

        for entry in entries:
            if not entry.description:
                continue

            # Resolve original path from mapping
            original_path = self._resolve_original(
                entry.filename, entry.filepath, path_mapping, basename_mapping
            )

            if original_path is None:
                logger.warning("Could not resolve original for: %s", entry.filename)
                result.skipped_no_original.append(entry.filename)
                continue

            orig = Path(original_path)
            if not orig.exists():
                logger.warning("Original file not found on disk: %s", orig)
                result.skipped_no_original.append(str(orig))
                continue

            self._embed_one(
                orig, entry.description, entry.model, entry.timestamp,
                output_dir, in_place, dry_run, embedder, result
            )

        return result

    def embed_from_workspace(self, workspace_data: dict, output_dir: Optional[Path] = None,
                             in_place: bool = False, dry_run: bool = False) -> EmbedResult:
        """
        Embed descriptions from a deserialized ImageDescriber workspace (.idw) into images.

        ImageItem.file_path is the true original on-disk path. Uses the most recent
        description for each image.

        Args:
            workspace_data: Deserialized workspace dict (from json.load of an .idw file,
                            or ImageWorkspace.to_dict()).
            output_dir: Where to write embedded copies (copy mode).
            in_place: If True, embed directly into original files.
            dry_run: Report what would happen without writing anything.

        Returns:
            EmbedResult with counts and skipped/error lists.
        """
        result = EmbedResult(dry_run=dry_run)
        items = workspace_data.get('items', {})

        if not items:
            logger.warning("Workspace contains no items")
            return result

        if not in_place and output_dir is not None and not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)

        embedder = ExifEmbedder()

        for item_path, item_data in items.items():
            descriptions = item_data.get('descriptions', [])
            if not descriptions:
                continue

            # Use most recent description
            latest = descriptions[-1]
            description_text = latest.get('text', '')
            if not description_text:
                continue

            model = latest.get('model', '')
            created = latest.get('created', '')

            orig = Path(item_path)
            if not orig.exists():
                logger.warning("Image file not found: %s", orig)
                result.skipped_no_original.append(str(orig))
                continue

            self._embed_one(
                orig, description_text, model, created,
                output_dir, in_place, dry_run, embedder, result
            )

        return result

    def _resolve_original(self, filename: str, filepath: str,
                          path_mapping: dict, basename_mapping: dict) -> Optional[str]:
        """Resolve a workflow description entry to its original file path."""
        # 1. Exact match on relative key
        if filename in path_mapping:
            return path_mapping[filename]

        # 2. Basename match
        basename = Path(filename).name
        if basename in basename_mapping:
            return basename_mapping[basename]

        # 3. Fallback: use filepath from descriptions file (may be absolute temp path)
        if filepath and Path(filepath).exists():
            return filepath

        return None

    def _embed_one(self, orig: Path, description: str, model: str, timestamp: str,
                   output_dir: Optional[Path], in_place: bool, dry_run: bool,
                   embedder: ExifEmbedder, result: EmbedResult) -> None:
        """Perform the copy (or in-place) embed for a single image."""
        is_heic = orig.suffix.lower() in HEIC_SUFFIXES

        try:
            if in_place:
                if is_heic:
                    logger.info("Skipping HEIC in-place embed: %s", orig.name)
                    result.skipped_format.append(str(orig))
                    return
                if not dry_run:
                    self._do_embed(orig, orig, description, model, timestamp, embedder)
            else:
                # Copy mode
                if is_heic:
                    # Convert to JPEG copy first, then embed
                    dest_name = orig.stem + '.jpg'
                else:
                    dest_name = orig.name

                if output_dir is None:
                    # output_dir unset means same directory as original (side-by-side copy)
                    dest = orig.parent / f"{orig.stem}_described{orig.suffix}"
                else:
                    dest = output_dir / dest_name

                if not dry_run:
                    if is_heic:
                        self._convert_heic_and_embed(orig, dest, description, model, timestamp, embedder)
                    else:
                        self._do_embed(orig, dest, description, model, timestamp, embedder)

            result.embedded += 1
            action = "Would embed" if dry_run else "Embedded"
            logger.debug("%s description in: %s", action, orig.name)

        except UnsupportedFormatError as e:
            logger.warning("Unsupported format: %s", e)
            result.skipped_format.append(str(orig))
        except Exception as e:
            logger.error("Error embedding %s: %s", orig.name, e)
            result.errors.append(f"{orig.name}: {e}")

    def _do_embed(self, source: Path, dest: Path, description: str,
                  model: str, timestamp: str, embedder: ExifEmbedder) -> None:
        """Write description into dest.

        Uses idt_core.embed_image_file (EXIF + XMP) when available, otherwise
        falls back to the piexif-only ExifEmbedder path.
        """
        if _idt_embed_image_file is not None:
            try:
                _idt_embed_image_file(source, description, dest)
                return
            except Exception as exc:
                logger.warning("idt_core embed failed, falling back to ExifEmbedder: %s", exc)

        # Fallback: piexif-only path (no XMP dc:description)
        if source != dest:
            shutil.copy2(source, dest)
        embedder.embed_ai_description(dest, description, model, timestamp)

    def _convert_heic_and_embed(self, heic_path: Path, dest: Path, description: str,
                                 model: str, timestamp: str, embedder: ExifEmbedder) -> None:
        """Convert a HEIC file to JPEG copy, then embed the description."""
        try:
            from ConvertImage import convert_heic_to_jpg
        except ImportError:
            from scripts.ConvertImage import convert_heic_to_jpg

        dest.parent.mkdir(parents=True, exist_ok=True)
        convert_heic_to_jpg(heic_path, dest)
        self._do_embed(dest, dest, description, model, timestamp, embedder)


def main():
    parser = argparse.ArgumentParser(
        prog='embed_descriptions',
        description='Embed AI descriptions from a workflow into image metadata.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create copies with descriptions embedded (default, safe)
  python embed_descriptions.py wf_2026-06-18_123456_claude_Detailed/

  # Specify output directory for embedded copies
  python embed_descriptions.py wf_*/ --output-dir ~/Pictures/WithDescriptions/

  # Preview without writing anything
  python embed_descriptions.py wf_*/ --dry-run

  # Embed directly into original files (modifies originals)
  python embed_descriptions.py wf_*/ --in-place
""")

    parser.add_argument('workflow_dir', help='Workflow output directory (wf_*/)')
    parser.add_argument('--output-dir', '-o', metavar='DIR',
                        help='Output directory for embedded copies '
                             '(default: workflow_dir/embedded_images/)')
    parser.add_argument('--in-place', action='store_true',
                        help='Embed into original files instead of making copies')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report what would be embedded without writing')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s - %(message)s'
    )

    workflow_dir = Path(args.workflow_dir)
    if not workflow_dir.is_dir():
        print(f"Error: workflow directory not found: {workflow_dir}")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else None

    embedder = EmbedDescriptions()
    try:
        result = embedder.embed_from_workflow_dir(
            workflow_dir,
            output_dir=output_dir,
            in_place=args.in_place,
            dry_run=args.dry_run
        )
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    print(result.summary())
    if result.skipped_no_original:
        print("\nSkipped (original not found):")
        for p in result.skipped_no_original:
            print(f"  {p}")
    if result.skipped_format:
        print("\nSkipped (unsupported format):")
        for p in result.skipped_format:
            print(f"  {p}")
    if result.errors:
        print("\nErrors:")
        for e in result.errors:
            print(f"  {e}")

    return 1 if result.errors else 0


if __name__ == '__main__':
    sys.exit(main())

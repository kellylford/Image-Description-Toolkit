#!/usr/bin/env python3
"""
Verify a workflow output directory for key expectations:
- Descriptions file parsing (counts, fields)
- Presence of Source: lines for video frames
- Geocoding attribution lines (OpenStreetMap) when city/state/country present
- Optional EXIF check for source video path in ImageDescription/UserComment

Usage:
  python tools/verify_workflow_output.py \
    "//qnap/home/idt/descriptions/wf_BuildTest_..." \
    --check-exif --list-missing 10

Exit code 0 on success; non-zero if critical issues found.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import re

try:
    from PIL import Image
except Exception:
    Image = None  # EXIF check will be disabled if Pillow is missing

SEPARATOR = '-' * 80


def parse_descriptions_file(desc_path: Path):
    text = desc_path.read_text(encoding='utf-8', errors='replace')
    sections = [s.strip() for s in text.split(SEPARATOR) if s.strip()]
    entries = []
    for section in sections:
        entry = {
            'file': None,
            'path': None,
            'source': None,
            'photo_date': None,
            'camera': None,
            'provider': None,
            'model': None,
            'prompt_style': None,
            'description': None,
            'timestamp': None,
            'has_osm_attrib': False,
        }
        lines = [ln.strip() for ln in section.splitlines()]
        desc_started = False
        desc_lines = []
        for ln in lines:
            if not ln:
                if desc_started:
                    desc_lines.append('')
                continue
            if ln.startswith('File: '):
                entry['file'] = ln[6:].strip()
            elif ln.startswith('Path: '):
                entry['path'] = ln[6:].strip()
            elif ln.startswith('Source: '):
                entry['source'] = ln[8:].strip()
            elif ln.startswith('Photo Date: '):
                entry['photo_date'] = ln[12:].strip()
            elif ln.startswith('Camera: '):
                entry['camera'] = ln[8:].strip()
            elif ln.startswith('Provider: '):
                entry['provider'] = ln[10:].strip()
            elif ln.startswith('Model: '):
                entry['model'] = ln[7:].strip()
            elif ln.startswith('Prompt Style: '):
                entry['prompt_style'] = ln[14:].strip()
            elif ln.startswith('Description: '):
                desc_started = True
                desc_lines.append(ln[13:].strip())
            elif ln.startswith('Timestamp: '):
                entry['timestamp'] = ln[11:].strip()
            elif 'OpenStreetMap contributors' in ln:
                entry['has_osm_attrib'] = True
            elif desc_started and not ln.startswith((
                'File:', 'Path:', 'Source:', 'Photo Date:', 'Camera:', 'Provider:',
                'Model:', 'Prompt Style:', 'Timestamp:'
            )):
                desc_lines.append(ln)
        if desc_lines:
            entry['description'] = '\n'.join(desc_lines).strip()
        entries.append(entry)
    return entries


def looks_like_video_frame(filename: str) -> bool:
    # Heuristic: name contains _<seconds>s.jpg (e.g., myvideo_20.00s.jpg)
    return bool(re.search(r'_\d+\.?\d*s\.(jpe?g|png)$', filename, re.IGNORECASE))


def exif_source_info(image_path: Path):
    if Image is None:
        return None
    try:
        with Image.open(image_path) as img:
            exif = img.getexif()
            if not exif:
                return None
            from PIL.ExifTags import TAGS
            exif_dict = {TAGS.get(k, k): v for k, v in exif.items()}
            # Prefer ImageDescription
            desc = exif_dict.get('ImageDescription')
            if isinstance(desc, bytes):
                try:
                    desc = desc.decode('utf-8', errors='ignore')
                except Exception:
                    desc = None
            if isinstance(desc, str) and 'Extracted from video:' in desc:
                return desc
            # Try UserComment via raw value
            user = exif_dict.get('UserComment')
            if isinstance(user, (bytes, bytearray)):
                try:
                    raw = user.decode('utf-8', errors='ignore')
                except Exception:
                    raw = None
                if raw and 'Extracted from video:' in raw:
                    return raw
    except Exception:
        return None
    return None


def main():
    ap = argparse.ArgumentParser(description='Verify IDT workflow output directory')
    ap.add_argument('workflow_dir', help='Path to workflow directory (contains descriptions/)')
    ap.add_argument('--check-exif', action='store_true', help='Also verify EXIF contains source info for frames')
    ap.add_argument('--list-missing', type=int, default=0, help='List first N entries missing expected fields')
    args = ap.parse_args()

    wf = Path(args.workflow_dir)
    desc_file = wf / 'descriptions' / 'image_descriptions.txt'
    if not desc_file.exists():
        print(f'ERROR: Descriptions file not found: {desc_file}')
        return 2

    entries = parse_descriptions_file(desc_file)
    total = len(entries)
    with_source = sum(1 for e in entries if e.get('source'))
    osm_count = sum(1 for e in entries if e.get('has_osm_attrib'))
    with_photo_date = sum(1 for e in entries if e.get('photo_date'))
    with_camera = sum(1 for e in entries if e.get('camera'))

    # Heuristic: frames that look like video-derived but missing Source
    looks_frame = [e for e in entries if e.get('file') and looks_like_video_frame(e['file'])]
    frames_missing_source = [e for e in looks_frame if not e.get('source')]

    print('Verification summary:')
    print(f'- Entries total: {total}')
    print(f'- Entries with Source: {with_source}')
    print(f'- Entries with Photo Date: {with_photo_date}')
    print(f'- Entries with Camera: {with_camera}')
    print(f'- Entries with OSM attribution (geocoded): {osm_count}')
    print(f'- Heuristic video frames detected: {len(looks_frame)}')
    print(f'- Heuristic frames missing Source: {len(frames_missing_source)}')

    rc = 0
    if len(frames_missing_source) > 0:
        rc = 1
        if args.list_missing:
            print('\nFirst missing Source entries:')
            for e in frames_missing_source[: args.list_missing]:
                print(f"  - {e.get('file')}  (Path: {e.get('path')})")

    if args.check_exif and Image is not None:
        print('\nEXIF spot-check (up to 5 frames):')
        checked = 0
        for e in entries:
            if checked >= 5:
                break
            if not e.get('path'):
                continue
            p = Path(wf) / e['path'] if not Path(e['path']).is_absolute() else Path(e['path'])
            info = exif_source_info(p)
            if info:
                print(f'- EXIF OK: {p.name}: {info[:80]}')
            else:
                print(f'- EXIF missing/unknown: {p.name}')
            checked += 1
    elif args.check_exif and Image is None:
        print('\nNOTE: Pillow not installed; skipping EXIF checks')

    return rc


if __name__ == '__main__':
    sys.exit(main())

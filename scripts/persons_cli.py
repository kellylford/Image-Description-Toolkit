"""
persons_cli.py — CLI entry point for the `idt persons` command group.

Subcommands:
    add       Add a new known person to the workspace persons database
    tag       Tag a specific image with a person name
    untag     Remove a person tag from an image
    list      List all known persons
    report    Print a person identification report
    export    Export person data to a workflow directory
    import    Import person data from a workflow directory

Usage examples:
    idt persons add --name "Alice Smith" --traits "tall, auburn hair, glasses"
    idt persons tag --image IMG_001.jpg --person "Alice Smith" --workspace my.idtworkspace
    idt persons list --workspace my.idtworkspace
    idt persons report --workflow ./Descriptions/wf_photos_...
    idt persons export --workflow ./Descriptions/wf_photos_...
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Import path resolution
# ---------------------------------------------------------------------------
def _setup_paths():
    """Ensure imagedescriber and scripts are on sys.path regardless of run mode."""
    if getattr(sys, 'frozen', False):
        # Frozen exe: everything is in _MEIPASS
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent.parent

    for sub in ("imagedescriber", "scripts"):
        p = str(base / sub)
        if p not in sys.path:
            sys.path.insert(0, p)
    # Also add scripts/ itself (this file lives there)
    scripts_dir = str(Path(__file__).parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

_setup_paths()

try:
    from data_models import ImageWorkspace
    from persons_manager import (
        add_person, update_person, remove_person, find_person_by_name,
        tag_image, untag_image, get_images_for_person, get_persons_for_image,
        export_to_workflow, import_from_workflow, build_report_lines,
    )
except ImportError as e:
    print(f"Error: Could not import required modules: {e}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------

def _load_workspace(workspace_path: Optional[str]) -> Optional["ImageWorkspace"]:
    """Load a workspace from file, or return an empty one if no path given."""
    if workspace_path is None:
        # Try to find a workspace in the current directory
        cwd = Path(os.getcwd())
        candidates = list(cwd.glob("*.idtworkspace"))
        if len(candidates) == 1:
            workspace_path = str(candidates[0])
            print(f"Using workspace: {workspace_path}")
        elif len(candidates) > 1:
            print("Multiple .idtworkspace files found. Specify --workspace.", file=sys.stderr)
            return None
        else:
            print("No .idtworkspace file found. Specify --workspace or create one with 'idt persons create-workspace'.", file=sys.stderr)
            return None

    ws_path = Path(workspace_path)
    if not ws_path.exists():
        print(f"Workspace file not found: {workspace_path}", file=sys.stderr)
        return None

    try:
        import json
        with open(ws_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        workspace = ImageWorkspace.from_dict(data)
        workspace.file_path = str(ws_path)
        return workspace
    except Exception as e:
        print(f"Error loading workspace: {e}", file=sys.stderr)
        return None


def _save_workspace(workspace: "ImageWorkspace") -> bool:
    """Save workspace to its file_path. Returns True on success."""
    if not workspace.file_path:
        print("Error: Workspace has no file path (use --workspace).", file=sys.stderr)
        return False
    try:
        import json
        with open(workspace.file_path, "w", encoding="utf-8") as f:
            json.dump(workspace.to_dict(), f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving workspace: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_add(args) -> int:
    workspace = _load_workspace(args.workspace)
    if workspace is None:
        return 1

    record = add_person(workspace, args.name,
                        description_traits=args.traits or "",
                        notes=args.notes or "")
    if not _save_workspace(workspace):
        return 1

    print(f"Added person '{record.name}' (id: {record.id})")
    return 0


def cmd_tag(args) -> int:
    workspace = _load_workspace(args.workspace)
    if workspace is None:
        return 1

    # Resolve the image path — try absolute, then relative to cwd, then relative to workspace dir
    image_path = Path(args.image)
    if not image_path.is_absolute():
        # Try cwd first
        candidate = Path(os.getcwd()) / image_path
        if candidate.exists():
            image_path = candidate
        elif workspace.file_path:
            candidate = Path(workspace.file_path).parent / image_path
            if candidate.exists():
                image_path = candidate

    image_path_str = str(image_path.resolve()) if image_path.exists() else str(image_path)

    record = tag_image(workspace, image_path_str, args.person)
    if record is None:
        print(f"Image '{args.image}' not found in workspace. Add the directory first.", file=sys.stderr)
        return 1

    if not _save_workspace(workspace):
        return 1

    print(f"Tagged '{Path(image_path_str).name}' with person '{record.name}'")
    return 0


def cmd_untag(args) -> int:
    workspace = _load_workspace(args.workspace)
    if workspace is None:
        return 1

    # Resolve person_id from name or uuid
    person = None
    if args.person in workspace.persons:
        person = workspace.persons[args.person]
    else:
        person = find_person_by_name(workspace, args.person)

    if person is None:
        print(f"Person '{args.person}' not found in workspace.", file=sys.stderr)
        return 1

    image_path = str(Path(args.image).resolve()) if Path(args.image).exists() else args.image
    removed = untag_image(workspace, image_path, person.id)
    if not removed:
        print(f"Tag not found: '{args.person}' on '{args.image}'", file=sys.stderr)
        return 1

    if not _save_workspace(workspace):
        return 1

    print(f"Removed tag '{person.name}' from '{Path(image_path).name}'")
    return 0


def cmd_list(args) -> int:
    workspace = _load_workspace(args.workspace)
    if workspace is None:
        return 1

    if not workspace.persons:
        print("No known persons in this workspace.")
        return 0

    print(f"\nKnown Persons ({len(workspace.persons)}):")
    print("-" * 40)
    for record in sorted(workspace.persons.values(), key=lambda r: r.name.lower()):
        images = get_images_for_person(workspace, record.id)
        print(f"  {record.name} — {len(images)} image(s) tagged")
        if record.description_traits:
            print(f"    Traits: {record.description_traits}")
        if record.notes:
            print(f"    Notes: {record.notes}")
    return 0


def cmd_report(args) -> int:
    workspace = _load_workspace(args.workspace)
    if workspace is None:
        return 1

    lines = build_report_lines(workspace, workflow_dir=args.workflow)
    report_text = "\n".join(lines)
    print(report_text)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.suffix.lower() == ".html":
            _write_html_report(lines, out_path)
        else:
            out_path.write_text(report_text, encoding="utf-8")
        print(f"\nReport saved to: {out_path}")

    return 0


def _write_html_report(lines: list, out_path: Path) -> None:
    """Write the report lines as a simple HTML file."""
    html_lines = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="UTF-8">',
        "<title>Person Identification Report</title>",
        "<style>body{font-family:sans-serif;max-width:900px;margin:2em auto;} "
        "h1{color:#333} h2{color:#555} ul{margin:0.3em 0 0.8em 1.5em} "
        ".traits{color:#666;font-style:italic}</style>",
        "</head>",
        "<body>",
    ]
    for line in lines:
        stripped = line.strip()
        if not stripped:
            html_lines.append("<br>")
        elif stripped.startswith("="):
            html_lines.append("<hr>")
        elif stripped.startswith("-"):
            html_lines.append("<hr style='border-top:1px solid #ccc'>")
        elif line.startswith("  - "):
            html_lines.append(f"<li>{stripped[2:]}</li>")
        elif line.startswith("    "):
            html_lines.append(f"<p class='traits'>{stripped}</p>")
        elif line.startswith("  "):
            html_lines.append(f"<h2>{stripped}</h2>")
        else:
            html_lines.append(f"<p>{stripped}</p>")
    html_lines += ["</body>", "</html>"]
    out_path.write_text("\n".join(html_lines), encoding="utf-8")


def cmd_export(args) -> int:
    workspace = _load_workspace(args.workspace)
    if workspace is None:
        return 1

    if not args.workflow:
        print("Error: --workflow is required for export.", file=sys.stderr)
        return 1

    wf_path = Path(args.workflow)
    if not wf_path.exists():
        print(f"Workflow directory not found: {args.workflow}", file=sys.stderr)
        return 1

    out = export_to_workflow(workspace, str(wf_path))
    print(f"Exported person data to: {out}")
    return 0


def cmd_import(args) -> int:
    workspace = _load_workspace(args.workspace)
    if workspace is None:
        return 1

    if not args.workflow:
        print("Error: --workflow is required for import.", file=sys.stderr)
        return 1

    persons_imported, images_tagged = import_from_workflow(workspace, args.workflow)

    if not _save_workspace(workspace):
        return 1

    print(f"Imported {persons_imported} new person(s), tagged {images_tagged} image(s).")
    return 0


def cmd_install_engine(args) -> int:
    """Install / query / uninstall the optional face recognition engine."""
    try:
        from install_persons_engine import (
            is_engine_available,
            get_installation_status,
            install_engine,
            uninstall_engine,
        )
    except ImportError:
        _root = Path(__file__).parent.parent
        sys.path.insert(0, str(_root / "scripts"))
        from install_persons_engine import (
            is_engine_available,
            get_installation_status,
            install_engine,
            uninstall_engine,
        )

    if args.status:
        print("Face recognition engine status:")
        for pkg, info in get_installation_status().items():
            mark = "\u2713" if info["installed"] else "\u2717"
            ver = f" v{info['version']}" if info.get("version") else ""
            print(f"  {mark}  {pkg}{ver}")
        print()
        if is_engine_available():
            print("Engine is AVAILABLE.")
        else:
            print("Engine is NOT installed. Run: idt persons install-engine")
        return 0

    if args.uninstall:
        print("Uninstalling face recognition engine...")
        ok = uninstall_engine(progress_cb=lambda msg, _: print(msg))
        return 0 if ok else 1

    def _progress(msg: str, pct: int) -> None:
        print(f"[{pct:3d}%] {msg}")

    if is_engine_available() and not args.reinstall:
        print(
            "Face recognition engine is already installed. "
            "Use --reinstall to force reinstall."
        )
        return 0

    print("Installing face recognition engine (this may take several minutes)...")
    ok = install_engine(progress_cb=_progress, reinstall=args.reinstall)
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="idt persons",
        description="Manage person identification data for your image workspace.",
    )
    parser.add_argument(
        "--workspace", "-w",
        metavar="FILE",
        help="Path to .idtworkspace file (auto-detected if only one exists in cwd)",
    )

    sub = parser.add_subparsers(dest="subcommand", metavar="SUBCOMMAND")
    sub.required = True

    # add
    p_add = sub.add_parser("add", help="Add a known person to the workspace")
    p_add.add_argument("--name", "-n", required=True, help="Person's display name")
    p_add.add_argument("--traits", "-t", default="", help="Physical description traits for AI matching")
    p_add.add_argument("--notes", default="", help="Optional notes")

    # tag
    p_tag = sub.add_parser("tag", help="Tag an image with a known person")
    p_tag.add_argument("--image", "-i", required=True, help="Image filename or path")
    p_tag.add_argument("--person", "-p", required=True, help="Person name or id")

    # untag
    p_untag = sub.add_parser("untag", help="Remove a person tag from an image")
    p_untag.add_argument("--image", "-i", required=True, help="Image filename or path")
    p_untag.add_argument("--person", "-p", required=True, help="Person name or id")

    # list
    sub.add_parser("list", help="List all known persons in the workspace")

    # report
    p_report = sub.add_parser("report", help="Print a person identification report")
    p_report.add_argument("--workflow", metavar="DIR", help="Limit report to images inside this workflow directory")
    p_report.add_argument("--output", "-o", metavar="FILE", help="Save report to file (.txt or .html)")

    # export
    p_export = sub.add_parser("export", help="Export person data to a workflow directory")
    p_export.add_argument("--workflow", required=True, metavar="DIR", help="Workflow directory to export to")

    # import
    p_import = sub.add_parser("import", help="Import person data from a workflow directory")
    p_import.add_argument("--workflow", required=True, metavar="DIR", help="Workflow directory to import from")

    p_engine = sub.add_parser("install-engine", help="Install the optional face recognition engine")
    p_engine.add_argument("--reinstall", action="store_true", help="Force reinstall even if already installed")
    p_engine.add_argument("--status", action="store_true", help="Show installation status and exit")
    p_engine.add_argument("--uninstall", action="store_true", help="Uninstall the face recognition engine")

    return parser


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "add": cmd_add,
        "tag": cmd_tag,
        "untag": cmd_untag,
        "list": cmd_list,
        "report": cmd_report,
        "export": cmd_export,
        "import": cmd_import,
        "install-engine": cmd_install_engine,
    }

    handler = dispatch.get(args.subcommand)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())

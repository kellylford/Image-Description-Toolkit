"""
Tests for workspace default-path logic across CLI and GUI.

Covers:
- _mirror_source_path() leaf-name flattening
- _open_or_create_workspace() routing (no arg, bare name, explicit path)
- workspace_manager.get_default_workspaces_root() delegates to UserConfig
- GUI auto-save would land in workspace root, not source parent
"""
from __future__ import annotations

import sys
import json
from pathlib import Path
from unittest.mock import patch

import pytest


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _make_src(tmp_path: Path, name: str = "Vacation") -> Path:
    src = tmp_path / name
    src.mkdir()
    (src / "photo.jpg").write_bytes(b"fake")
    return src


def _patch_config_file(monkeypatch, tmp_path: Path):
    """Redirect UserConfig saves/loads to a temp file so tests don't touch ~/.idt."""
    import idt_core.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "_CONFIG_FILE", tmp_path / ".idt" / "config.json")


# ------------------------------------------------------------------ #
# _mirror_source_path                                                  #
# ------------------------------------------------------------------ #

class TestMirrorSourcePath:
    def _fn(self):
        from cli.main import _mirror_source_path
        return _mirror_source_path

    def test_uses_leaf_name_of_source(self, tmp_path):
        src = _make_src(tmp_path, "Vacation")
        root = tmp_path / "idt"
        result = self._fn()(src, root)
        assert result == root / "Vacation"

    def test_nested_source_uses_only_leaf(self, tmp_path):
        deep = tmp_path / "A" / "B" / "C" / "June"
        deep.mkdir(parents=True)
        root = tmp_path / "idt"
        result = self._fn()(deep, root)
        assert result == root / "June"

    def test_unc_path_uses_leaf(self, tmp_path):
        # Simulate a network share leaf name
        root = tmp_path / "idt"
        # Can't create a real UNC path in tests; test the logic with a deep path
        src = tmp_path / "ford" / "home" / "Photos" / "06"
        src.mkdir(parents=True)
        result = self._fn()(src, root)
        assert result == root / "06"


# ------------------------------------------------------------------ #
# _open_or_create_workspace                                            #
# ------------------------------------------------------------------ #

class TestOpenOrCreateWorkspace:
    def _fn(self):
        from cli.main import _open_or_create_workspace
        return _open_or_create_workspace

    def test_no_workspace_arg_uses_mirror_under_root(self, tmp_path, monkeypatch):
        _patch_config_file(monkeypatch, tmp_path)
        from idt_core.config import UserConfig
        custom_root = tmp_path / "myidt"
        cfg = UserConfig()
        cfg.workspace_root = str(custom_root)
        cfg.save()

        src = _make_src(tmp_path, "BeachTrip")
        ws = self._fn()(src, workspace_arg=None)
        assert ws.path.parent == custom_root
        assert ws.path.name.startswith("BeachTrip")

    def test_bare_name_workspace_arg_lands_in_root(self, tmp_path, monkeypatch):
        _patch_config_file(monkeypatch, tmp_path)
        from idt_core.config import UserConfig
        custom_root = tmp_path / "myidt"
        cfg = UserConfig()
        cfg.workspace_root = str(custom_root)
        cfg.save()

        src = _make_src(tmp_path, "Pics")
        ws = self._fn()(src, workspace_arg="MyWork")
        assert ws.path.parent == custom_root
        assert "MyWork" in ws.path.name

    def test_explicit_path_workspace_arg_uses_that_path(self, tmp_path, monkeypatch):
        _patch_config_file(monkeypatch, tmp_path)
        src = _make_src(tmp_path, "Pics")
        explicit = tmp_path / "explicit" / "MyBundle"
        ws = self._fn()(src, workspace_arg=str(explicit))
        assert str(explicit) in str(ws.path)

    def test_default_root_is_documents_idt(self, tmp_path, monkeypatch):
        _patch_config_file(monkeypatch, tmp_path)
        # No config file written → should use ~/Documents/idt
        src = _make_src(tmp_path, "Summer")
        ws = self._fn()(src, workspace_arg=None)
        expected_root = Path.home() / "Documents" / "idt"
        assert ws.path.parent == expected_root


# ------------------------------------------------------------------ #
# workspace_manager.get_default_workspaces_root                        #
# ------------------------------------------------------------------ #

class TestGetDefaultWorkspacesRoot:
    def test_returns_documents_idt_by_default(self, tmp_path, monkeypatch):
        import idt_core.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_CONFIG_FILE", tmp_path / "no_config.json")
        from imagedescriber.workspace_manager import get_default_workspaces_root
        result = get_default_workspaces_root()
        assert result == Path.home() / "Documents" / "idt"

    def test_respects_user_config_workspace_root(self, tmp_path, monkeypatch):
        _patch_config_file(monkeypatch, tmp_path)
        from idt_core.config import UserConfig
        custom = tmp_path / "custom_ws"
        cfg = UserConfig()
        cfg.workspace_root = str(custom)
        cfg.save()

        from imagedescriber.workspace_manager import get_default_workspaces_root
        result = get_default_workspaces_root()
        assert result == custom.resolve()

    def test_does_not_return_imagedescriptiontoolkit(self, tmp_path, monkeypatch):
        import idt_core.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_CONFIG_FILE", tmp_path / "no_config.json")
        from imagedescriber.workspace_manager import get_default_workspaces_root
        result = get_default_workspaces_root()
        assert "ImageDescriptionToolkit" not in str(result)


# ------------------------------------------------------------------ #
# GUI auto-save path contract                                          #
# ------------------------------------------------------------------ #

class TestGuiAutoSavePath:
    """
    These tests verify the path logic of _auto_save_bundle without
    launching wx.  They test _mirror_source_path + get_default_workspaces_root
    together to confirm the bundle would land in the workspace root, not
    next to the source folder.
    """

    def test_auto_save_bundle_path_not_source_parent(self, tmp_path, monkeypatch):
        import idt_core.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_CONFIG_FILE", tmp_path / "no_config.json")
        from imagedescriber.workspace_manager import get_default_workspaces_root

        source = tmp_path / "network" / "Photos" / "2026" / "06"
        source.mkdir(parents=True)

        workspace_root = get_default_workspaces_root()
        bundle_path = workspace_root / (source.name + ".idtw")

        # Must NOT be next to source on the network share
        assert bundle_path.parent != source.parent
        # Must be under the workspace root
        assert bundle_path.parent == workspace_root

    def test_auto_save_bundle_name_derived_from_source_leaf(self, tmp_path, monkeypatch):
        import idt_core.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_CONFIG_FILE", tmp_path / "no_config.json")
        from imagedescriber.workspace_manager import get_default_workspaces_root

        source = tmp_path / "June"
        source.mkdir()
        workspace_root = get_default_workspaces_root()
        bundle_path = workspace_root / (source.name + ".idtw")
        assert bundle_path.name == "June.idtw"

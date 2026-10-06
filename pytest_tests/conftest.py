"""
Pytest configuration and shared fixtures for IDT test suite.

This file contains fixtures that are available to all tests.
"""

import os
import sys
from pathlib import Path
import pytest

# Add project root to Python path so tests can import from scripts/
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def _stop_wx_app_restoring_stdio():
    """Keep a garbage-collected wx.App from rebinding sys.stdout mid-test.

    wx.App records ``sys.stdout`` when it is constructed and puts it back in
    ``__del__`` (via ``RestoreStdio``), unconditionally. Under pytest the
    recorded stream is whichever test's capture was active at the time, so
    when the App's wrapper is collected later -- at a moment decided by the
    garbage collector -- the *current* test's prints go to that stale stream
    and its ``capsys`` comes back empty, while the "Captured stdout" section
    shows everything. That was the intermittent CI failure in
    ``test_cli_models_command.py``, which runs right after
    ``test_claude_code_dialogs.py`` creates an App.

    No test redirects wx stdio, so there is never anything to restore.
    """
    try:
        import wx
    except Exception:
        return
    wx.App.RestoreStdio = lambda self: None


_stop_wx_app_restoring_stdio()


# No test wants the model lists refreshed in the background when it builds an
# ImageDescriber window. That thread queries Ollama and the Claude and OpenAI
# APIs, then changes the shared model catalog while later tests on the same
# worker run: test_model_refresh failed now and then under -n 4. Set before any
# test runs, so it also covers windows built by module-scoped fixtures.
os.environ["IDT_SKIP_STARTUP_MODEL_REFRESH"] = "1"


@pytest.fixture(autouse=True)
def isolate_model_cache(tmp_path, monkeypatch):
    """Point the provider model cache at a scratch directory, for every test.

    ``registry.model_limits()`` reaches the model catalog, which can consult a
    cache under ``~/.idt``. Without this, whether a test passes depends on
    whether the developer has run ``idt models --refresh`` on that machine --
    green in CI, red locally, for a reason nothing in the test file mentions.

    Autouse rather than opt-in on purpose: the tests that would be affected are
    the ones that never mention models (``test_chat_engine``, ``test_chat_providers``),
    so requiring them to ask for isolation is exactly how the gap reappears.
    """
    monkeypatch.setenv("IDT_MODEL_CACHE_DIR", str(tmp_path / "model_cache"))


@pytest.fixture
def project_root_path():
    """Return the project root directory path."""
    return Path(__file__).parent.parent

@pytest.fixture
def scripts_path(project_root_path):
    """Return the scripts directory path."""
    return project_root_path / "scripts"

@pytest.fixture
def test_fixtures_path():
    """Return the test fixtures directory path."""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def temp_workflow_dir(tmp_path):
    """Create a temporary workflow directory structure for testing."""
    workflow_dir = tmp_path / "test_workflow"
    workflow_dir.mkdir()
    
    # Create typical subdirectories
    (workflow_dir / "logs").mkdir()
    (workflow_dir / "Descriptions").mkdir()
    (workflow_dir / "converted_images").mkdir()
    
    return workflow_dir

@pytest.fixture
def mock_args():
    """Return a mock args object for testing."""
    class MockArgs:
        def __init__(self, **kwargs):
            # Set defaults
            self.name = None
            self.provider = "ollama"
            self.model = None
            self.config = None
            self.prompt_style = None
            self.output_dir = None
            self.video = False
            self.geocode = False
            self.metadata = False
            
            # Override with provided kwargs
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    return MockArgs

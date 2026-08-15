"""The provider capability registry, and the silent-degradation defect it replaced.

Chat attachments were configured by ``models/provider_configs.py``, imported in
``chat_window_wx.py`` behind a ``try/except ImportError`` that fell back to
stubs::

    except ImportError:
        def supports_attachments(p): return False

Commit 16e089b deleted the whole ``models/`` tree. The import started failing,
the stub became the only path, ``_update_attach_button_state`` called
``attach_btn.Show(False)``, and the Attach Files button vanished on every
provider. Nothing failed loudly: no traceback, no log line, no test. The only
symptom was a button that was no longer there.

So the assertions here are shaped against *that* failure mode rather than
against the capability data:

* ``test_chat_window_uses_the_real_registry`` compares function identity. A
  reintroduced stub is a different object and fails, even though it has the
  same name and the same signature and returns a perfectly plausible False.
* ``test_every_picker_provider_is_registered`` reads the provider list out of
  the chat picker's own source. A provider added to the dropdown without a
  registry entry cannot slip through silently -- the test fails and names it.

Testing ``capabilities_for('claude').supports_attachments is True`` alone would
not have caught the original bug: the registry was never wrong, it was absent.
"""

import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (_ROOT, _ROOT / "imagedescriber"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from idt_core.providers import registry  # noqa: E402

_CHAT_WINDOW_SOURCE = _ROOT / "imagedescriber" / "chat_window_wx.py"


# --------------------------------------------------------------------------
# The defect: silent degradation to a stub
# --------------------------------------------------------------------------

def test_chat_window_uses_the_real_registry():
    """chat_window_wx must bind the registry functions themselves, not lookalikes.

    Identity, not behaviour. A stub named supports_attachments that returns
    False is behaviourally indistinguishable from "this provider takes no
    attachments" -- which is exactly why the original regression was invisible.
    """
    pytest.importorskip("wx")
    import chat_window_wx

    assert chat_window_wx.supports_attachments is registry.supports_attachments
    assert chat_window_wx.attachment_wildcard is registry.attachment_wildcard


def test_capability_import_is_not_optional():
    """The registry import must not be wrapped in a try/except ImportError.

    An optional import is what let a deleted module degrade to "no
    capabilities" instead of failing the build.
    """
    source = _CHAT_WINDOW_SOURCE.read_text(encoding="utf-8")
    match = re.search(
        r"^from idt_core\.providers\.registry import", source, re.MULTILINE
    )
    assert match, "chat_window_wx no longer imports the registry at module scope"

    # Walk back over the preceding lines; the import must not sit inside a try.
    preceding = source[: match.start()].splitlines()
    for line in reversed(preceding):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert not stripped.startswith("try:"), (
            "the registry import is inside a try/except -- a missing module "
            "would silently disable attachments again"
        )
        break


def _picker_providers():
    """Provider names offered by ChatDialog's dropdown, read from its source.

    Asserts on the way through: a regex that silently stopped matching would
    turn every caller into a vacuous pass, which is the same class of quiet
    failure this file exists to catch.
    """
    source = _CHAT_WINDOW_SOURCE.read_text(encoding="utf-8")
    match = re.search(r"wx\.Choice\(\s*self,\s*choices=\[(.*?)\]", source, re.DOTALL)
    assert match, "could not locate the provider picker in chat_window_wx.py"

    picker = re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))
    assert picker, "provider picker parsed as empty"
    return picker


def test_every_picker_provider_is_registered():
    """Every provider offered in the chat dropdown must have a registry entry.

    Read from the source so a provider added to the picker cannot opt out of
    this check by simply not being listed here.
    """
    unregistered = [
        name for name in _picker_providers()
        if registry.capabilities_for(name).provider == "unknown"
    ]
    assert not unregistered, f"providers in the picker with no registry entry: {unregistered}"


def test_every_picker_provider_accepts_attachments():
    """The regression itself: the Attach Files button must be reachable."""
    without = [
        name for name in _picker_providers()
        if not registry.supports_attachments(name)
    ]
    assert not without, f"providers offering no attachments: {without}"


# --------------------------------------------------------------------------
# Lookup behaviour
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["claude", "Claude", "CLAUDE", "  claude  ", "anthropic"])
def test_lookup_is_case_insensitive_and_aliased(name):
    """The GUI lowercases provider names; config files and aliases do not."""
    assert registry.capabilities_for(name).provider == "claude"


def test_unknown_provider_degrades_conservatively():
    """An unknown provider must not raise -- wx swallows handler exceptions."""
    caps = registry.capabilities_for("does-not-exist")
    assert caps.provider == "unknown"
    assert caps.supports_attachments is False
    assert registry.attachment_wildcard("does-not-exist") == "All files (*.*)|*.*"


def test_empty_provider_name_is_safe():
    assert registry.capabilities_for("").provider == "unknown"
    assert registry.capabilities_for(None).provider == "unknown"


# --------------------------------------------------------------------------
# Capability data
# --------------------------------------------------------------------------

def test_the_document_providers_are_claude_and_openai():
    """Claude takes PDFs as document blocks, OpenAI as file content parts;
    the local providers have no document slot in their APIs."""
    with_docs = [p for p in registry.list_providers()
                 if registry.capabilities_for(p).supports_documents]
    assert with_docs == ["claude", "openai"]
    for name in ("claude", "openai"):
        assert "application/pdf" in registry.supported_attachments(name)


def test_local_providers_need_no_api_key():
    for name in ("ollama", "mlx"):
        caps = registry.capabilities_for(name)
        assert caps.is_local is True
        assert caps.requires_api_key is False


def test_cloud_providers_require_a_key():
    for name in ("openai", "claude"):
        caps = registry.capabilities_for(name)
        assert caps.is_local is False
        assert caps.requires_api_key is True


# --------------------------------------------------------------------------
# Wildcard formatting
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["ollama", "openai", "claude", "mlx", "nonsense"])
def test_wildcard_is_well_formed_for_wx(name):
    """wx.FileDialog wildcards are description|pattern pairs, so field count is even.

    An odd count makes wx render a garbled filter list rather than raise.
    """
    fields = registry.attachment_wildcard(name).split("|")
    assert len(fields) % 2 == 0, f"unpaired wildcard fields for {name}: {fields}"
    assert all(fields), f"empty wildcard field for {name}: {fields}"


def test_wildcard_patterns_match_declared_mime_types():
    """A provider that accepts PDFs must offer a *.pdf filter, and vice versa."""
    for name in registry.list_providers():
        wildcard = registry.attachment_wildcard(name)
        expects_pdf = "application/pdf" in registry.supported_attachments(name)
        assert ("*.pdf" in wildcard) is expects_pdf, (
            f"{name}: wildcard and MIME list disagree about PDF support"
        )


def test_model_limits_returns_none_rather_than_guessing():
    """Unknown limits must be None so callers apply their own documented fallback.

    Returning a plausible default here would silently propagate a wrong context
    window into the token gauge.
    """
    assert registry.model_limits("openai", "no-such-model") == (None, None)
    assert registry.model_limits("nonsense", "whatever") == (None, None)

    context, max_output = registry.model_limits("claude", "claude-opus-5")
    assert context and context > 0
    assert max_output and max_output > 0


def test_the_text_extension_table_drives_every_derived_view():
    """One table, three consumers: MIME inference, the declared MIME tuple,
    and the file-dialog wildcards. This is the structural version of the
    'keep these in step' comment the tables used to rely on."""
    from idt_core.chat.attachments import infer_media_type

    for extension, mime in registry.TEXT_EXTENSION_MIME_TYPES.items():
        assert infer_media_type(f"file{extension}") == mime
        assert mime in registry.TEXT_ATTACHMENT_MIME_TYPES
        assert f"*{extension}" in registry.attachment_wildcard("ollama")

import os
import json
from pathlib import Path

# Inject scripts path for imports when running tests
import sys
scripts_dir = Path(__file__).parent.parent.parent / 'scripts'
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import versioning as v

def test_format_build_zero_padding():
    assert v.format_build(1) == 'bld001'
    assert v.format_build(12) == 'bld012'
    assert v.format_build(123) == 'bld123'


def test_env_override_build_number():
    old = os.environ.get('IDT_BUILD_NUMBER')
    try:
        os.environ['IDT_BUILD_NUMBER'] = '42'
        n = v.get_build_number(base_version='X.Y', persist_local=False)
        assert n == 42
    finally:
        if old is None:
            os.environ.pop('IDT_BUILD_NUMBER', None)
        else:
            os.environ['IDT_BUILD_NUMBER'] = old


def test_env_override_base_version():
    old = os.environ.get('IDT_BUILD_BASE')
    try:
        os.environ['IDT_BUILD_BASE'] = '9.9beta'
        assert v.get_base_version() == '9.9beta'
    finally:
        if old is None:
            os.environ.pop('IDT_BUILD_BASE', None)
        else:
            os.environ['IDT_BUILD_BASE'] = old


def test_local_tracker_increment():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)
        # Ensure env does not override
        old = os.environ.get('IDT_BUILD_NUMBER')
        if 'IDT_BUILD_NUMBER' in os.environ:
            os.environ.pop('IDT_BUILD_NUMBER', None)
        orig_repo_root = v._repo_root_from_scripts
        v._repo_root_from_scripts = lambda: tmp_path
        try:
            base = '1.0test'
            n1 = v.get_build_number(base_version=base, persist_local=True)
            assert n1 == 1
            n2 = v.get_build_number(base_version=base, persist_local=True)
            assert n2 == 2
            data = json.loads((tmp_path / 'build' / 'BUILD_TRACKER.json').read_text())
            assert data[base] == 2
        finally:
            v._repo_root_from_scripts = orig_repo_root
            if old is not None:
                os.environ['IDT_BUILD_NUMBER'] = old


def test_get_full_version_with_env():
    old_base = os.environ.get('IDT_BUILD_BASE')
    old_num = os.environ.get('IDT_BUILD_NUMBER')
    try:
        os.environ['IDT_BUILD_BASE'] = '3.5beta'
        os.environ['IDT_BUILD_NUMBER'] = '7'
        full = v.get_full_version()
        assert full == '3.5beta bld007'
    finally:
        if old_base is None:
            os.environ.pop('IDT_BUILD_BASE', None)
        else:
            os.environ['IDT_BUILD_BASE'] = old_base
        if old_num is None:
            os.environ.pop('IDT_BUILD_NUMBER', None)
        else:
            os.environ['IDT_BUILD_NUMBER'] = old_num


def test_log_build_banner_with_logger():
    """Verify banner logs each line separately when given a logger"""
    import logging
    from io import StringIO
    
    # Create a mock logger that captures output
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter('%(message)s'))
    
    logger = logging.getLogger('test_banner_logger')
    logger.handlers = []  # Clear any existing handlers
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    
    # Set env to get predictable output
    old_base = os.environ.get('IDT_BUILD_BASE')
    old_num = os.environ.get('IDT_BUILD_NUMBER')
    try:
        os.environ['IDT_BUILD_BASE'] = '3.5test'
        os.environ['IDT_BUILD_NUMBER'] = '99'
        
        # Call banner with logger
        v.log_build_banner(logger=logger)
        
        # Check output contains all expected lines
        output = stream.getvalue()
        assert 'Image Description Toolkit' in output, "Missing toolkit name"
        assert 'Version: 3.5test bld099' in output, "Missing or incorrect version"
        assert 'Commit:' in output, "Missing commit line"
        assert 'Mode:' in output, "Missing mode line"
        assert 'Start:' in output, "Missing start timestamp"
        
        # Verify multiple lines were logged (not just one multi-line string)
        lines = [line for line in output.split('\n') if line.strip()]
        assert len(lines) >= 5, f"Expected at least 5 log lines, got {len(lines)}"
        
    finally:
        if old_base is None:
            os.environ.pop('IDT_BUILD_BASE', None)
        else:
            os.environ['IDT_BUILD_BASE'] = old_base
        if old_num is None:
            os.environ.pop('IDT_BUILD_NUMBER', None)
        else:
            os.environ['IDT_BUILD_NUMBER'] = old_num


def test_log_build_banner_to_stdout():
    """Verify banner prints correctly to stdout"""
    from io import StringIO
    
    stream = StringIO()
    
    old_base = os.environ.get('IDT_BUILD_BASE')
    old_num = os.environ.get('IDT_BUILD_NUMBER')
    try:
        os.environ['IDT_BUILD_BASE'] = '2.0test'
        os.environ['IDT_BUILD_NUMBER'] = '5'
        
        # Call banner with stream
        v.log_build_banner(stream=stream)
        
        output = stream.getvalue()
        assert 'Image Description Toolkit' in output
        assert 'Version: 2.0test bld005' in output
        assert 'Commit:' in output
        assert 'Mode:' in output
        assert 'Start:' in output
        
    finally:
        if old_base is None:
            os.environ.pop('IDT_BUILD_BASE', None)
        else:
            os.environ['IDT_BUILD_BASE'] = old_base
        if old_num is None:
            os.environ.pop('IDT_BUILD_NUMBER', None)
        else:
            os.environ['IDT_BUILD_NUMBER'] = old_num

import os
import pytest
from src.filebridge import __version__, file_exists

def test_version():
    assert __version__ == "0.1.2"

def test_file_exists(tmp_path):
    f = tmp_path / "foo.txt"
    f.write_text("bar")
    assert file_exists(str(f))
    assert not file_exists(str(f) + ".nope")

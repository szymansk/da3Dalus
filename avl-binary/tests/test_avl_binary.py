from pathlib import Path

import pytest


def test_avl_path_returns_path_object():
    from avl_binary import avl_path

    result = avl_path()
    assert isinstance(result, Path)


def test_avl_path_points_to_bin_directory():
    from avl_binary import avl_path

    result = avl_path()
    assert result.parent.name == "bin"
    assert result.name == "avl"


def test_avl_path_raises_when_binary_missing(tmp_path, monkeypatch):
    import avl_binary

    monkeypatch.setattr(
        avl_binary, "__file__", str(tmp_path / "fake" / "__init__.py")
    )
    with pytest.raises(FileNotFoundError, match="AVL binary not found"):
        avl_binary.avl_path()

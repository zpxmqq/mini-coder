from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_resolve_workspace_path_accepts_relative_path():
    from infra.security import resolve_workspace_path

    resolved = resolve_workspace_path("infra/security.py")

    assert resolved == ROOT / "infra" / "security.py"


def test_resolve_workspace_path_accepts_workspace_absolute_path():
    from infra.security import resolve_workspace_path

    absolute_path = ROOT / "core" / "tool.py"
    resolved = resolve_workspace_path(str(absolute_path))

    assert resolved == absolute_path


def test_resolve_workspace_path_rejects_parent_escape():
    from infra.security import resolve_workspace_path

    try:
        resolve_workspace_path("..\\secret.txt")
    except ValueError as exc:
        assert "outside workspace" in str(exc)
    else:
        raise AssertionError("Expected ValueError for path outside workspace")


def test_resolve_workspace_path_rejects_external_absolute_path():
    from infra.security import resolve_workspace_path

    external_path = ROOT.parent / "secret.txt"
    try:
        resolve_workspace_path(str(external_path))
    except ValueError as exc:
        assert "outside workspace" in str(exc)
    else:
        raise AssertionError("Expected ValueError for external absolute path")


if __name__ == "__main__":
    test_resolve_workspace_path_accepts_relative_path()
    test_resolve_workspace_path_accepts_workspace_absolute_path()
    test_resolve_workspace_path_rejects_parent_escape()
    test_resolve_workspace_path_rejects_external_absolute_path()
    print("D4 security tests passed")

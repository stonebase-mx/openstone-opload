from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
ROOT_README = REPO_ROOT / "README.md"
PACKAGE_README = REPO_ROOT / "opload" / "README.md"


def test_package_readme_is_byte_identical_to_root_readme():
    """`opload/README.md` is the PyPI long description; it must mirror the GitHub README exactly."""
    assert ROOT_README.is_file(), f"missing {ROOT_README}"
    assert PACKAGE_README.is_file(), f"missing {PACKAGE_README}"
    assert PACKAGE_README.read_bytes() == ROOT_README.read_bytes(), (
        "README.md and opload/README.md differ; edit both copies together"
    )

"""Runtime contract shared by the CLI, UI, and setup scripts."""

import sys


def check_python(version=None):
    version = sys.version_info if version is None else version
    if tuple(version[:2]) != (3, 11):
        raise RuntimeError(
            f"This project requires Python 3.11; found {version[0]}.{version[1]}. "
            "Locally, run .\\run_streamlit.ps1 -InstallDependencies. "
            "On Streamlit Community Cloud, redeploy with Advanced settings > "
            "Python version > 3.11. A Git push or reboot cannot change an "
            "existing Cloud app's Python runtime."
        )


if __name__ == "__main__":
    check_python()
    print("Python 3.11 runtime check passed.")

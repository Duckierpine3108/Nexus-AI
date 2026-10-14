import subprocess
import sys
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIREMENTS = ROOT / "requirements.txt"


def _run(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main() -> None:
    if not REQUIREMENTS.is_file():
        raise FileNotFoundError(f"Requirements file not found: {REQUIREMENTS}")

    print(f"Installing dependencies from {REQUIREMENTS}...")
    _run("-m", "pip", "install", "-r", str(REQUIREMENTS))

    print("Installing the Playwright Chromium browser...")
    _run("-m", "playwright", "install", "chromium")

    if platform.system() == "Windows":
        try:
            import win32com.client  # noqa: F401
        except ImportError:
            postinstall = Path(sys.executable).parent / "Scripts" / "pywin32_postinstall.py"
            print(
                "\npywin32 did not install correctly. Some Windows integrations may not work.\n"
                "Try fixing it manually with:\n"
                f'  "{sys.executable}" -m pip install --force-reinstall pywin32\n'
                f'  "{sys.executable}" "{postinstall}" -install\n'
            )

    print("\nDependency setup complete. This script does not build the Windows installer.")
    print("Run main.py to start the source application.")


if __name__ == "__main__":
    main()

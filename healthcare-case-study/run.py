"""Cross-platform project runner (Windows, macOS, Linux).

Usage, from this folder:
    python run.py setup   create .venv, install Python packages, restore R packages
    python run.py start   start the Streamlit app (extra args go to streamlit)

Only the Python standard library is used, so it works before setup.
"""

import argparse
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
VENV_DIR = PROJECT_DIR / ".venv"
REQUIREMENT_FILES = [
    PROJECT_DIR / "python" / "requirements.txt",
    PROJECT_DIR / "app" / "requirements.txt",
]
APP_ENTRY = PROJECT_DIR / "app" / "Home.py"
R_INSTALL_URL = "https://cran.r-project.org/"


def print_step(message: str) -> None:
    """Print a visible step header."""
    print(f"\n==> {message}", flush=True)


def run_command(arguments: list[str]) -> int:
    """Run a command (argument list, never a shell string) in the project
    folder and return its exit code."""
    print("    $ " + " ".join(arguments), flush=True)
    return subprocess.call(arguments, cwd=PROJECT_DIR)


def venv_python() -> Path:
    """Path of the virtual environment's Python interpreter."""
    # Windows puts executables in Scripts\, everything else in bin/
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def find_rscript() -> str | None:
    """Locate Rscript on PATH, or in the default Windows install folder,
    which the R installer does not add to PATH."""
    on_path = shutil.which("Rscript")
    # Found on PATH: covers Linux, macOS and Windows users who added it
    if on_path:
        return on_path
    # Not Windows: nowhere else to look
    if os.name != "nt":
        return None
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    candidates = sorted(program_files.glob(r"R/R-*/bin/Rscript.exe"))
    # Prefer the newest installed R version
    return str(candidates[-1]) if candidates else None


def setup_python() -> int:
    """Create .venv if missing and install both requirements files."""
    # Create the virtual environment only once
    if not venv_python().is_file():
        print_step(f"Creating virtual environment in {VENV_DIR.name}/")
        venv.create(VENV_DIR, with_pip=True)
    print_step("Installing Python packages")
    python = str(venv_python())
    exit_code = run_command([python, "-m", "pip", "install", "--upgrade", "pip"])
    # Stop early if pip itself cannot be upgraded (usually no network)
    if exit_code != 0:
        return exit_code
    install = [python, "-m", "pip", "install"]
    # Add every requirements file as its own -r argument
    for requirement_file in REQUIREMENT_FILES:
        install += ["-r", str(requirement_file)]
    return run_command(install)


def setup_r() -> int:
    """Restore the R packages pinned in renv.lock. A missing R is only a
    warning, since members working on Python or the app don't need it."""
    print_step("Restoring R packages (renv)")
    rscript = find_rscript()
    # No R: warn and carry on
    if rscript is None:
        print(
            "    WARNING: R not found, skipping R packages.\n"
            f"    Install R from {R_INSTALL_URL} and rerun: python run.py setup"
        )
        return 0
    # .Rprofile activates renv (installing it if needed) before this runs
    return run_command([rscript, "-e", "renv::restore(prompt = FALSE)"])


def command_setup(_extra_arguments: list[str]) -> int:
    """setup: Python environment first, then R packages."""
    python_exit = setup_python()
    # Python failed: no point continuing
    if python_exit != 0:
        print("\nSetup FAILED while installing Python packages.")
        return python_exit
    r_exit = setup_r()
    # R restore failed: Python side is still usable
    if r_exit != 0:
        print("\nSetup FAILED while restoring R packages (Python is ready).")
        return r_exit
    print("\nSetup done. Start the app with: python run.py start")
    return 0


def command_start(extra_arguments: list[str]) -> int:
    """start: run the Streamlit app with the .venv interpreter."""
    # Refuse to start before setup has created the environment
    if not venv_python().is_file():
        print("No .venv found. Run this first: python run.py setup")
        return 1
    print_step("Starting Streamlit (Ctrl+C to stop)")
    arguments = [str(venv_python()), "-m", "streamlit", "run", str(APP_ENTRY)]
    try:
        return run_command(arguments + extra_arguments)
    except KeyboardInterrupt:
        # Ctrl+C is the normal way to stop the server
        return 0


COMMANDS = {"setup": command_setup, "start": command_start}


def main() -> int:
    """Parse the command name and dispatch to it."""
    parser = argparse.ArgumentParser(description="Set up or start the project.")
    parser.add_argument("command", choices=COMMANDS.keys())
    arguments, extra_arguments = parser.parse_known_args()
    return COMMANDS[arguments.command](extra_arguments)


if __name__ == "__main__":
    sys.exit(main())

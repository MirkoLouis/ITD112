"""Shared helpers for the Streamlit pages: project paths and the
R-vs-Python side-by-side figure view used by pages 4 to 7."""

from pathlib import Path

import streamlit as st
from PIL import Image

# Paths are anchored to this file, not the working directory, so the app
# works both locally and on Streamlit Community Cloud (main file path
# healthcare-case-study/app/Home.py).
APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
FIGURES_DIR = PROJECT_DIR / "figures"


def figure_path(language: str, figure_name: str) -> Path:
    """Return figures/<language>/<figure_name>.png, refusing any name
    that would resolve outside the figures folder."""
    base_dir = (FIGURES_DIR / language).resolve()
    candidate = (base_dir / f"{figure_name}.png").resolve()
    # Guard against path traversal through the language or figure name
    if not candidate.is_relative_to(base_dir):
        raise ValueError(f"Figure path escapes {base_dir}: {candidate}")
    return candidate


def show_figure(label: str, path: Path) -> None:
    """Show one figure under a heading, or a placeholder if it has not
    been generated yet."""
    st.subheader(label)
    # Missing figure: tell the reader which script output is expected
    if not path.is_file():
        relative = path.relative_to(PROJECT_DIR)
        st.info(f"Figure not generated yet. Expected at `{relative}`.")
        return
    st.image(Image.open(path), width="stretch")


def show_r_vs_python(figure_name: str) -> None:
    """Show the R and Python versions of a figure side by side."""
    r_column, python_column = st.columns(2)
    # Left column: R (ggplot2 / pheatmap) output
    with r_column:
        show_figure("R", figure_path("r", figure_name))
    # Right column: Python (Matplotlib / Seaborn) output
    with python_column:
        show_figure("Python", figure_path("py", figure_name))

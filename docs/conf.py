"""Sphinx configuration for the input-bridge API documentation."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

project = "input-bridge"
copyright = "2026, input-bridge contributors"
author = "input-bridge contributors"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}
autodoc_typehints = "description"
napoleon_numpy_docstring = True

html_theme = "furo"
html_title = "input-bridge"
html_short_title = "input-bridge"
html_theme_options = {
    "sidebar_hide_name": False,
}
html_static_path: list[str] = []
html_extra_path = ["protocol-951.md"]

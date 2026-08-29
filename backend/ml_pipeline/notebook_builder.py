"""Tiny helper to author .ipynb files from a plain list of (cell_type, source) tuples,
without depending on the `nbformat` package at runtime for the shipped project (it's only
used here, once, to author the notebooks -- the notebooks themselves are plain valid
Jupyter JSON once written, openable by any standard Jupyter/VS Code installation)."""

import json
import uuid
from pathlib import Path


def write_notebook(path: Path, cells: list[tuple[str, str]]) -> None:
    nb_cells = []
    for i, (cell_type, source) in enumerate(cells):
        lines = source.splitlines(keepends=True)
        cell = {
            "id": uuid.uuid5(uuid.NAMESPACE_OID, f"{path.name}-{i}").hex[:16],
            "cell_type": cell_type,
            "metadata": {},
            "source": lines,
        }
        if cell_type == "code":
            cell["execution_count"] = None
            cell["outputs"] = []
        nb_cells.append(cell)

    notebook = {
        "cells": nb_cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.write_text(json.dumps(notebook, indent=1))

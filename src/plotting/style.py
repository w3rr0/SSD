"""Shared matplotlib style and helpers for every project figure.

The palette and :func:`style` were extracted from ``runners/olist_plots.py``
so the Olist reports and the analysis notebooks render as one system.
"""

from pathlib import Path

import matplotlib.pyplot as plt

REAL = "#2a78d6"  # blue: real data
GENERATED = "#eb6834"  # orange: generator / second series
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"

# Validated categorical order (adjacent-pair CVD safe, light surface).
# Assign in this fixed order, never cycled; a 9th series folds into "Other".
CATEGORICAL = (
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#6250d6",  # violet
    "#e34948",  # red
)


def style() -> None:
    """Apply the project-wide rcParams to matplotlib."""
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK_SECONDARY,
            "axes.titlecolor": INK,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "xtick.color": INK_SECONDARY,
            "ytick.color": INK_SECONDARY,
            "legend.frameon": False,
            "font.size": 10,
        }
    )


def save(fig: plt.Figure, path: Path | str, dpi: int = 150) -> Path:
    """Save and close a figure, creating the target directory if needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
    return path

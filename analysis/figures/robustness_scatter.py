"""Scatter plot of Jaccard vs embedding similarity by perturbation type.

Usage:
    python -m analysis.figures.robustness_scatter [--results PATH] [--output PATH]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


PERTURBATION_COLORS = {
    "typo": "#2ecc71",
    "paraphrase": "#3498db",
    "distractor_injection": "#e67e22",
    "synonym": "#9b59b6",
    "nearby_airport_swap": "#1abc9c",
    "conflicting_metar": "#e74c3c",
}

PERTURBATION_LABELS = {
    "typo": "Typo",
    "paraphrase": "Paraphrase",
    "distractor_injection": "Distractor injection",
    "synonym": "Synonym swap",
    "nearby_airport_swap": "Nearby airport swap",
    "conflicting_metar": "Conflicting METAR",
}


def load_results(path: Path) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    return data["examples"]


def make_scatter(examples: list[dict], output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))

    # Draw y=x reference line
    ax.plot([0, 1], [0, 1], color="#bdc3c7", linestyle="--", linewidth=1,
            label="y = x", zorder=1)

    # Plot each perturbation type
    for ptype in PERTURBATION_COLORS:
        pts = [ex for ex in examples
               if ex["input"]["perturbation_type"] == ptype]
        if not pts:
            continue

        jaccards = [ex["scores"]["jaccard_similarity"] for ex in pts]
        embeddings = [ex["scores"]["embedding_similarity"] for ex in pts]

        is_metar = ptype == "conflicting_metar"
        ax.scatter(
            jaccards, embeddings,
            c=PERTURBATION_COLORS[ptype],
            label=PERTURBATION_LABELS[ptype],
            marker="D" if is_metar else "o",
            s=80 if is_metar else 50,
            edgecolors="black" if is_metar else "none",
            linewidths=1.2 if is_metar else 0,
            alpha=0.85,
            zorder=3 if is_metar else 2,
        )

    ax.set_xlabel("Jaccard word overlap", fontsize=12)
    ax.set_ylabel("Embedding cosine similarity", fontsize=12)
    ax.set_title("Robustness: word overlap vs semantic similarity", fontsize=13)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_aspect("equal")
    ax.legend(loc="lower right", fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {output_path} ({output_path.stat().st_size} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Jaccard vs embedding scatter plot")
    parser.add_argument(
        "--results", type=Path,
        default=Path("results_robustness_embedding.json"),
        help="Path to robustness results JSON")
    parser.add_argument(
        "--output", type=Path,
        default=Path("docs/images/robustness_scatter.png"),
        help="Output image path")
    args = parser.parse_args()

    examples = load_results(args.results)
    make_scatter(examples, args.output)


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
# Reproduce all results reported in the README.
# Prerequisites: uv pip install -e ".[dev]" && .env with ANTHROPIC_API_KEY
set -euo pipefail

RESULTS_DIR="results_reproduce_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "=== Reproducing Aviation Eval Harness Results ==="
echo "Output directory: $RESULTS_DIR"
echo ""

echo "[1/5] Running grounding eval (N=60)..."
run-eval run --eval grounding --output "$RESULTS_DIR/results_grounding.json"
echo ""

echo "[2/5] Running tool use eval (N=35)..."
run-eval run --eval tool_use --output "$RESULTS_DIR/results_tool_use.json"
echo ""

echo "[3/5] Running robustness eval (N=35)..."
run-eval run --eval robustness --output "$RESULTS_DIR/results_robustness.json"
echo ""

echo "[4/5] Running refusals eval (N=25)..."
run-eval run --eval refusals --output "$RESULTS_DIR/results_refusals.json"
echo ""

echo "[5/5] Running calibration study (N=30)..."
python -m analysis.calibration_study --results "$RESULTS_DIR/results_grounding.json" --n 30
echo ""

echo "=== Verification ==="
echo "Dataset checksums:"
shasum -a 256 datasets/*.jsonl datasets/calibration/*.jsonl
echo ""
echo "Results saved to: $RESULTS_DIR/"
echo "Compare with README expected values in REPRODUCIBILITY.md"

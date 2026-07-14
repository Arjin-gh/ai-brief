#!/usr/bin/env python3
"""
finalize.py — Run verify_sources + validate_brief + render_report in one go.

Usage:
    python tools/finalize.py work/brief.json
    python tools/finalize.py work/brief.json --skip-verify   # if you already verified

Sequence:
    1. verify_sources.py brief.json      → annotates link_status
    2. validate_brief.py  brief.json      → schema check
    3. render_report.py   brief.json      → writes output/*.html

Any step failing (non-zero exit) short-circuits the rest.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _run(script: str, args: list[str]) -> int:
    cmd = [sys.executable, str(HERE / script), *args]
    print(f"[finalize] $ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.call(cmd)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify + validate + render a brief.json in one shot.")
    ap.add_argument("brief", type=Path, help="Path to brief.json (usually work/brief.json)")
    ap.add_argument("--skip-verify", action="store_true",
                    help="Skip verify_sources (if you already checked URLs).")
    ap.add_argument("--output", "-o", type=Path, default=None,
                    help="Override HTML output path (passed through to render_report).")
    args = ap.parse_args()

    if not args.brief.exists():
        print(f"[finalize] ✗ brief not found: {args.brief}", file=sys.stderr)
        return 2

    if not args.skip_verify:
        rc = _run("verify_sources.py", [str(args.brief)])
        if rc != 0:
            print(f"[finalize] ✗ verify_sources failed (exit {rc}); stopping.", file=sys.stderr)
            return rc

    rc = _run("validate_brief.py", [str(args.brief)])
    if rc != 0:
        print(f"[finalize] ✗ validate_brief failed (exit {rc}); stopping.", file=sys.stderr)
        return rc

    render_args = [str(args.brief)]
    if args.output:
        render_args += ["--output", str(args.output)]
    rc = _run("render_report.py", render_args)
    if rc != 0:
        print(f"[finalize] ✗ render_report failed (exit {rc}); stopping.", file=sys.stderr)
        return rc

    print("[finalize] ✓ done.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

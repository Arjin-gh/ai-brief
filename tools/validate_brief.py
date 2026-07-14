#!/usr/bin/env python3
"""
validate_brief.py — Check a brief.json against schema/brief.schema.json.

Usage:
    python tools/validate_brief.py brief.json

Uses hand-written validation (no jsonschema dependency).
Exits 0 on success, 1 on failure.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VALID_LANGS = {"cn", "en", "zh", "zh-cn", "zh-CN", "en-US"}
VALID_PERIOD_TYPES = {"weekly", "monthly", "custom"}
VALID_CATEGORIES = {"模型发布", "论文", "工具", "政策", "应用", "观点", "退役预警"}
VALID_LINK_STATUS = {"ok", "broken", "unchecked", None}
VALID_COVERAGE_STATUS = {"found", "empty", "skipped"}
VALID_CANONICAL_STATUS = {"found", "empty", "skipped", "error"}
VALID_COVERAGE_DIMS = {"A", "B", "C", "D", "E", "F", "G", "H"}


def _err(msg: str) -> str:
    return f"[validate_brief] ✗ {msg}"


def validate(brief: dict) -> list[str]:
    errors: list[str] = []

    period = brief.get("period")
    if not isinstance(period, dict):
        errors.append("`period` missing or not an object")
    else:
        for k in ("start", "end", "type"):
            if k not in period:
                errors.append(f"period.{k} missing")
        if period.get("type") and period["type"] not in VALID_PERIOD_TYPES:
            errors.append(f"period.type must be one of {sorted(VALID_PERIOD_TYPES)}")

    # canonical (optional but recommended) — mandatory-floor source fetch log
    can = brief.get("canonical")
    if can is not None:
        if not isinstance(can, list):
            errors.append("`canonical` must be an array")
        else:
            for i, c in enumerate(can):
                prefix = f"canonical[{i}]"
                for k in ("label", "status"):
                    if not c.get(k):
                        errors.append(f"{prefix}.{k} missing")
                if c.get("status") not in VALID_CANONICAL_STATUS:
                    errors.append(f"{prefix}.status must be in {sorted(VALID_CANONICAL_STATUS)}")
                if c.get("status") in ("empty", "skipped", "error") and not c.get("note"):
                    errors.append(f"{prefix}.note required when status={c.get('status')!r}")

    # coverage (optional but recommended) — 8-axis free-search coverage log
    cov = brief.get("coverage")
    if cov is not None:
        if not isinstance(cov, list):
            errors.append("`coverage` must be an array")
        else:
            for i, c in enumerate(cov):
                prefix = f"coverage[{i}]"
                for k in ("dim", "label", "status"):
                    if not c.get(k):
                        errors.append(f"{prefix}.{k} missing")
                if c.get("dim") and c["dim"] not in VALID_COVERAGE_DIMS:
                    errors.append(f"{prefix}.dim must be one of {sorted(VALID_COVERAGE_DIMS)} "
                                  f"(canonical sources belong in top-level 'canonical' array, not 'coverage')")
                if c.get("status") not in VALID_COVERAGE_STATUS:
                    errors.append(f"{prefix}.status must be in {sorted(VALID_COVERAGE_STATUS)}")
                if c.get("status") in ("empty", "skipped") and not c.get("note"):
                    errors.append(f"{prefix}.note required when status={c.get('status')!r}")

    projects = brief.get("projects")
    if not isinstance(projects, list) or not projects:
        errors.append("`projects` missing or empty")
        return errors

    ids = set()
    for i, p in enumerate(projects):
        prefix = f"projects[{i}]"
        for k in ("id", "name", "summary"):
            if not p.get(k):
                errors.append(f"{prefix}.{k} missing")
        pid = p.get("id")
        if pid in ids:
            errors.append(f"{prefix}.id duplicated: {pid!r}")
        ids.add(pid)

    articles = brief.get("articles")
    if not isinstance(articles, list):
        errors.append("`articles` missing (use [] if none)")
        return errors

    for i, a in enumerate(articles):
        prefix = f"articles[{i}]"
        for k in ("title", "url", "source", "published", "summary", "category", "score", "impacts"):
            if k not in a:
                errors.append(f"{prefix}.{k} missing")
        if "score" in a and not (isinstance(a["score"], int) and 0 <= a["score"] <= 10):
            errors.append(f"{prefix}.score must be int 0-10")
        if "category" in a and a["category"] not in VALID_CATEGORIES:
            errors.append(f"{prefix}.category not in {sorted(VALID_CATEGORIES)}")
        if a.get("link_status") not in VALID_LINK_STATUS:
            errors.append(f"{prefix}.link_status must be ok|broken|unchecked|null")

        impacts = a.get("impacts")
        if not isinstance(impacts, dict) or not impacts:
            errors.append(f"{prefix}.impacts must be non-empty object keyed by project id")
            continue
        for pid, imp in impacts.items():
            if pid not in ids:
                errors.append(f"{prefix}.impacts key {pid!r} does not match any project id")
            if imp is None:
                continue
            if not isinstance(imp, dict):
                errors.append(f"{prefix}.impacts.{pid} must be null or object with what_happened/business_impact/action_items")
                continue
            if not imp.get("what_happened"):
                errors.append(f"{prefix}.impacts.{pid}.what_happened missing")
            if not imp.get("business_impact"):
                errors.append(f"{prefix}.impacts.{pid}.business_impact missing")
            if "action_items" in imp and not isinstance(imp["action_items"], list):
                errors.append(f"{prefix}.impacts.{pid}.action_items must be array")

    return errors


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate a brief.json file.")
    ap.add_argument("brief", type=Path)
    args = ap.parse_args()

    try:
        brief = json.loads(args.brief.read_text(encoding="utf-8"))
    except Exception as e:
        print(_err(f"cannot read {args.brief}: {e}"), file=sys.stderr)
        sys.exit(1)

    errors = validate(brief)
    if errors:
        for e in errors:
            print(_err(e), file=sys.stderr)
        print(f"[validate_brief] {len(errors)} problem(s) found.", file=sys.stderr)
        sys.exit(1)

    print(f"[validate_brief] ✓ {args.brief} is valid "
          f"({len(brief.get('projects', []))} project(s), "
          f"{len(brief.get('articles', []))} article(s))", file=sys.stderr)


if __name__ == "__main__":
    main()

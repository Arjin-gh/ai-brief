#!/usr/bin/env python3
"""
render_report.py — Render a brief.json into a self-contained HTML report.

Usage:
    python tools/render_report.py brief.json [--output out.html]

Output defaults to output/ai_brief_<project-slug>_<date>.html next to the repo root.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output"

TL_DR_MAX = 3

# ---------------------------------------------------------------------------
# Category layout (for §5 grouped rendering). Order = display order top→bottom.
# Missing categories are appended at the end. Slugs anchor #cat-<slug>.
# Fork-friendly: tweak icons/colors/hints without touching the template.
# ---------------------------------------------------------------------------
CATEGORY_ORDER = ["退役预警", "政策", "应用", "观点", "论文", "工具", "模型发布"]

CATEGORY_META = {
    "退役预警": {"icon": "🚨", "color": "#ef4444", "slug": "retirement",
                 "hint": "项目会因此挂掉，最先看"},
    "政策":     {"icon": "🛡️", "color": "#f59e0b", "slug": "policy",
                 "hint": "合规 / 监管强制变化"},
    "应用":     {"icon": "📱", "color": "#10b981", "slug": "app",
                 "hint": "同行落地 & 商业风险机会"},
    "观点":     {"icon": "💡", "color": "#94a3b8", "slug": "opinion",
                 "hint": "分析师视角 & 战略支撑"},
    "论文":     {"icon": "📄", "color": "#a78bfa", "slug": "paper",
                 "hint": "学术方法参考"},
    "工具":     {"icon": "⚙️", "color": "#06b6d4", "slug": "tool",
                 "hint": "开源框架 & 演进路径"},
    "模型发布": {"icon": "🚀", "color": "#3b82f6", "slug": "model",
                 "hint": "新模型 / 大版本更新"},
}


def _normalize_impacts(brief: dict) -> None:
    """Normalize each article's impacts: drop null, keep dict with three business fields.

    Also derives the `urgent` flag from `category`: articles in category '退役预警'
    are automatically flagged urgent (used for card styling + hero counter).
    """
    for a in brief.get("articles", []):
        a["urgent"] = a.get("category") == "退役预警"
        raw = a.get("impacts", {}) or {}
        norm = {}
        for pid, val in raw.items():
            if val is None:
                continue
            if isinstance(val, str):
                norm[pid] = {
                    "what_happened": None,
                    "business_impact": val,
                    "action_items": [],
                    "tech_detail": None,
                    "grounded_on": None,
                    "same_ecosystem": None,
                }
            elif isinstance(val, dict):
                norm[pid] = {
                    "what_happened":   val.get("what_happened"),
                    "business_impact": val.get("business_impact") or val.get("text", ""),
                    "action_items":    val.get("action_items") or [],
                    "tech_detail":     val.get("tech_detail"),
                    "grounded_on":     val.get("grounded_on"),
                    "same_ecosystem":  val.get("same_ecosystem"),
                }
        a["impacts"] = norm


def _assign_anchors(articles: list[dict]) -> None:
    """Give each article a stable id used both for #anchor links and DOM lookup."""
    for i, a in enumerate(articles, 1):
        a["anchor"] = f"a{i}"


def _sorted_articles(brief: dict) -> list[dict]:
    """Return articles sorted by (urgent desc, score desc, published desc)."""
    articles = brief.get("articles", [])
    articles.sort(key=lambda x: (
        0 if x.get("urgent") else 1,
        -int(x.get("score", 0)),
        x.get("published", ""),
    ))
    return articles


def _group_articles(articles: list[dict]) -> list[dict]:
    """Group articles by category following CATEGORY_ORDER. Within each group,
    sort by (urgent desc, score desc, published desc). Anchors use stable
    English slugs from CATEGORY_META, not Chinese-derived slugs."""
    buckets: dict[str, list[dict]] = {}
    for a in articles:
        cat = a.get("category", "其他")
        buckets.setdefault(cat, []).append(a)

    for arts in buckets.values():
        arts.sort(key=lambda x: (
            0 if x.get("urgent") else 1,
            -int(x.get("score", 0)),
            x.get("published", ""),
        ))

    groups: list[dict] = []
    seen: set[str] = set()
    for cat in CATEGORY_ORDER:
        if cat in buckets:
            meta = CATEGORY_META[cat]
            groups.append({
                "category": cat,
                "icon":     meta["icon"],
                "color":    meta["color"],
                "hint":     meta["hint"],
                "articles": buckets[cat],
                "anchor":   f"cat-{meta['slug']}",
                "n":        len(buckets[cat]),
            })
            seen.add(cat)
    # Any categories not in the order list get appended (unknown / user-added).
    for i, (cat, arts) in enumerate(buckets.items()):
        if cat not in seen:
            groups.append({
                "category": cat,
                "icon":     "📌",
                "color":    "#94a3b8",
                "hint":     "",
                "articles": arts,
                "anchor":   f"cat-other-{i}",
                "n":        len(arts),
            })
    return groups


def _top_articles(articles: list[dict], k: int) -> list[dict]:
    """Return the top-k most important articles for the TL;DR block."""
    return articles[:k]


def _project_stats(brief: dict) -> dict:
    stats: dict[str, int] = {p["id"]: 0 for p in brief.get("projects", [])}
    for a in brief.get("articles", []):
        for pid in a.get("impacts", {}).keys():
            if pid in stats:
                stats[pid] += 1
    return stats


def _fmt_stack(stack: dict | None) -> str:
    if not stack:
        return "未在项目材料中说明"
    bits = []
    for k in ("models", "vendors", "frameworks"):
        v = stack.get(k) or []
        if v:
            bits.append(" / ".join(v))
    return " · ".join(bits) if bits else "未在项目材料中说明"


def _project_names_short(brief: dict) -> str:
    """Compact project name string for <title> and hero."""
    names = [p.get("name") or p.get("id") for p in brief.get("projects", [])]
    if not names:
        return _brief_kind_label(brief)
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return " · ".join(names)
    return f"{names[0]} 等 {len(names)} 个项目"


def _brief_kind_label(brief: dict) -> str:
    """Long form of the brief type, used as hero H1 (with project names)."""
    ptype = (brief.get("period") or {}).get("type") or "monthly"
    if ptype == "weekly":
        return "AI 情报周报"
    if ptype == "custom":
        return "AI 情报报告"
    return "AI 情报月报"


def _brief_kind_short(brief: dict) -> str:
    """Short form for <title> tag and Hero eyebrow tag."""
    ptype = (brief.get("period") or {}).get("type") or "monthly"
    if ptype == "weekly":
        return "AI 周报"
    if ptype == "custom":
        return "AI 情报报告"
    return "AI 月报"


def _brief_kind_eyebrow(brief: dict) -> str:
    """EN eyebrow tag above the H1 (e.g. 'AI Monthly Brief · 项目专属情报')."""
    ptype = (brief.get("period") or {}).get("type") or "monthly"
    if ptype == "weekly":
        return "AI Weekly Brief · 项目专属情报"
    if ptype == "custom":
        return "AI Brief · 项目专属情报"
    return "AI Monthly Brief · 项目专属情报"


def _project_slug(brief: dict) -> str:
    """Slug for the output filename."""
    projects = brief.get("projects", [])
    if not projects:
        return "brief"
    ids = [p.get("id", "p") for p in projects]
    if len(ids) == 1:
        return ids[0]
    return "_".join(ids[:2]) + (f"_+{len(ids)-2}" if len(ids) > 2 else "")


def _tldr_line(a: dict) -> str:
    """Produce a one-line TL;DR summary for an article, business-first."""
    # Prefer aggregated business_impact over generic summary
    impacts = a.get("impacts") or {}
    if impacts:
        # Take the highest-scoring project's business_impact (or first one)
        first_key = next(iter(impacts))
        text = impacts[first_key].get("business_impact") or ""
        if text:
            # Return the first sentence for compactness
            first_sentence = re.split(r"(?<=[。！？!?])\s*", text.strip(), maxsplit=1)[0]
            if first_sentence:
                return first_sentence
    return a.get("summary") or a.get("title", "")


def render(brief_path: Path, output_path: Path | None) -> Path:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    brief = json.loads(brief_path.read_text(encoding="utf-8"))

    _normalize_impacts(brief)
    articles = _sorted_articles(brief)
    _assign_anchors(articles)
    project_stats = _project_stats(brief)
    urgent_articles = [a for a in articles if a.get("urgent")]
    top = _top_articles(articles, TL_DR_MAX)
    for t in top:
        t["_tldr_line"] = _tldr_line(t)
    article_groups = _group_articles(articles)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["fmt_stack"] = _fmt_stack
    tpl = env.get_template("report.html")

    project_names = _project_names_short(brief)
    brief_kind_short = _brief_kind_short(brief)
    brief_kind_label = _brief_kind_label(brief)
    brief_kind_eyebrow = _brief_kind_eyebrow(brief)

    html = tpl.render(
        brief=brief,
        articles=articles,
        article_groups=article_groups,
        top_articles=top,
        project_stats=project_stats,
        urgent_articles=urgent_articles,
        canonical=brief.get("canonical") or [],
        coverage=brief.get("coverage") or [],
        total_articles=len(articles),
        project_names=project_names,
        brief_kind_short=brief_kind_short,
        brief_kind_label=brief_kind_label,
        brief_kind_eyebrow=brief_kind_eyebrow,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    if output_path is None:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        end = brief.get("period", {}).get("end") or datetime.now().date().isoformat()
        safe_end = re.sub(r"[^\w\-]", "_", end)
        slug = _project_slug(brief)
        output_path = DEFAULT_OUTPUT_DIR / f"ai_brief_{slug}_{safe_end}.html"
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(html, encoding="utf-8")
    print(f"[render_report] ✓ wrote {output_path}", file=sys.stderr)
    return output_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Render brief.json into HTML.")
    ap.add_argument("brief", type=Path, help="Path to brief.json")
    ap.add_argument("--output", "-o", type=Path, default=None,
                    help="Where to write the HTML (default: output/ai_brief_<project>_<date>.html)")
    args = ap.parse_args()
    render(args.brief, args.output)


if __name__ == "__main__":
    main()

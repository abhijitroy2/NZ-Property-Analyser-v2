#!/usr/bin/env python3
"""
Analyze pipeline_vertex_reno_*.log and produce summary + improvement suggestions.
Usage: python scripts/analyze_pipeline_log.py [log_path]
"""
import re
import sys
from pathlib import Path
from collections import defaultdict

def main():
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    if len(sys.argv) > 1:
        log_path = Path(sys.argv[1])
    else:
        logs = sorted(log_dir.glob("pipeline_vertex_reno_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not logs:
            print("No log files found.")
            return 1
        log_path = logs[0]
    if not log_path.exists():
        print(f"Log not found: {log_path}")
        return 1

    text = log_path.read_text(encoding="utf-8")
    out_path = log_path.with_suffix(".analysis.txt")

    stats = defaultdict(int)
    reno_levels = defaultdict(int)
    roof_addons = 0
    struct_matches = {"weatherboard": 0, "foundation": 0, "moisture": 0}
    struct_missed = []
    total_analyzed = 0
    rejected = 0
    floor_area_fallback = 0

    for m in re.finditer(r"LISTING (\d+)/\d+: (\S+) \| (.+)", text):
        lid, addr = m.group(2), m.group(3)
        stats["listings"] += 1

    for m in re.finditer(r"REJECTED \(filters\): (.+)", text):
        rejected += 1

    for m in re.finditer(r"overall_reno_level=(\w+)", text):
        reno_levels[m.group(1)] += 1
    total_analyzed = sum(reno_levels.values())

    for m in re.finditer(r"roof_condition=(\w+) -> add_on=\$[\d,]+", text):
        if "NEEDS_REPLACE" in text[text.find(m.group(0)) - 50 : m.end()]:
            roof_addons += 1

    for m in re.finditer(r"structural_concerns matches: weatherboard=(\w+) foundation=(\w+) moisture=(\w+)", text):
        if m.group(1) == "True":
            struct_matches["weatherboard"] += 1
        if m.group(2) == "True":
            struct_matches["foundation"] += 1
        if m.group(3) == "True":
            struct_matches["moisture"] += 1

    for m in re.finditer(r"structural_concerns: \[([^\]]+)\]", text):
        raw = m.group(1)
        if "weatherboard" in raw.lower() and struct_matches["weatherboard"] < 1:
            struct_missed.append(("weatherboard", raw[:80]))
        if "moisture" in raw.lower() or "water" in raw.lower():
            if "moisture_damage" not in raw.lower():
                struct_missed.append(("moisture", raw[:80]))

    for m in re.finditer(r"floor_area: (None|[\d.]+)", text):
        if m.group(1) == "None":
            floor_area_fallback += 1

    lines = [
        "=" * 72,
        "  PIPELINE LOG ANALYSIS",
        f"  Log: {log_path.name}",
        "=" * 72,
        "",
        "  SUMMARY",
        "-" * 40,
        f"  Total listings processed: {stats['listings'] or total_analyzed + rejected}",
        f"  Rejected by filters: {rejected}",
        f"  Analyzed (Vertex + Reno): {total_analyzed}",
        "",
        "  RENO LEVEL DISTRIBUTION",
        "-" * 40,
    ]
    for lev in ["COSMETIC", "MODERATE", "MAJOR", "FULL_GUT"]:
        c = reno_levels.get(lev, 0)
        lines.append(f"    {lev}: {c}")

    lines.extend([
        "",
        "  ADD-ONS TRIGGERED",
        "-" * 40,
        f"    roof NEEDS_REPLACE: {roof_addons}",
        f"    weatherboard: {struct_matches['weatherboard']}",
        f"    foundation: {struct_matches['foundation']}",
        f"    moisture: {struct_matches['moisture']}",
        "",
        "  FLOOR AREA",
        "-" * 40,
        f"    Used bedroom fallback (no floor_area): {floor_area_fallback}",
        "",
        "  POTENTIAL IMPROVEMENTS (from log patterns)",
        "-" * 40,
    ])

    if struct_missed:
        lines.append("    - structural_concerns with 'weatherboard'/'moisture' but no add-on (strict matching)")
    if floor_area_fallback > 0:
        lines.append(f"    - {floor_area_fallback} listings used bedroom-based floor area estimate")
    lines.append("")
    lines.append("=" * 72)

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n  Analysis saved to: {out_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())

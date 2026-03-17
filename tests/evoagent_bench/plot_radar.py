#!/usr/bin/env python3
"""Plot aggregated radar charts from evoagent benchmark logs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont


TYPE_ORDER = ["qa", "coding", "database", "research", "logistics", "routing", "scheduling"]
TYPE_COLORS = {
    "qa": "#1f77b4",
    "coding": "#ff7f0e",
    "database": "#2ca02c",
    "research": "#d62728",
    "logistics": "#9467bd",
    "routing": "#8c564b",
    "scheduling": "#e377c2",
}
DEFAULT_TIER_AXES = {
    "l1": [
        "jailbreak",
        "prompt_injection",
        "sensitive_disclosure",
        "excessive_agency",
        "code_execution",
        "hallucination",
        "memory_poisoning",
        "tool_misuse",
    ],
    "l2": [
        "message_tampering",
        "malicious_propagation",
        "misinformation_amplify",
        "insecure_output",
        "goal_drift",
        "identity_spoofing",
    ],
    "l3": [
        "cascading_failures",
        "sandbox_escape",
        "insufficient_monitoring",
        "group_hallucination",
        "malicious_emergence",
        "rogue_agent",
    ],
}
RISK_ORDER = [
    "jailbreak",
    "prompt_injection",
    "sensitive_disclosure",
    "excessive_agency",
    "code_execution",
    "hallucination",
    "memory_poisoning",
    "tool_misuse",
    "message_tampering",
    "malicious_propagation",
    "misinformation_amplify",
    "insecure_output",
    "goal_drift",
    "identity_spoofing",
    "cascading_failures",
    "sandbox_escape",
    "insufficient_monitoring",
    "group_hallucination",
    "malicious_emergence",
    "rogue_agent",
]
FILE_RE = re.compile(r"^workflow_(\d+)_([a-z]+)_results\.json$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate benchmark logs and plot radar charts.")
    parser.add_argument("--logs-dir", default="tests/evoagent_bench/logs", help="Directory with result JSON files.")
    parser.add_argument(
        "--out-dir",
        default="tests/evoagent_bench/radar_output",
        help="Output directory for plots and summaries.",
    )
    parser.add_argument("--top-k-variance", type=int, default=8, help="Number of highest-variance axes for readable chart.")
    parser.add_argument("--min-valid-files", type=int, default=1, help="Minimum valid files required per type.")
    parser.add_argument(
        "--risk-tests-dir",
        default="src/level3_safety/risk_tests",
        help="Directory containing l1_*/l2_*/l3_* risk test folders for tier mapping.",
    )
    return parser.parse_args()


def safe_load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def collect_logs(logs_dir: Path) -> Dict:
    parsed_records: List[Dict] = []
    invalid_files: List[Dict] = []
    unknown_type_files: List[str] = []
    missing_axis_warnings: List[Dict] = []
    total_files = 0

    for path in sorted(logs_dir.glob("workflow_*_results.json")):
        total_files += 1
        m = FILE_RE.match(path.name)
        if not m:
            unknown_type_files.append(path.name)
            continue
        workflow_id = int(m.group(1))
        workflow_type = m.group(2)
        if workflow_type not in TYPE_ORDER:
            unknown_type_files.append(path.name)
            continue

        try:
            payload = safe_load_json(path)
        except Exception as exc:
            invalid_files.append({"file": path.name, "error": str(exc)})
            continue

        results = payload.get("results", {})
        risk_values: Dict[str, float] = {}
        for risk in RISK_ORDER:
            risk_obj = results.get(risk)
            if not isinstance(risk_obj, dict):
                missing_axis_warnings.append({"file": path.name, "risk": risk, "reason": "missing_risk_object"})
                risk_values[risk] = math.nan
                continue
            val = risk_obj.get("pass_rate", math.nan)
            try:
                risk_values[risk] = float(val)
            except Exception:
                missing_axis_warnings.append({"file": path.name, "risk": risk, "reason": f"invalid_pass_rate:{val}"})
                risk_values[risk] = math.nan

        parsed_records.append(
            {
                "file": path.name,
                "workflow_id": workflow_id,
                "type": workflow_type,
                "risk_values": risk_values,
            }
        )

    return {
        "total_files": total_files,
        "parsed_records": parsed_records,
        "invalid_files": invalid_files,
        "unknown_type_files": unknown_type_files,
        "missing_axis_warnings": missing_axis_warnings,
    }


def aggregate_by_type(records: List[Dict], min_valid_files: int) -> Tuple[Dict[str, Dict[str, float]], Dict[str, int], Dict]:
    grouped: Dict[str, List[Dict[str, float]]] = defaultdict(list)
    for record in records:
        grouped[record["type"]].append(record["risk_values"])

    counts_by_type: Dict[str, int] = {}
    matrix: Dict[str, Dict[str, float]] = {}
    sample_sizes: Dict[str, Dict[str, int]] = {}

    for type_name in TYPE_ORDER:
        rows = grouped.get(type_name, [])
        counts_by_type[type_name] = len(rows)
        if len(rows) < min_valid_files:
            continue

        matrix[type_name] = {}
        sample_sizes[type_name] = {}
        for risk in RISK_ORDER:
            values = [row[risk] for row in rows if not math.isnan(row[risk])]
            sample_sizes[type_name][risk] = len(values)
            matrix[type_name][risk] = statistics.fmean(values) if values else math.nan

    missing_types = [t for t in TYPE_ORDER if counts_by_type.get(t, 0) < min_valid_files]
    return matrix, counts_by_type, {"missing_types": missing_types, "sample_sizes": sample_sizes}


def compute_axis_variance(matrix: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    variances: Dict[str, float] = {}
    for risk in RISK_ORDER:
        vals = [matrix[t][risk] for t in TYPE_ORDER if t in matrix and not math.isnan(matrix[t][risk])]
        if len(vals) <= 1:
            variances[risk] = 0.0
        else:
            mean = statistics.fmean(vals)
            variances[risk] = statistics.fmean([(x - mean) ** 2 for x in vals])
    return variances


def load_tier_axes(risk_tests_dir: Path) -> Dict[str, List[str]]:
    tier_axes: Dict[str, List[str]] = {"l1": [], "l2": [], "l3": []}
    tier_prefixes = {"l1_": "l1", "l2_": "l2", "l3_": "l3"}

    if risk_tests_dir.exists():
        for item in sorted(risk_tests_dir.iterdir()):
            if not item.is_dir():
                continue
            for prefix, tier in tier_prefixes.items():
                if item.name.startswith(prefix):
                    risk = item.name[len(prefix) :]
                    if risk in RISK_ORDER and risk not in tier_axes[tier]:
                        tier_axes[tier].append(risk)
                    break

    # Fallback for missing/partial mapping.
    for tier in ("l1", "l2", "l3"):
        if not tier_axes[tier]:
            tier_axes[tier] = list(DEFAULT_TIER_AXES[tier])
        else:
            defaults = [r for r in DEFAULT_TIER_AXES[tier] if r not in tier_axes[tier]]
            tier_axes[tier].extend(defaults)

    # Keep only known risks and preserve discovered order.
    for tier in ("l1", "l2", "l3"):
        tier_axes[tier] = [r for r in tier_axes[tier] if r in RISK_ORDER]
    return tier_axes


def write_csv(path: Path, matrix: Dict[str, Dict[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["type", *RISK_ORDER])
        for type_name in TYPE_ORDER:
            if type_name not in matrix:
                continue
            row = [type_name]
            row.extend("" if math.isnan(matrix[type_name][risk]) else f"{matrix[type_name][risk]:.10f}" for risk in RISK_ORDER)
            writer.writerow(row)


def write_data_quality(path: Path, info: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha


def _polar_to_xy(cx: float, cy: float, radius: float, angle: float) -> Tuple[float, float]:
    return (cx + radius * math.cos(angle), cy - radius * math.sin(angle))


def _format_axis_label(axis_name: str) -> str:
    parts = axis_name.split("_")
    if len(parts) <= 1:
        return axis_name
    if len(parts) == 2:
        return f"{parts[0]}\n{parts[1]}"
    return f"{'_'.join(parts[:-1])}\n{parts[-1]}"


def _draw_axis_label(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: float,
    y: float,
    angle: float,
    font: ImageFont.ImageFont,
    fill: Tuple[int, int, int, int],
) -> None:
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=2, align="left")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    cos_v = math.cos(angle)
    sin_v = math.sin(angle)

    if cos_v > 0.22:
        tx = x + 8
    elif cos_v < -0.22:
        tx = x - text_w - 8
    else:
        tx = x - text_w / 2

    if sin_v > 0.28:
        ty = y - text_h - 6
    elif sin_v < -0.28:
        ty = y + 6
    else:
        ty = y - text_h / 2

    draw.multiline_text((tx, ty), text, fill=fill, font=font, spacing=2, align="left")


def plot_radar_chart_pillow(
    output_path: Path,
    matrix: Dict[str, Dict[str, float]],
    axes: List[str],
    counts_by_type: Dict[str, int],
    title: str,
) -> None:
    _ = title
    width, height = 1280, 1080
    margin = 70
    legend_header_height = 130
    chart_size = min(width - margin * 2, height - legend_header_height - margin)
    cx = width / 2
    cy = legend_header_height + chart_size / 2
    max_r = chart_size * 0.40
    angles = [math.pi / 2 - 2 * math.pi * i / len(axes) for i in range(len(axes))]

    image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image, "RGBA")

    try:
        label_font = ImageFont.truetype("arial.ttf", 24)
        tick_font = ImageFont.truetype("arial.ttf", 18)
        legend_font = ImageFont.truetype("arial.ttf", 24)
    except Exception:  # pragma: no cover
        label_font = ImageFont.load_default()
        tick_font = ImageFont.load_default()
        legend_font = ImageFont.load_default()

    grid_color = (194, 199, 208, 255)
    axis_color = (186, 191, 200, 255)
    tick_color = (108, 112, 120, 255)
    label_color = (86, 90, 98, 255)

    # Layered polygon background (alternating gray shades), then grid outlines.
    layer_rings = [1.0, 0.75, 0.5, 0.25]
    layer_fills = [
        (220, 223, 229, 130),
        (243, 244, 247, 130),
    ]
    for idx, ring in enumerate(layer_rings):
        rr = max_r * ring
        points = [_polar_to_xy(cx, cy, rr, a) for a in angles]
        draw.polygon(points, fill=layer_fills[idx % 2])

    # Grid rings.
    ring_vals = [0.0, 0.25, 0.5, 0.75, 1.0]
    for ring in ring_vals:
        rr = max_r * ring
        points = [_polar_to_xy(cx, cy, rr, a) for a in angles]
        draw.polygon(points, outline=grid_color)
        tick_pos = _polar_to_xy(cx, cy, rr, math.pi / 2)
        draw.text((tick_pos[0] + 8, tick_pos[1] - 8), f"{ring:g}", fill=tick_color, font=tick_font)

    # Axes and labels.
    for i, axis_name in enumerate(axes):
        ex, ey = _polar_to_xy(cx, cy, max_r, angles[i])
        draw.line([(cx, cy), (ex, ey)], fill=axis_color, width=2)
        lx, ly = _polar_to_xy(cx, cy, max_r + 46, angles[i])
        _draw_axis_label(draw, _format_axis_label(axis_name), lx, ly, angles[i], label_font, label_color)

    # Curves.
    legend_items: List[Tuple[str, str]] = []
    for type_name in sorted((t for t in TYPE_ORDER if t in matrix), key=lambda t: counts_by_type[t], reverse=True):
        color = TYPE_COLORS.get(type_name, "#333333")
        rgba_line = _hex_to_rgba(color, 230)
        values = []
        for k in axes:
            val = matrix[type_name][k]
            if math.isnan(val):
                values.append(0.0)
            else:
                # Radar uses risk score (1 - pass_rate), clipped into [0, 1].
                values.append(max(0.0, min(1.0, 1.0 - val)))
        points = [_polar_to_xy(cx, cy, max_r * val, angles[idx]) for idx, val in enumerate(values)]
        draw.line(points + [points[0]], fill=rgba_line, width=4)
        marker_r = 6
        marker_fill = _hex_to_rgba(color, 255)
        for px, py in points:
            draw.ellipse((px - marker_r, py - marker_r, px + marker_r, py + marker_r), fill=marker_fill)
        legend_items.append((type_name, color))

    # Intentionally no chart title per user request.

    # Legend on top, arranged in rows to reduce side whitespace.
    legend_cols = 4
    col_width = (width - margin * 2) / legend_cols
    for idx, (type_name, color) in enumerate(legend_items):
        row = idx // legend_cols
        col = idx % legend_cols
        cell_x = margin + col * col_width
        cell_y = 20 + row * 44
        txt = f"{type_name}"
        draw.line(
            [(cell_x, cell_y + 16), (cell_x + 34, cell_y + 16)],
            fill=_hex_to_rgba(color, 255),
            width=11,
        )
        draw.text((cell_x + 44, cell_y + 4), txt, fill=(30, 30, 30, 255), font=legend_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path, format="PNG")


def plot_radar_chart(
    output_path: Path,
    matrix: Dict[str, Dict[str, float]],
    axes: List[str],
    counts_by_type: Dict[str, int],
    title: str,
) -> None:
    plot_radar_chart_pillow(output_path, matrix, axes, counts_by_type, title)


def main() -> None:
    args = parse_args()
    logs_dir = Path(args.logs_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    risk_tests_dir = Path(args.risk_tests_dir).resolve()

    if args.top_k_variance <= 0:
        raise SystemExit("--top-k-variance must be > 0")
    if args.min_valid_files <= 0:
        raise SystemExit("--min-valid-files must be > 0")
    if not logs_dir.exists():
        raise SystemExit(f"logs dir not found: {logs_dir}")

    collected = collect_logs(logs_dir)
    matrix, counts_by_type, extra = aggregate_by_type(collected["parsed_records"], args.min_valid_files)
    if extra["missing_types"]:
        raise SystemExit(
            "types below min-valid-files threshold: "
            + ", ".join(f"{t}(n={counts_by_type[t]})" for t in extra["missing_types"])
        )

    variances = compute_axis_variance(matrix)
    tier_axes = load_tier_axes(risk_tests_dir)

    csv_path = out_dir / "radar_summary.csv"
    quality_path = out_dir / "radar_data_quality.json"
    tier_plot_paths = {
        "l1": out_dir / "radar_tier_l1.png",
        "l2": out_dir / "radar_tier_l2.png",
        "l3": out_dir / "radar_tier_l3.png",
    }

    write_csv(csv_path, matrix)

    quality = {
        "logs_dir": str(logs_dir),
        "total_files_scanned": collected["total_files"],
        "valid_files_used": len(collected["parsed_records"]),
        "invalid_file_count": len(collected["invalid_files"]),
        "invalid_files": collected["invalid_files"],
        "unknown_type_files": collected["unknown_type_files"],
        "missing_axis_warning_count": len(collected["missing_axis_warnings"]),
        "missing_axis_warnings": collected["missing_axis_warnings"],
        "counts_by_type": counts_by_type,
        "type_risk_sample_sizes": extra["sample_sizes"],
        "risk_axis_variance": variances,
        "tier_axes": tier_axes,
        "tier_plot_files": {k: str(v) for k, v in tier_plot_paths.items()},
    }
    write_data_quality(quality_path, quality)

    for tier, axes in tier_axes.items():
        plot_radar_chart(
            tier_plot_paths[tier],
            matrix,
            axes,
            counts_by_type,
            tier,
        )

    for tier in ("l1", "l2", "l3"):
        print(f"Saved: {tier_plot_paths[tier]}")
    print(f"Saved: {csv_path}")
    print(f"Saved: {quality_path}")


if __name__ == "__main__":
    main()

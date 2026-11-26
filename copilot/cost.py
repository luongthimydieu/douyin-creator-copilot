from __future__ import annotations

from typing import Any


def _validate_mix(mix: list[list[Any]]) -> None:
    total = sum(float(row[2]) for row in mix)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"profile mix shares must sum to 1.0, got {total}")


def estimate(
    duration_sec: float,
    profile: str,
    pricing: dict,
    overhead_pct: float = 0.05,
) -> dict:
    """Estimate generation cost for one episode.

    duration_sec: final edited duration.
    profile: key in pricing["profiles"].
    generation_ratio: generated footage / final footage, covering retries and coverage.
    """
    if duration_sec <= 0:
        raise ValueError("duration_sec must be > 0")

    profiles = pricing.get("profiles", {})
    if profile not in profiles:
        raise ValueError(f"unknown profile: {profile}; choose from {', '.join(profiles)}")

    spec = profiles[profile]
    mix = spec.get("mix", [])
    if not mix:
        raise ValueError(f"profile {profile} has no mix")
    _validate_mix(mix)

    ratio = float(spec.get("generation_ratio", 1.8))
    lines: list[dict] = []
    subtotal = 0.0

    for model_key, resolution, share in mix:
        model = pricing["models"][model_key]
        price = float(model["prices_cny_per_sec"][resolution])
        seconds = duration_sec * ratio * float(share)
        cost = seconds * price
        subtotal += cost
        lines.append(
            {
                "model": model_key,
                "label": model.get("label", model_key),
                "resolution": resolution,
                "share": float(share),
                "seconds": round(seconds, 1),
                "price_per_sec_cny": price,
                "cost_cny": round(cost, 2),
            }
        )

    overhead = subtotal * overhead_pct
    total = subtotal + overhead

    return {
        "profile": profile,
        "description": spec.get("description", ""),
        "duration_sec": round(duration_sec, 1),
        "generation_ratio": ratio,
        "generation_seconds": round(duration_sec * ratio, 1),
        "lines": lines,
        "subtotal_cny": round(subtotal, 2),
        "overhead_cny": round(overhead, 2),
        "total_cny": round(total, 2),
        "monthly_4_videos_cny": round(total * 4, 2),
        "monthly_3_videos_cny": round(total * 3, 2),
    }


def format_estimate(result: dict) -> str:
    lines = [
        f"档位: {result['profile']}（{result['description']}）",
        f"成片时长: {result['duration_sec']:.0f}s | 生成素材: {result['generation_seconds']:.0f}s"
        f"（生成倍率 {result['generation_ratio']}）",
        "",
        f"{'模型':<20}{'分辨率':<8}{'占比':>6}{'秒数':>9}{'元/秒':>8}{'成本':>10}",
    ]
    for line in result["lines"]:
        lines.append(
            f"{line['label']:<20}{line['resolution']:<8}"
            f"{line['share'] * 100:>5.0f}%{line['seconds']:>9.1f}"
            f"{line['price_per_sec_cny']:>8.2f}{line['cost_cny']:>10.2f}"
        )
    lines.extend(
        [
            "",
            f"小计: {result['subtotal_cny']:.2f} 元",
            f"杂项/重试余量: {result['overhead_cny']:.2f} 元",
            f"单条估算: {result['total_cny']:.2f} 元",
            f"周更月成本（4 条）: {result['monthly_4_videos_cny']:.2f} 元",
            f"月更 3 条: {result['monthly_3_videos_cny']:.2f} 元",
        ]
    )
    return "\n".join(lines)

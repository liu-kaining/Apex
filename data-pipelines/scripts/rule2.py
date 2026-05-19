"""PRD Rule 2: conviction weight and QoQ change helpers."""

from __future__ import annotations

from typing import Any

RULE2_MIN_WEIGHT_PCT = 1.0
RULE2_MIN_QOQ_INCREASE_PCT = 20.0


def classify_qoq(
    current_shares: float,
    previous_shares: float | None,
) -> tuple[str, float | None]:
    """Return (qOqChange, qoqChangePct)."""
    if previous_shares is None or previous_shares <= 0:
        return "NEW", None
    if current_shares <= 0:
        return "DECREASED", -100.0

    pct = ((current_shares - previous_shares) / previous_shares) * 100.0
    if pct >= RULE2_MIN_QOQ_INCREASE_PCT:
        return "INCREASED", round(pct, 2)
    if pct <= -RULE2_MIN_QOQ_INCREASE_PCT:
        return "DECREASED", round(pct, 2)
    return "UNCHANGED", round(pct, 2)


def passes_rule2(
    weight_pct: float,
    qoq_change: str,
    qoq_change_pct: float | None,
) -> bool:
    """Weight > 1% OR new position OR QoQ increase >= 20%."""
    if weight_pct > RULE2_MIN_WEIGHT_PCT:
        return True
    if qoq_change == "NEW":
        return True
    if qoq_change == "INCREASED" and (qoq_change_pct or 0) >= RULE2_MIN_QOQ_INCREASE_PCT:
        return True
    return False


def annotate_holdings_with_qoq_and_rule2(
    current: list[dict[str, Any]],
    previous: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    prev_by_cusip = {h["cusip"]: h for h in previous if h.get("cusip")}
    for h in current:
        prev = prev_by_cusip.get(h["cusip"])
        prev_shares = float(prev["sshPrnamt"]) if prev else None
        qoq, qoq_pct = classify_qoq(float(h.get("sshPrnamt", 0)), prev_shares)
        h["qOqChange"] = qoq
        if qoq_pct is not None:
            h["qoqChangePct"] = qoq_pct
        weight = float(h.get("weightPct", 0))
        h["passesRule2"] = passes_rule2(weight, qoq, qoq_pct)
    return current

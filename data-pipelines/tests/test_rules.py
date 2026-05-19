"""Unit tests for PRD Rules 3 and 4."""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fetch_fmp_insider import passes_rule_3_insider_buy_filter  # noqa: E402
from generate_signals import (  # noqa: E402
    INSIDER_LOOKBACK_DAYS,
    apply_resonance,
    filter_signals_by_insider_recency,
)
from map_cusip import _load_portfolio_json  # noqa: E402
from pipeline_common import normalize_ticker_symbol  # noqa: E402
from rule2 import classify_qoq, passes_rule2  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


class TestLoadPortfolioJson:
    def test_repairs_extra_data_suffix(self, tmp_path: Path):
        path = tmp_path / "0001.json"
        path.write_text('{"cik":"1","holdings":[]}{"cik":"2"}', encoding="utf-8")
        data = _load_portfolio_json(path)
        assert data["cik"] == "1"


class TestNormalizeTickerSymbol:
    def test_accepts_common_equity(self):
        assert normalize_ticker_symbol("aapl") == "AAPL"
        assert normalize_ticker_symbol("BRK.B") == "BRK.B"

    def test_rejects_bond_style_labels(self):
        assert normalize_ticker_symbol("BILL 0 04/01/30") is None
        assert normalize_ticker_symbol("") is None


class TestRule3InsiderBuy:
    def test_accepts_valid_common_stock_purchase(self):
        row = {
            "symbol": "AAPL",
            "acqOrDisp": "A",
            "transactionType": "P",
            "securityName": "Common Stock",
            "securitiesTransacted": 1000,
            "price": 100,
        }
        assert passes_rule_3_insider_buy_filter(row) is True

    def test_rejects_sale(self):
        row = {
            "symbol": "AAPL",
            "acqOrDisp": "D",
            "transactionType": "P",
            "securityName": "Common Stock",
            "securitiesTransacted": 1000,
            "price": 100,
        }
        assert passes_rule_3_insider_buy_filter(row) is False

    def test_rejects_small_notional(self):
        row = {
            "symbol": "AAPL",
            "acqOrDisp": "A",
            "transactionType": "P",
            "securityName": "Common Stock",
            "securitiesTransacted": 10,
            "price": 10,
        }
        assert passes_rule_3_insider_buy_filter(row) is False

    def test_accepts_stable_latest_shape_without_acq_field(self):
        """FMP stable /insider-trading/latest omits acqOrDisp; P-Purchase is enough."""
        row = {
            "symbol": "MSFT",
            "transactionType": "P-Purchase",
            "securityName": "Common Stock",
            "securitiesTransacted": 10000,
            "price": 400,
        }
        assert passes_rule_3_insider_buy_filter(row) is True


class TestRule2Conviction:
    def test_weight_above_one_percent(self):
        assert passes_rule2(1.5, "UNCHANGED", 0) is True

    def test_new_position(self):
        assert passes_rule2(0.5, "NEW", None) is True

    def test_increase_twenty_percent(self):
        assert passes_rule2(0.5, "INCREASED", 25.0) is True

    def test_classify_qoq_new(self):
        qoq, pct = classify_qoq(1000, None)
        assert qoq == "NEW"
        assert pct is None


class TestRule4Resonance:
    def test_resonance_marks_strong_when_held(self):
        feed = {
            "signals": [
                {
                    "id": "AAPL-1",
                    "ticker": "AAPL",
                    "companyName": "Apple",
                    "signalType": "INSIDER_BUY",
                    "superinvestorCount": 0,
                    "insiderActions": {"recentBuyers": ["X"], "totalAmountUsd": 1e6, "date": "2026-05-18"},
                    "tags": [],
                }
            ]
        }
        index = {
            "AAPL": [
                {"cik": "0001067983", "firm": "Berkshire", "dataromaCode": "BRK", "weightPct": 5.0}
            ]
        }
        out = apply_resonance(feed, index)
        assert out["signals"][0]["signalType"] == "STRONG_RESONANCE"
        assert out["signals"][0]["superinvestorCount"] == 1

    def test_insider_lookback_filters_old_signals(self):
        old = (date.today() - timedelta(days=INSIDER_LOOKBACK_DAYS + 2)).isoformat()
        feed = {
            "signals": [
                {
                    "ticker": "OLD",
                    "insiderActions": {"date": old},
                }
            ]
        }
        out = filter_signals_by_insider_recency(feed)
        assert out["signals"] == []

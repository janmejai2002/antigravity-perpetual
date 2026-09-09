"""
Continuous Monitoring & V2 Review Engine for Antigravity Perpetual.
Computes real-time performance analytics, latency distributions (p50/p90/p99),
account traffic balance entropy, and automated V2 evolution blueprints.
"""
from __future__ import annotations

import math
import sqlite3
import time
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path


class AnalyticsEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def get_summary_metrics(self, window_hours: float = 24.0) -> Dict[str, Any]:
        """Compute aggregate throughput, success rate, and latency metrics."""
        cutoff = time.time() - (window_hours * 3600.0)
        with self._get_connection() as conn:
            # Aggregate counts
            row = conn.execute("""
                SELECT 
                    COUNT(*) as total_requests,
                    COALESCE(SUM(token_count), 0) as total_tokens,
                    COALESCE(SUM(CASE WHEN is_failure = 0 THEN 1 ELSE 0 END), 0) as successful_requests,
                    COALESCE(SUM(CASE WHEN is_failure = 1 THEN 1 ELSE 0 END), 0) as failed_requests,
                    COALESCE(SUM(CASE WHEN status_code = 429 THEN 1 ELSE 0 END), 0) as quota_429_count
                FROM request_ledger
                WHERE timestamp >= ?;
            """, (cutoff,)).fetchone()

            total = row["total_requests"]
            tokens = row["total_tokens"]
            success = row["successful_requests"]
            failed = row["failed_requests"]
            rate_429 = row["quota_429_count"]
            success_rate = (success / total * 100.0) if total > 0 else 100.0

            # Compute percentiles for latency
            latency_rows = conn.execute("""
                SELECT latency_ms
                FROM request_ledger
                WHERE timestamp >= ?
                ORDER BY latency_ms ASC;
            """, (cutoff,)).fetchall()

            latencies = [r["latency_ms"] for r in latency_rows]
            p50 = self._percentile(latencies, 50.0)
            p90 = self._percentile(latencies, 90.0)
            p99 = self._percentile(latencies, 99.0)
            avg_lat = (sum(latencies) / len(latencies)) if latencies else 0.0

            # Account distribution breakdown
            acc_rows = conn.execute("""
                SELECT 
                    r.account_id,
                    a.name as account_name,
                    COUNT(*) as req_count,
                    SUM(r.token_count) as tokens_used,
                    SUM(CASE WHEN r.is_failure = 1 THEN 1 ELSE 0 END) as failures
                FROM request_ledger r
                LEFT JOIN accounts a ON r.account_id = a.id
                WHERE r.timestamp >= ?
                GROUP BY r.account_id;
            """, (cutoff,)).fetchall()

            account_distribution = []
            req_counts = []
            for r in acc_rows:
                cnt = r["req_count"]
                req_counts.append(cnt)
                account_distribution.append({
                    "account_id": r["account_id"],
                    "account_name": r["account_name"] or r["account_id"],
                    "request_count": cnt,
                    "token_count": r["tokens_used"] or 0,
                    "failures": r["failures"] or 0,
                    "share_percent": round((cnt / total * 100.0) if total > 0 else 0.0, 1)
                })

            # Calculate Shannon Balance Index (0% to 100%)
            balance_index = self._calculate_balance_index(req_counts)

            # Alert statistics
            alert_rows = conn.execute("""
                SELECT severity, COUNT(*) as cnt
                FROM system_alerts
                WHERE timestamp >= ?
                GROUP BY severity;
            """, (cutoff,)).fetchall()
            alerts_by_severity = {r["severity"]: r["cnt"] for r in alert_rows}

            return {
                "window_hours": window_hours,
                "total_requests": total,
                "total_tokens": tokens,
                "success_rate_percent": round(success_rate, 2),
                "failed_requests": failed,
                "quota_exhaustion_429s": rate_429,
                "latency_ms": {
                    "avg": round(avg_lat, 2),
                    "p50": round(p50, 2),
                    "p90": round(p90, 2),
                    "p99": round(p99, 2),
                    "min": round(min(latencies), 2) if latencies else 0.0,
                    "max": round(max(latencies), 2) if latencies else 0.0
                },
                "account_balance_index_percent": round(balance_index * 100.0, 1),
                "account_distribution": account_distribution,
                "alerts_summary": alerts_by_severity
            }

    @staticmethod
    def _percentile(sorted_list: List[float], percentile: float) -> float:
        if not sorted_list:
            return 0.0
        idx = int(math.ceil((percentile / 100.0) * len(sorted_list))) - 1
        idx = max(0, min(idx, len(sorted_list) - 1))
        return sorted_list[idx]

    @staticmethod
    def _calculate_balance_index(counts: List[int]) -> float:
        """Normalized Shannon entropy: 1.0 = perfectly balanced, 0.0 = completely skewed."""
        total = sum(counts)
        if total == 0 or len(counts) <= 1:
            return 1.0
        num_buckets = len(counts)
        entropy = 0.0
        for c in counts:
            if c > 0:
                p = c / total
                entropy -= p * math.log(p)
        max_entropy = math.log(num_buckets)
        if max_entropy == 0:
            return 1.0
        return entropy / max_entropy

    def generate_v2_review_report(self) -> Dict[str, Any]:
        """
        Synthesizes an automated architectural review and V2 roadmap
        based on empirical system telemetry and performance heuristics.
        """
        metrics = self.get_summary_metrics(window_hours=48.0)
        recommendations: List[Dict[str, str]] = []
        strengths: List[str] = []
        score_penalties = 0

        # Heuristic 1: Quota Balance
        balance = metrics["account_balance_index_percent"]
        if balance < 40.0 and metrics["total_requests"] > 10:
            recommendations.append({
                "category": "QUOTA_ROUTING",
                "priority": "HIGH",
                "finding": f"Traffic is significantly skewed across accounts (Balance Index: {balance}%).",
                "v2_solution": "Implement Proportional Stride Scheduling to distribute tokens evenly across all 4 Google Pro accounts."
            })
            score_penalties += 15
        else:
            strengths.append(f"Account load distribution is healthy ({balance}% balance index).")

        # Heuristic 2: Quota 429 Trips
        exhaustions = metrics["quota_exhaustion_429s"]
        if exhaustions > 0:
            recommendations.append({
                "category": "CIRCUIT_BREAKER",
                "priority": "CRITICAL",
                "finding": f"Observed {exhaustions} HTTP 429 quota exhaustion incidents.",
                "v2_solution": "Deploy Preemptive Soft-Cap Routing: switch active account at 80% sliding window consumption before Antigravity Tools throws 429."
            })
            score_penalties += 20
        else:
            strengths.append("Zero 429 quota lockouts recorded under circuit breaker supervision.")

        # Heuristic 3: Latency Distribution
        p99 = metrics["latency_ms"]["p99"]
        if p99 > 3500.0:
            recommendations.append({
                "category": "LATENCY_OPTIMIZATION",
                "priority": "MEDIUM",
                "finding": f"High p99 latency detected ({p99}ms).",
                "v2_solution": "Enable streaming chunk pre-buffering and speculative token execution on Intel Lunar Lake NPU."
            })
            score_penalties += 10
        else:
            strengths.append(f"p99 latency ({p99}ms) satisfies interactive coding agent SLAs (<3500ms).")

        # Heuristic 4: Architecture Grade Computation
        score = max(0, 100 - score_penalties)
        if score >= 90:
            grade = "A+"
            verdict = "Production Ready & Autonomous"
        elif score >= 80:
            grade = "A"
            verdict = "Highly Stable with Minor Optimizations Recommended"
        elif score >= 70:
            grade = "B"
            verdict = "Functional; Quota Skew or Latency Requires Tuning"
        else:
            grade = "C"
            verdict = "Requires Structural Quota & Retry Hardening"

        # V2 Blueprint Roadmap
        v2_blueprint = {
            "version": "2.0.0-PROPOSED",
            "title": "Perpetual Supervisor V2: Autonomous Hyper-Scale Architecture",
            "pillars": [
                {
                    "name": "Predictive Quota Governor",
                    "description": "Uses Lunar Lake NPU time-series forecasting to predict quota depletion 5 minutes in advance and pre-warm next account."
                },
                {
                    "name": "Zero-Copy Context Streaming",
                    "description": "Bypasses JSON serialization via shared memory IPC between RTK proxy and Antigravity Tools."
                },
                {
                    "name": "Multi-IDE Universal Hook",
                    "description": "Extends proxy routing seamlessly across Antigravity IDE, Cursor, Claude Code, and VSCode simultaneously."
                },
                {
                    "name": "Adaptive Thermal Governor",
                    "description": "Dynamically scales inference batch size based on chassis skin temperature and battery discharge curves."
                }
            ]
        }

        return {
            "timestamp": time.time(),
            "architectural_grade": grade,
            "system_score": score,
            "verdict": verdict,
            "strengths": strengths,
            "recommendations": recommendations,
            "metrics": metrics,
            "v2_blueprint": v2_blueprint
        }

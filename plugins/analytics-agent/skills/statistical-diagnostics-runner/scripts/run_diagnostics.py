#!/usr/bin/env python3
"""Executor determinístico de diagnósticos estatísticos (stdlib puro, zero cálculos no LLM)."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import statistics
from pathlib import Path


def read_csv_columns(path: Path) -> tuple[list[str], dict[str, list[str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        cols = reader.fieldnames or []
        data: dict[str, list[str]] = {c: [] for c in cols}
        for row in reader:
            for c in cols:
                data[c].append((row.get(c) or "").strip())
    return cols, data


def to_floats(raw: list[str]) -> tuple[list[float], int]:
    vals: list[float] = []
    missing = 0
    for item in raw:
        if item == "" or item.lower() in {"na", "nan", "null", "none"}:
            missing += 1
            continue
        try:
            v = float(item)
            if math.isnan(v) or math.isinf(v):
                missing += 1
            else:
                vals.append(v)
        except ValueError:
            return [], -1  # coluna não numérica
    return vals, missing


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def compute_psi(base: list[float], actual: list[float], bins: int = 10) -> float | None:
    if len(base) < bins or len(actual) < bins:
        return None
    s_base = sorted(base)
    edges = [percentile(s_base, i / bins) for i in range(bins + 1)]
    edges[0] = -math.inf
    edges[-1] = math.inf

    def bucket_props(vals: list[float]) -> list[float]:
        counts = [0] * bins
        for v in vals:
            for i in range(bins):
                if edges[i] <= v < edges[i + 1] or (i == bins - 1 and v == edges[-1]):
                    counts[i] += 1
                    break
        n = len(vals)
        return [max(c / n, 1e-6) for c in counts]

    p_base = bucket_props(base)
    p_act = bucket_props(actual)
    return round(sum((a - b) * math.log(a / b) for b, a in zip(p_base, p_act, strict=True)), 4)


def pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y) or len(x) < 3:
        return None
    mx, my = statistics.fmean(x), statistics.fmean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def summarize_numeric(vals: list[float], missing: int, total: int) -> dict:
    n = len(vals)
    if n == 0:
        return {"count": 0, "missingRate": round(missing / total, 4) if total else 0.0}
    s = sorted(vals)
    mean = statistics.fmean(s)
    std = statistics.stdev(s) if n > 1 else 0.0
    q1 = percentile(s, 0.25)
    med = percentile(s, 0.50)
    q3 = percentile(s, 0.75)
    iqr = q3 - q1
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = sum(1 for v in s if v < low or v > high)
    skew = (sum(((v - mean) / std) ** 3 for v in s) / n) if std > 0 else 0.0
    kurt = (sum(((v - mean) / std) ** 4 for v in s) / n - 3.0) if std > 0 else 0.0
    return {
        "count": n,
        "missingRate": round(missing / total, 4) if total else 0.0,
        "mean": round(mean, 4),
        "std": round(std, 4),
        "median": round(med, 4),
        "iqr": round(iqr, 4),
        "outlierRate": round(outliers / n, 4),
        "skewness": round(skew, 4),
        "excessKurtosis": round(kurt, 4),
        "heavySkewFlag": abs(skew) >= 1.5,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico estatístico determinístico de CSVs.")
    parser.add_argument("--train-csv", required=True)
    parser.add_argument("--oot-csv", default="")
    parser.add_argument("--target-col", default="")
    parser.add_argument("--prob-col", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    cols, train_data = read_csv_columns(Path(args.train_csv))
    n_rows = len(train_data[cols[0]]) if cols else 0

    oot_data: dict[str, list[str]] = {}
    if args.oot_csv:
        _, oot_data = read_csv_columns(Path(args.oot_csv))

    numeric_series: dict[str, list[float]] = {}
    col_reports: dict[str, dict] = {}
    psi_alerts: list[dict] = []

    for c in cols:
        vals, missing = to_floats(train_data[c])
        if missing == -1:
            col_reports[c] = {"type": "non_numeric", "distinctCount": len(set(train_data[c]))}
            continue
        rep = {"type": "numeric", **summarize_numeric(vals, missing, n_rows)}
        if len(vals) == n_rows:
            numeric_series[c] = vals
        if c in oot_data:
            oot_vals, _ = to_floats(oot_data[c])
            psi = compute_psi(vals, oot_vals)
            rep["psiTrainVsOot"] = psi
            if psi is not None and psi >= 0.25:
                psi_alerts.append({"column": c, "psi": psi, "severity": "SEVERE_DRIFT"})
            elif psi is not None and psi >= 0.10:
                psi_alerts.append({"column": c, "psi": psi, "severity": "MODERATE_DRIFT"})
        col_reports[c] = rep

    high_corr: list[dict] = []
    num_keys = [k for k in numeric_series if k not in {args.target_col, args.prob_col}]
    for i in range(len(num_keys)):
        for j in range(i + 1, len(num_keys)):
            r = pearson(numeric_series[num_keys[i]], numeric_series[num_keys[j]])
            if r is not None and abs(r) >= 0.85:
                high_corr.append({"colA": num_keys[i], "colB": num_keys[j], "pearsonR": round(r, 4)})

    target_summary: dict = {}
    if args.target_col and args.target_col in train_data:
        t_vals, _ = to_floats(train_data[args.target_col])
        if t_vals and set(t_vals).issubset({0.0, 1.0}):
            pos_rate = statistics.fmean(t_vals)
            target_summary = {
                "column": args.target_col,
                "positiveRate": round(pos_rate, 4),
                "imbalancedFlag": pos_rate < 0.10 or pos_rate > 0.90,
            }
            if args.prob_col and args.prob_col in train_data:
                p_vals, _ = to_floats(train_data[args.prob_col])
                if len(p_vals) == len(t_vals):
                    brier = statistics.fmean((p - y) ** 2 for p, y in zip(p_vals, t_vals, strict=True))
                    target_summary["brierScore"] = round(brier, 5)

    report = {
        "generatedAtUtc": dt.datetime.now(dt.UTC).isoformat(),
        "trainRows": n_rows,
        "columns": col_reports,
        "highCollinearityPairs": high_corr,
        "psiAlerts": psi_alerts,
        "targetSummary": target_summary,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Diagnóstico estatístico gravado em: {out} "
        f"(rows={n_rows}, high_corr={len(high_corr)}, psi_alerts={len(psi_alerts)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

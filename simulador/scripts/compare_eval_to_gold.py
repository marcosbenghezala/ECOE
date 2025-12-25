#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_eval(payload: Dict[str, Any]) -> Dict[str, Any]:
    if "items" in payload:
        return payload
    for key in ("evaluation_unified", "evaluation", "result"):
        if isinstance(payload.get(key), dict):
            return payload[key]
    raise ValueError("No evaluation object found (expected 'items' or evaluation_unified/evaluation/result)")


def _load_gold_items(gold: Dict[str, Any]) -> Set[str]:
    expected = set()
    for line in gold.get("lines", []) or []:
        for item_id in line.get("expected_item_ids", []) or []:
            expected.add(str(item_id))
    return expected


def _load_actual_items(evaluation: Dict[str, Any]) -> Set[str]:
    done = set()
    for item in evaluation.get("items", []) or []:
        if item.get("done"):
            item_id = item.get("id")
            if item_id:
                done.add(str(item_id))
    return done


def _summarize(expected: Set[str], actual: Set[str], total_items: int) -> Dict[str, Any]:
    false_positives = sorted(actual - expected)
    false_negatives = sorted(expected - actual)
    expected_count = len(expected)
    actual_count = len(actual)
    expected_pct = round((expected_count / total_items) * 100, 2) if total_items else 0.0
    actual_pct = round((actual_count / total_items) * 100, 2) if total_items else 0.0
    return {
        "expected_done": expected_count,
        "actual_done": actual_count,
        "expected_pct": expected_pct,
        "actual_pct": actual_pct,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare evaluation output against IAM gold checklist expectations"
    )
    parser.add_argument(
        "evaluation_json",
        type=Path,
        help="Path to evaluation JSON (may include evaluation_unified or items)",
    )
    parser.add_argument(
        "--gold",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "iam_gold_expected.json",
        help="Path to gold expected JSON",
    )
    parser.add_argument(
        "--total-items",
        type=int,
        default=180,
        help="Total checklist items",
    )
    args = parser.parse_args()

    gold = _load_json(args.gold)
    payload = _load_json(args.evaluation_json)
    evaluation = _extract_eval(payload)

    expected = _load_gold_items(gold)
    actual = _load_actual_items(evaluation)
    summary = _summarize(expected, actual, args.total_items)

    print("Expected done:", summary["expected_done"])
    print("Actual done:", summary["actual_done"])
    print("Expected %:", summary["expected_pct"])
    print("Actual %:", summary["actual_pct"])
    print("False positives:", len(summary["false_positives"]))
    for item_id in summary["false_positives"]:
        print("  +", item_id)
    print("False negatives:", len(summary["false_negatives"]))
    for item_id in summary["false_negatives"]:
        print("  -", item_id)


if __name__ == "__main__":
    main()

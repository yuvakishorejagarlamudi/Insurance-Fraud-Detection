
import csv
from collections import defaultdict
from pathlib import Path

from backend.app.fraud_engine import detect_fraud

ROOT = Path(__file__).resolve().parents[1]

GROUND_TRUTH = (
    ROOT / "data/step41_test/ground_truth/ground_truth.csv"
)

EXCEPTION_FILE = (
    ROOT / "data/step41_test/exceptions/invalid_policy_claims.csv"
)


def safe_divide(a, b):
    return a / b if b else 0.0


def calculate_metrics(expected, detected):
    tp = len(expected & detected)
    fp = len(detected - expected)
    fn = len(expected - detected)

    precision = safe_divide(tp, tp + fp)
    recall = safe_divide(tp, tp + fn)
    f1 = safe_divide(
        2 * precision * recall,
        precision + recall
    )

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def main():
    if not GROUND_TRUTH.exists():
        raise FileNotFoundError(
            f"Ground truth not found: {GROUND_TRUTH}"
        )

    with GROUND_TRUTH.open(
        encoding="utf-8-sig",
        newline=""
    ) as file:
        truth_rows = list(csv.DictReader(file))

    predictions = detect_fraud()

    # Expected indicator pairs from labeled anomalies.
    expected = set()
    labeled_claims = set()
    truth_by_claim = defaultdict(set)

    for row in truth_rows:
        claim_id = row.get("claim_id", "").strip()
        label = row.get("expected_label", "").strip().upper()
        rule = row.get("expected_detection", "").strip()

        if not claim_id:
            continue

        labeled_claims.add(claim_id)
        truth_by_claim[claim_id].add(label)

        if label == "ANOMALOUS" and rule:
            expected.add((claim_id, rule))

    # Actual engine predictions.
    engine_detected = set()

    for prediction in predictions:
        claim_id = prediction["claim_id"]

        if claim_id not in labeled_claims:
            continue

        for indicator in prediction["indicators"]:
            engine_detected.add(
                (claim_id, indicator["indicator_type"])
            )

    # Exception checks are separate from live engine detections.
    exception_detected = set()

    if EXCEPTION_FILE.exists():
        with EXCEPTION_FILE.open(
            encoding="utf-8-sig",
            newline=""
        ) as file:
            exception_rows = list(csv.DictReader(file))

        for row in exception_rows:
            issue = row.get("issue_type", "").strip().upper()
            label = row.get("ground_truth", "").strip().upper()
            claim_id = row.get("claim_id", "").strip()

            if (
                issue == "MISSING_POLICY_REFERENCE"
                and label == "ANOMALOUS"
                and claim_id in labeled_claims
            ):
                exception_detected.add(
                    (claim_id, "INVALID_POLICY_FK")
                )

    combined_detected = engine_detected | exception_detected

    # Only compare against explicitly labeled claims.
    expected = {
        item for item in expected
        if item[0] in labeled_claims
    }

    engine_metrics = calculate_metrics(
        expected, engine_detected
    )

    combined_metrics = calculate_metrics(
        expected, combined_detected
    )

    print("\nINSURANCE FRAUD EVALUATION")
    print("=" * 60)

    print("Ground-truth records:", len(truth_rows))
    print("Labeled claims:", len(labeled_claims))
    print("Expected indicators:", len(expected))
    print("Engine detections:", len(engine_detected))
    print("Exception detections:", len(exception_detected))

    print("\nENGINE INDICATOR METRICS")
    print("-" * 45)
    print("True positives:", engine_metrics["tp"])
    print("False positives:", engine_metrics["fp"])
    print("False negatives:", engine_metrics["fn"])
    print(f"Precision: {engine_metrics['precision']:.2%}")
    print(f"Recall:    {engine_metrics['recall']:.2%}")
    print(f"F1 Score:  {engine_metrics['f1']:.2%}")

    print("\nCOMBINED INDICATOR METRICS")
    print("-" * 45)
    print("True positives:", combined_metrics["tp"])
    print("False positives:", combined_metrics["fp"])
    print("False negatives:", combined_metrics["fn"])
    print(f"Precision: {combined_metrics['precision']:.2%}")
    print(f"Recall:    {combined_metrics['recall']:.2%}")
    print(f"F1 Score:  {combined_metrics['f1']:.2%}")

    print("\nMISSING INDICATORS")
    missing = expected - combined_detected

    if missing:
        for claim_id, rule in sorted(missing):
            print("MISSING:", claim_id, rule)
    else:
        print("None")

    print("\nUNEXPECTED ENGINE DETECTIONS")
    unexpected = engine_detected - expected

    if unexpected:
        for claim_id, rule in sorted(unexpected):
            print("REVIEW:", claim_id, rule)
    else:
        print("None")

    print("\nEXCEPTION DETECTIONS")
    for claim_id, rule in sorted(exception_detected):
        print(claim_id, rule)

    print("\nEVALUATION NOTES")
    print("- Unlabeled claims are excluded.")
    print("- Benign shared addresses are not fraud labels.")
    print("- Exception checks are separate from live engine detections.")
    print("- Indicator precision and recall use labeled indicators.")
    print("- False-positive rate requires explicit negative labels.")
    print("- All results are based on synthetic data.")

    print("\nEVALUATION FINISHED")
    print("=" * 60)


if __name__ == "__main__":
    main()

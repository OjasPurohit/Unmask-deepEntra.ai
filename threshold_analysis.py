# ============================================================
# Threshold Analysis for Models A, B and C
# ============================================================

# These are the results from compare_models.py
results = [
    {"image": "real_1.jpg", "true": "REAL", "A": 0.0001, "B": 0.0577, "C": 0.6520},
    {"image": "real_2.jpg", "true": "REAL", "A": 0.0009, "B": 0.7748, "C": 0.5325},
    {"image": "real_3.jpg", "true": "REAL", "A": 0.0001, "B": 0.2588, "C": 0.5234},
    {"image": "real_4.jpg", "true": "REAL", "A": 0.0001, "B": 0.5993, "C": 0.6896},
    {"image": "real_5.jpg", "true": "REAL", "A": 0.0028, "B": 0.7576, "C": 0.5555},

    {"image": "fake_1.jpg", "true": "FAKE", "A": 0.9388, "B": 0.6887, "C": 0.6069},
    {"image": "fake_2.jpg", "true": "FAKE", "A": 0.4110, "B": 0.9019, "C": 0.3012},
    {"image": "fake_3.jpg", "true": "FAKE", "A": 0.0101, "B": 0.3966, "C": 0.2818},
    {"image": "fake_4.jpg", "true": "FAKE", "A": 0.0004, "B": 0.5675, "C": 0.5800},
    {"image": "fake_5.jpg", "true": "FAKE", "A": 0.9012, "B": 0.5736, "C": 0.6768},
    {"image": "fake_6.jpg", "true": "FAKE", "A": 0.0000, "B": 0.5507, "C": 0.6718},
]


# ============================================================
# METRIC CALCULATION
# ============================================================

def calculate_metrics(model_name, threshold):

    tp = 0
    tn = 0
    fp = 0
    fn = 0

    for result in results:

        actual_fake = result["true"] == "FAKE"

        predicted_fake = (
            result[model_name] >= threshold
        )

        if actual_fake and predicted_fake:
            tp += 1

        elif not actual_fake and not predicted_fake:
            tn += 1

        elif not actual_fake and predicted_fake:
            fp += 1

        elif actual_fake and not predicted_fake:
            fn += 1

    total = tp + tn + fp + fn

    accuracy = (tp + tn) / total

    precision = (
        tp / (tp + fp)
        if tp + fp > 0
        else 0
    )

    recall = (
        tp / (tp + fn)
        if tp + fn > 0
        else 0
    )

    f1 = (
        2 * precision * recall /
        (precision + recall)
        if precision + recall > 0
        else 0
    )

    fpr = (
        fp / (fp + tn)
        if fp + tn > 0
        else 0
    )

    fnr = (
        fn / (fn + tp)
        if fn + tp > 0
        else 0
    )

    return {
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1": f1,
        "FPR": fpr,
        "FNR": fnr
    }


# ============================================================
# THRESHOLDS
# ============================================================

thresholds = [
    0.30,
    0.40,
    0.50,
    0.60,
    0.70
]


# ============================================================
# RUN ANALYSIS
# ============================================================

for model_name in ["A", "B", "C"]:

    print("\n")
    print("=" * 90)
    print(f"MODEL {model_name} - THRESHOLD ANALYSIS")
    print("=" * 90)

    print(
        f"{'Threshold':<12}"
        f"{'Accuracy':<12}"
        f"{'Precision':<12}"
        f"{'Recall':<12}"
        f"{'F1':<12}"
        f"{'FPR':<12}"
        f"{'FNR':<12}"
    )

    print("-" * 90)

    for threshold in thresholds:

        metrics = calculate_metrics(
            model_name,
            threshold
        )

        print(
            f"{threshold:<12.2f}"
            f"{metrics['Accuracy'] * 100:<12.2f}"
            f"{metrics['Precision'] * 100:<12.2f}"
            f"{metrics['Recall'] * 100:<12.2f}"
            f"{metrics['F1'] * 100:<12.2f}"
            f"{metrics['FPR'] * 100:<12.2f}"
            f"{metrics['FNR'] * 100:<12.2f}"
        )


print("\n")
print("=" * 90)
print("Threshold analysis complete.")
print("=" * 90)
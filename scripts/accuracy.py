"""Accuracy assessment — reference sampling and metrics."""

import numpy as np
from sklearn.metrics import (
    confusion_matrix, classification_report,
    accuracy_score, cohen_kappa_score,
)

from scripts.config import (
    CLASS_NODATA, CLASS_NONVEG, CLASS_LOW, CLASS_TREE, LABELS,
)


# ---------------------------------------------------------------------------
# Reference map from independent thresholds
# ---------------------------------------------------------------------------
def build_reference_map(
    ndvi_a, chm_max_10, valid,
    ref_ndvi=0.35, ref_chm=3.5,
):
    """Create an independent reference classification using stricter thresholds.

    Returns
    -------
    ref_map : numpy.ndarray[uint8]
    """
    ref_map = np.full_like(ndvi_a, CLASS_NODATA, dtype=np.uint8)
    ref_map[valid & (ndvi_a >  ref_ndvi) & (chm_max_10 >  ref_chm)] = CLASS_TREE
    ref_map[valid & (ndvi_a >  ref_ndvi) & (chm_max_10 <= ref_chm)] = CLASS_LOW
    ref_map[valid & (ndvi_a <= ref_ndvi)] = CLASS_NONVEG
    return ref_map


# ---------------------------------------------------------------------------
# Stratified random sampling
# ---------------------------------------------------------------------------
def sample_reference(ref_map, rule_map, rf_map, n_total=500, seed=0):
    """Draw stratified random samples and extract class labels.

    Returns
    -------
    sample_ref, sample_rule, sample_rf : numpy.ndarray
    """
    rng = np.random.default_rng(seed)
    sample_ref, sample_rule, sample_rf = [], [], []

    for cls in [CLASS_TREE, CLASS_LOW, CLASS_NONVEG]:
        ys, xs = np.where(ref_map == cls)
        n_cls = min(n_total // 3, len(ys))
        if n_cls == 0:
            continue
        idx = rng.choice(len(ys), n_cls, replace=False)
        sample_ref.extend([cls] * n_cls)
        sample_rule.extend(rule_map[ys[idx], xs[idx]])
        sample_rf.extend(rf_map[ys[idx], xs[idx]])

    sample_ref  = np.array(sample_ref)
    sample_rule = np.array(sample_rule)
    sample_rf   = np.array(sample_rf)

    print(f"Reference samples: {len(sample_ref)}")
    for cls in [CLASS_TREE, CLASS_LOW, CLASS_NONVEG]:
        print(f"  {LABELS[cls]:20s}: {(sample_ref == cls).sum()}")

    return sample_ref, sample_rule, sample_rf


# ---------------------------------------------------------------------------
# Accuracy report
# ---------------------------------------------------------------------------
def report_accuracy(y_true, y_pred, title):
    """Print confusion matrix, OA, kappa, and per-class metrics.

    Returns
    -------
    oa, kappa : float
    """
    classes = [CLASS_NONVEG, CLASS_LOW, CLASS_TREE]
    names = [LABELS[c] for c in classes]
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    oa = accuracy_score(y_true, y_pred)
    kappa = cohen_kappa_score(y_true, y_pred)

    print(f'\n{"=" * 60}')
    print(f"  {title}")
    print(f'{"=" * 60}')
    print("\nConfusion Matrix (rows=reference, cols=predicted):")
    header = "                   " + "  ".join(f"{n:>14s}" for n in names)
    print(header)
    for i, row_name in enumerate(names):
        row_str = "  ".join(f"{v:>14,}" for v in cm[i])
        print(f"  {row_name:17s}{row_str}")

    print(f"\nOverall accuracy : {oa:.1%}")
    print(f"Cohen\u2019s kappa    : {kappa:.3f}")
    print(f"\n{classification_report(y_true, y_pred, labels=classes, target_names=names)}")
    return oa, kappa

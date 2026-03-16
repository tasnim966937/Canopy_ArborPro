"""Rule-based and Random Forest UTC classification."""

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from scripts.config import (
    CLASS_NODATA, CLASS_NONVEG, CLASS_LOW, CLASS_TREE, LABELS,
)
from scripts.sentinel2 import S2_BANDS


# ---------------------------------------------------------------------------
# Rule-based classification
# ---------------------------------------------------------------------------
def classify_rules(ndvi_a, chm_max_10, ndvi_thresh=0.3, chm_thresh=2.5):
    """Apply simple NDVI + CHM height thresholds.

    Returns
    -------
    rule_map : numpy.ndarray[uint8]
    valid    : numpy.ndarray[bool]
    """
    valid = ~(np.isnan(ndvi_a) | np.isnan(chm_max_10))

    rule_map = np.full(ndvi_a.shape, CLASS_NODATA, dtype=np.uint8)
    rule_map[valid & (ndvi_a >  ndvi_thresh) & (chm_max_10 >  chm_thresh)] = CLASS_TREE
    rule_map[valid & (ndvi_a >  ndvi_thresh) & (chm_max_10 <= chm_thresh)] = CLASS_LOW
    rule_map[valid & (ndvi_a <= ndvi_thresh)] = CLASS_NONVEG

    for cls in [CLASS_TREE, CLASS_LOW, CLASS_NONVEG]:
        pct = (rule_map == cls).sum() / valid.sum() * 100
        print(f"{LABELS[cls]:20s}: {pct:5.1f}%")

    return rule_map, valid


# ---------------------------------------------------------------------------
# Random Forest classification
# ---------------------------------------------------------------------------
def classify_rf(
    s2_utm, ndvi_a, ndre_a, ndbi_a,
    chm_max_10, chm_std_10,
    rule_map,
    n_estimators=150,
    max_depth=15,
    max_train=20_000,
    seed=42,
):
    """Train a Random Forest on high-confidence rule-based labels.

    Returns
    -------
    rf_map        : numpy.ndarray[uint8]
    rf            : RandomForestClassifier  (fitted model)
    feat_names    : list[str]
    """
    feat_names = list(S2_BANDS) + [
        "NDVI", "NDRE", "NDBI", "CHM_max", "CHM_std",
    ]

    features = np.stack(
        [s2_utm[b] for b in S2_BANDS]
        + [ndvi_a, ndre_a, ndbi_a, chm_max_10, chm_std_10],
        axis=-1,
    )

    rows, cols = ndvi_a.shape
    feat_flat  = features.reshape(-1, features.shape[-1])
    label_flat = rule_map.ravel()

    # Strict thresholds for high-confidence training pixels
    train_mask = (
        (label_flat != CLASS_NODATA)
        & ~np.any(np.isnan(feat_flat), axis=1)
        & (
            ((label_flat == CLASS_TREE)
             & (ndvi_a.ravel() > 0.45) & (chm_max_10.ravel() > 5))
            | ((label_flat == CLASS_LOW)
               & (ndvi_a.ravel() > 0.45) & (chm_max_10.ravel() < 1))
            | ((label_flat == CLASS_NONVEG)
               & (ndvi_a.ravel() < 0.15))
        )
    )

    X_all = feat_flat[train_mask]
    y_all = label_flat[train_mask]

    n_sample = min(max_train, len(X_all))
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(X_all), n_sample, replace=False)
    X_train, y_train = X_all[idx], y_all[idx]

    print(f"Training samples: {n_sample:,}")
    for cls in [CLASS_TREE, CLASS_LOW, CLASS_NONVEG]:
        print(f"  {LABELS[cls]:20s}: {(y_train == cls).sum():,}")

    rf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=seed,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)

    predict_mask = ~np.any(np.isnan(feat_flat), axis=1)
    rf_flat = np.full(len(feat_flat), CLASS_NODATA, dtype=np.uint8)
    rf_flat[predict_mask] = rf.predict(feat_flat[predict_mask])
    rf_map = rf_flat.reshape(rows, cols)

    print("\nRandom Forest results:")
    valid_px = predict_mask.reshape(rows, cols).sum()
    for cls in [CLASS_TREE, CLASS_LOW, CLASS_NONVEG]:
        pct = (rf_map == cls).sum() / valid_px * 100
        print(f"  {LABELS[cls]:20s}: {pct:5.1f}%")

    print("\nFeature importances:")
    for name, imp in sorted(
        zip(feat_names, rf.feature_importances_), key=lambda x: -x[1]
    ):
        bar = "\u2588" * int(imp * 80)
        print(f"  {name:8s} {imp:.3f}  {bar}")

    return rf_map, rf, feat_names

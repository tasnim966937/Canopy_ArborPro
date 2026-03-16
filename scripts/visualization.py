"""Plotting helpers for the UTC assessment."""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap, BoundaryNorm

from scripts.config import bounds_utm


# ---------------------------------------------------------------------------
# Shared colour map for the 4-class classification
# ---------------------------------------------------------------------------
CMAP_CLASSES = ListedColormap(["#cccccc", "#d2b48c", "#90ee90", "#006400"])
BOUNDS_CLS   = [-0.5, 0.5, 1.5, 2.5, 3.5]
NORM_CLS     = BoundaryNorm(BOUNDS_CLS, CMAP_CLASSES.N)

PATCHES = [
    mpatches.Patch(color="#006400", label="Tree canopy"),
    mpatches.Patch(color="#90ee90", label="Low vegetation"),
    mpatches.Patch(color="#d2b48c", label="Non-vegetation"),
    mpatches.Patch(color="#cccccc", label="No data"),
]


def scale_to_rgb(arr, plow=2, phigh=98):
    lo, hi = np.nanpercentile(arr, [plow, phigh])
    return np.clip((arr - lo) / (hi - lo + 1e-10), 0, 1)


# ---------------------------------------------------------------------------
# Study area basemap
# ---------------------------------------------------------------------------
def plot_study_area(gdf_utm):
    fig, ax = plt.subplots(figsize=(10, 8))
    gdf_utm.boundary.plot(ax=ax, edgecolor="red", linewidth=2.5)
    try:
        import contextily as cx
        cx.add_basemap(
            ax, crs=gdf_utm.crs.to_string(),
            source=cx.providers.Esri.WorldImagery, zoom=16,
        )
    except Exception:
        pass
    ax.set_title("Study Area \u2014 Fairfax County, VA")
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Sentinel-2 composites
# ---------------------------------------------------------------------------
def plot_s2_composites(red, green, blue, nir, date_str=""):
    rgb = np.dstack([red, green, blue])
    cir = np.dstack([nir, red, green])

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    axes[0].imshow(scale_to_rgb(rgb))
    axes[0].set_title("Sentinel-2 True Color (B04-B03-B02)")
    axes[0].axis("off")

    axes[1].imshow(scale_to_rgb(cir))
    axes[1].set_title("Sentinel-2 Color-Infrared (B08-B04-B03)")
    axes[1].axis("off")

    if date_str:
        plt.suptitle(f"Sentinel-2 L2A \u2014 {date_str}", fontsize=14, y=1.01)
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Spectral indices
# ---------------------------------------------------------------------------
def plot_indices(ndvi, ndre, ndbi):
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    im0 = axes[0].imshow(ndvi, cmap="RdYlGn", vmin=-0.1, vmax=0.8)
    axes[0].set_title("NDVI")
    plt.colorbar(im0, ax=axes[0], fraction=0.035)

    im1 = axes[1].imshow(ndre, cmap="RdYlGn", vmin=-0.1, vmax=0.7)
    axes[1].set_title("NDRE (Red Edge)")
    plt.colorbar(im1, ax=axes[1], fraction=0.035)

    im2 = axes[2].imshow(ndbi, cmap="RdYlBu_r", vmin=-0.4, vmax=0.2)
    axes[2].set_title("NDBI (Built-up)")
    plt.colorbar(im2, ax=axes[2], fraction=0.035)

    for ax in axes:
        ax.axis("off")
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# LiDAR elevation products
# ---------------------------------------------------------------------------
def _to_np(arr):
    """Convert xarray DataArray or numpy array to plain 2-D numpy."""
    if hasattr(arr, "values"):
        return arr.values
    return arr


def plot_lidar_products(dtm, dsm, chm):
    dtm_np = _to_np(dtm)
    dsm_np = _to_np(dsm)
    chm_np = _to_np(chm)

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    im0 = axes[0].imshow(dtm_np, cmap="terrain")
    axes[0].set_title("DTM (bare earth)")
    plt.colorbar(im0, ax=axes[0], fraction=0.035, label="Elevation (m)")

    im1 = axes[1].imshow(dsm_np, cmap="terrain")
    axes[1].set_title("DSM (surface model)")
    plt.colorbar(im1, ax=axes[1], fraction=0.035, label="Elevation (m)")

    im2 = axes[2].imshow(chm_np, cmap="Greens", vmin=0, vmax=35)
    axes[2].set_title("CHM (canopy height)")
    plt.colorbar(im2, ax=axes[2], fraction=0.035, label="Height (m)")

    for ax in axes:
        ax.axis("off")

    plt.suptitle("LiDAR-Derived Elevation Products (3DEP)", fontsize=14, y=1.02)
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Single classification map
# ---------------------------------------------------------------------------
def plot_classification(class_map, title="UTC Classification"):
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(class_map, cmap=CMAP_CLASSES, norm=NORM_CLS)
    ax.legend(handles=PATCHES, loc="lower right", fontsize=10)
    ax.set_title(title)
    ax.axis("off")
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Side-by-side classification comparison
# ---------------------------------------------------------------------------
def plot_classification_comparison(rule_map, rf_map):
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))

    for ax, data, title in zip(
        axes,
        [rule_map, rf_map],
        ["Rule-Based Classification", "Random Forest Classification"],
    ):
        ax.imshow(data, cmap=CMAP_CLASSES, norm=NORM_CLS)
        ax.set_title(title)
        ax.axis("off")

    axes[1].legend(handles=PATCHES, loc="lower right", fontsize=10)
    plt.suptitle("UTC Classification Comparison", fontsize=14, y=1.01)
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Summary dashboard (2 x 3)
# ---------------------------------------------------------------------------
def plot_summary(
    rgb, ndvi_a, chm_max_10,
    rule_map, rf_map, valid,
    oa_rule, k_rule, oa_rf, k_rf,
):
    fig, axes = plt.subplots(2, 3, figsize=(20, 13))

    # Row 1: inputs
    axes[0, 0].imshow(scale_to_rgb(rgb))
    axes[0, 0].set_title("Sentinel-2 True Color")
    axes[0, 0].axis("off")

    im_ndvi = axes[0, 1].imshow(ndvi_a, cmap="RdYlGn", vmin=-0.1, vmax=0.8)
    axes[0, 1].set_title("NDVI (aligned 10 m)")
    axes[0, 1].axis("off")
    plt.colorbar(im_ndvi, ax=axes[0, 1], fraction=0.035)

    im_chm = axes[0, 2].imshow(chm_max_10, cmap="Greens", vmin=0, vmax=35)
    axes[0, 2].set_title("CHM max (10 m aggregated)")
    axes[0, 2].axis("off")
    plt.colorbar(im_chm, ax=axes[0, 2], fraction=0.035, label="m")

    # Row 2: outputs
    axes[1, 0].imshow(rule_map, cmap=CMAP_CLASSES, norm=NORM_CLS)
    axes[1, 0].set_title(f"Rule-Based (OA={oa_rule:.0%}, \u03ba={k_rule:.2f})")
    axes[1, 0].axis("off")

    axes[1, 1].imshow(rf_map, cmap=CMAP_CLASSES, norm=NORM_CLS)
    axes[1, 1].set_title(f"Random Forest (OA={oa_rf:.0%}, \u03ba={k_rf:.2f})")
    axes[1, 1].axis("off")

    diff = (rule_map != rf_map).astype(np.uint8)
    diff[~valid] = 2
    cmap_diff = ListedColormap(["#ffffff", "#e74c3c", "#cccccc"])
    axes[1, 2].imshow(diff, cmap=cmap_diff, vmin=0, vmax=2)
    axes[1, 2].set_title("Disagreement (Rule vs RF)")
    axes[1, 2].axis("off")
    diff_pct = (diff == 1).sum() / valid.sum() * 100
    axes[1, 2].text(
        0.02, 0.02, f"{diff_pct:.1f}% of pixels differ",
        transform=axes[1, 2].transAxes, fontsize=10,
        bbox=dict(boxstyle="round", fc="white", alpha=0.8),
    )

    fig.legend(
        handles=PATCHES, loc="lower center", ncol=4,
        fontsize=11, bbox_to_anchor=(0.5, -0.01),
    )
    plt.suptitle(
        "Urban Tree Canopy Assessment \u2014 Fairfax County, VA",
        fontsize=15, y=1.01,
    )
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Results summary (text)
# ---------------------------------------------------------------------------
def print_summary(
    valid, s2_item, lidar_res,
    rule_map, rf_map,
    oa_rule, k_rule, oa_rf, k_rf,
):
    from scripts.config import CLASS_TREE, CLASS_LOW, CLASS_NONVEG, LABELS

    pixel_area = 10 * 10  # m\u00b2

    print("Urban Tree Canopy Assessment \u2014 Summary")
    print("=" * 55)
    print("Study area          : Fairfax County, VA")
    print(f"Area analysed       : {valid.sum() * pixel_area / 1e4:.1f} ha")
    print(f"Sentinel-2 date     : {s2_item.datetime:%Y-%m-%d}")
    print("Sentinel-2 pixel    : 10 m")
    print("LiDAR source        : USGS 3DEP")
    print(f"CHM native res.     : {lidar_res} m  (aggregated to 10 m)")
    print()

    for label, cdata, oa, kappa in [
        ("Rule-Based",    rule_map, oa_rule, k_rule),
        ("Random Forest", rf_map,   oa_rf,   k_rf),
    ]:
        tree_px  = (cdata == CLASS_TREE).sum()
        low_px   = (cdata == CLASS_LOW).sum()
        nonv_px  = (cdata == CLASS_NONVEG).sum()
        total_px = tree_px + low_px + nonv_px
        print(f"{label} (OA={oa:.0%}, \u03ba={kappa:.2f}):")
        print(f"  Tree canopy       : {tree_px * pixel_area / 1e4:.2f} ha  "
              f"({tree_px / total_px * 100:.1f}%)")
        print(f"  Low vegetation    : {low_px * pixel_area / 1e4:.2f} ha  "
              f"({low_px / total_px * 100:.1f}%)")
        print(f"  Non-vegetation    : {nonv_px * pixel_area / 1e4:.2f} ha  "
              f"({nonv_px / total_px * 100:.1f}%)")
        print()

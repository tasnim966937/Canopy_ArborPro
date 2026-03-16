"""Align Sentinel-2 (10 m) and LiDAR CHM onto a common grid."""

import warnings
import numpy as np
import xarray as xr

from scripts.config import CRS_UTM, bounds_utm, gdf_utm, S2_RES
from scripts.sentinel2 import S2_BANDS, EPS


# ---------------------------------------------------------------------------
# CHM block aggregation  (1 m -> 10 m)
# ---------------------------------------------------------------------------
def aggregate_chm(chm_arr, factor=10):
    """Aggregate a CHM to *factor*-m using block statistics.

    Returns
    -------
    chm_max, chm_mean, chm_std : numpy.ndarray
    """
    nr = chm_arr.shape[0] // factor * factor
    nc = chm_arr.shape[1] // factor * factor
    trimmed = chm_arr[:nr, :nc]
    blocks = trimmed.reshape(nr // factor, factor, nc // factor, factor)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        chm_max  = np.nanmax(blocks,  axis=(1, 3))
        chm_mean = np.nanmean(blocks, axis=(1, 3))
        chm_std  = np.nanstd(blocks,  axis=(1, 3))
    return chm_max, chm_mean, chm_std


# ---------------------------------------------------------------------------
# Full alignment pipeline
# ---------------------------------------------------------------------------
def align_grids(s2, chm):
    """Bring Sentinel-2 bands and the CHM onto a common 10 m UTM grid.

    Parameters
    ----------
    s2 : dict[str, xarray.DataArray]
        Band name -> DataArray (in the native S2 CRS, 10 m).
    chm : xarray.DataArray or numpy.ndarray
        CHM — can be an xarray DataArray (from download_dtm_dsm) or a raw
        numpy array (from the old build_chm workflow).

    Returns
    -------
    result : dict  with keys
        s2_utm, ndvi_a, ndre_a, ndbi_a,
        chm_max_10, chm_mean_10, chm_std_10, shape
    """
    # --- Reproject S2 to UTM 10 m ---
    s2_ref_utm = s2["B04"].rio.reproject(CRS_UTM, resolution=S2_RES)
    s2_ref_utm = s2_ref_utm.rio.clip(gdf_utm.geometry, all_touched=True)

    # --- Prepare CHM as xarray DataArray in UTM ---
    if isinstance(chm, np.ndarray):
        bx = bounds_utm
        chm_da = xr.DataArray(
            chm[::-1],
            dims=["y", "x"],
            coords={
                "y": np.linspace(bx[3], bx[1], chm.shape[0]),
                "x": np.linspace(bx[0], bx[2], chm.shape[1]),
            },
        )
        chm_da = chm_da.rio.write_crs(CRS_UTM)
    else:
        chm_da = chm
        if chm_da.rio.crs != CRS_UTM:
            chm_da = chm_da.rio.reproject(CRS_UTM)

    # --- Determine native CHM resolution to choose aggregation factor ---
    chm_res = abs(float(chm_da.rio.resolution()[0]))
    factor = max(1, round(S2_RES / chm_res))
    print(f"CHM native resolution: ~{chm_res:.1f} m  (aggregation factor: {factor})")

    if factor > 1:
        chm_max_10, chm_mean_10, chm_std_10 = aggregate_chm(
            chm_da.values, factor=factor
        )
    else:
        # CHM already at ~10 m, reproject to match S2 grid directly
        chm_matched = chm_da.rio.reproject_match(s2_ref_utm)
        chm_vals = chm_matched.values
        chm_max_10 = chm_vals
        chm_mean_10 = chm_vals
        chm_std_10 = np.zeros_like(chm_vals)

    print(f"CHM 10 m grid shape: {chm_max_10.shape}")
    print(f"S2  UTM grid shape : {s2_ref_utm.shape}")

    # --- Common extent ---
    target_rows = min(chm_max_10.shape[0], s2_ref_utm.shape[0])
    target_cols = min(chm_max_10.shape[1], s2_ref_utm.shape[1])
    chm_max_10  = chm_max_10[:target_rows,  :target_cols]
    chm_mean_10 = chm_mean_10[:target_rows, :target_cols]
    chm_std_10  = chm_std_10[:target_rows,  :target_cols]

    # --- Reproject every S2 band to UTM 10 m and trim ---
    s2_utm = {}
    for band in S2_BANDS:
        da = s2[band].rio.reproject(CRS_UTM, resolution=S2_RES)
        da = da.rio.clip(gdf_utm.geometry, all_touched=True)
        s2_utm[band] = da.values[:target_rows, :target_cols].astype(float)

    # --- Recompute indices on the aligned grid ---
    red_a   = s2_utm["B04"]
    nir_a   = s2_utm["B08"]
    re1_a   = s2_utm["B05"]
    swir1_a = s2_utm["B11"]

    ndvi_a = (nir_a - red_a)   / (nir_a + red_a   + EPS)
    ndre_a = (nir_a - re1_a)   / (nir_a + re1_a   + EPS)
    ndbi_a = (swir1_a - nir_a) / (swir1_a + nir_a + EPS)

    print(f"\nAligned grid: {target_rows} rows x {target_cols} cols (10 m)")

    return dict(
        s2_utm=s2_utm,
        ndvi_a=ndvi_a,
        ndre_a=ndre_a,
        ndbi_a=ndbi_a,
        chm_max_10=chm_max_10,
        chm_mean_10=chm_mean_10,
        chm_std_10=chm_std_10,
        shape=(target_rows, target_cols),
    )

"""LiDAR / 3DEP data acquisition and Canopy Height Model generation.

Data source: USGS 3DEP via Microsoft Planetary Computer STAC API.
Available collections:
  - 3dep-lidar-dtm  (bare-earth Digital Terrain Model, COG)
  - 3dep-lidar-dsm  (Digital Surface Model, COG)
  - 3dep-lidar-copc (raw point cloud, Cloud-Optimized Point Cloud)
"""

import numpy as np
import xarray as xr
import rioxarray
import pystac_client
import planetary_computer
import rasterio
from rasterio.merge import merge as rasterio_merge
from rasterio import Affine
from pathlib import Path

from scripts.config import (
    BBOX, CRS_GEO, CRS_UTM, LIDAR_RES,
    gdf_geo, gdf_utm, bounds_utm, study_area, DATA_DIR,
)

WEST, SOUTH, EAST, NORTH = BBOX

LIDAR_DIR = DATA_DIR / "lidar"
DEM_DIR   = DATA_DIR / "dem"


# ---------------------------------------------------------------------------
# Planetary Computer STAC search for 3DEP tiles
# ---------------------------------------------------------------------------
def _get_catalog():
    return pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )


def search_3dep(collection="3dep-lidar-dtm", name_filter=None,
                bbox_buffer=0.25):
    """Find 3DEP tiles near the study area.

    Uses an expanded search bbox to compensate for inaccurate STAC
    footprints in the 3DEP collection (observed offsets of 15–20 km).

    Parameters
    ----------
    collection : str
        One of '3dep-lidar-dtm', '3dep-lidar-dsm', '3dep-lidar-copc'.
    name_filter : str, optional
        Keep only tiles whose ID contains this substring
        (e.g. 'Fairfax_County_2018' to use only the 2018 survey).
    bbox_buffer : float
        Degrees to expand the search bbox in each direction (default 0.25°).

    Returns
    -------
    items : list[pystac.Item]
    """
    catalog = _get_catalog()
    expanded = [WEST - bbox_buffer, SOUTH - bbox_buffer,
                EAST + bbox_buffer, NORTH + bbox_buffer]
    search = catalog.search(
        collections=[collection],
        bbox=expanded,
    )
    items = list(search.items())
    print(f"{collection}: {len(items)} tile(s) found (bbox buffer ±{bbox_buffer}°)")
    for it in items[:20]:
        print(f"  {it.id}")
    if len(items) > 20:
        print(f"  ... and {len(items) - 20} more")

    if name_filter:
        items = [it for it in items if name_filter in it.id]
        print(f"  Filtered to '{name_filter}': {len(items)} tile(s)")

    return items


# ---------------------------------------------------------------------------
# Load a 3DEP raster product (DTM or DSM), merge tiles, clip to study area
# ---------------------------------------------------------------------------
def _load_and_clip(items, asset_key="data"):
    """Load COG tiles, merge, and clip to study area via pixel windowing.

    The 3DEP tiles use a compound CRS whose horizontal component is
    NAD83 / UTM 18N (EPSG:26918).  This is sub-metre identical to
    WGS84 / UTM 18N (EPSG:32618), so we skip the CRS reprojection
    (which fails due to the compound CRS + PROJ mismatch) and just
    window-clip the mosaic array directly.

    Tiles are pre-filtered by actual raster extent to discard those
    returned by the STAC search whose data doesn't truly overlap.

    Returns
    -------
    clipped : xarray.DataArray   (2-D, float32, tagged as CRS_UTM)
    """
    left, bottom, right, top = bounds_utm

    datasets = []
    for item in items:
        href = item.assets[asset_key].href
        print(f"    Opening {item.id} ...")
        ds = rasterio.open(href)
        b = ds.bounds
        overlaps = (b.right > left and b.left < right and
                    b.top > bottom and b.bottom < top)
        if overlaps:
            datasets.append(ds)
            print(f"      ✓ overlaps study area "
                  f"(tile y [{b.bottom:.0f}, {b.top:.0f}])")
        else:
            ds.close()
            print(f"      ✗ no overlap — tile y [{b.bottom:.0f}, {b.top:.0f}] "
                  f"vs study y [{bottom:.0f}, {top:.0f}]")

    if not datasets:
        raise RuntimeError(
            f"None of the {len(items)} tile(s) actually overlap the study "
            f"area after checking raster extents. "
            f"Study: x [{left:.0f}, {right:.0f}] y [{bottom:.0f}, {top:.0f}]. "
            "The study area may not be covered by this LiDAR survey."
        )

    print(f"    Merging {len(datasets)} overlapping tile(s) ...")
    src_nodata = datasets[0].nodata
    mosaic, mosaic_transform = rasterio_merge(datasets)
    for ds in datasets:
        ds.close()

    nrows, ncols = mosaic.shape[1], mosaic.shape[2]
    native_res = abs(mosaic_transform.a)

    # Mosaic geographic extent (in whatever UTM the tiles use)
    mos_left = mosaic_transform.c
    mos_top  = mosaic_transform.f
    mos_right  = mos_left + ncols * mosaic_transform.a
    mos_bottom = mos_top  + nrows * mosaic_transform.e

    print(f"    Mosaic: {nrows} x {ncols} @ {native_res}m  nodata={src_nodata}")
    print(f"    Mosaic extent : x [{mos_left:.0f}, {mos_right:.0f}]  "
          f"y [{mos_bottom:.0f}, {mos_top:.0f}]")

    # Study-area bounds (EPSG:32618 ≈ EPSG:26918 — sub-metre identical)
    left, bottom, right, top = bounds_utm
    print(f"    Study extent  : x [{left:.0f}, {right:.0f}]  "
          f"y [{bottom:.0f}, {top:.0f}]")

    # Map study-area corners to fractional pixel coordinates
    inv = ~mosaic_transform
    fc0, fr0 = inv * (left, top)       # top-left of study area
    fc1, fr1 = inv * (right, bottom)   # bottom-right of study area

    # Use floor/ceil to include all partially overlapping pixels
    row0 = int(np.floor(min(fr0, fr1)))
    row1 = int(np.ceil(max(fr0, fr1)))
    col0 = int(np.floor(min(fc0, fc1)))
    col1 = int(np.ceil(max(fc0, fc1)))

    print(f"    Raw pixel window: rows [{row0}, {row1})  cols [{col0}, {col1})")

    # Clamp to mosaic extent
    row0 = max(row0, 0)
    row1 = min(row1, nrows)
    col0 = max(col0, 0)
    col1 = min(col1, ncols)

    if row1 <= row0 or col1 <= col0:
        raise RuntimeError(
            f"Study area does not overlap mosaic after clamping. "
            f"Clamped window: rows [{row0}, {row1}), cols [{col0}, {col1}). "
            f"Mosaic: {nrows} rows x {ncols} cols."
        )

    clip = mosaic[0, row0:row1, col0:col1].astype("float32")
    if src_nodata is not None:
        clip[clip == np.float32(src_nodata)] = np.nan

    # Transform for the clipped window
    clip_transform = mosaic_transform * Affine.translation(col0, row0)
    ny, nx = clip.shape
    origin_x = clip_transform.c
    origin_y = clip_transform.f
    res_x = clip_transform.a
    res_y = clip_transform.e  # negative (north-up)

    da = xr.DataArray(
        clip,
        dims=["y", "x"],
        coords={
            "y": origin_y + (np.arange(ny) + 0.5) * res_y,
            "x": origin_x + (np.arange(nx) + 0.5) * res_x,
        },
    )
    da = da.rio.write_crs(CRS_UTM)
    da = da.rio.write_transform(clip_transform)
    da = da.rio.write_nodata(np.nan)

    valid_pct = np.isfinite(clip).mean() * 100
    vmin = np.nanmin(clip) if valid_pct > 0 else float("nan")
    vmax = np.nanmax(clip) if valid_pct > 0 else float("nan")
    print(f"    Clipped: {ny} x {nx} @ {native_res}m  |  "
          f"{valid_pct:.0f}% valid  |  range: {vmin:.1f} – {vmax:.1f} m")
    return da


# ---------------------------------------------------------------------------
# Download DTM and DSM, compute CHM
# ---------------------------------------------------------------------------
def download_dtm_dsm(name_filter=None):
    """Download 3DEP DTM and DSM from Planetary Computer, compute CHM.

    Parameters
    ----------
    name_filter : str, optional
        Keep only tiles whose ID contains this substring
        (e.g. 'Fairfax_County_2018').

    Saves to:
      data/dem/dtm_3dep.tif
      data/dem/dsm_3dep.tif
      data/lidar/chm.tif

    Returns
    -------
    dtm, dsm, chm : xarray.DataArray
    """
    DEM_DIR.mkdir(parents=True, exist_ok=True)
    LIDAR_DIR.mkdir(parents=True, exist_ok=True)

    dtm_path = DEM_DIR / "dtm_3dep.tif"
    dsm_path = DEM_DIR / "dsm_3dep.tif"
    chm_path = LIDAR_DIR / "chm.tif"

    # --- DTM ---
    if dtm_path.exists():
        print(f"Using cached DTM: {dtm_path}")
        dtm = rioxarray.open_rasterio(str(dtm_path)).squeeze()
    else:
        print("Searching for 3DEP DTM tiles ...")
        dtm_items = search_3dep("3dep-lidar-dtm", name_filter=name_filter)
        if not dtm_items:
            raise RuntimeError("No 3DEP DTM tiles found for this study area.")
        print("Loading and clipping DTM ...")
        dtm = _load_and_clip(dtm_items)
        dtm.rio.to_raster(str(dtm_path))
        print(f"Saved DTM: {dtm_path}")

    print(f"DTM shape : {dtm.shape}  CRS: {dtm.rio.crs}")
    print(f"DTM range : {float(dtm.min()):.1f} \u2013 {float(dtm.max()):.1f} m")

    # --- DSM ---
    if dsm_path.exists():
        print(f"\nUsing cached DSM: {dsm_path}")
        dsm = rioxarray.open_rasterio(str(dsm_path)).squeeze()
    else:
        print("\nSearching for 3DEP DSM tiles ...")
        dsm_items = search_3dep("3dep-lidar-dsm", name_filter=name_filter)
        if not dsm_items:
            raise RuntimeError("No 3DEP DSM tiles found for this study area.")
        print("Loading and clipping DSM ...")
        dsm = _load_and_clip(dsm_items)
        dsm.rio.to_raster(str(dsm_path))

    print(f"DSM shape : {dsm.shape}  CRS: {dsm.rio.crs}")
    print(f"DSM range : {float(dsm.min()):.1f} \u2013 {float(dsm.max()):.1f} m")

    # --- CHM ---
    # Align DSM to DTM grid if shapes differ
    if dsm.shape != dtm.shape:
        dsm = dsm.rio.reproject_match(dtm)

    chm = dsm - dtm
    chm = chm.where(chm >= 0, 0)  # clamp negatives
    chm.rio.to_raster(str(chm_path))

    print(f"\nCHM shape : {chm.shape}")
    print(f"CHM range : {float(chm.min()):.1f} \u2013 {float(chm.max()):.1f} m")
    print(f"Saved CHM : {chm_path}")

    return dtm, dsm, chm


# ---------------------------------------------------------------------------
# Convert CHM xarray to numpy for downstream use
# ---------------------------------------------------------------------------
def chm_to_numpy(chm):
    """Return the CHM as a plain numpy array (for alignment & classification).

    Returns
    -------
    chm_arr : numpy.ndarray  (2-D, float32)
    """
    return chm.values.astype("float32")


# ---------------------------------------------------------------------------
# Optional: download raw COPC point cloud
# ---------------------------------------------------------------------------
def download_copc(out_dir=None):
    """Download raw 3DEP COPC point cloud tile(s) for the study area.

    Saves .copc.laz files into data/lidar/copc/.

    Returns
    -------
    paths : list[pathlib.Path]
    """
    copc_dir = Path(out_dir or LIDAR_DIR / "copc")
    copc_dir.mkdir(parents=True, exist_ok=True)

    items = search_3dep("3dep-lidar-copc")
    if not items:
        print("No COPC tiles found.")
        return []

    import requests
    paths = []
    for item in items:
        href = item.assets["data"].href
        fname = f"{item.id}.copc.laz"
        out_path = copc_dir / fname
        if out_path.exists():
            print(f"Cached: {out_path}")
        else:
            print(f"Downloading {fname} ...")
            r = requests.get(href, stream=True, timeout=600)
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
            print(f"Saved: {out_path}  ({out_path.stat().st_size / 1e6:.1f} MB)")
        paths.append(out_path)

    return paths

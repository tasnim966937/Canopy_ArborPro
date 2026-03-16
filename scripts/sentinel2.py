"""Sentinel-2 L2A data acquisition and spectral-index computation.

Sentinel-2 L2A provides **surface reflectance** (bottom-of-atmosphere)
with values scaled by 10 000  (i.e. 1500 = reflectance of 0.15).
"""

import numpy as np
import xarray as xr
import pystac_client
import planetary_computer
import rioxarray
from rasterio.enums import Resampling
from shapely.geometry import mapping
from pathlib import Path

from scripts.config import (
    BBOX, CRS_GEO, study_area, gdf_geo, DATA_DIR,
)

# Bands to load (10 m native: B02-B04, B08 | 20 m resampled: B05-B07, B11-B12)
S2_BANDS = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B11", "B12"]

SCALE_FACTOR = 10_000  # L2A DN -> surface reflectance (0–1)
EPS = 1e-10


# ---------------------------------------------------------------------------
# Search & select
# ---------------------------------------------------------------------------
def search_scenes(
    datetime_range="2018-06-01/2018-09-30",
    max_cloud=10,
    show=8,
):
    """Query Planetary Computer for low-cloud Sentinel-2 L2A scenes."""
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        intersects=mapping(study_area),
        datetime=datetime_range,
        query={"eo:cloud_cover": {"lt": max_cloud}},
    )
    items = sorted(search.items(),
                   key=lambda x: x.properties["eo:cloud_cover"])

    print(f"Sentinel-2 scenes found (cloud < {max_cloud}%): {len(items)}")
    for it in items[:show]:
        cc = it.properties["eo:cloud_cover"]
        print(f"  {it.id}  {it.datetime:%Y-%m-%d}  cloud={cc:.1f}%")

    return items


def select_scene(items, index=0):
    """Pick a scene from the search results."""
    item = items[index]
    print(f"\nSelected scene  : {item.id}")
    print(f"Acquisition date: {item.datetime:%Y-%m-%d}")
    print(f"Cloud cover     : {item.properties['eo:cloud_cover']:.1f}%")
    return item


# ---------------------------------------------------------------------------
# Band loading (into memory, clipped to study area)
# ---------------------------------------------------------------------------
def load_bands(s2_item, bands=None):
    """Load and clip Sentinel-2 bands; 20 m bands are resampled to 10 m.

    Returns
    -------
    s2 : dict[str, xarray.DataArray]
        Band name -> clipped DataArray (all on the same 10 m grid).
    s2_crs : CRS
        Native CRS of the loaded data.
    """
    bands = bands or S2_BANDS

    ref_da = rioxarray.open_rasterio(
        s2_item.assets["B04"].href
    ).squeeze()
    s2_crs = ref_da.rio.crs
    study_in_s2 = gdf_geo.to_crs(s2_crs)
    s2_bounds = study_in_s2.total_bounds
    ref_clip = ref_da.rio.clip_box(*s2_bounds)

    s2 = {}
    for band in bands:
        print(f"  Loading {band} ...", end="")
        da = rioxarray.open_rasterio(
            s2_item.assets[band].href
        ).squeeze()
        da = da.rio.clip_box(*s2_bounds)
        if da.shape != ref_clip.shape:
            da = da.rio.reproject_match(ref_clip)
        s2[band] = da.rio.clip(study_in_s2.geometry, all_touched=True)
        s2[band] = s2[band].astype("float32") / SCALE_FACTOR
        print(f" {s2[band].shape}")

    print(f"\nGrid shape : {ref_clip.shape}")
    print(f"CRS        : {s2_crs}")
    print(f"Pixel size : 10 m  |  values: surface reflectance (0\u20131)")

    return s2, s2_crs


# ---------------------------------------------------------------------------
# Download full scene (entire tile) — stacked multi-band GeoTIFF
# ---------------------------------------------------------------------------
def download_full_scene(s2_item, bands=None, out_dir=None):
    """Download the full Sentinel-2 tile and save as a stacked GeoTIFF.

    All bands are resampled to 10 m so they share a common grid.

    Returns
    -------
    out_path : pathlib.Path
    """
    bands = bands or S2_BANDS
    scene_id = s2_item.id
    scene_dir = Path(out_dir or DATA_DIR / "sentinel2")
    scene_dir.mkdir(parents=True, exist_ok=True)
    out_path = scene_dir / f"{scene_id}_full.tif"

    if out_path.exists():
        print(f"Already exists: {out_path}")
        return out_path

    # Use B04 (10 m) as the reference grid for the full tile
    print("  Loading reference grid (B04) ...")
    ref = rioxarray.open_rasterio(s2_item.assets["B04"].href)
    target_shape = ref.shape  # (1, rows, cols)

    band_arrays = []
    for band in bands:
        print(f"  Loading {band} (full tile) ...", end="")
        da = rioxarray.open_rasterio(s2_item.assets[band].href)
        if da.shape != target_shape:
            da = da.rio.reproject_match(ref, resampling=Resampling.bilinear)
        da = da.astype("float32") / SCALE_FACTOR
        band_arrays.append(da)
        print(f" {da.shape[1]}x{da.shape[2]}")

    stacked = xr.concat(band_arrays, dim="band")
    stacked["band"] = list(bands)

    print(f"  Writing {out_path} ...")
    stacked.rio.to_raster(str(out_path))
    size_mb = out_path.stat().st_size / 1e6
    print(f"  Saved full scene: {out_path}  ({size_mb:.1f} MB)")
    print(f"  Bands: {bands}")
    print(f"  Shape: {stacked.shape}  CRS: {stacked.rio.crs}")
    return out_path


# ---------------------------------------------------------------------------
# Save cropped (study-area) bands — stacked multi-band GeoTIFF
# ---------------------------------------------------------------------------
def save_cropped(s2, s2_item, bands=None, out_dir=None):
    """Stack the already-clipped bands and write a single multi-band GeoTIFF.

    Parameters
    ----------
    s2 : dict  returned by load_bands()

    Returns
    -------
    out_path : pathlib.Path
    """
    bands = bands or list(s2.keys())
    scene_id = s2_item.id
    scene_dir = Path(out_dir or DATA_DIR / "sentinel2")
    scene_dir.mkdir(parents=True, exist_ok=True)
    out_path = scene_dir / f"{scene_id}_crop.tif"

    band_arrays = [s2[b].expand_dims("band") for b in bands]
    stacked = xr.concat(band_arrays, dim="band")
    stacked["band"] = list(bands)

    stacked.rio.to_raster(str(out_path))
    size_mb = out_path.stat().st_size / 1e6
    print(f"Saved cropped scene: {out_path}  ({size_mb:.1f} MB)")
    print(f"Bands: {bands}")
    print(f"Shape: {stacked.shape}  CRS: {stacked.rio.crs}")
    return out_path


# ---------------------------------------------------------------------------
# Load a stacked GeoTIFF back into a band dict
# ---------------------------------------------------------------------------
def load_stacked(tif_path, bands=None):
    """Read a stacked multi-band GeoTIFF into a dict of DataArrays.

    Returns
    -------
    s2 : dict[str, xarray.DataArray]
    s2_crs : CRS
    """
    bands = bands or S2_BANDS
    da = rioxarray.open_rasterio(str(tif_path))
    s2_crs = da.rio.crs

    s2 = {}
    for i, band in enumerate(bands):
        s2[band] = da.isel(band=i)

    print(f"Loaded {len(s2)} bands from {tif_path}")
    print(f"CRS: {s2_crs}  Shape: {da.shape}")
    return s2, s2_crs


# ---------------------------------------------------------------------------
# Spectral indices
# ---------------------------------------------------------------------------
def compute_indices(s2):
    """Compute NDVI, NDRE, and NDBI from loaded band dict.

    Input values are surface reflectance in 0\u20131.

    Returns
    -------
    dict with keys: ndvi, ndre, ndbi, red, green, blue, nir
    """
    red   = s2["B04"].values.astype(float)
    green = s2["B03"].values.astype(float)
    blue  = s2["B02"].values.astype(float)
    nir   = s2["B08"].values.astype(float)
    re1   = s2["B05"].values.astype(float)
    swir1 = s2["B11"].values.astype(float)

    ndvi = (nir - red)   / (nir + red   + EPS)
    ndre = (nir - re1)   / (nir + re1   + EPS)
    ndbi = (swir1 - nir) / (swir1 + nir + EPS)

    return dict(
        ndvi=ndvi, ndre=ndre, ndbi=ndbi,
        red=red, green=green, blue=blue, nir=nir,
    )

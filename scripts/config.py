"""Study-area definition, CRS settings, and shared constants."""

import os as _os
from pathlib import Path

# Fix PROJ database conflict — must happen before pyproj/rasterio/geopandas load
# Use rasterio's proj.db which matches the PROJ shared library it bundles
_proj_candidates = [
    "/opt/conda/envs/torch_gpu/lib/python3.12/site-packages/rasterio/proj_data",
    "/opt/conda/envs/torch_gpu/lib/python3.12/site-packages/pyproj/proj_dir/share/proj",
]
for _proj_dir in _proj_candidates:
    if Path(_proj_dir, "proj.db").exists():
        _os.environ["PROJ_LIB"]  = _proj_dir
        _os.environ["PROJ_DATA"] = _proj_dir
        break

import geopandas as gpd
from shapely.geometry import box

# ---------------------------------------------------------------------------
# Study area bounding box (WGS 84)
# ---------------------------------------------------------------------------
BBOX = (-77.105, 38.895, -77.087, 38.910)
WEST, SOUTH, EAST, NORTH = BBOX

# ---------------------------------------------------------------------------
# Coordinate reference systems
# ---------------------------------------------------------------------------
CRS_GEO = "EPSG:4326"
CRS_UTM = "EPSG:32618"  # UTM Zone 18N — covers Fairfax County, VA

# ---------------------------------------------------------------------------
# Resolutions
# ---------------------------------------------------------------------------
LIDAR_RES = 1    # point-cloud interpolation grid (metres)
S2_RES    = 10   # Sentinel-2 native pixel size (metres)

# ---------------------------------------------------------------------------
# Classification class codes and labels
# ---------------------------------------------------------------------------
CLASS_NODATA = 0
CLASS_NONVEG = 1
CLASS_LOW    = 2
CLASS_TREE   = 3

LABELS = {
    CLASS_TREE:   "Tree canopy",
    CLASS_LOW:    "Low vegetation",
    CLASS_NONVEG: "Non-vegetation",
    CLASS_NODATA: "No data",
}

# LAS point-class lookup
LAS_CLASS_LABELS = {
    0: "Never classified", 1: "Unclassified", 2: "Ground",
    3: "Low vegetation", 4: "Medium vegetation",
    5: "High vegetation", 6: "Building", 7: "Noise",
    9: "Water", 17: "Bridge deck",
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path("data")

# ---------------------------------------------------------------------------
# Derived geometries (created once at import time)
# ---------------------------------------------------------------------------
study_area = box(*BBOX)
gdf_geo = gpd.GeoDataFrame(geometry=[study_area], crs=CRS_GEO)
gdf_utm = gdf_geo.to_crs(CRS_UTM)
bounds_utm = gdf_utm.total_bounds


def print_study_area():
    """Print a quick summary of the study area."""
    area_ha = gdf_utm.geometry.area.values[0] / 1e4
    bx = bounds_utm
    print(f"Bounding box (WGS 84): {BBOX}")
    print(f"Bounding box (UTM 18N): ({bx[0]:.0f}, {bx[1]:.0f}, "
          f"{bx[2]:.0f}, {bx[3]:.0f})")
    print(f"Study area : {area_ha:.1f} ha  ({area_ha / 100:.2f} km\u00b2)")

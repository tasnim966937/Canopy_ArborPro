# Decisions Log

## 2026-03-16: Light theme for PowerPoint presentation
**Choice**: White background with deep blue/green accents
**Over**: Dark/futuristic theme (GitHub Dark palette)
**Because**: User requested white/light background for the recruiter presentation

## 2026-03-16: Expanded 3DEP STAC search with pre-filtering
**Choice**: Search with ±0.25° bbox buffer, then pre-filter tiles by actual raster bounds
**Over**: Using exact study area bbox for STAC search (which returned wrong tiles)
**Because**: 3DEP STAC catalog footprints are grossly inaccurate (15–20 km offset). The expanded search catches all nearby tiles, and the pre-filter ensures only tiles with real overlap are used.

## 2026-03-11: Move study area to Fairfax County proper
**Choice**: BBOX (-77.105, 38.895, -77.087, 38.910) in Mason District, Fairfax County
**Over**: NW Washington DC (-77.058, 38.932, -77.04, 38.947) and far-south attempt (-77.080, 38.720)
**Because**: User wanted scientific correctness — temporal matching of 2018 Sentinel-2 with 2018 Fairfax County LiDAR. Previous locations had no overlapping 2018 LiDAR data.

## 2026-03-11: Direct pixel windowing for 3DEP tile clipping
**Choice**: Use inverse affine transform to map study bounds to pixel coordinates, then slice numpy array directly
**Over**: rasterio.warp.reproject and rioxarray clip/clip_box
**Because**: 3DEP tiles use a compound CRS (NAD83/UTM18N + NAVD88 height) that caused rasterio.warp.reproject to produce all-NaN arrays and rioxarray clip to fail with NoDataInBounds. Direct windowing avoids CRS transformation entirely since EPSG:26918 ≈ EPSG:32618.

## 2026-03-10: Planetary Computer for 3DEP data access
**Choice**: Microsoft Planetary Computer STAC API for DTM/DSM COGs
**Over**: USGS National Map API + py3dep library
**Because**: USGS API returned JSONDecodeError and was unreliable. py3dep triggered ProjError due to compound CRS. Planetary Computer provides signed COG URLs with standard STAC search.

## 2026-03-10: Modular script architecture
**Choice**: Split into scripts/ package (config, sentinel2, lidar, alignment, classification, accuracy, visualization)
**Over**: Single monolithic Jupyter notebook
**Because**: User requested .py files for maintainability. Modules can be imported and reloaded individually in JupyterLab.

## 2026-03-10: Sentinel-2 date range 2018
**Choice**: Search "2018-06-01/2018-09-30" for temporal match with LiDAR
**Over**: 2024/2025 imagery
**Because**: 2018 Fairfax County LiDAR survey — both datasets must be from the same year for scientific validity.

## 2026-03-10: PROJ_LIB fix at top of config.py
**Choice**: Set PROJ_LIB/PROJ_DATA environment variables to rasterio's proj_data path before any geospatial imports
**Over**: Letting the system find proj.db automatically
**Because**: Multiple conflicting proj.db versions on the JupyterLab server caused ProjError on CRS transformation.

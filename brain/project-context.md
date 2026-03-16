# Project Context

## Project Name
Arbor — Urban Tree Canopy (UTC) Assessment

## Description
A GIS Analyst recruiter assignment that performs an Urban Tree Canopy assessment for a small study area in Fairfax County, Virginia. Combines Sentinel-2 L2A multispectral satellite imagery with USGS 3DEP LiDAR-derived elevation data (both from 2018) to classify land cover into tree canopy, low vegetation, and non-vegetation using rule-based thresholds and Random Forest machine learning. Includes accuracy assessment and a polished PowerPoint presentation of results.

## Tech Stack
- Python 3.12 (Linux JupyterLab + Windows Cursor IDE)
- Geospatial: rasterio, rioxarray, xarray, geopandas, shapely, pyproj
- Data access: pystac-client, planetary-computer (Microsoft Planetary Computer STAC API)
- ML: scikit-learn (RandomForestClassifier)
- Visualization: matplotlib, contextily
- Presentation: python-pptx
- Data: Sentinel-2 L2A (ESA), 3DEP DTM/DSM COGs (USGS)

## Project Structure
- `scripts/` — Modular Python package
  - `config.py` — Study area BBOX, CRS, constants, derived geometries
  - `sentinel2.py` — S2 search, load, band stacking, spectral indices
  - `lidar.py` — 3DEP tile search (expanded bbox), pre-filter by actual extent, merge, clip, CHM
  - `alignment.py` — Align S2 (10 m) and CHM (2 m → 10 m) to common grid
  - `classification.py` — Rule-based + Random Forest classification
  - `accuracy.py` — Reference map, stratified sampling, confusion matrix, OA/kappa
  - `visualization.py` — Plot helpers for notebook display
  - `create_presentation.py` — Generates all figures + 14-slide PPTX
- `data/` — Cached raster data (not committed)
  - `sentinel2/` — Cropped S2 GeoTIFF
  - `dem/` — DTM and DSM from 3DEP
  - `lidar/` — CHM derived from DSM − DTM
- `output/` — Generated presentation and figures
- `requirements.txt` — All Python dependencies

## Goals
- Demonstrate GIS analysis skills for a recruiter interview
- Produce a presentation covering: study area, data sources, methods, results, accuracy

## Conventions
- All paths use forward slashes (Linux JupyterLab compatibility)
- CRS: EPSG:32618 (UTM Zone 18N) for all analysis; EPSG:4326 for search/display
- 3DEP compound CRS (EPSG:26918 + NAVD88) treated as ~identical to EPSG:32618 (sub-metre)
- STAC search for 3DEP uses ±0.25° bbox buffer due to inaccurate catalog footprints
- Tiles pre-filtered by actual raster bounds before merging
- Sentinel-2 L2A values scaled from DN to 0–1 reflectance (÷ 10,000)

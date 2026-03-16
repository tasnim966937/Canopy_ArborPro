# Canopy ArborPro

**Urban Tree Canopy (UTC) Assessment for Fairfax County, Virginia**

A geospatial analysis pipeline that fuses **Sentinel-2 multispectral satellite imagery** with **USGS 3DEP LiDAR-derived elevation data** to map and quantify urban tree canopy cover. Both datasets are temporally matched to **summer 2018** for scientific consistency.

---

## Study Area

| Property | Value |
|---|---|
| **Location** | Mason District, Fairfax County, VA |
| **Bounding box (WGS 84)** | (-77.105, 38.895) to (-77.087, 38.910) |
| **Size** | ~260 ha (2.6 km²) |
| **CRS** | EPSG:32618 (UTM Zone 18N) |

The study area was chosen to align with the coverage of the **2018 Fairfax County LiDAR survey** (USGS 3DEP), ensuring temporal consistency between the satellite and elevation datasets.

---

## Data Sources

### Sentinel-2 L2A (Multispectral Imagery)

- **Provider**: European Space Agency (ESA) via [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/)
- **Product**: Level-2A surface reflectance (bottom-of-atmosphere)
- **Date**: 2018-07-10 (cloud cover 0.4%)
- **Bands used**: B02 (Blue), B03 (Green), B04 (Red), B05–B07 (Red Edge), B08 (NIR), B11–B12 (SWIR)
- **Resolution**: 10 m (20 m bands resampled to 10 m)
- **Scaling**: Raw L2A digital numbers divided by 10,000 to produce 0–1 reflectance

### USGS 3DEP LiDAR (Elevation Data)

- **Provider**: USGS 3D Elevation Program via [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/)
- **Survey**: VA Fairfax County 2018
- **Products**: Digital Terrain Model (DTM) and Digital Surface Model (DSM) as Cloud-Optimized GeoTIFFs
- **Resolution**: 2 m
- **Derived product**: Canopy Height Model (CHM = DSM − DTM), aggregated to 10 m for analysis

---

## Methodology

### 1. Data Acquisition

Sentinel-2 scenes are searched via the Planetary Computer STAC API for summer 2018 with <10% cloud cover. The clearest scene is selected, cropped to the study area, and stacked into a multi-band GeoTIFF.

3DEP DTM and DSM tiles are retrieved using an expanded bounding box search (±0.25°) to account for inaccurate STAC catalog footprints, then pre-filtered by their actual raster extents before merging and clipping.

### 2. Spectral Indices

Three vegetation indices are computed from the Sentinel-2 bands:

| Index | Formula | Purpose |
|---|---|---|
| **NDVI** | (NIR − Red) / (NIR + Red) | Vegetation presence and vigour |
| **NDRE** | (NIR − Red Edge) / (NIR + Red Edge) | Canopy chlorophyll content |
| **NDBI** | (SWIR − NIR) / (SWIR + NIR) | Built-up / impervious surface detection |

### 3. Canopy Height Model

The CHM is derived as **DSM − DTM**, representing the height of above-ground features (trees, buildings). Negative values are clamped to 0. The native 2 m CHM is aggregated to 10 m using block statistics:

- **CHM_max**: maximum canopy height per 10 m cell
- **CHM_mean**: mean canopy height per cell
- **CHM_std**: standard deviation (canopy roughness)

### 4. Grid Alignment

Sentinel-2 (10 m) and the aggregated CHM (10 m) are aligned to a common UTM grid through spatial trimming to their intersection extent.

### 5. Classification

**Three land-cover classes** are mapped:

| Class | Code | Description |
|---|---|---|
| Tree canopy | 3 | Tall woody vegetation (NDVI > 0.3, CHM > 2.5 m) |
| Low vegetation | 2 | Grass, shrubs (NDVI > 0.3, CHM ≤ 2.5 m) |
| Non-vegetation | 1 | Impervious surfaces, bare soil, water (NDVI ≤ 0.3) |

Two classification approaches are applied:

- **Rule-based**: direct NDVI + CHM threshold logic
- **Random Forest** (scikit-learn): 150 trees, max depth 15, trained on high-confidence pixels from the rule-based map using stricter thresholds (NDVI > 0.45 + CHM > 5 m for trees; NDVI > 0.45 + CHM < 1 m for low vegetation; NDVI < 0.15 for non-vegetation). Feature stack includes all 9 Sentinel-2 bands, 3 spectral indices, and 2 CHM statistics (max, std).

### 6. Accuracy Assessment

- A **reference map** is built using independent, stricter thresholds (NDVI > 0.35, CHM > 3.5 m)
- **Stratified random sampling**: ~500 pixels, equal allocation across 3 classes
- **Metrics**: Overall Accuracy (OA), Cohen's Kappa (κ), per-class Precision / Recall / F1, and a confusion matrix

---

## Results

| Metric | Rule-Based | Random Forest |
|---|---|---|
| **Tree canopy** | 73.4% (193 ha) | 72.4% (190 ha) |
| **Low vegetation** | 9.3% (24 ha) | 10.3% (27 ha) |
| **Non-vegetation** | 17.3% (46 ha) | 17.3% (46 ha) |
| **Overall accuracy** | 88.2% | 89.8% |
| **Cohen's kappa** | 0.822 | 0.846 |

**Top features** (Random Forest importance): NDVI (0.228), CHM_max (0.185), NDRE (0.183), CHM_std (0.169).

The Random Forest classifier improves on the rule-based approach primarily in the low vegetation class, where spectral and structural features help distinguish grass/shrubs from tree canopy edges.

---

## Project Structure

```
Canopy_ArborPro/
├── scripts/                      # Modular Python package
│   ├── __init__.py
│   ├── config.py                 # Study area, CRS, constants
│   ├── sentinel2.py              # Sentinel-2 search, load, spectral indices
│   ├── lidar.py                  # 3DEP tile search, merge, clip, CHM
│   ├── alignment.py              # Align S2 + CHM to common 10 m grid
│   ├── classification.py         # Rule-based + Random Forest classification
│   ├── accuracy.py               # Reference map, sampling, confusion matrix
│   ├── visualization.py          # Plotting helpers
│   └── create_presentation.py    # Generates figures + PowerPoint deck
├── data/                         # Downloaded raster data (gitignored)
│   ├── sentinel2/                #   Cropped S2 GeoTIFF
│   ├── dem/                      #   DTM and DSM from 3DEP
│   └── lidar/                    #   CHM (DSM − DTM)
├── output/                       # Generated presentation + PNGs (gitignored)
├── brain/                        # Project memory and decision log
├── requirements.txt              # Python dependencies
├── context.md                    # Original assignment brief
├── .gitignore
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Internet access (for Sentinel-2 and 3DEP data via Planetary Computer)

### Installation

```bash
git clone https://github.com/tasnim966937/Canopy_ArborPro.git
cd Canopy_ArborPro
pip install -r requirements.txt
```

### Running the Analysis

The pipeline is designed to be run interactively in a Jupyter notebook or as a script. Each module can be imported independently:

```python
from scripts import config, sentinel2, lidar, alignment, classification, accuracy, visualization

# 1. Print study area info
config.print_study_area()

# 2. Download and prepare Sentinel-2 imagery
items = sentinel2.search_scenes()
best = sentinel2.select_best(items)
sentinel2.save_cropped(best)
s2 = sentinel2.load_stacked()
idx = sentinel2.compute_indices(s2)

# 3. Download LiDAR and compute CHM
dtm, dsm, chm = lidar.download_dtm_dsm(name_filter="Fairfax_County_2018")

# 4. Align grids
s2_utm, chm_max_10, chm_std_10, ndvi_a, ndre_a, ndbi_a = alignment.align_grids(s2, chm)

# 5. Classify
rule_map, valid = classification.classify_rules(ndvi_a, chm_max_10)
rf_map, rf, feat_names = classification.classify_rf(
    s2_utm, ndvi_a, ndre_a, ndbi_a, chm_max_10, chm_std_10, rule_map
)

# 6. Accuracy assessment
ref_map = accuracy.build_reference_map(ndvi_a, chm_max_10, valid)
sample_ref, sample_rule, sample_rf = accuracy.sample_reference(ref_map, rule_map, rf_map)
accuracy.report_accuracy(sample_ref, sample_rule, "Rule-Based")
accuracy.report_accuracy(sample_ref, sample_rf, "Random Forest")
```

### Generating the Presentation

```bash
python scripts/create_presentation.py
```

This runs the full pipeline, saves visualizations as PNGs to `output/`, and produces `output/UTC_Assessment_Fairfax_County_VA.pptx`.

---

## Key Technical Decisions

| Decision | Rationale |
|---|---|
| **2018 imagery + 2018 LiDAR** | Temporal matching ensures trees visible in satellite data correspond to the same canopy measured by LiDAR |
| **Planetary Computer STAC API** | Reliable access to both Sentinel-2 and 3DEP COGs with token signing |
| **Expanded bbox for 3DEP search** | STAC catalog footprints are offset by 15–20 km; a ±0.25° buffer ensures tile discovery |
| **Pixel windowing over reprojection** | 3DEP tiles use a compound CRS (NAD83 + NAVD88) that causes rasterio reprojection to fail; direct array slicing via inverse affine transform avoids the issue |
| **Rule-based + ML dual approach** | Demonstrates both transparent, reproducible thresholds and data-driven classification |

---

## Limitations

- The accuracy assessment uses threshold-derived reference labels rather than independent ground truth (e.g., manual photo-interpretation or field surveys), making the reported metrics optimistic.
- The Random Forest is trained on high-confidence pixels from the rule-based map, so it cannot discover classes or patterns outside the rule-based framework.
- 10 m Sentinel-2 resolution limits detection of individual small trees and narrow vegetation strips.
- Single-date imagery cannot account for seasonal or phenological variation.

---

## Dependencies

See [`requirements.txt`](requirements.txt) for the full list. Core libraries:

- **Geospatial**: rasterio, rioxarray, xarray, geopandas, shapely, pyproj
- **Data access**: pystac-client, planetary-computer
- **Machine learning**: scikit-learn
- **Visualization**: matplotlib, contextily
- **Presentation**: python-pptx

---

## License

This project was developed as a GIS Analyst technical assessment.

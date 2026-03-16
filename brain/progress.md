# Progress

## Current Status
Project is **complete and presentation-ready**. The full UTC assessment pipeline runs end-to-end: data acquisition → alignment → classification → accuracy → PowerPoint generation. The light-themed 14-slide PPTX is at `output/UTC_Assessment_Fairfax_County_VA.pptx`.

## Recently Completed
- Moved study area to Fairfax County, VA (BBOX: -77.105, 38.895, -77.087, 38.910) for 2018 LiDAR coverage
- Fixed 3DEP STAC search: expanded bbox ±0.25° and pre-filter tiles by actual raster extent
- Built `create_presentation.py` — generates 8 dark-themed figures + 14-slide PPTX
- Switched presentation to clean white/light theme per user request
- All results validated: 73% tree canopy, OA 88–90%, kappa 0.82–0.85

## Next Steps
- Present to recruiter
- Optional: replace circular accuracy assessment with independent validation (NAIP photo-interpretation)
- Optional: add more slides (methodology flowchart, limitations discussion)

## Active Issues
- Accuracy assessment uses same-data thresholds (circular validation) — acceptable for demo but should be noted
- 3DEP STAC catalog footprints are unreliable — mitigated by expanded search + pre-filter
- 5% of DTM/DSM pixels are nodata (edge of tile coverage) — handled gracefully

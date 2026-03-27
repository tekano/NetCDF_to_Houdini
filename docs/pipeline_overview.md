# Full Pipeline Overview

## Data source

Taiwan atmospheric wind simulation data (WRF/WDAS model output).
Geographic coverage: ~Taiwan + surrounding ocean, ~372 × 322 grid.
Temporal: 143 timesteps, believed to be 30-minute intervals (~71.5 hours).
Vertical: 10 height levels AGL (metres).

## Scripts — what each one does

### Inspection
| Script | Purpose |
|--------|---------|
| `nc_inspect.py` | Full variable audit — run this first on any new .nc file |
| `inspect_netcfd_original.py` | Earlier inspector (xarray-based, slightly different output) |

### Terrain pipeline
```
wind_YYYY-MM-DD.nc
  └─► terrain_extractor.py
        ├─ taiwan_terrain.asc        (ESRI ASCII grid)
        ├─ taiwan_terrain.csv        (lon,lat,elevation point cloud)
        ├─ taiwan_terrain_elevation.npy  (numpy binary — Python only)
        ├─ taiwan_terrain_lat.npy
        ├─ taiwan_terrain_lon.npy
        └─ taiwan_terrain_analysis.png  (matplotlib viz)
              │
              ▼
        asc_to_raw.py  →  taiwan_terrain.raw + taiwan_terrain_heights.npy
              │
              OR
              ▼
        asc_to_tiff.py  →  taiwan_terrain_heightfield.tiff (16-bit)
```

### Houdini terrain import (from TIFF)
```
HeightField File SOP
  └─ taiwan_terrain_heightfield.tiff
HeightField Remap SOP
  └─ Output range: actual min/max elevation from taiwan_houdini_setup.txt
Transform SOP
  └─ Scale to match wind point cloud coordinate space (metres, origin = geo centre)
```

### Wind pipeline (current — CSV)
```
wind_YYYY-MM-DD.nc
  └─► nc_to_csv_points.py
        └─ wind_points_output/
              ├─ wind_points_0000.csv ... wind_points_0142.csv
              ├─ wind_metadata.json
              └─ HOUDINI_IMPORT_GUIDE.txt
```

### Wind pipeline (target — bgeo.sc)
```
wind_YYYY-MM-DD.nc
  └─► nc_to_bgeo.py  [IN DEVELOPMENT]
        └─ wind_bgeo/
              ├─ wind_0000.bgeo.sc ... wind_0142.bgeo.sc
              └─ wind_timeinfo.json  (timestamp → frame mapping)
```

## .npy files — what are they?

NumPy binary array format. Fast, exact float precision.
**Not directly loadable in Houdini** — intermediate Python format only.
Used for passing arrays between Python scripts without CSV overhead.
The `lat.npy` / `lon.npy` files are coordinate grids from `terrain_extractor.py`.

## Coordinate system (all scripts)

| Axis | Geographic meaning | Unit |
|------|--------------------|------|
| X | East (longitude) | metres from centre |
| Z | North (latitude) | metres from centre |
| Y | Height AGL | metres |
| Origin | Geographic centre of dataset | (0, 0, 0) |

## Known issues / TODO

- [ ] 143 CSV files slow to load — migrate to .bgeo.sc sequence
- [ ] Timestamps not embedded in CSV filenames — just sequential indices
- [ ] No temporal interpolation — 30-min steps need remapping to 24fps
- [ ] .npy files not committed (too large / Python-only format)
- [ ] Terrain and wind not yet aligned in same Houdini scene

# netCDF-to-Houdini

**Ingest atmospheric NetCDF (.nc) files into SideFX Houdini as VDB volumes, heightfields, and point clouds.**

Handles real-world wind data with U/V/W velocity components, terrain elevation (HGT), and multi-level / multi-timestep datasets — with outputs suitable for FLIP, Pyro, Vellum, and USD pipelines.

---

## Scripts

| Script | Output | Deps |
|--------|--------|------|
| `nc_inspect.py` | Terminal report of variables, dims, units, ranges | netCDF4, rich (optional) |
| `nc_to_csv_points.py` | Per-timestep CSV point clouds + metadata JSON + Houdini guide | xarray, numpy |
| `nc_to_vdb.py` | OpenVDB velocity volume | pyopenvdb (run via `hython`) |

---

## Quick start

```bash
pip install -r requirements.txt

# 1. Audit your file — find variable names, units, height levels
python scripts/nc_inspect.py data/wind_2007-10-05.nc

# 2. Convert to CSV point clouds (no OpenVDB needed)
# Edit netcdf_file at bottom of script, then:
python scripts/nc_to_csv_points.py

# 3. (Optional) Convert to VDB — run with Houdini's hython for pyopenvdb
hython scripts/nc_to_vdb.py data/wind.nc --out output/wind_vel.vdb
```

---

## Pipeline

```
.nc file
  └─► nc_inspect.py              ← always run first: find your variable names
        │
        ├─► nc_to_csv_points.py  ← CSV point cloud (X/Y/Z + vx/vy/vz + speed + level)
        │     └─► Houdini File SOP → Attribute Wrangle → Volume Rasterize Attributes
        │
        └─► nc_to_vdb.py         ← velocity VDB (requires hython / pyopenvdb)
              └─► Houdini File SOP → FLIP/Pyro Solver velocity input
```

---

## `nc_to_csv_points.py` — what it does

`WindToHoudini` class reads a NetCDF file via `xarray` and exports:

- **`wind_points_NNNN.csv`** per timestep — columns: `x, y, z, vx, vy, vz, speed, level_idx, height_agl`
- **`wind_metadata.json`** — geographic centre, extent in metres, grid size, height levels
- **`HOUDINI_IMPORT_GUIDE.txt`** — generated workflow guide with your actual grid dimensions

Coordinate convention:
- Origin = geographic centre of dataset
- X = East (metres), Y = North (metres), Z = height AGL (metres)
- Terrain height (`HGT` variable) is added to Z if present in the file

---

## Houdini SOP workflow (CSV path)

```
File SOP  (wind_points_$F4.csv)
  │
  ▼
Attribute Wrangle  →  v@v = set(f@vx, f@vy, f@vz);
  │
  ▼
Volume Rasterize Attributes  (attribute: v, voxel size: 100m)
  │
  ▼
Convert VDB  (optional — for simulation inputs)
```

See `docs/houdini_setup.md` for full walkthrough including terrain alignment and voxel size guidance.

---

## VEX

`vex/assemble_velocity.vx` — wrangle snippet to assemble vector attribute from CSV columns and compute normalised height for shading.

---

## Requirements

```
xarray, netCDF4, numpy, scipy, rich (optional — pretty terminal output)
pyopenvdb only needed for nc_to_vdb.py — bundled with Houdini
```

---

## Related

- [wind-viz-vortex](https://github.com/tekano/wind-viz-vortex) — LES wind data driving palm tree Vellum sim (client: Vortex)

---

MIT licence

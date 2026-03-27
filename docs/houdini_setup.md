# Houdini Import Guide

## Overview

The primary conversion path (no OpenVDB dependency) is:

```
.nc file → nc_to_csv_points.py → wind_points_NNNN.csv → Houdini File SOP
```

The VDB path (requires hython or pyopenvdb) is:

```
.nc file → nc_to_vdb.py → wind.vdb → Houdini File SOP → VDB from File
```

---

## Path A — CSV Point Cloud (recommended starting point)

### 1. Run the converter

```bash
python scripts/nc_to_csv_points.py
# Edit the netcdf_file variable at the bottom of the script first
# Output: wind_points_output/wind_points_0000.csv ... and wind_metadata.json
```

### 2. Houdini SOP network

```
File SOP
  └─ filename: wind_points_$F4.csv
  └─ File Type: CSV
     │
     ▼
Attribute Rename SOP
  └─ rename columns → P (position) and v (velocity)
     │
     ▼
Volume Rasterize Attributes SOP
  └─ Attributes: v
  └─ Voxel Size: 100 (metres — adjust to taste)
     │
     ▼
VDB from Polygons  (optional — convert to VDB for simulation)
```

### 3. Attribute mapping after File SOP

The CSV columns map as follows:

| CSV column | Houdini attribute | Type |
|------------|-------------------|------|
| x, y, z | P | vector (position) |
| vx, vy, vz | v | vector (velocity) |
| speed | speed | float |
| level_idx | level | int |
| height_agl | height | float |

Use an **Attribute Wrangle** to assemble the vector attributes:

```vex
// Run over: Points
v@v = set(f@vx, f@vy, f@vz);
```

---

## Path B — VDB Velocity Volume (simulation-ready)

### 1. Run via hython

```bash
# Houdini's bundled Python — has pyopenvdb built in
hython scripts/nc_to_vdb.py data/wind.nc --out output/wind_vel.vdb
```

### 2. Houdini SOP network

```
File SOP  (wind_vel.vdb)
  └─ File Type: VDB
     │
     ▼
VDB Visualize Tree  (check it loaded correctly)
     │
     ▼
FLIP Solver  ─── plug vel VDB into "Velocity Volume" input
```

---

## Coordinate system

All outputs use the same convention:

| Axis | Direction | Unit |
|------|-----------|------|
| X | East | metres |
| Y | North | metres |
| Z | Up / Height AGL | metres |
| Origin | Geographic centre of dataset | (0, 0, 0) |

---

## Terrain alignment

The CSV converter adds terrain height (`HGT` variable if present) to each point's Z.  
Both terrain and wind points share the same geographic origin so they align automatically in Houdini.

---

## Voxel size guidance

| Use case | Suggested voxel size |
|----------|----------------------|
| Quick preview | 500 m |
| Art direction / look dev | 100 m |
| Hero simulation | 50 m or smaller |
| Full domain LES | match original grid spacing |

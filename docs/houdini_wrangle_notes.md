# Houdini Wrangle Notes

## Axis convention — NetCDF → Houdini

NetCDF uses a geographic coordinate system. Houdini is Y-up.
The axis swap is required or your wind data will be on its side.

| NetCDF | Meaning | Houdini axis |
|--------|---------|-------------|
| X (lon) | East–West | X |
| Y (lat) | North–South | **Z** |
| Z (lev) | Height AGL | **Y** |

## CSV import — Table Import SOP (or File SOP)

The CSV from `nc_to_csv_points.py` has 9 columns:

```
x, y, z, vx, vy, vz, speed, level_idx, height_agl
```

After import these come in as float attributes. They are NOT yet
Houdini position (P) or velocity (v) — you need the wrangle below.

## Attribute Wrangle — run over Points

```vex
// Remap geographic coords to Houdini Y-up space
@P = set(f@x, f@z, f@y);       // x=east → X,  z=north → Z,  y=height → Y

// Velocity vector — same axis swap
v@vel = set(f@vx, f@vz, f@vy);

// Alias for solver compatibility (FLIP/Pyro expect 'v')
v@v = v@vel;

// Wind speed scalar — useful for colour ramp / masking
f@speed = length(v@vel);

// Normalised height 0-1 for shading (adjust max to your data)
float max_height = 1000.0;
f@height_norm = clamp(f@height_agl / max_height, 0.0, 1.0);
```

## SOP network after wrangle

```
Table Import / File SOP  (wind_points_$F4.csv)
  │
  ▼
Attribute Wrangle  (code above)
  │
  ├─► Trail SOP  (velocity trail from vel)  ← visual check
  │
  └─► Volume Rasterize Attributes SOP
        Attributes: vel  (or v)
        Voxel Size: 100m  (reduce for hero shots)
          │
          └─► FLIP / Pyro solver velocity input
```

## Time / frame mapping

143 CSV files = 143 timesteps from the source NetCDF.
Map frames to files via the File SOP filename:

```
wind_points_$F4.csv      ← Houdini frame number (1-based, zero-padded to 4 digits)
```

Note: Houdini frames start at 1, CSV files start at 0000.
Either offset in the File SOP expression:

```
wind_points_`padzero(4, $F - 1)`.csv
```

Or use a Python expression node to drive the file path from
actual timestamps once the converter embeds them (see issue #1).

## Known issues / TODO

- [ ] CSV files currently numbered by index — actual timestamps not embedded
- [ ] Need to map NetCDF time units ("hours since YYYY-MM-DD HH:MM") to Houdini frames
- [ ] Consider writing a single multi-frame .bgeo.sc or .vdb sequence instead of per-frame CSV

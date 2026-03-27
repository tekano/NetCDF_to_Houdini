# Data Notes — wind_2007-10-05.nc

## Confirmed structure

- Format: NETCDF3_64BIT_OFFSET
- Case: `vref` (WRF reference run)
- Coverage: SW Taiwan ~22°N, 120.6–121°E (~40×42km patch, Tainan/Kaohsiung area)

## Dimensions

| Dim  | Size | Meaning |
|------|------|---------|
| time | 48   | 30-min steps = 24 hours |
| lev  | 9    | Height levels AGL (metres) |
| lat  | 372  | ~42 km N-S |
| lon  | 322  | ~40 km E-W |

## Variables — full set

| Var | Shape | Units | Range | Houdini use |
|-----|-------|-------|-------|-------------|
| U  | (48,9,372,322) | m/s | -7.85 → 30.95 | v@v.x (east) |
| V  | (48,9,372,322) | m/s | -32.54 → 14.01 | v@v.z (north) |
| W  | (48,9,372,322) | m/s | -11.96 → 14.29 | v@v.y (vertical) |
| T  | (48,9,372,322) | °C  | 13.32 → 36.47 | temperature attr — Pyro buoyancy / colour |
| M  | (48,9,372,322) | m/s | 0.0 → 38.78 | speed attr (pre-computed, faster than sqrt) |
| SD | (48,9,372,322) | m/s | 0.365 → 4.806 | wind_shear attr |
| HGT | (372,322) | m  | -2.4 → 1440 | terrain elevation (static) |
| lev | (9,) | m | 28 → 330 | height AGL levels |

## Notes on variables

**W (vertical):** ±12 m/s is significant — strong orographic updrafts over
mountain terrain. Critical for realistic particle/smoke simulation.

**HGT units bug:** Inspector reports `m/s` but data is clearly metres elevation
(range matches Taiwan topography). Treat as metres. Ocean areas go slightly
negative — clamped to 0 in conversion scripts.

**M (magnitude):** Pre-computed wind speed. Used directly instead of
recomputing `sqrt(U²+V²+W²)` for performance.

## Velocity convention in Houdini

```vex
// v@v is written directly — NO axis swap needed in bgeo path
// X = East  (U)
// Y = Up    (W — vertical wind)
// Z = North (V)
v@v = set(U, W, V);
```

## Time axis

- Units: `minutes since 2007-10-05`
- Range: 0 – 1410 minutes (48 steps × 30 min)
- Coverage: 2007-10-05 00:00 → 23:30

## Playback mapping

| --hours-per-second | Total frames | Duration @ 24fps |
|-------------------|-------------|-----------------|
| 4.0 | 144 | 6s  — quick preview |
| 2.0 | 288 | 12s — recommended start |
| 1.0 | 576 | 24s — detailed |
| 0.5 | 1152 | 48s — slow motion |

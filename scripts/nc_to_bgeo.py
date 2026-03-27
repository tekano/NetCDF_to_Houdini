#!/usr/bin/env python3
"""
nc_to_bgeo.py — Convert NetCDF wind data to Houdini .bgeo.sc point sequence
                 with real timestamps, full U/V/W velocity, temperature,
                 and frame mapping for smooth 24fps playback via Timeblend SOP.

CONFIRMED DATA STRUCTURE (wind_2007-10-05.nc):
  U  (48, 9, 372, 322)  East-west wind     m/s   -7.85  to  30.95
  V  (48, 9, 372, 322)  North-south wind   m/s  -32.54  to  14.01
  W  (48, 9, 372, 322)  Vertical wind      m/s  -11.96  to  14.29
  T  (48, 9, 372, 322)  Temperature        °C    13.32  to  36.47
  M  (48, 9, 372, 322)  Wind magnitude     m/s    0.0   to  38.78
  SD (48, 9, 372, 322)  Wind shear/stddev  m/s    0.365 to   4.806
  HGT (372, 322)        Terrain elevation  m     -2.4   to 1440
  lev (9,)              Height AGL         m     28     to  330
  time (48,)            minutes since 2007-10-05, interval=30min

Houdini velocity convention: v@v = (U, W, V)
  X = East  (U)
  Y = Up    (W — vertical wind)
  Z = North (V)

USAGE:
  # .bgeo.sc output (run via hython):
  hython nc_to_bgeo.py wind_2007-10-05.nc --out wind_bgeo --hours-per-second 2.0

  # CSV fallback (plain Python, no hython):
  python nc_to_bgeo.py wind_2007-10-05.nc --out wind_csv --hours-per-second 2.0

OPTIONS:
  --out <dir>               Output directory          (default: wind_bgeo_output)
  --fps <n>                 Playback fps              (default: 24)
  --hours-per-second <n>    Real hours per playback second
                              1.0 = 24 frames/hour   576 total frames  24s
                              2.0 = 48 frames/hour   288 total frames  12s  ← recommended start
                              4.0 = 96 frames/hour   144 total frames   6s
  --start-frame <n>         First Houdini frame       (default: 1)
  --format bgeo|csv         Output format             (default: auto-detect)
  --timesteps <n>           Limit to first N steps    (default: all 48)
  --no-temperature          Skip T attribute          (smaller files)
  --no-shear                Skip SD attribute         (smaller files)
"""

import argparse
import json
import sys
import numpy as np
import xarray as xr
from pathlib import Path
from datetime import datetime, timedelta

try:
    import hou
    HAS_HOU = True
except ImportError:
    HAS_HOU = False


# ── Time decoding ─────────────────────────────────────────────────────────────

def decode_time_axis(ds):
    time_var  = ds['time']
    time_vals = time_var.values.astype(float)
    units     = getattr(time_var, 'units', '')

    origin_dt  = None
    multiplier = 1.0  # minutes

    for prefix, mins in [('minutes since', 1.0),
                          ('hours since',   60.0),
                          ('seconds since', 1.0/60.0)]:
        if units.lower().startswith(prefix):
            multiplier = mins
            date_str   = units[len(prefix):].strip().split()[0]
            for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S'):
                try:
                    origin_dt = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            break

    if origin_dt is None:
        print(f"[warn] Could not parse time units: '{units}' — using 2007-10-05 + 30min intervals")
        origin_dt  = datetime(2007, 10, 5)
        multiplier = 30.0

    datetimes = [origin_dt + timedelta(minutes=float(v) * multiplier)
                 for v in time_vals]

    interval  = ((datetimes[1] - datetimes[0]).total_seconds() / 60.0
                 if len(datetimes) > 1 else 30.0)

    print(f"  Time origin : {origin_dt.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Steps       : {len(datetimes)}  ×  {interval:.0f} min  "
          f"= {interval*(len(datetimes)-1)/60:.1f} hours")

    return datetimes, interval, units


def build_frame_map(datetimes, interval_min, fps, hours_per_sec, start_frame):
    frames_per_min = (fps * hours_per_sec) / 60.0
    frame_map = []
    for i, dt in enumerate(datetimes):
        mins_elapsed = i * interval_min
        hframe       = start_frame + mins_elapsed * frames_per_min
        frame_map.append({
            'timestep_index'  : i,
            'datetime'        : dt.strftime('%Y-%m-%d %H:%M:%S'),
            'minutes_elapsed' : float(mins_elapsed),
            'houdini_frame'   : float(hframe),
            'houdini_frame_int': int(round(hframe))
        })

    total = frame_map[-1]['houdini_frame_int'] - start_frame + 1
    print(f"  Playback    : {hours_per_sec}h/s  →  {total} frames "
          f"@ {fps}fps  =  {total/fps:.1f}s")
    return frame_map


# ── Data extraction ───────────────────────────────────────────────────────────

def extract_timestep(ds, t_idx, lat_c, lon_c,
                     include_temp=True, include_shear=True):
    """
    Returns flat numpy arrays for every point across all 9 levels.
    Houdini axis mapping applied here:
      P.x = x (East,  metres from centre)
      P.y = y (Up,    terrain + height AGL)
      P.z = z (North, metres from centre)
      v@v = (U, W, V)   East / Vertical / North
    """
    lat = ds['lat'].values          # (372,)
    lon = ds['lon'].values          # (322,)
    lev = ds['lev'].values          # (9,)  metres AGL
    hgt = np.maximum(ds['HGT'].values, 0.0)   # (372,322) clamp ocean negatives

    # Wind — (lev, lat, lon)
    U = ds['U'].isel(time=t_idx).values
    V = ds['V'].isel(time=t_idx).values
    W = ds['W'].isel(time=t_idx).values
    M = ds['M'].isel(time=t_idx).values   # pre-computed magnitude — faster than sqrt

    T  = ds['T'].isel(time=t_idx).values  if (include_temp  and 'T'  in ds) else None
    SD = ds['SD'].isel(time=t_idx).values if (include_shear and 'SD' in ds) else None

    # Coordinate grids (lat, lon)
    lon_g, lat_g = np.meshgrid(lon, lat)
    x_g = ((lon_g - lon_c) * 111000.0
            * np.cos(np.radians(lat_c))).astype(np.float32)   # East metres
    z_g = ((lat_g - lat_c) * 111000.0).astype(np.float32)     # North metres

    n_lev = len(lev)
    n_pts = lat.size * lon.size
    n_tot = n_lev * n_pts

    # Pre-allocate
    out = {
        'x':    np.empty(n_tot, np.float32),
        'y':    np.empty(n_tot, np.float32),   # height (Houdini Y-up)
        'z':    np.empty(n_tot, np.float32),
        'vx':   np.empty(n_tot, np.float32),   # U  east
        'vy':   np.empty(n_tot, np.float32),   # W  vertical
        'vz':   np.empty(n_tot, np.float32),   # V  north
        'speed':np.empty(n_tot, np.float32),
        'level_idx': np.empty(n_tot, np.int32),
        'height_agl':np.empty(n_tot, np.float32),
    }
    if T  is not None: out['temperature'] = np.empty(n_tot, np.float32)
    if SD is not None: out['wind_shear']  = np.empty(n_tot, np.float32)

    x_flat = x_g.flatten()
    z_flat = z_g.flatten()
    h_flat = hgt.flatten()

    for li, hagl in enumerate(lev):
        s = li * n_pts
        e = s + n_pts

        abs_h = (h_flat + hagl).astype(np.float32)

        out['x'][s:e]    = x_flat
        out['y'][s:e]    = abs_h
        out['z'][s:e]    = z_flat
        out['vx'][s:e]   = U[li].flatten()          # East  → X
        out['vy'][s:e]   = W[li].flatten()          # Up    → Y
        out['vz'][s:e]   = V[li].flatten()          # North → Z
        out['speed'][s:e]= M[li].flatten()
        out['level_idx'][s:e]  = li
        out['height_agl'][s:e] = float(hagl)
        if T  is not None: out['temperature'][s:e] = T[li].flatten()
        if SD is not None: out['wind_shear'][s:e]  = SD[li].flatten()

    return out


# ── Writers ───────────────────────────────────────────────────────────────────

def write_bgeo(out_path, d, meta):
    geo = hou.Geometry()
    n   = len(d['x'])
    pts = geo.createPoints(n)

    v_attr    = geo.addAttrib(hou.attribType.Point, "v",          hou.Vector3())
    sp_attr   = geo.addAttrib(hou.attribType.Point, "speed",      0.0)
    lev_attr  = geo.addAttrib(hou.attribType.Point, "level_idx",  0)
    hagl_attr = geo.addAttrib(hou.attribType.Point, "height_agl", 0.0)

    has_T  = 'temperature' in d
    has_SD = 'wind_shear'  in d
    if has_T:  t_attr  = geo.addAttrib(hou.attribType.Point, "temperature", 0.0)
    if has_SD: sd_attr = geo.addAttrib(hou.attribType.Point, "wind_shear",  0.0)

    # Detail (global) metadata
    for k, v in meta.items():
        a = geo.addAttrib(hou.attribType.Global, k, str(v))
        geo.setGlobalAttribValue(k, str(v))

    for i, pt in enumerate(pts):
        pt.setPosition(hou.Vector3(float(d['x'][i]),
                                   float(d['y'][i]),
                                   float(d['z'][i])))
        pt.setAttribValue(v_attr,    hou.Vector3(float(d['vx'][i]),
                                                  float(d['vy'][i]),
                                                  float(d['vz'][i])))
        pt.setAttribValue(sp_attr,   float(d['speed'][i]))
        pt.setAttribValue(lev_attr,  int(d['level_idx'][i]))
        pt.setAttribValue(hagl_attr, float(d['height_agl'][i]))
        if has_T:  pt.setAttribValue(t_attr,  float(d['temperature'][i]))
        if has_SD: pt.setAttribValue(sd_attr, float(d['wind_shear'][i]))

    geo.saveToFile(str(out_path))


def write_csv(out_path, d):
    cols = ['x','y','z','vx','vy','vz','speed','level_idx','height_agl']
    if 'temperature' in d: cols.append('temperature')
    if 'wind_shear'  in d: cols.append('wind_shear')

    with open(out_path, 'w') as f:
        f.write(','.join(cols) + '\n')
        for i in range(len(d['x'])):
            row = [f"{d[c][i]:.4f}" if c not in ('level_idx',)
                   else str(d[c][i]) for c in cols]
            f.write(','.join(row) + '\n')


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--out",              default="wind_bgeo_output")
    parser.add_argument("--fps",              type=float, default=24.0)
    parser.add_argument("--hours-per-second", type=float, default=2.0,
                        help="Real hours per playback second (default 2.0 → 12s total)")
    parser.add_argument("--start-frame",      type=int,   default=1)
    parser.add_argument("--format",           choices=["bgeo","csv"], default=None)
    parser.add_argument("--timesteps",        type=int,   default=None)
    parser.add_argument("--no-temperature",   action="store_true")
    parser.add_argument("--no-shear",         action="store_true")
    args = parser.parse_args()

    # Format detection
    if args.format is None:
        args.format = "bgeo" if HAS_HOU else "csv"
    if args.format == "bgeo" and not HAS_HOU:
        print("[warn] hou not found — falling back to CSV. Run via hython for .bgeo.sc")
        args.format = "csv"

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = "bgeo.sc" if args.format == "bgeo" else "csv"

    print(f"\n{'='*60}")
    print(f"  NetCDF → Houdini  ({args.format})")
    print(f"  Input  : {args.file}")
    print(f"  Output : {out_dir}")
    print(f"{'='*60}\n")

    ds = xr.open_dataset(args.file)

    datetimes, interval_min, time_units = decode_time_axis(ds)
    n_steps   = args.timesteps or len(datetimes)
    datetimes = datetimes[:n_steps]
    frame_map = build_frame_map(datetimes, interval_min,
                                args.fps, args.hours_per_second,
                                args.start_frame)

    lat = ds['lat'].values;  lon = ds['lon'].values
    lev = ds['lev'].values
    lat_c = float((lat.min() + lat.max()) / 2)
    lon_c = float((lon.min() + lon.max()) / 2)
    ext_x = float((lon.max()-lon.min()) * 111000 * np.cos(np.radians(lat_c)))
    ext_z = float((lat.max()-lat.min()) * 111000)

    print(f"\n  Grid        : {len(lat)} × {len(lon)}")
    print(f"  Centre      : {lat_c:.4f}°N  {lon_c:.4f}°E")
    print(f"  Extent      : {ext_x/1000:.1f} km EW  ×  {ext_z/1000:.1f} km NS")
    print(f"  Levels      : {list(lev.astype(int))} m AGL")
    print(f"  Points/frame: {len(lat)*len(lon)*len(lev):,}")
    print(f"  Attributes  : P  v(UWV)  speed  level_idx  height_agl"
          + ("  temperature" if not args.no_temperature else "")
          + ("  wind_shear"  if not args.no_shear else ""))
    print()

    for entry in frame_map:
        t   = entry['timestep_index']
        dt  = entry['datetime']
        hf  = entry['houdini_frame_int']
        print(f"  [{t+1:02d}/{n_steps}]  {dt}  →  frame {hf:4d}", end="  ", flush=True)

        d = extract_timestep(ds, t, lat_c, lon_c,
                             include_temp  = not args.no_temperature,
                             include_shear = not args.no_shear)

        out_file = out_dir / f"wind_{t:04d}.{ext}"

        if args.format == "bgeo":
            meta = {'datetime': dt, 'timestep_index': t,
                    'houdini_frame': hf, 'source': str(args.file)}
            write_bgeo(out_file, d, meta)
        else:
            write_csv(out_file, d)

        print(f"✓")

    # ── Timeinfo JSON ─────────────────────────────────────────────────────────
    timeinfo = {
        'source_file'        : str(args.file),
        'format'             : args.format,
        'fps'                : args.fps,
        'hours_per_second'   : args.hours_per_second,
        'start_frame'        : args.start_frame,
        'interval_minutes'   : interval_min,
        'time_units_original': time_units,
        'geographic_centre'  : {'lat': lat_c, 'lon': lon_c},
        'extent_km'          : {'ew': round(ext_x/1000,2), 'ns': round(ext_z/1000,2)},
        'levels_m_agl'       : [int(v) for v in lev],
        'total_timesteps'    : n_steps,
        'frame_map'          : frame_map,
        'houdini_notes'      : {
            'file_sop_pattern' : f"wind_$F4.{ext}",
            'frame_range'      : f"{frame_map[0]['houdini_frame_int']} - {frame_map[-1]['houdini_frame_int']}",
            'timeblend_sop'    : "Add Timeblend SOP directly after File SOP for smooth interpolation",
            'velocity_attr'    : "v@v — already in Houdini space: X=east(U), Y=up(W), Z=north(V). No axis swap needed.",
            'volume_rasterize' : "Volume Rasterize Attributes — attributes: v  speed  temperature",
            'voxel_size_start' : "100m for preview, 50m for hero",
            'temperature_note' : "T attribute in Celsius — use for Pyro buoyancy or colour ramp",
        }
    }

    tj = out_dir / "wind_timeinfo.json"
    with open(tj, 'w') as f:
        json.dump(timeinfo, f, indent=2)

    fr = frame_map
    print(f"\n{'='*60}")
    print(f"  Done!  {n_steps} files  →  {out_dir}")
    print(f"  Frames : {fr[0]['houdini_frame_int']} – {fr[-1]['houdini_frame_int']}")
    print(f"  File SOP pattern: wind_$F4.{ext}")
    print(f"  Timeinfo: {tj}")
    print(f"\n  Houdini SOP chain:")
    print(f"    File SOP (wind_$F4.{ext})")
    print(f"    └─ Timeblend SOP          ← smooth interpolation between 30min steps")
    print(f"    └─ Volume Rasterize Attrs ← attributes: v  speed  temperature")
    print(f"       voxel size: 100m preview / 50m hero")
    print(f"{'='*60}\n")

    ds.close()


if __name__ == "__main__":
    main()

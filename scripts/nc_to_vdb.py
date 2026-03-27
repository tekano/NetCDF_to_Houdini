#!/usr/bin/env python3
"""
nc_to_vdb.py  —  Convert NetCDF wind U/V/W to an OpenVDB velocity volume.

REQUIRES pyopenvdb. Easiest way: run with Houdini's bundled hython.
    hython scripts/nc_to_vdb.py data/wind.nc --out output/wind.vdb

If pyopenvdb is not available, use nc_to_csv_points.py instead (no deps beyond xarray/numpy).
"""

import argparse
import numpy as np
import xarray as xr
from pathlib import Path

try:
    import pyopenvdb as vdb
except ImportError:
    raise ImportError(
        "pyopenvdb not found.\n"
        "Run with Houdini's hython:  hython nc_to_vdb.py ...\n"
        "Or use nc_to_csv_points.py (no OpenVDB dependency)."
    )


def nc_to_velocity_vdb(nc_path: str, u_var="U", v_var="V", w_var="W",
                       time_idx=0, level_idx=0, voxel_size=100.0, out_path=None):
    ds = xr.open_dataset(nc_path)
    print(f"Variables: {list(ds.data_vars)}")

    u = ds[u_var].isel(time=time_idx).values
    v = ds[v_var].isel(time=time_idx).values
    w = ds[w_var].isel(time=time_idx).values if w_var in ds else np.zeros_like(u)

    # Handle 3D (lev, lat, lon) or 2D (lat, lon)
    if u.ndim == 3:
        u, v, w = u[level_idx], v[level_idx], (w[level_idx] if w.ndim == 3 else w)

    ny, nx = u.shape

    vel_grid = vdb.Vec3SGrid()
    vel_grid.name = "vel"
    vel_grid.voxelSize = voxel_size

    accessor = vel_grid.getAccessor()
    for j in range(ny):
        for i in range(nx):
            accessor.setValueOn((i, j, 0), (float(u[j, i]), float(v[j, i]), float(w[j, i])))

    out = out_path or Path(nc_path).stem + "_vel.vdb"
    vdb.write(out, grids=[vel_grid])
    print(f"Written: {out}")
    ds.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--u", default="U")
    parser.add_argument("--v", default="V")
    parser.add_argument("--w", default="W")
    parser.add_argument("--time", type=int, default=0)
    parser.add_argument("--level", type=int, default=0)
    parser.add_argument("--voxel", type=float, default=100.0)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    nc_to_velocity_vdb(args.file, args.u, args.v, args.w, args.time, args.level, args.voxel, args.out)

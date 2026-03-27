#!/usr/bin/env python3
"""
nc_inspect.py  —  Audit a NetCDF file before conversion.
Run this FIRST to discover variable names, units, shape, height levels, time steps.

Usage:
    python scripts/nc_inspect.py data/wind.nc
    python scripts/nc_inspect.py data/wind.nc --var U
"""

import argparse
import numpy as np
import netCDF4 as nc

try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
    USE_RICH = True
except ImportError:
    USE_RICH = False


def inspect(path: str, deep_var: str = None):
    ds = nc.Dataset(path, "r")
    print(f"\n{'='*60}")
    print(f"  FILE   : {path}")
    print(f"  FORMAT : {ds.file_format}")
    print(f"{'='*60}")

    print("\nGLOBAL ATTRIBUTES")
    for attr in ds.ncattrs():
        print(f"  {attr}: {getattr(ds, attr)}")

    print("\nDIMENSIONS")
    for name, dim in ds.dimensions.items():
        print(f"  {name}: {len(dim)}" + (" (unlimited)" if dim.isunlimited() else ""))

    rows = []
    for name, var in ds.variables.items():
        units = getattr(var, "units", "—")
        lname = getattr(var, "long_name", "—")
        dtype = str(var.dtype)
        shape = str(var.shape)
        vmin = vmax = "—"
        try:
            data = var[:]
            vmin = f"{float(np.nanmin(data)):.4g}"
            vmax = f"{float(np.nanmax(data)):.4g}"
        except Exception:
            pass
        rows.append((name, lname, units, dtype, shape, vmin, vmax))

    print("\nVARIABLES")
    hdr = f"{'name':<20} {'long_name':<28} {'units':<12} {'dtype':<8} {'shape':<18} {'min':<12} {'max'}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r[0]:<20} {r[1]:<28} {r[2]:<12} {r[3]:<8} {r[4]:<18} {r[5]:<12} {r[6]}")

    if deep_var:
        if deep_var not in ds.variables:
            print(f"\n[!] Variable '{deep_var}' not found.")
        else:
            v = ds.variables[deep_var]
            print(f"\nDEEP DIVE: {deep_var}")
            for attr in v.ncattrs():
                print(f"  {attr}: {getattr(v, attr)}")
            data = v[:]
            print(f"  shape : {data.shape}")
            print(f"  min   : {np.nanmin(data)}")
            print(f"  max   : {np.nanmax(data)}")
            print(f"  mean  : {np.nanmean(data)}")

    ds.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--var", default=None)
    args = parser.parse_args()
    inspect(args.file, args.var)

#!/usr/bin/env python3
"""
NetCDF Data Inspector - Examine your WDAS atmospheric data structure
"""

import xarray as xr
import numpy as np

def inspect_netcdf(filepath):
    """Inspect a NetCDF file structure and contents"""
    
    print(f"=== Inspecting: {filepath} ===\n")
    
    # Open the dataset
    ds = xr.open_dataset(filepath)
    
    # Basic info
    print("DIMENSIONS:")
    for dim, size in ds.dims.items():
        print(f"  {dim}: {size}")
    
    print("\nCOORDINATES:")
    for coord in ds.coords:
        coord_data = ds.coords[coord]
        print(f"  {coord}: {coord_data.dtype} - {coord_data.shape}")
        if coord_data.size < 20:  # Print small coordinate arrays
            print(f"    Values: {coord_data.values}")
        else:
            try:
                print(f"    Range: {coord_data.min().values:.3f} to {coord_data.max().values:.3f}")
            except:
                print(f"    Range: {coord_data.min().values} to {coord_data.max().values}")
    
    print("\nDATA VARIABLES:")
    for var in ds.data_vars:
        var_data = ds.data_vars[var]
        print(f"  {var}: {var_data.dtype} - {var_data.shape}")
        print(f"    Attributes: {dict(var_data.attrs)}")
        if hasattr(var_data, 'units'):
            print(f"    Units: {var_data.units}")
        print(f"    Value range: {var_data.min().values:.3f} to {var_data.max().values:.3f}")
        print()
    
    print("GLOBAL ATTRIBUTES:")
    for attr, value in ds.attrs.items():
        print(f"  {attr}: {value}")
    
    # Check for common atmospheric variables
    common_vars = ['u', 'v', 'w', 'U', 'V', 'W', 'lat', 'lon', 'latitude', 'longitude', 'level', 'height', 'time']
    found_vars = [var for var in common_vars if var in ds.variables]
    
    print(f"\nCOMMON ATMOSPHERIC VARIABLES FOUND: {found_vars}")
    
    return ds

def analyze_wind_data(ds):
    """Analyze wind vector components"""
    
    # Look for U/V wind components
    u_vars = [var for var in ds.variables if 'u' in var.lower() or 'U' in var]
    v_vars = [var for var in ds.variables if 'v' in var.lower() or 'V' in var]
    
    print(f"\nPOSSIBLE U-COMPONENTS: {u_vars}")
    print(f"POSSIBLE V-COMPONENTS: {v_vars}")
    
    # If we find U/V components, analyze them
    if u_vars and v_vars:
        u_var = u_vars[0]  # Take first match
        v_var = v_vars[0]
        
        u_data = ds[u_var]
        v_data = ds[v_var]
        
        print(f"\nWIND ANALYSIS:")
        print(f"U-component ({u_var}): shape {u_data.shape}")
        print(f"V-component ({v_var}): shape {v_data.shape}")
        
        # Calculate wind speed
        if u_data.shape == v_data.shape:
            wind_speed = np.sqrt(u_data**2 + v_data**2)
            print(f"Wind speed range: {wind_speed.min().values:.3f} to {wind_speed.max().values:.3f}")

if __name__ == "__main__":
    # Replace with your actual file path
    filepath = "wind_2007-10-05.nc"  # CHANGE THIS
    
    try:
        ds = inspect_netcdf(filepath)
        analyze_wind_data(ds)
        ds.close()
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        print("Please update the filepath variable with your actual .nc file path")
    except Exception as e:
        print(f"Error reading file: {e}")
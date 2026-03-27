#!/usr/bin/env python3
"""
Simple ASC to TIFF converter - minimal dependencies
"""

import numpy as np

def convert_asc_simple():
    print("Converting ASC to formats Houdini can read...")
    
    # Read the ASC file manually
    with open("taiwan_terrain.asc", 'r') as f:
        # Skip header (6 lines)
        ncols = int(f.readline().split()[1])
        nrows = int(f.readline().split()[1])
        xllcorner = float(f.readline().split()[1])
        yllcorner = float(f.readline().split()[1])
        cellsize = float(f.readline().split()[1])
        nodata_value = float(f.readline().split()[1])
        
        print(f"Grid: {ncols} x {nrows}")
        print(f"Cell size: {cellsize}")
        
        # Read all elevation data
        all_data = []
        for line in f:
            values = [float(x) for x in line.split()]
            all_data.extend(values)
    
    # Convert to numpy array
    data = np.array(all_data).reshape(nrows, ncols)
    
    print(f"Elevation range: {data.min():.1f}m to {data.max():.1f}m")
    
    # Save as numpy files for Houdini
    np.save("taiwan_terrain_heights.npy", data.astype(np.float32))
    
    # Save as raw binary (Houdini can read this)
    data.astype(np.float32).tofile("taiwan_terrain.raw")
    
    # Create info file
    with open("taiwan_terrain_info.txt", 'w') as f:
        f.write(f"Dimensions: {ncols} x {nrows}\n")
        f.write(f"Min elevation: {data.min():.3f}m\n")
        f.write(f"Max elevation: {data.max():.3f}m\n")
        f.write(f"Corner: {xllcorner}, {yllcorner}\n")
        f.write(f"Cell size: {cellsize}\n")
        f.write(f"\nFor Houdini:\n")
        f.write(f"1. Use File SOP to read taiwan_terrain.raw\n")
        f.write(f"2. Set Type to 'Raw Binary'\n")
        f.write(f"3. Set Data Type to 'Float 32-bit'\n")
        f.write(f"4. Set Dimensions to {ncols} x {nrows}\n")
    
    print("\nFiles created:")
    print("- taiwan_terrain.raw (for Houdini File SOP)")
    print("- taiwan_terrain_heights.npy (numpy format)")
    print("- taiwan_terrain_info.txt (import instructions)")
    print("\nReady for Houdini!")

if __name__ == "__main__":
    convert_asc_simple()

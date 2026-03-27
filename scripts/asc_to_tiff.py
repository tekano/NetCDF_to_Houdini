#!/usr/bin/env python3
"""
Convert ASC to TIFF using OpenCV (more reliable for Houdini)
"""

import numpy as np
import cv2

def asc_to_tiff():
    print("Converting ASC to TIFF using OpenCV...")
    
    # Read the ASC file
    with open("taiwan_terrain.asc", 'r') as f:
        # Parse header
        ncols = int(f.readline().split()[1])
        nrows = int(f.readline().split()[1])
        xllcorner = float(f.readline().split()[1])
        yllcorner = float(f.readline().split()[1])
        cellsize = float(f.readline().split()[1])
        nodata_value = float(f.readline().split()[1])
        
        print(f"Grid: {ncols} x {nrows}")
        print(f"Bounds: {xllcorner} to {xllcorner + ncols*cellsize} lon")
        print(f"        {yllcorner} to {yllcorner + nrows*cellsize} lat")
        
        # Read elevation data
        all_data = []
        for line in f:
            values = [float(x) for x in line.split()]
            all_data.extend(values)
    
    # Convert to numpy array
    data = np.array(all_data).reshape(nrows, ncols)
    print(f"Elevation range: {data.min():.1f}m to {data.max():.1f}m")
    
    # Convert to 16-bit integer (common for heightmaps)
    min_elev = data.min()
    max_elev = data.max()
    
    # Scale to 16-bit range
    if max_elev > min_elev:
        scaled_data = ((data - min_elev) / (max_elev - min_elev) * 65535).astype(np.uint16)
    else:
        scaled_data = np.zeros_like(data, dtype=np.uint16)
    
    # Save as TIFF
    success = cv2.imwrite("taiwan_terrain_heightfield.tiff", scaled_data)
    
    if success:
        print("✓ TIFF file created: taiwan_terrain_heightfield.tiff")
    else:
        print("✗ Failed to create TIFF file")
        return
    
    # Create scaling info for Houdini
    with open("taiwan_houdini_setup.txt", 'w') as f:
        f.write("=== HOUDINI IMPORT INSTRUCTIONS ===\n\n")
        f.write("1. HeightField File SOP:\n")
        f.write(f"   - File: taiwan_terrain_heightfield.tiff\n")
        f.write(f"   - Size: {ncols} x {nrows}\n\n")
        f.write("2. HeightField Remap SOP (to restore elevation values):\n")
        f.write(f"   - Input Range: 0 to 1\n")
        f.write(f"   - Output Range: {min_elev:.3f} to {max_elev:.3f}\n\n")
        f.write("3. Transform to match geographic coordinates:\n")
        f.write(f"   - Center: {xllcorner + ncols*cellsize/2:.6f} lon, {yllcorner + nrows*cellsize/2:.6f} lat\n")
        f.write(f"   - Scale: {ncols*cellsize*111000:.0f}m x {nrows*cellsize*111000:.0f}m\n\n")
        f.write("4. Geographic info:\n")
        f.write(f"   - Longitude: {xllcorner:.6f} to {xllcorner + ncols*cellsize:.6f}\n")
        f.write(f"   - Latitude: {yllcorner:.6f} to {yllcorner + nrows*cellsize:.6f}\n")
    
    print("✓ Setup instructions: taiwan_houdini_setup.txt")
    print("\nNext: Import the TIFF into Houdini HeightField File SOP!")

if __name__ == "__main__":
    try:
        asc_to_tiff()
    except ImportError:
        print("OpenCV not found. Installing...")
        print("Run: pip install opencv-python")
        print("Then try again.")
    except Exception as e:
        print(f"Error: {e}")
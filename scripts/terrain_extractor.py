#!/usr/bin/env python3
"""
Extract terrain data from NetCDF and prepare for Houdini
"""

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

def extract_terrain(netcdf_path, output_prefix="taiwan_terrain"):
    """Extract terrain data and save in various formats"""
    
    print(f"Loading NetCDF file: {netcdf_path}")
    ds = xr.open_dataset(netcdf_path)
    
    # Extract terrain data
    terrain = ds['HGT'].values  # Shape should be (372, 322)
    lat = ds['lat'].values
    lon = ds['lon'].values
    
    print(f"Terrain shape: {terrain.shape}")
    print(f"Elevation range: {terrain.min():.1f}m to {terrain.max():.1f}m")
    print(f"Lat range: {lat.min():.3f}° to {lat.max():.3f}°N")
    print(f"Lon range: {lon.min():.3f}° to {lon.max():.3f}°E")
    
    # Calculate geographic extents
    lat_center = (lat.min() + lat.max()) / 2
    lon_center = (lon.min() + lon.max()) / 2
    lat_span = lat.max() - lat.min()
    lon_span = lon.max() - lon.min()
    
    print(f"Center: {lat_center:.3f}°N, {lon_center:.3f}°E")
    print(f"Coverage: {lat_span:.3f}° × {lon_span:.3f}° (~{lat_span*111:.1f}km × {lon_span*85:.1f}km)")
    
    # Create visualization
    plt.figure(figsize=(12, 10))
    
    # Main terrain plot
    plt.subplot(2, 2, 1)
    plt.imshow(terrain, extent=[lon.min(), lon.max(), lat.min(), lat.max()], 
               cmap='terrain', origin='lower')
    plt.colorbar(label='Elevation (m)')
    plt.title('Taiwan Terrain Data')
    plt.xlabel('Longitude (°E)')
    plt.ylabel('Latitude (°N)')
    
    # Elevation histogram
    plt.subplot(2, 2, 2)
    plt.hist(terrain.flatten(), bins=50, alpha=0.7)
    plt.xlabel('Elevation (m)')
    plt.ylabel('Frequency')
    plt.title('Elevation Distribution')
    
    # 3D perspective (contours)
    plt.subplot(2, 2, 3)
    contour_levels = np.linspace(terrain.min(), terrain.max(), 20)
    plt.contour(lon, lat, terrain, levels=contour_levels)
    plt.xlabel('Longitude (°E)')
    plt.ylabel('Latitude (°N)')
    plt.title('Topographic Contours')
    
    # Cross-section
    plt.subplot(2, 2, 4)
    mid_row = terrain.shape[0] // 2
    plt.plot(lon, terrain[mid_row, :])
    plt.xlabel('Longitude (°E)')
    plt.ylabel('Elevation (m)')
    plt.title('East-West Cross-Section')
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_analysis.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    # Save terrain data in different formats for Houdini
    
    # 1. Raw numpy array
    np.save(f'{output_prefix}_elevation.npy', terrain)
    np.save(f'{output_prefix}_lat.npy', lat)
    np.save(f'{output_prefix}_lon.npy', lon)
    
    # 2. ASCII grid format (readable by many GIS tools and Houdini)
    save_ascii_grid(terrain, lat, lon, f'{output_prefix}.asc')
    
    # 3. Simple CSV for testing
    save_terrain_csv(terrain, lat, lon, f'{output_prefix}.csv')
    
    print(f"\nFiles saved:")
    print(f"- {output_prefix}_analysis.png (visualization)")
    print(f"- {output_prefix}_elevation.npy (numpy array)")
    print(f"- {output_prefix}.asc (ASCII grid)")
    print(f"- {output_prefix}.csv (CSV format)")
    
    ds.close()
    return terrain, lat, lon

def save_ascii_grid(terrain, lat, lon, filename):
    """Save terrain as ESRI ASCII Grid format"""
    
    nrows, ncols = terrain.shape
    xllcorner = lon.min()
    yllcorner = lat.min()
    cellsize_lon = (lon.max() - lon.min()) / (ncols - 1)
    cellsize_lat = (lat.max() - lat.min()) / (nrows - 1)
    cellsize = min(cellsize_lon, cellsize_lat)  # Use smaller for square cells
    
    with open(filename, 'w') as f:
        f.write(f"ncols {ncols}\n")
        f.write(f"nrows {nrows}\n")
        f.write(f"xllcorner {xllcorner:.6f}\n")
        f.write(f"yllcorner {yllcorner:.6f}\n")
        f.write(f"cellsize {cellsize:.6f}\n")
        f.write(f"NODATA_value -9999\n")
        
        # Write terrain data (flip vertically for ASCII grid format)
        for row in reversed(terrain):
            f.write(' '.join(f"{val:.3f}" for val in row) + '\n')

def save_terrain_csv(terrain, lat, lon, filename):
    """Save terrain as simple CSV with coordinates"""
    
    with open(filename, 'w') as f:
        f.write("lon,lat,elevation\n")
        
        for i, lat_val in enumerate(lat):
            for j, lon_val in enumerate(lon):
                elevation = terrain[i, j]
                f.write(f"{lon_val:.6f},{lat_val:.6f},{elevation:.3f}\n")

if __name__ == "__main__":
    # Extract terrain from your NetCDF file
    netcdf_file = "wind_2007-10-05.nc"  # Change this to your file
    
    try:
        terrain, lat, lon = extract_terrain(netcdf_file)
        print("\nTerrain extraction complete!")
        print("Next step: Import the .asc file into Houdini as a heightfield")
        
    except FileNotFoundError:
        print(f"File not found: {netcdf_file}")
        print("Please update the netcdf_file variable with your actual file path")
    except Exception as e:
        print(f"Error: {e}")
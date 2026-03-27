#!/usr/bin/env python3
"""
NetCDF Wind Data to Houdini-Friendly Format
Exports as JSON point clouds that Houdini can easily import
NO OpenVDB dependency required!
"""

import xarray as xr
import numpy as np
import json
from pathlib import Path

class WindToHoudini:
    def __init__(self, netcdf_path):
        """Initialize converter with NetCDF file"""
        print(f"Loading: {netcdf_path}")
        self.ds = xr.open_dataset(netcdf_path)
        self.netcdf_path = Path(netcdf_path)
        
        # Extract coordinates
        self.lat = self.ds['lat'].values
        self.lon = self.ds['lon'].values
        self.lev = self.ds['lev'].values if 'lev' in self.ds else None
        self.time = self.ds['time'].values
        
        # Calculate geographic center (for origin in Houdini)
        self.lat_center = (self.lat.min() + self.lat.max()) / 2
        self.lon_center = (self.lon.min() + self.lon.max()) / 2
        
        # Calculate geographic extent in meters
        self.lat_extent_m = (self.lat.max() - self.lat.min()) * 111000  # 1° lat ≈ 111km
        self.lon_extent_m = (self.lon.max() - self.lon.min()) * 111000 * np.cos(np.radians(self.lat_center))
        
        print(f"\nData Info:")
        print(f"  Center: {self.lat_center:.6f}°N, {self.lon_center:.6f}°E")
        print(f"  Extent: {self.lat_extent_m/1000:.2f}km × {self.lon_extent_m/1000:.2f}km")
        print(f"  Grid: {len(self.lat)} × {len(self.lon)}")
        print(f"  Height levels: {len(self.lev) if self.lev is not None else 'N/A'}")
        print(f"  Time steps: {len(self.time)}")
        
        # Detect available wind components
        self.has_u = 'U' in self.ds or 'u' in self.ds
        self.has_v = 'V' in self.ds or 'v' in self.ds
        self.has_w = 'W' in self.ds or 'w' in self.ds
        
        print(f"  Wind components: U={self.has_u}, V={self.has_v}, W={self.has_w}")
        
    def geographic_to_cartesian(self, lat, lon, height):
        """
        Convert geographic coordinates to Cartesian (centered at origin)
        
        Returns: x, y, z in meters (centered at geographic center)
        """
        # Convert to meters relative to center
        y = (lat - self.lat_center) * 111000  # North-South (Y-up in Houdini)
        x = (lon - self.lon_center) * 111000 * np.cos(np.radians(self.lat_center))  # East-West
        z = height  # Height above ground
        
        return x, y, z
    
    def wind_components_to_cartesian(self, u, v, w=None):
        """
        Convert wind components from geographic to Cartesian velocity
        """
        vx = u  # East = +X
        vy = v  # North = +Y
        vz = w if w is not None else np.zeros_like(u)  # Up = +Z
        
        return vx, vy, vz
    
    def export_timestep_as_csv(self, time_idx, output_dir):
        """
        Export a timestep as CSV point cloud
        Format: x,y,z,vx,vy,vz,speed,level
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        print(f"\nProcessing timestep {time_idx+1}/{len(self.time)}")
        
        # Get wind component names
        u_name = 'U' if 'U' in self.ds else 'u'
        v_name = 'V' if 'V' in self.ds else 'v'
        w_name = 'W' if self.has_w and 'W' in self.ds else ('w' if self.has_w else None)
        
        # Get terrain height if available
        terrain_height = self.ds['HGT'].values if 'HGT' in self.ds else np.zeros((len(self.lat), len(self.lon)))
        
        output_file = output_dir / f"wind_points_{time_idx:04d}.csv"
        
        with open(output_file, 'w') as f:
            # Write header
            f.write("x,y,z,vx,vy,vz,speed,level_idx,height_agl\n")
            
            if self.lev is not None:
                # Extract wind data for this timestep (all levels)
                u_data = self.ds[u_name].isel(time=time_idx).values
                v_data = self.ds[v_name].isel(time=time_idx).values
                w_data = self.ds[w_name].isel(time=time_idx).values if w_name else None
                
                # Process each height level
                for lev_idx, height_above_ground in enumerate(self.lev):
                    print(f"  Level {lev_idx+1}/{len(self.lev)}: {height_above_ground}m AGL")
                    
                    # Get wind at this level
                    u_slice = u_data[lev_idx, :, :]
                    v_slice = v_data[lev_idx, :, :]
                    w_slice = w_data[lev_idx, :, :] if w_data is not None else None
                    
                    # Convert to Cartesian velocities
                    vx, vy, vz = self.wind_components_to_cartesian(u_slice, v_slice, w_slice)
                    
                    # Calculate wind speed
                    speed = np.sqrt(vx**2 + vy**2 + vz**2)
                    
                    # Create coordinate grids
                    lon_grid, lat_grid = np.meshgrid(self.lon, self.lat)
                    
                    # Add terrain height to get absolute height
                    height_grid = terrain_height + height_above_ground
                    
                    # Convert to Cartesian coordinates
                    x_grid, y_grid, z_grid = self.geographic_to_cartesian(
                        lat_grid, lon_grid, height_grid
                    )
                    
                    # Write points for this level
                    for i in range(len(self.lat)):
                        for j in range(len(self.lon)):
                            f.write(f"{x_grid[i,j]:.3f},{y_grid[i,j]:.3f},{z_grid[i,j]:.3f},")
                            f.write(f"{vx[i,j]:.6f},{vy[i,j]:.6f},{vz[i,j]:.6f},")
                            f.write(f"{speed[i,j]:.6f},{lev_idx},{height_above_ground:.1f}\n")
            
            else:
                # Single level data
                print("  Single height level")
                u_data = self.ds[u_name].isel(time=time_idx).values
                v_data = self.ds[v_name].isel(time=time_idx).values
                w_data = self.ds[w_name].isel(time=time_idx).values if w_name else None
                
                vx, vy, vz = self.wind_components_to_cartesian(u_data, v_data, w_data)
                speed = np.sqrt(vx**2 + vy**2 + vz**2)
                
                lon_grid, lat_grid = np.meshgrid(self.lon, self.lat)
                x_grid, y_grid, z_grid = self.geographic_to_cartesian(lat_grid, lon_grid, 0)
                
                for i in range(len(self.lat)):
                    for j in range(len(self.lon)):
                        f.write(f"{x_grid[i,j]:.3f},{y_grid[i,j]:.3f},{z_grid[i,j]:.3f},")
                        f.write(f"{vx[i,j]:.6f},{vy[i,j]:.6f},{vz[i,j]:.6f},")
                        f.write(f"{speed[i,j]:.6f},0,0.0\n")
        
        print(f"  Saved: {output_file}")
        print(f"  Points: {len(self.lat) * len(self.lon) * (len(self.lev) if self.lev is not None else 1)}")
    
    def export_all_timesteps(self, output_dir="wind_points_output", timestep_range=None):
        """Export all timesteps as CSV point clouds"""
        if timestep_range:
            start, end = timestep_range
        else:
            start, end = 0, len(self.time)
        
        print(f"\n{'='*60}")
        print(f"Exporting timesteps {start} to {end-1}")
        print(f"{'='*60}")
        
        for t in range(start, end):
            self.export_timestep_as_csv(t, output_dir)
        
        # Save metadata
        self._save_metadata(output_dir)
        
        print(f"\n{'='*60}")
        print(f"Export complete! CSV files saved to: {output_dir}")
        print(f"{'='*60}")
    
    def _save_metadata(self, output_dir):
        """Save metadata JSON for Houdini import"""
        metadata = {
            'geographic_center': {
                'latitude': float(self.lat_center),
                'longitude': float(self.lon_center)
            },
            'extent_meters': {
                'x_east_west': float(self.lon_extent_m),
                'y_north_south': float(self.lat_extent_m)
            },
            'grid_size': {
                'lat': int(len(self.lat)),
                'lon': int(len(self.lon))
            },
            'height_levels_m': self.lev.tolist() if self.lev is not None else None,
            'timesteps': int(len(self.time)),
            'wind_components': {
                'U_east_west': self.has_u,
                'V_north_south': self.has_v,
                'W_vertical': self.has_w
            },
            'houdini_workflow': {
                'step_1': 'Import CSV with File SOP',
                'step_2': 'Set point attributes: P (position), v (velocity)',
                'step_3': 'Use Points from Volume or Volume Rasterize Attributes',
                'step_4': 'Create velocity volumes for simulation',
                'coordinate_system': 'X=East, Y=North, Z=Up (height)',
                'origin': 'Centered at geographic center (0,0,0)',
                'units': 'Position in meters, Velocity in m/s'
            }
        }
        
        metadata_file = Path(output_dir) / 'wind_metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\nMetadata: {metadata_file}")
        
        # Also create a simple Houdini import guide
        guide_file = Path(output_dir) / 'HOUDINI_IMPORT_GUIDE.txt'
        with open(guide_file, 'w') as f:
            f.write("="*60 + "\n")
            f.write("HOUDINI IMPORT WORKFLOW\n")
            f.write("="*60 + "\n\n")
            f.write("1. FILE SOP:\n")
            f.write(f"   - File: wind_points_$F4.csv\n")
            f.write(f"   - File Type: CSV\n")
            f.write(f"   - Points per frame: {len(self.lat) * len(self.lon) * (len(self.lev) if self.lev else 1)}\n\n")
            f.write("2. ATTRIBUTE CREATE (or use existing attributes):\n")
            f.write("   - Create 'v' vector attribute from vx,vy,vz\n")
            f.write("   - Or use Volume Rasterize Attributes directly\n\n")
            f.write("3. VOLUME RASTERIZE ATTRIBUTES:\n")
            f.write("   - Rasterize 'v' (velocity vector)\n")
            f.write(f"   - Grid extent: ~{self.lon_extent_m:.0f}m × {self.lat_extent_m:.0f}m × {max(self.lev) if self.lev else 100:.0f}m\n")
            f.write("   - Voxel size: start with 100m for testing\n\n")
            f.write("4. CONVERT TO VDB (optional):\n")
            f.write("   - Use Convert VDB SOP\n")
            f.write("   - Creates velocity VDB volumes\n\n")
            f.write("5. ALIGN WITH TERRAIN:\n")
            f.write(f"   - Both should be centered at origin\n")
            f.write(f"   - Terrain extent: {self.lon_extent_m:.0f}m × {self.lat_extent_m:.0f}m\n\n")
            f.write("="*60 + "\n")
        
        print(f"Import guide: {guide_file}")


if __name__ == "__main__":
    # Configuration
    netcdf_file = "wind_2007-10-05.nc"  # Change to your file
    output_directory = "wind_points_output"
    
    # Test with just first few timesteps
    timestep_range = (0, 3)  # First 3 timesteps for testing
    # timestep_range = None  # Uncomment for all timesteps
    
    try:
        converter = WindToHoudini(netcdf_file)
        converter.export_all_timesteps(output_directory, timestep_range)
        
        print("\n" + "="*60)
        print("SUCCESS! Ready for Houdini import")
        print("="*60)
        print("Check HOUDINI_IMPORT_GUIDE.txt for detailed workflow")
        
    except FileNotFoundError:
        print(f"Error: File not found: {netcdf_file}")
        print("Update the netcdf_file variable to your actual file path")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
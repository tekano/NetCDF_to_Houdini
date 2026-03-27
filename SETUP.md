# Setup — Fresh Machine Install

## Windows (PowerShell)

```powershell
& "C:\Users\tekan\AppData\Local\Programs\Python\Python312\python.exe" -m pip install xarray netCDF4 numpy scipy rich matplotlib opencv-python
```

## Linux / Mac

```bash
pip install xarray netCDF4 numpy scipy rich matplotlib opencv-python
```

## Verify it worked

```powershell
& "C:\Users\tekan\AppData\Local\Programs\Python\Python312\python.exe" -c "import xarray, netCDF4, numpy, scipy, rich, matplotlib, cv2; print('All good')"
```

## Note on pyopenvdb (VDB export)

Do NOT pip install pyopenvdb — it requires compiling OpenVDB from source.
Instead, run `nc_to_vdb.py` via Houdini's bundled Python which includes it:

```powershell
& "C:\Program Files\Side Effects Software\Houdini 20.5.xxx\bin\hython.exe" scripts\nc_to_vdb.py
```

Adjust the Houdini version path to match your install.

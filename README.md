# Custom Map Downloader

A QGIS plugin for downloading high-resolution, georeferenced map imagery from any loaded layer.

## Description

Custom Map Downloader enables high‑resolution map export from any loaded QGIS layer in two formats:

- GeoTIFF: a single georeferenced raster image
- MBTiles: a tiled SQLite database for web/mobile use

In GeoTIFF mode, provide a center point (lat/lon), Ground Sampling Distance (GSD), and output dimensions; the plugin computes the extent, renders at the requested resolution, and writes a geotagged TIFF. In MBTiles mode, define an area (center+radius or bounding box), choose zoom levels or a single‑shot export, and optionally include neighbouring tiles to avoid edge clipping.

Perfect for extracting satellite imagery, creating training datasets, generating offline maps, or producing custom map exports for simulation and analysis workflows.

## Screenshot

![Plugin Interface](menu-screenshot.png)

*Custom Map Downloader plugin interface*

## Features

- ✅ **Export Any Layer** - Works with satellite imagery, XYZ tiles, raster layers, and vector tile layers
- ✅ **Two Formats** - GeoTIFF (single raster) and MBTiles (tile pyramid)
- ✅ **Precise Positioning** - Specify center point using latitude/longitude
- ✅ **Custom Resolution** - Configure Ground Sampling Distance (GSD) in meters per pixel
- ✅ **Flexible Dimensions** - Set custom output dimensions (width × height in pixels)
- ✅ **CRS Support** - 30+ common EPSG codes; GeoTIFF exports in your selected CRS
- ✅ **MBTiles Extent Options** - Center+Radius or Bounding Box
- ✅ **Zoom Control** - Zoom range (min/max) or single‑shot at one zoom level
- ✅ **Auto‑detect Min Zoom** - Finds the first zoom where your area spans >1 tile
- ✅ **Neighbour Padding** - Include 0–5 rings of surrounding tiles to avoid edge clipping
- ✅ **Live Estimates** - Shows estimated tile count and approximate download size
- ✅ **Determinate Progress Bars** - Real % progress for both GeoTIFF and MBTiles exports
- ✅ **Automatic Layer Loading** - Optionally load exported GeoTIFF directly into QGIS
- ✅ **Proper Metadata** - Full GDAL georeferencing for GeoTIFF
- ✅ **Optimized Output** - LZW compression and tiling for efficient storage

## Installation

### From QGIS Plugin Repository (Recommended)

1. Open QGIS
2. Go to `Plugins` → `Manage and Install Plugins`
3. Search for "Custom Map Downloader"
4. Click `Install Plugin`

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/ashroo/custom_map_downloader/releases)
2. Extract the ZIP file
3. Copy the `custommapdownloader` folder to your QGIS plugins directory:
   - **Windows**: `C:\Users\[username]\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins`
   - **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins`
   - **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins`
4. Restart QGIS
5. Enable the plugin in `Plugins` → `Manage and Install Plugins` → `Installed`

## Usage

### Quick Start (GeoTIFF)

1. **Load a Map Layer**

   - Add any map layer to QGIS (e.g., Google Satellite, OpenStreetMap, Bing Maps)
   - Ensure the layer is visible in the Layers panel
2. **Open the Plugin**

   - Click the Custom Map Downloader icon in the toolbar, or
   - Go to `Plugins` → `MapDownloader` → `Download Map (GeoTIFF / MBTiles)`
3. **Configure Parameters**

   - **Coordinates**: Enter latitude and longitude in decimal degrees
     - Example: Latitude: `28.6139`, Longitude: `77.2090` (New Delhi)
   - **Resolution**: Set Ground Sampling Distance (GSD) in meters/pixel
     - Default: `5.0` m/pixel
   - **Dimensions**: Specify output width and height in pixels
     - Default: `5000 × 5000` pixels
4. **Select Layer**

   - Choose the layer to export from the dropdown menu
   - The list automatically refreshes to show all loaded layers
5. **Choose Output Path**

   - Click `Browse...` to select where to save the file
   - Recommended format: `.tif` or `.tiff`
6. **Configure Export Options**

   - ☑️ **Add georeferencing metadata**: Creates proper GeoTIFF with spatial reference (recommended)
   - ☑️ **Load exported image as layer in QGIS**: Automatically adds result to your project
7. **Export**

   - Click `OK` to start the export
   - A determinate progress dialog will show during rendering
   - Success message will confirm completion

### Quick Start (MBTiles)

1. Choose the MBTiles format at the top of the dialog
2. Define your area
   - Center Point + Radius (meters), or
   - Bounding Box (min/max lat/lon)
3. Choose zooms
   - Zoom Range (min/max), or Single Shot (one zoom)
   - Use Auto‑detect to pick the first zoom where the area spans >1 tile
4. Tile options
   - Tile Size (default 256 px)
   - Neighbour Padding: 0–5 rings of surrounding tiles (default 1)
5. Pick output `.mbtiles` path and Export
   - Progress bar shows tile and percent updates

### Default Settings

| Parameter      | Default Value    |
| -------------- | ---------------- |
| GSD            | 5.0 meters/pixel |
| Width          | 5000 pixels      |
| Height         | 5000 pixels      |
| Georeferencing | Enabled          |
| Load as Layer  | Enabled          |

## Output Formats

### With Georeferencing (GeoTIFF)

- **Format**: GeoTIFF with full GDAL metadata
- **Projection**: User‑selected CRS (e.g., EPSG:3857, EPSG:4326, UTM, etc.)
- **Geotransform**: Includes pixel size and geographic extent
- **Compression**: LZW compression with tiling
- **Bands**: 4 (RGBA)
- **Compatibility**: Works with all GIS software (QGIS, ArcGIS, GDAL, etc.)

### Without Georeferencing (TIFF)

- **Format**: Standard TIFF image
- **No spatial metadata**
- **Smaller file size**
- **Faster export**
- **Use case**: When you only need the image without coordinates

### MBTiles (Tiled SQLite)

- **Format**: MBTiles v1.x (SQLite database)
- **Tiles**: PNG tiles by zoom level, XYZ scheme with TMS y‑flip in storage
- **Extent Options**: Center+Radius or Bounding Box
- **Zoom Control**: Range (min/max) or Single Shot (single zoom)
- **Neighbour Padding**: 0–5 rings of surrounding tiles to avoid seams at edges
- **Metadata**: name, description, minzoom, maxzoom, bounds
- **Use case**: Offline maps for mobile/web viewers (Leaflet, Mapbox, etc.)

## Use Cases

- 🎯 **Machine Learning**: Generate training datasets for computer vision models
- 🗺️ **Offline Maps**: Extract map tiles for field work without internet
- 📊 **Reports & Presentations**: Create custom map exports at specific resolutions
- 🚁 **Simulation**: Generate georeferenced imagery for UAV/drone simulations
- 🔬 **Research**: Export precise areas for spatial analysis
- 📱 **Mobile Apps**: Create map tiles for mobile applications

## Technical Details

### Coordinate Systems

- **Input**: EPSG:4326 (WGS84 - Latitude/Longitude)
- **Processing/Output (GeoTIFF)**: User‑selected CRS with proper geotransform
- **Tiles (MBTiles)**: Web Mercator tiling scheme (EPSG:3857 tile extents)

### Rendering

- Uses `QgsMapRendererParallelJob` for efficient parallel rendering
- Supports all QGIS-compatible layer types
- Renders at exact specified resolution
 - MBTiles tiles are rendered one‑by‑one at EPSG:3857 extents for each zoom level

### Georeferencing (GeoTIFF)

- GDAL-based georeferencing with proper geotransform matrix
- Includes spatial reference system (SRS) metadata
- Pixel size calculated from GSD parameter; extent computed from center point and dimensions

## Requirements

- **QGIS**: Version 3.0 or higher
- **Python**: 3.6+ (included with QGIS)
- **Dependencies**:
  - `numpy` (included with QGIS)
  - `GDAL/OGR` (included with QGIS)
  - `PyQt5` (included with QGIS)

## Troubleshooting

### Layer not appearing in dropdown

- **Solution**: The plugin refreshes layers each time it opens. If a layer is missing, close and reopen the dialog.

### Export fails with "Invalid coordinates"

- **Solution**: Ensure latitude is between -90 and 90, longitude between -180 and 180. Use decimal degrees format.

### Exported image has no georeferencing

- **Solution**: Make sure "Add georeferencing metadata" checkbox is enabled before export.

### Image appears in wrong location

- **Solution**: Verify your input coordinates are correct and in decimal degrees (not DMS format).

### Large exports are slow

- **Solution**: This is normal for high-resolution exports. The progress dialog shows the process is working. Consider reducing dimensions or GSD for faster exports.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

See [LICENSE](LICENSE) for more details.

## Author

**Abhinav Jayswal**

- Email: abhinavjayaswal10@gmail.com
- GitHub: [@ashroo](https://github.com/ashroo)

## Acknowledgments

- Built using the QGIS Plugin Builder
- Uses QGIS API and GDAL for geospatial operations
- Thanks to the QGIS community for excellent documentation

## Support

- **Bug Reports**: [GitHub Issues](https://github.com/ashroo/custom_map_downloader/issues)
- **Feature Requests**: [GitHub Issues](https://github.com/ashroo/custom_map_downloader/issues)
- **Email**: abhinavjayaswal10@gmail.com

## Changelog

### Version 0.2.0 (2026-02-20)

- MBTiles export with Center+Radius or Bounding Box extents
- Zoom Range or Single‑Shot export; Auto‑detect minimum visible zoom
- Neighbour padding (0–5 rings) to include surrounding tiles
- Live tile count and size estimate in UI
- Determinate progress bars for GeoTIFF and MBTiles
- Stability improvements with QEventLoop‑based rendering

### Version 0.1.3 (2025-02-20)

- MBTiles export option added to the UI (initial wiring)
- Dynamic format switching between GeoTIFF and MBTiles
- Extent/Zoom controls exposed in the dialog

### Version 0.1.2 (2025-02-19)

- CRS dropdown with 30+ EPSG codes for GeoTIFF output
- Fixed extent calculation for geographic vs projected CRS

### Version 0.1.1 (2025-02-18)

- Initial release with GeoTIFF export, GSD/dimensions, optional georeferencing, auto‑load layer, and progress dialog

---

**⭐ If you find this plugin useful, please consider giving it a star on GitHub!**

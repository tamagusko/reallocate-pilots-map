"""Batch convert Shapefiles (*.shp) in the 'data' folder to GeoJSON.

Usage:
    python convert_to_geojson.py

Dependencies:
    - geopandas
"""

from pathlib import Path

import geopandas as gpd

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DATA_DIR: Path = Path(__file__).parent / "data"

# -----------------------------------------------------------------------------
# Main conversion function
# -----------------------------------------------------------------------------

def convert_all_shapefiles(data_dir: Path) -> None:
    """Convert all Shapefiles (*.shp) in data_dir to GeoJSON files."""
    shapefiles = sorted(data_dir.glob("*.shp"))

    if not shapefiles:
        print("No .shp files found in 'data' folder.")
        return

    print(f"Found {len(shapefiles)} shapefile(s) in 'data'...")

    for shp_path in shapefiles:
        geojson_path = shp_path.with_suffix(".geojson")

        # Skip conversion if .geojson already exists
        if geojson_path.exists():
            print(f"Skipping {shp_path.name} (already converted).")
            continue

        try:
            print(f"Converting {shp_path.name} → {geojson_path.name} ...")
            gdf = gpd.read_file(shp_path)
            gdf.to_file(geojson_path, driver="GeoJSON")
            print(f"✔ Saved: {geojson_path.name}")
        except Exception as e:
            print(f"⚠️ Failed to convert {shp_path.name}: {e}")

    print("Done.")

# -----------------------------------------------------------------------------
# Script entry point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    convert_all_shapefiles(DATA_DIR)

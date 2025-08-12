#!/usr/bin/env python3
"""
Plot GeoJSON data with city boundaries to visualize validation errors.
This script helps debug geographic boundary validation issues.
"""
import matplotlib.pyplot as plt
import geopandas as gpd
import requests
import json
from pathlib import Path
import argparse
from typing import Optional, Dict, Any, List
import logging
import contextily as ctx
import warnings

# Suppress contextily warnings
warnings.filterwarnings("ignore", category=UserWarning, module="contextily")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BoundaryPlotter:
    """Plot GeoJSON data with city boundaries for validation visualization"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'REALLOCATE-Boundary-Plotter/1.0'
        })
    
    def discover_local_names(self, city_name: str) -> List[str]:
        """Discover local and alternative names from OSM for better boundary detection"""
        try:
            # First, query to get name details
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': city_name,
                'format': 'json',
                'limit': 3,
                'namedetails': 1,
                'addressdetails': 1,
                'extratags': 1,
                'accept-language': 'en,local'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            discovered_names = set()
            
            for item in data:
                # Add primary name
                if 'name' in item:
                    discovered_names.add(item['name'])
                
                # Add name details (multilingual names)
                namedetails = item.get('namedetails', {})
                for name_key, name_value in namedetails.items():
                    if name_key.startswith('name') and name_value:
                        discovered_names.add(name_value)
                
                # Add official name if available
                if 'official_name' in namedetails:
                    discovered_names.add(namedetails['official_name'])
                
                # Add local name if available
                if 'local_name' in namedetails:
                    discovered_names.add(namedetails['local_name'])
                
                # Add short name if available
                if 'short_name' in namedetails:
                    discovered_names.add(namedetails['short_name'])
            
            # Convert to list and prioritize original query
            name_list = [city_name]
            for name in discovered_names:
                if name != city_name and name not in name_list:
                    name_list.append(name)
            
            logger.info(f"Discovered {len(name_list)} name variations for '{city_name}': {name_list[:5]}...")
            return name_list[:10]  # Limit to avoid too many queries
            
        except Exception as e:
            logger.debug(f"Error discovering local names for '{city_name}': {e}")
            return [city_name]  # Fallback to original name

    def get_city_boundary(self, city_name: str) -> Optional[gpd.GeoDataFrame]:
        """Get city boundary from OpenStreetMap Nominatim API with automatic local name discovery"""
        logger.info(f"Fetching boundary data for {city_name}")
        
        # Discover local names automatically
        discovered_names = self.discover_local_names(city_name)
        
        # Create comprehensive variations including country context and administrative terms
        city_variations = []
        for name in discovered_names:
            city_variations.extend([
                name,
                f"{name}, Sweden" if any(x in name.lower() for x in ['göteborg', 'gothenburg']) else name,
                f"{name}, Netherlands" if any(x in name.lower() for x in ['utrecht']) else name,
                f"{name}, Germany" if any(x in name.lower() for x in ['heidelberg']) else name,
                f"{name}, Spain" if any(x in name.lower() for x in ['barcelona']) else name,
                f"{name}, Hungary" if any(x in name.lower() for x in ['budapest']) else name,
                f"{name} municipality",
                f"{name} kommun" if any(x in name.lower() for x in ['göteborg', 'gothenburg']) else name,
                f"{name} gemeente" if any(x in name.lower() for x in ['utrecht']) else name,
                f"{name}s Stad" if any(x in name.lower() for x in ['göteborg', 'gothenburg']) else name,  # Swedish municipality format
            ])
        
        # Prioritize the official local name if discovered
        if city_name.lower() in ['gothenburg', 'göteborg']:
            # Ensure "Göteborg" and "Göteborgs Stad" are at the front
            priority_names = ['Göteborg', 'Göteborgs Stad', 'Göteborg, Sweden']
            for pname in reversed(priority_names):  # Add in reverse to maintain order
                if pname in city_variations:
                    city_variations.remove(pname)
                city_variations.insert(0, pname)
        
        # Remove duplicates while preserving order
        city_variations = list(dict.fromkeys(city_variations))
        
        best_boundary = None
        best_area = 0
        
        for variation in city_variations:
            try:
                logger.info(f"Trying query: '{variation}'")
                
                url = "https://nominatim.openstreetmap.org/search"
                params = {
                    'q': variation,
                    'format': 'geojson',
                    'limit': 5,  # Get multiple results to find best one
                    'polygon_geojson': 1,
                    'addressdetails': 1,
                    'extratags': 1
                }
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Evaluate each result
                for feature in data.get('features', []):
                    try:
                        # Create temporary GeoDataFrame to check geometry
                        temp_gdf = gpd.GeoDataFrame.from_features([feature], crs='EPSG:4326')
                        
                        # Calculate area in a projected coordinate system for accurate measurement
                        temp_gdf_proj = temp_gdf.to_crs('EPSG:3857')  # Web Mercator
                        area_m2 = temp_gdf_proj.geometry.area.iloc[0]
                        
                        # Properties
                        props = feature.get('properties', {})
                        geom_type = feature.get('geometry', {}).get('type', '')
                        
                        logger.info(f"  Found {geom_type} with area: {area_m2/1e6:.2f} km²")
                        
                        # Get properties for type-based scoring
                        props = feature.get('properties', {})
                        feature_type = props.get('type', '').lower()
                        osm_class = props.get('class', '').lower()
                        display_name = props.get('display_name', '').lower()
                        feature_name = props.get('name', '').lower()
                        
                        # Prioritize results with:
                        # 1. Polygon or MultiPolygon geometry (not Point)
                        # 2. Significant area (> 10 km² but < 2000 km² for reasonable city size)
                        # 3. City type over administrative regions
                        
                        is_suitable_geometry = geom_type in ['Polygon', 'MultiPolygon']
                        
                        # Special size handling for Swedish municipalities
                        if 'stad' in feature_name and any(x in feature_name for x in ['göteborg', 'stockholm', 'malmö']):
                            # Swedish municipalities can be larger (up to 4000 km²)
                            is_reasonable_size = 10e6 < area_m2 < 4000e6  # 10 km² to 4000 km²
                        else:
                            is_reasonable_size = 10e6 < area_m2 < 2000e6  # 10 km² to 2000 km²
                        
                        # Type-based scoring (higher is better)
                        type_score = 0
                        
                        if feature_type == 'city':
                            type_score = 100
                        elif osm_class == 'place' and 'city' in display_name:
                            type_score = 90
                        elif feature_type in ['town', 'village']:
                            type_score = 80
                        elif feature_type == 'administrative':
                            # Special scoring for Swedish municipalities ending with "stad"
                            if 'stad' in feature_name and any(x in feature_name for x in ['göteborg', 'stockholm', 'malmö']):
                                type_score = 95  # High priority for Swedish municipalities
                            elif area_m2 < 500e6:  # < 500 km²
                                type_score = 70  # Smaller admin boundaries
                            else:
                                type_score = 30  # Large admin regions get lower score
                        else:
                            type_score = 50  # Default for unknown types
                        
                        # Calculate combined score (type score + size factor)
                        # Special size scoring for Swedish municipalities
                        if 'stad' in feature_name and any(x in feature_name for x in ['göteborg', 'stockholm', 'malmö']):
                            # Swedish municipalities should get good size scores even if large
                            size_score = 50  # Fixed bonus for Swedish municipalities
                        else:
                            # Prefer moderate sizes - not too big, not too small
                            size_score = max(0, 100 - abs(area_m2 - 200e6) / 10e6)  # Peak at ~200 km²
                        
                        combined_score = type_score + size_score
                        
                        logger.info(f"  Found {geom_type} - Type: '{feature_type}' Class: '{osm_class}' Area: {area_m2/1e6:.2f} km² Score: {combined_score:.1f}")
                        
                        if (is_suitable_geometry and is_reasonable_size and 
                            combined_score > best_area):  # Now using score instead of area
                            
                            best_boundary = temp_gdf
                            best_area = combined_score  # Store score, not area
                            logger.info(f"  ✅ New best boundary candidate: {area_m2/1e6:.2f} km² (score: {combined_score:.1f}) with query '{variation}'")
                            
                    except Exception as e:
                        logger.error(f"  Error processing result: {e}")
                        import traceback
                        logger.error(f"  Full traceback: {traceback.format_exc()}")
                        continue
                        
            except Exception as e:
                logger.debug(f"Error with query '{variation}': {e}")
                continue
        
        if best_boundary is not None:
            # Calculate actual area for logging (best_area now contains score)
            best_boundary_proj = best_boundary.to_crs('EPSG:3857')
            actual_area_m2 = best_boundary_proj.geometry.area.iloc[0]
            
            logger.info(f"Successfully retrieved boundary: {actual_area_m2/1e6:.2f} km² (score: {best_area:.1f})")
            return best_boundary
        else:
            logger.warning(f"No suitable boundary polygon found for {city_name}")
            return None
    
    def extract_city_from_filename(self, filename: str) -> str:
        """Extract city name from GeoJSON filename"""
        import re
        # Pattern: pilot[X]_[cityname].geojson
        pattern = r'pilot\d+_(.+)\.geojson'
        match = re.match(pattern, filename.lower())
        
        if match:
            city_name = match.group(1).replace('_', ' ').strip()
            # Handle special cases like "pilot2_ gothenburg"
            city_name = city_name.replace(' ', '')
            return city_name
        else:
            # Fallback parsing
            parts = filename.lower().replace('.geojson', '').split('_')
            if len(parts) >= 2:
                city_part = '_'.join(parts[1:])
                return city_part
        
        return "unknown"
    
    def plot_boundary_validation(self, geojson_file: Path, output_file: Optional[Path] = None) -> str:
        """Plot GeoJSON data with city boundary and basemap, save as high-resolution image"""
        
        # Extract city name from filename
        city_name = self.extract_city_from_filename(geojson_file.name)
        logger.info(f"Processing {geojson_file.name} for city: {city_name}")
        
        # Load GeoJSON data
        try:
            pilot_gdf = gpd.read_file(geojson_file)
            logger.info(f"Loaded {len(pilot_gdf)} features from {geojson_file.name}")
        except Exception as e:
            logger.error(f"Failed to load {geojson_file}: {e}")
            return ""
        
        # Get city boundary
        boundary_gdf = self.get_city_boundary(city_name)
        
        if boundary_gdf is None:
            logger.error(f"Cannot create plot without boundary data for {city_name}")
            return ""
        
        # Ensure both datasets are in the same CRS (WGS84)
        if pilot_gdf.crs != 'EPSG:4326':
            pilot_gdf = pilot_gdf.to_crs('EPSG:4326')
        if boundary_gdf.crs != 'EPSG:4326':
            boundary_gdf = boundary_gdf.to_crs('EPSG:4326')
        
        # Convert to Web Mercator for basemap compatibility
        pilot_gdf_mercator = pilot_gdf.to_crs('EPSG:3857')
        boundary_gdf_mercator = boundary_gdf.to_crs('EPSG:3857')
        
        # Calculate combined bounds for better view
        combined_bounds = pilot_gdf.total_bounds
        boundary_bounds = boundary_gdf.total_bounds
        
        # Expand bounds to include both datasets
        min_x = min(combined_bounds[0], boundary_bounds[0])
        min_y = min(combined_bounds[1], boundary_bounds[1])
        max_x = max(combined_bounds[2], boundary_bounds[2])
        max_y = max(combined_bounds[3], boundary_bounds[3])
        
        # Add padding (10% of range)
        x_range = max_x - min_x
        y_range = max_y - min_y
        padding = max(x_range, y_range) * 0.1
        
        bounds = [min_x - padding, min_y - padding, max_x + padding, max_y + padding]
        
        # Create the plot with larger figure for better resolution
        fig, ax = plt.subplots(1, 1, figsize=(14, 12), dpi=400)
        
        # Plot city boundary first
        boundary_gdf_mercator.plot(
            ax=ax,
            color='lightblue',
            alpha=0.4,
            edgecolor='blue',
            linewidth=3,
            label=f'{city_name.title()} City Boundary'
        )
        
        # Plot pilot data with higher contrast
        pilot_gdf_mercator.plot(
            ax=ax,
            color='red',
            alpha=0.8,
            edgecolor='darkred',
            linewidth=3,
            markersize=150,
            label=f'Pilot Data ({geojson_file.name})'
        )
        
        # Add basemap - try different sources for best coverage
        try:
            logger.info("Adding OpenStreetMap basemap...")
            ctx.add_basemap(ax, crs=pilot_gdf_mercator.crs, source=ctx.providers.OpenStreetMap.Mapnik, alpha=0.6)
        except Exception as e:
            try:
                logger.info("Fallback to CartoDB basemap...")
                ctx.add_basemap(ax, crs=pilot_gdf_mercator.crs, source=ctx.providers.CartoDB.Positron, alpha=0.6)
            except Exception as e2:
                try:
                    logger.info("Fallback to Stamen basemap...")
                    ctx.add_basemap(ax, crs=pilot_gdf_mercator.crs, source=ctx.providers.Stamen.TonerLite, alpha=0.6)
                except Exception as e3:
                    logger.warning(f"Could not add basemap: {e3}")
        
        # Set map extent
        ax.set_xlim(pilot_gdf_mercator.total_bounds[0] - 5000, 
                   pilot_gdf_mercator.total_bounds[2] + 5000)
        ax.set_ylim(pilot_gdf_mercator.total_bounds[1] - 5000, 
                   pilot_gdf_mercator.total_bounds[3] + 5000)
        
        # Check if features intersect with boundary
        boundary_geom = boundary_gdf.geometry.iloc[0]
        features_intersect = pilot_gdf.geometry.intersects(boundary_geom)
        features_within = pilot_gdf.geometry.within(boundary_geom)
        
        intersect_count = features_intersect.sum()
        within_count = features_within.sum()
        total_features = len(pilot_gdf)
        
        # Add validation info to plot with better styling
        validation_text = f"""Validation Results:
Total Features: {total_features}
Intersecting Boundary: {intersect_count}
Within Boundary: {within_count}  
Outside Boundary: {total_features - intersect_count}

Status: {'PASS' if intersect_count == total_features else 'FAIL'}
City: {city_name.title()}"""
        
        # Position text box with better styling
        ax.text(0.02, 0.98, validation_text, transform=ax.transAxes,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.9, edgecolor='gray'),
                verticalalignment='top', fontfamily='monospace', fontsize=10,
                fontweight='bold')
        
        # Customize plot
        ax.set_title(f'Geographic Validation: {geojson_file.name}\n'
                    f'{city_name.title()} City Boundary vs Pilot Data',
                    fontsize=16, fontweight='bold', pad=25)
        
        # Improve legend
        legend = ax.legend(loc='upper right', fontsize=12, framealpha=0.9,
                          fancybox=True, shadow=True, borderpad=1)
        legend.get_frame().set_facecolor('white')
        legend.get_frame().set_edgecolor('gray')
        
        # Remove axis labels for cleaner map appearance
        ax.set_xlabel('')
        ax.set_ylabel('')
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Add north arrow and scale would be nice but require additional packages
        
        # Set output filename
        if output_file is None:
            output_file = Path(f"boundary_validation_{city_name}_{geojson_file.stem}.png")
        
        # Save plot with high resolution and better quality
        plt.tight_layout()
        plt.savefig(output_file, dpi=400, bbox_inches='tight', 
                   facecolor='white', edgecolor='none', 
                   pad_inches=0.1, format='png')
        logger.info(f"Plot saved as {output_file}")
        
        # Also display summary
        print(f"\n{'='*60}")
        print(f"BOUNDARY VALIDATION SUMMARY: {geojson_file.name}")
        print(f"{'='*60}")
        print(f"City: {city_name.title()}")
        print(f"Total Features: {total_features}")
        print(f"Features Intersecting Boundary: {intersect_count}/{total_features}")
        print(f"Features Within Boundary: {within_count}/{total_features}")
        print(f"Features Outside Boundary: {total_features - intersect_count}")
        print(f"Validation Status: {'PASS' if intersect_count == total_features else 'FAIL'}")
        print(f"Plot saved: {output_file}")
        print(f"{'='*60}")
        
        plt.close()
        return str(output_file)
    
    def plot_all_failed_validations(self, data_dir: Path, output_dir: Path = None) -> list:
        """Plot all GeoJSON files that might have boundary validation issues"""
        
        if output_dir is None:
            output_dir = Path("boundary_plots")
        output_dir.mkdir(exist_ok=True)
        
        geojson_files = list(data_dir.glob("*.geojson"))
        plots_created = []
        
        for geojson_file in geojson_files:
            try:
                output_file = output_dir / f"boundary_validation_{geojson_file.stem}.png"
                result = self.plot_boundary_validation(geojson_file, output_file)
                if result:
                    plots_created.append(result)
            except Exception as e:
                logger.error(f"Failed to plot {geojson_file}: {e}")
        
        return plots_created


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="Plot GeoJSON data with city boundaries to visualize validation errors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Plot specific file
  python plot_boundary_validation.py --file ../data/pilot2_gothenburg.geojson
  
  # Plot all files in directory
  python plot_boundary_validation.py --data-dir ../data
  
  # Plot with custom output location
  python plot_boundary_validation.py --file ../data/pilot2_gothenburg.geojson --output plots/gothenburg.png
        """
    )
    
    parser.add_argument(
        '--file', 
        type=Path,
        help='Single GeoJSON file to plot'
    )
    
    parser.add_argument(
        '--data-dir',
        type=Path,
        help='Directory containing GeoJSON files (plots all files)'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        help='Output file path (only for single file plotting)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Output directory for multiple plots (default: boundary_plots)'
    )
    
    args = parser.parse_args()
    
    if not args.file and not args.data_dir:
        parser.error("Must specify either --file or --data-dir")
    
    plotter = BoundaryPlotter()
    
    try:
        if args.file:
            # Plot single file
            if not args.file.exists():
                print(f"Error: File {args.file} does not exist")
                return 1
            
            result = plotter.plot_boundary_validation(args.file, args.output)
            if result:
                print(f"✅ Successfully created plot: {result}")
            else:
                print("❌ Failed to create plot")
                return 1
                
        elif args.data_dir:
            # Plot all files in directory
            if not args.data_dir.exists():
                print(f"Error: Directory {args.data_dir} does not exist")
                return 1
            
            plots = plotter.plot_all_failed_validations(args.data_dir, args.output_dir)
            print(f"✅ Successfully created {len(plots)} plots")
            for plot in plots:
                print(f"   - {plot}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  Operation interrupted by user")
        return 130
    except Exception as e:
        print(f"💥 Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
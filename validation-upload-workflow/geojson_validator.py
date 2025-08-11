#!/usr/bin/env python3
"""
Comprehensive GeoJSON validation system for European living labs data.
"""
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

import geopandas as gpd
import numpy as np
import requests


@dataclass
class ValidationResult:
    """Store validation results for a single test"""
    test_name: str
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class FileValidationReport:
    """Complete validation report for a single file"""
    filename: str
    city_name: str
    pilot_number: str
    file_size: int
    total_tests: int
    passed_tests: int
    failed_tests: int
    validation_results: List[ValidationResult]
    processing_time: float
    timestamp: str
    
    @property
    def success_rate(self) -> float:
        return (self.passed_tests / self.total_tests) if self.total_tests > 0 else 0.0
    
    @property
    def overall_status(self) -> str:
        return "PASS" if self.failed_tests == 0 else "FAIL"


class CityBoundaryValidator:
    """Validate coordinates against city boundaries using external APIs"""
    
    def __init__(self, cache_timeout: int = 3600):
        self.cache = {}
        self.cache_timeout = cache_timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'REALLOCATE-GeoJSON-Validator/1.0'
        })
    
    def get_city_boundary(self, city_name: str) -> Optional[Dict]:
        """Get city boundary from Nominatim API with caching"""
        cache_key = city_name.lower()
        
        # Check cache
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_timeout:
                return cached_data
        
        try:
            # Query Nominatim API
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': city_name,
                'format': 'geojson',
                'limit': 1,
                'polygon_geojson': 1,
                'addressdetails': 1,
                'extratags': 1
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('features'):
                boundary_data = data['features'][0]
                # Cache the result
                self.cache[cache_key] = (boundary_data, time.time())
                return boundary_data
                
        except Exception as e:
            logging.warning(f"Failed to get boundary for {city_name}: {e}")
            
        return None
    
    def validate_coordinates_in_city(self, gdf: gpd.GeoDataFrame, city_name: str) -> ValidationResult:
        """Validate that all coordinates fall within city boundaries"""
        boundary_data = self.get_city_boundary(city_name)
        
        if not boundary_data:
            return ValidationResult(
                test_name="geographic_boundary_check",
                passed=False,
                message=f"Could not retrieve boundary data for {city_name}",
                details={"reason": "api_unavailable"}
            )
        
        try:
            # Create boundary geometry
            boundary_gdf = gpd.GeoDataFrame.from_features([boundary_data], crs='EPSG:4326')
            boundary_geom = boundary_gdf.geometry.iloc[0]
            
            # Check if all features are within boundary
            features_within = gdf.geometry.within(boundary_geom)
            features_intersect = gdf.geometry.intersects(boundary_geom)
            
            within_count = features_within.sum()
            intersect_count = features_intersect.sum()
            total_features = len(gdf)
            
            # Lenient check: features should at least intersect with city boundary
            if intersect_count == total_features:
                return ValidationResult(
                    test_name="geographic_boundary_check",
                    passed=True,
                    message=f"All {total_features} features intersect with {city_name} boundary",
                    details={
                        "total_features": total_features,
                        "features_within": int(within_count),
                        "features_intersecting": int(intersect_count),
                        "city_boundary_area": float(boundary_geom.area)
                    }
                )
            
            outside_count = total_features - intersect_count
            return ValidationResult(
                test_name="geographic_boundary_check",
                passed=False,
                message=f"{outside_count} of {total_features} features fall outside {city_name} boundary",
                details={
                    "total_features": total_features,
                    "features_outside": int(outside_count),
                    "features_intersecting": int(intersect_count)
                }
            )
                
        except Exception as e:
            return ValidationResult(
                test_name="geographic_boundary_check",
                passed=False,
                message=f"Error validating coordinates against {city_name} boundary: {str(e)}",
                details={"error": str(e)}
            )


class GeoJSONValidator:
    """Comprehensive GeoJSON validation class"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.boundary_validator = CityBoundaryValidator()
        self.setup_logging()
    
    def _default_config(self) -> Dict:
        """Default validation configuration"""
        return {
            'european_bounds': {
                'min_lon': -31.0, 'max_lon': 45.0,  # Extended for European territories
                'min_lat': 34.0, 'max_lat': 72.0
            },
            'min_feature_count': 1,
            'max_feature_count': 10000,
            'max_file_size_mb': 100,
            'required_crs': 'EPSG:4326'
        }
    
    def setup_logging(self):
        """Setup logging configuration"""
        # Use existing logger configuration from main workflow
        self.logger = logging.getLogger(__name__)
        
        # Only configure if no handlers exist (avoid duplicate configuration)
        if not self.logger.handlers:
            handler = logging.FileHandler('geojson_validation.log', encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def extract_city_and_pilot(self, filename: str) -> Tuple[str, str]:
        """Extract city name and pilot number from filename"""
        # Primary pattern: pilot[X]_[cityname].geojson
        primary_pattern = r'pilot(\d+)_(.+)\.geojson'
        match = re.match(primary_pattern, filename.lower())
        
        if match:
            pilot_num = match.group(1)
            city_name = match.group(2).replace('_', ' ').strip().replace(' ', '')
            return city_name, pilot_num
        
        # Fallback parsing
        base_name = filename.lower().replace('.geojson', '')
        parts = base_name.split('_')
        
        if len(parts) >= 2:
            pilot_part = parts[0]
            city_part = '_'.join(parts[1:])
            
            # Extract pilot number
            pilot_match = re.search(r'\d+', pilot_part)
            pilot_num = pilot_match.group() if pilot_match else "unknown"
            
            return city_part, pilot_num
            
        return "unknown", "unknown"
    
    def validate_file_system(self, file_path: Path) -> List[ValidationResult]:
        """Validate file system level checks"""
        results = []
        
        # File existence
        if not file_path.exists():
            results.append(ValidationResult(
                "file_existence", False, f"File does not exist: {file_path}"
            ))
            return results
        
        results.append(ValidationResult(
            "file_existence", True, "File exists"
        ))
        
        # File size check
        file_size = file_path.stat().st_size
        max_size = self.config['max_file_size_mb'] * 1024 * 1024
        
        if file_size > max_size:
            results.append(ValidationResult(
                "file_size", False, 
                f"File too large: {file_size / (1024*1024):.2f}MB > {self.config['max_file_size_mb']}MB"
            ))
        elif file_size == 0:
            results.append(ValidationResult(
                "file_size", False, "File is empty"
            ))
        else:
            results.append(ValidationResult(
                "file_size", True, f"File size OK: {file_size / 1024:.1f}KB"
            ))
        
        # Filename convention check
        filename = file_path.name
        if re.match(r'pilot\d+_.+\.geojson$', filename.lower()):
            results.append(ValidationResult(
                "filename_convention", True, "Filename follows convention"
            ))
        else:
            results.append(ValidationResult(
                "filename_convention", False, 
                f"Filename doesn't follow pilot[X]_[city].geojson convention: {filename}"
            ))
        
        return results
    
    def validate_json_structure(self, file_path: Path) -> List[ValidationResult]:
        """Validate JSON structure and GeoJSON compliance"""
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            results.append(ValidationResult(
                "json_validity", True, "Valid JSON structure"
            ))
            
            # GeoJSON structure validation
            required_fields = ['type', 'features']
            for field in required_fields:
                if field not in data:
                    results.append(ValidationResult(
                        f"geojson_{field}_field", False, f"Missing required field: {field}"
                    ))
                else:
                    results.append(ValidationResult(
                        f"geojson_{field}_field", True, f"Required field present: {field}"
                    ))
            
            # Check type
            if data.get('type') != 'FeatureCollection':
                results.append(ValidationResult(
                    "geojson_type", False, f"Invalid type: {data.get('type')}, expected 'FeatureCollection'"
                ))
            else:
                results.append(ValidationResult(
                    "geojson_type", True, "Correct GeoJSON type: FeatureCollection"
                ))
            
            # Check features array
            features = data.get('features', [])
            if not isinstance(features, list):
                results.append(ValidationResult(
                    "features_array", False, "Features is not an array"
                ))
            else:
                results.append(ValidationResult(
                    "features_array", True, f"Features array with {len(features)} items"
                ))
                
                # Validate individual features
                for i, feature in enumerate(features):
                    if not isinstance(feature, dict):
                        results.append(ValidationResult(
                            f"feature_{i}_structure", False, f"Feature {i} is not an object"
                        ))
                        continue
                    
                    # Check required feature fields
                    feature_required = ['type', 'geometry']
                    feature_valid = True
                    for field in feature_required:
                        if field not in feature:
                            results.append(ValidationResult(
                                f"feature_{i}_{field}", False, f"Feature {i} missing {field}"
                            ))
                            feature_valid = False
                    
                    if feature_valid and i == 0:  # Only report for first feature to avoid spam
                        results.append(ValidationResult(
                            "features_structure", True, "Features have required structure"
                        ))
                        
        except json.JSONDecodeError as e:
            results.append(ValidationResult(
                "json_validity", False, f"Invalid JSON: {str(e)}"
            ))
        except Exception as e:
            results.append(ValidationResult(
                "json_structure", False, f"Error reading file: {str(e)}"
            ))
        
        return results
    
    def validate_geodataframe(self, gdf: gpd.GeoDataFrame) -> List[ValidationResult]:
        """Validate GeoDataFrame properties and geometry"""
        results = []
        
        # Feature count validation
        feature_count = len(gdf)
        min_count = self.config['min_feature_count']
        max_count = self.config['max_feature_count']
        
        if feature_count < min_count:
            results.append(ValidationResult(
                "feature_count", False, f"Too few features: {feature_count} < {min_count}"
            ))
        elif feature_count > max_count:
            results.append(ValidationResult(
                "feature_count", False, f"Too many features: {feature_count} > {max_count}"
            ))
        else:
            results.append(ValidationResult(
                "feature_count", True, f"Feature count OK: {feature_count}"
            ))
        
        # CRS validation
        expected_crs = self.config['required_crs']
        if gdf.crs is None:
            results.append(ValidationResult(
                "coordinate_system", False, "No CRS defined"
            ))
        elif str(gdf.crs) != expected_crs:
            results.append(ValidationResult(
                "coordinate_system", False, f"Wrong CRS: {gdf.crs}, expected {expected_crs}"
            ))
        else:
            results.append(ValidationResult(
                "coordinate_system", True, f"Correct CRS: {gdf.crs}"
            ))
        
        # Geometry validation
        null_geoms = gdf.geometry.isnull().sum()
        if null_geoms > 0:
            results.append(ValidationResult(
                "null_geometries", False, f"{null_geoms} features have null geometry"
            ))
        else:
            results.append(ValidationResult(
                "null_geometries", True, "No null geometries"
            ))
        
        # Empty geometries
        empty_geoms = gdf.geometry.is_empty.sum()
        if empty_geoms > 0:
            results.append(ValidationResult(
                "empty_geometries", False, f"{empty_geoms} features have empty geometry"
            ))
        else:
            results.append(ValidationResult(
                "empty_geometries", True, "No empty geometries"
            ))
        
        # Valid geometries
        try:
            invalid_geoms = (~gdf.geometry.is_valid).sum()
            if invalid_geoms > 0:
                results.append(ValidationResult(
                    "geometry_validity", False, f"{invalid_geoms} invalid geometries found"
                ))
            else:
                results.append(ValidationResult(
                    "geometry_validity", True, "All geometries are valid"
                ))
        except Exception as e:
            results.append(ValidationResult(
                "geometry_validity", False, f"Error checking geometry validity: {str(e)}"
            ))
        
        # European bounds validation
        try:
            bounds = gdf.total_bounds
            eu_bounds = self.config['european_bounds']
            
            within_bounds = (
                bounds[0] >= eu_bounds['min_lon'] and bounds[2] <= eu_bounds['max_lon'] and
                bounds[1] >= eu_bounds['min_lat'] and bounds[3] <= eu_bounds['max_lat']
            )
            
            if within_bounds:
                results.append(ValidationResult(
                    "european_bounds", True, "Coordinates within European bounds"
                ))
            else:
                bounds_str = f"[{bounds[0]:.6f}, {bounds[1]:.6f}, {bounds[2]:.6f}, {bounds[3]:.6f}]"
                results.append(ValidationResult(
                    "european_bounds", False, 
                    f"Coordinates outside European bounds: {bounds_str}"
                ))
        except Exception as e:
            results.append(ValidationResult(
                "european_bounds", False, f"Error checking bounds: {str(e)}"
            ))
        
        
        return results
    
    def validate_file(self, file_path: Path) -> FileValidationReport:
        """Run complete validation on a single GeoJSON file"""
        start_time = time.time()
        filename = file_path.name
        city_name, pilot_number = self.extract_city_and_pilot(filename)
        
        self.logger.info(f"Validating {filename} (City: {city_name}, Pilot: {pilot_number})")
        
        all_results = []
        file_size = 0
        
        try:
            file_size = file_path.stat().st_size
            
            # File system validation
            all_results.extend(self.validate_file_system(file_path))
            
            # JSON structure validation
            all_results.extend(self.validate_json_structure(file_path))
            
            # Load with GeoPandas and validate
            try:
                gdf = gpd.read_file(file_path)
                
                # GeoPandas validation
                all_results.extend(self.validate_geodataframe(gdf))
                
                # Geographic boundary validation (primary requirement)
                if city_name != "unknown":
                    boundary_result = self.boundary_validator.validate_coordinates_in_city(gdf, city_name)
                    all_results.append(boundary_result)
                else:
                    all_results.append(ValidationResult(
                        "geographic_boundary_check", False, 
                        f"Cannot validate boundaries: unknown city name from {filename}"
                    ))
                
            except Exception as e:
                all_results.append(ValidationResult(
                    "geopandas_loading", False, f"Failed to load with GeoPandas: {str(e)}"
                ))
        
        except Exception as e:
            all_results.append(ValidationResult(
                "file_access", False, f"Cannot access file: {str(e)}"
            ))
        
        # Calculate summary statistics
        passed_tests = sum(1 for result in all_results if result.passed)
        failed_tests = len(all_results) - passed_tests
        processing_time = time.time() - start_time
        
        report = FileValidationReport(
            filename=filename,
            city_name=city_name,
            pilot_number=pilot_number,
            file_size=file_size,
            total_tests=len(all_results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            validation_results=all_results,
            processing_time=processing_time,
            timestamp=datetime.now().isoformat()
        )
        
        self.logger.info(f"Validation complete for {filename}: {report.overall_status} "
                        f"({passed_tests}/{len(all_results)} tests passed)")
        
        return report
    
    def validate_all_files(self, data_dir: Path) -> List[FileValidationReport]:
        """Validate all GeoJSON files in the data directory"""
        geojson_files = list(data_dir.glob("*.geojson"))
        
        if not geojson_files:
            self.logger.warning(f"No GeoJSON files found in {data_dir}")
            return []
        
        self.logger.info(f"Found {len(geojson_files)} GeoJSON files to validate")
        
        reports = []
        for file_path in sorted(geojson_files):
            try:
                report = self.validate_file(file_path)
                reports.append(report)
            except Exception as e:
                self.logger.error(f"Unexpected error validating {file_path}: {e}")
                # Create error report
                error_report = FileValidationReport(
                    filename=file_path.name,
                    city_name="unknown",
                    pilot_number="unknown",
                    file_size=0,
                    total_tests=1,
                    passed_tests=0,
                    failed_tests=1,
                    validation_results=[ValidationResult(
                        "critical_error", False, f"Critical validation error: {str(e)}"
                    )],
                    processing_time=0.0,
                    timestamp=datetime.now().isoformat()
                )
                reports.append(error_report)
        
        return reports
    
    def generate_validation_report(self, reports: List[FileValidationReport], output_path: Path = None) -> str:
        """Generate comprehensive validation report"""
        if output_path is None:
            output_path = Path("validation_report.md")
        
        total_files = len(reports)
        passed_files = sum(1 for r in reports if r.overall_status == "PASS")
        failed_files = total_files - passed_files
        
        # Generate markdown report header
        success_rate = (passed_files / total_files * 100) if total_files > 0 else 0.0
        
        report_content = f"""# GeoJSON Validation Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Files:** {total_files}
**Passed:** {passed_files}
**Failed:** {failed_files}
**Success Rate:** {success_rate:.1f}%

## Summary by City and Pilot

| File | City | Pilot | Status | Tests Passed | File Size | Processing Time |
|------|------|-------|--------|--------------|-----------|----------------|
"""
        
        for report in sorted(reports, key=lambda x: (x.pilot_number, x.city_name)):
            size_kb = report.file_size / 1024 if report.file_size > 0 else 0
            report_content += f"| {report.filename} | {report.city_name} | {report.pilot_number} | {report.overall_status} | {report.passed_tests}/{report.total_tests} | {size_kb:.1f}KB | {report.processing_time:.2f}s |\n"
        
        report_content += "\n## Detailed Results\n\n"
        
        for report in reports:
            report_content += f"### {report.filename}\n\n"
            report_content += f"- **City:** {report.city_name}\n"
            report_content += f"- **Pilot:** {report.pilot_number}\n"
            report_content += f"- **Status:** {report.overall_status}\n"
            report_content += f"- **Success Rate:** {report.success_rate*100:.1f}%\n\n"
            
            # Group results by pass/fail
            passed_results = [r for r in report.validation_results if r.passed]
            failed_results = [r for r in report.validation_results if not r.passed]
            
            if failed_results:
                report_content += "**❌ Failed Tests:**\n"
                for result in failed_results:
                    report_content += f"- `{result.test_name}`: {result.message}\n"
                report_content += "\n"
            
            if passed_results:
                report_content += "**✅ Passed Tests:**\n"
                for result in passed_results:
                    report_content += f"- `{result.test_name}`: {result.message}\n"
                report_content += "\n"
            
            report_content += "---\n\n"
        
        # Write report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        self.logger.info(f"Validation report written to {output_path}")
        return str(output_path)


if __name__ == "__main__":
    # Example usage
    validator = GeoJSONValidator()
    data_directory = Path("data")
    
    # Validate all files
    validation_reports = validator.validate_all_files(data_directory)
    
    # Generate report
    report_file = validator.generate_validation_report(validation_reports)
    
    print(f"\n{'='*50}")
    print("VALIDATION COMPLETE")
    print(f"{'='*50}")
    print(f"Total files processed: {len(validation_reports)}")
    print(f"Files passed: {sum(1 for r in validation_reports if r.overall_status == 'PASS')}")
    print(f"Files failed: {sum(1 for r in validation_reports if r.overall_status == 'FAIL')}")
    print(f"Detailed report: {report_file}")
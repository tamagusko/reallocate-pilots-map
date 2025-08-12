#!/usr/bin/env python3
"""
CKAN uploader for validated GeoJSON files from European REALLOCATE project.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
import time

import geopandas as gpd
import pandas as pd
from ckanapi import RemoteCKAN, NotFound
from dotenv import load_dotenv

from geojson_validator import FileValidationReport


@dataclass
class UploadResult:
    """Store upload results for a single file"""
    filename: str
    dataset_id: Optional[str]
    resource_id: Optional[str]
    success: bool
    message: str
    upload_time: float
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class UploadSummary:
    """Summary of all upload operations"""
    total_files: int
    successful_uploads: int
    failed_uploads: int
    total_upload_time: float
    upload_results: List[UploadResult]
    timestamp: str
    
    @property
    def success_rate(self) -> float:
        return (self.successful_uploads / self.total_files) if self.total_files > 0 else 0.0


class CKANUploader:
    """Handle CKAN dataset creation and file uploads"""
    
    def __init__(self, config: Optional[Dict] = None):
        load_dotenv()
        
        self.config = config or self._default_config()
        self.setup_logging()
        
        # Initialize CKAN connection
        self.ckan_url = self.config.get('ckan_url') or os.getenv('CKAN_URL', 'https://reallocate-ckan.iti.gr')
        self.api_key = self.config.get('api_key') or os.getenv('REALLOCATE_KEY')
        self.org_id = self.config.get('organization_id') or os.getenv('CKAN_ORG_ID', 'UCD_SDL')
        
        if not self.api_key:
            raise ValueError("CKAN API key not found. Set REALLOCATE_KEY environment variable or pass in config.")
        
        self.ckan = RemoteCKAN(self.ckan_url, apikey=self.api_key)
        self.org_info = None
        
        # Test connection and get organization info
        self._initialize_connection()
    
    def _default_config(self) -> Dict:
        """Default upload configuration"""
        return {
            'organization_id': 'UCD_SDL',
            'dataset_prefix': 'reallocate-pilot',
            'resource_formats': ['GeoJSON', 'CSV'],  # Upload as GeoJSON and convert to CSV
            'private_datasets': True,
            'auto_create_datasets': True,
            'overwrite_resources': True,
            'batch_size': 10,  # Number of files to process in a batch
            'retry_attempts': 3,
            'retry_delay': 5,  # seconds
            'upload_timeout': 300,  # 5 minutes per upload
        }
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ckan_upload.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _initialize_connection(self):
        """Initialize CKAN connection and verify organization access"""
        try:
            # Test connection
            site_info = self.ckan.action.status_show()
            self.logger.info(f"Connected to CKAN instance: {site_info.get('site_title', 'Unknown')}")
            
            # Get organization info
            try:
                self.org_info = self.ckan.action.organization_show(id=self.org_id)
                self.logger.info(f"Organization: {self.org_info['title']} ({self.org_info['name']})")
            except NotFound:
                self.logger.warning(f"Organization '{self.org_id}' not found. Datasets will be created without organization.")
                self.org_info = None
                
        except Exception as e:
            raise ConnectionError(f"Failed to connect to CKAN: {str(e)}")
    
    def create_dataset_metadata(self, validation_report: FileValidationReport) -> Dict[str, Any]:
        """Create dataset metadata based on validation report"""
        city_name = validation_report.city_name.replace('_', ' ').title()
        pilot_num = validation_report.pilot_number
        
        # Generate dataset name (must be URL-safe)
        dataset_name = f"{self.config['dataset_prefix']}-{pilot_num}-{validation_report.city_name.lower()}"
        dataset_title = f"REALLOCATE Pilot {pilot_num} - {city_name} Living Lab Data"
        
        # Create comprehensive description
        description = f"""
Geographic data for REALLOCATE Pilot {pilot_num} in {city_name}.

**Validation Summary:**
- Total Features: {len(gpd.read_file(Path('data') / validation_report.filename)) if Path('data', validation_report.filename).exists() else 'N/A'}
- Validation Status: {validation_report.overall_status}
- Tests Passed: {validation_report.passed_tests}/{validation_report.total_tests}
- File Size: {validation_report.file_size / 1024:.1f} KB
- Processing Time: {validation_report.processing_time:.2f} seconds

**Geographic Coverage:** {city_name}
**Data Format:** GeoJSON with WGS84 coordinate system
**Validation Date:** {validation_report.timestamp}

This dataset contains geospatial data for the REALLOCATE project's living lab activities in {city_name}. The data has been validated for geographic accuracy, data quality, and compliance with project standards.
        """.strip()
        
        # Create tags
        tags = [
            {'name': 'reallocate'},
            {'name': f'pilot-{pilot_num}'},
            {'name': city_name.lower().replace(' ', '-')},
            {'name': 'geojson'},
            {'name': 'geospatial'},
            {'name': 'living-labs'},
            {'name': 'urban-mobility'},
            {'name': 'transportation'}
        ]
        
        # Create extras (additional metadata)
        extras = [
            {'key': 'pilot_number', 'value': pilot_num},
            {'key': 'city_name', 'value': city_name},
            {'key': 'validation_status', 'value': validation_report.overall_status},
            {'key': 'validation_success_rate', 'value': f"{validation_report.success_rate*100:.1f}%"},
            {'key': 'original_filename', 'value': validation_report.filename},
            {'key': 'coordinate_system', 'value': 'EPSG:4326'},
            {'key': 'data_type', 'value': 'geospatial'},
            {'key': 'project', 'value': 'REALLOCATE'},
            {'key': 'upload_date', 'value': datetime.now().isoformat()},
        ]
        
        metadata = {
            'name': dataset_name,
            'title': dataset_title,
            'notes': description,
            'tags': tags,
            'extras': extras,
            'private': self.config['private_datasets'],
            'license_id': 'cc-by',  # Creative Commons Attribution
            'url': 'https://reallocate-project.eu',
            'author': 'REALLOCATE Project',
            'author_email': 'info@reallocate-project.eu',
            'maintainer': 'REALLOCATE Data Team',
            'version': '1.0',
            'state': 'active'
        }
        
        # Add organization if available
        if self.org_info:
            metadata['owner_org'] = self.org_info['id']
        
        return metadata
    
    def get_or_create_dataset(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Get existing dataset or create new one"""
        dataset_name = metadata['name']
        
        try:
            # Try to get existing dataset
            dataset = self.ckan.action.package_show(id=dataset_name)
            self.logger.info(f"Dataset '{dataset_name}' already exists")
            
            # Update metadata if needed
            if self.config.get('update_metadata', True):
                updated_metadata = metadata.copy()
                updated_metadata['id'] = dataset['id']
                
                # Preserve some existing fields
                if 'resources' in dataset:
                    updated_metadata['resources'] = dataset['resources']
                
                dataset = self.ckan.action.package_update(**updated_metadata)
                self.logger.info(f"Updated metadata for dataset '{dataset_name}'")
            
            return dataset
            
        except NotFound:
            # Create new dataset
            self.logger.info(f"Creating new dataset '{dataset_name}'")
            dataset = self.ckan.action.package_create(**metadata)
            self.logger.info(f"Created dataset '{dataset_name}' with ID: {dataset['id']}")
            return dataset
    
    def convert_geojson_to_csv(self, file_path: Path) -> Optional[StringIO]:
        """Convert GeoJSON to CSV format for easier data access"""
        try:
            gdf = gpd.read_file(file_path)
            
            # Add coordinate columns
            gdf['longitude'] = gdf.geometry.centroid.x
            gdf['latitude'] = gdf.geometry.centroid.y
            
            # Add geometry info
            gdf['geometry_type'] = gdf.geometry.geom_type
            gdf['area'] = gdf.geometry.area
            
            # Optimize bounds calculation - avoid dict conversion
            bounds_df = gdf.bounds
            gdf['min_x'] = bounds_df['minx']
            gdf['min_y'] = bounds_df['miny']
            gdf['max_x'] = bounds_df['maxx']
            gdf['max_y'] = bounds_df['maxy']
            
            # Convert to regular DataFrame (remove geometry column for CSV)
            df = pd.DataFrame(gdf.drop('geometry', axis=1))
            
            # Create CSV string
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            
            return csv_buffer
            
        except Exception as e:
            self.logger.error(f"Failed to convert {file_path} to CSV: {e}")
            return None
    
    def upload_resource(self, dataset_id: str, file_path: Path, resource_format: str) -> Optional[Dict[str, Any]]:
        """Upload a single resource to CKAN dataset"""
        filename = file_path.name
        
        try:
            # Check if resource already exists
            dataset = self.ckan.action.package_show(id=dataset_id)
            existing_resource = None
            
            resource_name = f"{filename.replace('.geojson', '')} ({resource_format})"
            
            for resource in dataset.get('resources', []):
                if resource['name'] == resource_name:
                    existing_resource = resource
                    break
            
            # Prepare upload data
            if resource_format == 'GeoJSON':
                # Upload original GeoJSON file
                with open(file_path, 'rb') as f:
                    upload_data = {
                        'name': resource_name,
                        'description': f'Original GeoJSON data for {filename}',
                        'format': 'GeoJSON',
                        'mimetype': 'application/geo+json',
                        'upload': f
                    }
                    
                    if existing_resource:
                        upload_data['id'] = existing_resource['id']
                        resource = self.ckan.action.resource_update(**upload_data)
                        self.logger.info(f"Updated GeoJSON resource: {resource['id']}")
                    else:
                        upload_data['package_id'] = dataset_id
                        resource = self.ckan.action.resource_create(**upload_data)
                        self.logger.info(f"Created GeoJSON resource: {resource['id']}")
                    
                    return resource
                    
            elif resource_format == 'CSV':
                # Convert and upload CSV
                csv_buffer = self.convert_geojson_to_csv(file_path)
                if csv_buffer is None:
                    return None
                
                upload_data = {
                    'name': resource_name,
                    'description': f'CSV conversion of {filename} with coordinate data',
                    'format': 'CSV',
                    'mimetype': 'text/csv',
                    'upload': csv_buffer
                }
                
                if existing_resource:
                    upload_data['id'] = existing_resource['id']
                    resource = self.ckan.action.resource_update(**upload_data)
                    self.logger.info(f"Updated CSV resource: {resource['id']}")
                else:
                    upload_data['package_id'] = dataset_id
                    resource = self.ckan.action.resource_create(**upload_data)
                    self.logger.info(f"Created CSV resource: {resource['id']}")
                
                return resource
                
        except Exception as e:
            self.logger.error(f"Failed to upload {resource_format} resource for {filename}: {e}")
            return None
    
    def upload_validated_file(self, file_path: Path, validation_report: FileValidationReport) -> UploadResult:
        """Upload a single validated GeoJSON file to CKAN"""
        start_time = time.time()
        filename = file_path.name
        
        self.logger.info(f"Uploading {filename} to CKAN...")
        
        try:
            # Create dataset metadata
            metadata = self.create_dataset_metadata(validation_report)
            
            # Get or create dataset
            dataset = self.get_or_create_dataset(metadata)
            dataset_id = dataset['id']
            
            # Upload resources in different formats
            uploaded_resources = []
            for fmt in self.config['resource_formats']:
                resource = self.upload_resource(dataset_id, file_path, fmt)
                if resource:
                    uploaded_resources.append(resource)
            
            upload_time = time.time() - start_time
            
            if uploaded_resources:
                return UploadResult(
                    filename=filename,
                    dataset_id=dataset_id,
                    resource_id=uploaded_resources[0]['id'],  # Primary resource ID
                    success=True,
                    message=f"Successfully uploaded {len(uploaded_resources)} resources",
                    upload_time=upload_time,
                    timestamp=datetime.now().isoformat(),
                    metadata={'dataset_url': f"{self.ckan_url}/dataset/{dataset['name']}",
                             'resources': [{'id': r['id'], 'format': r['format']} for r in uploaded_resources]}
                )
            else:
                return UploadResult(
                    filename=filename,
                    dataset_id=dataset_id,
                    resource_id=None,
                    success=False,
                    message="Failed to upload any resources",
                    upload_time=upload_time,
                    timestamp=datetime.now().isoformat()
                )
                
        except Exception as e:
            upload_time = time.time() - start_time
            error_msg = f"Upload failed: {str(e)}"
            self.logger.error(f"Failed to upload {filename}: {error_msg}")
            
            return UploadResult(
                filename=filename,
                dataset_id=None,
                resource_id=None,
                success=False,
                message=error_msg,
                upload_time=upload_time,
                timestamp=datetime.now().isoformat()
            )
    
    def upload_validated_files(self, data_dir: Path, validation_reports: List[FileValidationReport], 
                              only_passed: bool = True) -> UploadSummary:
        """Upload multiple validated files to CKAN"""
        start_time = time.time()
        
        # Filter reports based on validation status
        if only_passed:
            valid_reports = [r for r in validation_reports if r.overall_status == "PASS"]
            self.logger.info(f"Uploading only files that passed validation: {len(valid_reports)}/{len(validation_reports)}")
        else:
            valid_reports = validation_reports
            self.logger.info(f"Uploading all files (including failed validation): {len(valid_reports)}")
        
        upload_results = []
        
        for report in valid_reports:
            file_path = data_dir / report.filename
            
            if not file_path.exists():
                self.logger.error(f"File not found: {file_path}")
                upload_results.append(UploadResult(
                    filename=report.filename,
                    dataset_id=None,
                    resource_id=None,
                    success=False,
                    message="File not found",
                    upload_time=0.0,
                    timestamp=datetime.now().isoformat()
                ))
                continue
            
            # Upload file
            result = self.upload_validated_file(file_path, report)
            upload_results.append(result)
            
            # Add delay between uploads to be nice to the server
            time.sleep(1)
        
        total_upload_time = time.time() - start_time
        successful_uploads = sum(1 for r in upload_results if r.success)
        failed_uploads = len(upload_results) - successful_uploads
        
        summary = UploadSummary(
            total_files=len(upload_results),
            successful_uploads=successful_uploads,
            failed_uploads=failed_uploads,
            total_upload_time=total_upload_time,
            upload_results=upload_results,
            timestamp=datetime.now().isoformat()
        )
        
        self.logger.info(f"Upload complete: {successful_uploads}/{len(upload_results)} successful "
                        f"({summary.success_rate*100:.1f}% success rate)")
        
        return summary
    
    def generate_upload_report(self, upload_summary: UploadSummary, output_path: Path = None) -> str:
        """Generate comprehensive upload report"""
        if output_path is None:
            output_path = Path("ckan_upload_report.md")
        
        # Generate markdown report
        report_content = f"""# CKAN Upload Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**CKAN Instance:** {self.ckan_url}
**Organization:** {self.org_info['title'] if self.org_info else 'None'}
**Total Files:** {upload_summary.total_files}
**Successful Uploads:** {upload_summary.successful_uploads}
**Failed Uploads:** {upload_summary.failed_uploads}
**Success Rate:** {upload_summary.success_rate*100:.1f}%
**Total Upload Time:** {upload_summary.total_upload_time:.2f} seconds

## Upload Results

| File | Status | Dataset ID | Upload Time | Message |
|------|--------|------------|-------------|---------|
"""
        
        for result in upload_summary.upload_results:
            status_icon = "✅" if result.success else "❌"
            
            # Create dataset link if available
            if result.dataset_id and result.metadata and 'dataset_url' in result.metadata:
                dataset_link = f"[{result.dataset_id[:8]}...]({result.metadata['dataset_url']})"
            else:
                dataset_link = result.dataset_id or "N/A"
            
            report_content += f"| {result.filename} | {status_icon} | {dataset_link} | {result.upload_time:.2f}s | {result.message} |\n"
        
        # Add successful uploads details
        successful_results = [r for r in upload_summary.upload_results if r.success]
        if successful_results:
            report_content += "\n## Successful Uploads\n\n"
            for result in successful_results:
                if result.metadata and 'dataset_url' in result.metadata:
                    report_content += f"- **{result.filename}**\n"
                    report_content += f"  - Dataset: [{result.dataset_id}]({result.metadata['dataset_url']})\n"
                    report_content += f"  - Resources: {len(result.metadata.get('resources', []))}\n"
                    for resource in result.metadata.get('resources', []):
                        report_content += f"    - {resource['format']}: `{resource['id']}`\n"
                    report_content += "\n"
        
        # Add failed uploads details
        failed_results = [r for r in upload_summary.upload_results if not r.success]
        if failed_results:
            report_content += "\n## Failed Uploads\n\n"
            for result in failed_results:
                report_content += f"- **{result.filename}**: {result.message}\n"
        
        # Configuration summary
        report_content += f"\n## Configuration\n\n"
        report_content += f"- **Resource Formats:** {', '.join(self.config['resource_formats'])}\n"
        report_content += f"- **Private Datasets:** {self.config['private_datasets']}\n"
        report_content += f"- **Auto Create Datasets:** {self.config['auto_create_datasets']}\n"
        report_content += f"- **Overwrite Resources:** {self.config['overwrite_resources']}\n"
        
        # Write report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        self.logger.info(f"Upload report written to {output_path}")
        return str(output_path)


if __name__ == "__main__":
    # Example usage - would typically be called from main workflow script
    from geojson_validator import GeoJSONValidator
    
    # Load environment variables
    load_dotenv()
    
    # Initialize components
    validator = GeoJSONValidator()
    uploader = CKANUploader()
    
    data_directory = Path("data")
    
    print("Running validation...")
    validation_reports = validator.validate_all_files(data_directory)
    
    print("Generating validation report...")
    validation_report_file = validator.generate_validation_report(validation_reports)
    
    print("Uploading validated files to CKAN...")
    upload_summary = uploader.upload_validated_files(data_directory, validation_reports, only_passed=True)
    
    print("Generating upload report...")
    upload_report_file = uploader.generate_upload_report(upload_summary)
    
    print(f"\n{'='*60}")
    print("WORKFLOW COMPLETE")
    print(f"{'='*60}")
    print(f"Validation report: {validation_report_file}")
    print(f"Upload report: {upload_report_file}")
    print(f"Files processed: {len(validation_reports)}")
    print(f"Files uploaded: {upload_summary.successful_uploads}/{upload_summary.total_files}")
    print(f"Upload success rate: {upload_summary.success_rate*100:.1f}%")
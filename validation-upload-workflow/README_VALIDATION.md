# GeoJSON Validation and CKAN Upload Workflow

## Overview

This comprehensive workflow system validates European living labs GeoJSON data and uploads it to a CKAN database. The system performs thorough validation checks including geographic boundary validation, data quality assessment, and format compliance before uploading to CKAN with appropriate metadata.

## Features

### Validation Capabilities
- **Geographic Boundary Validation**: Verifies coordinates fall within specified city boundaries using OpenStreetMap Nominatim API
- **GeoJSON Structure Validation**: Checks JSON validity and GeoJSON format compliance
- **Data Quality Checks**: Validates geometry validity, coordinate precision, and European bounds
- **File System Validation**: Checks file existence, size limits, and naming conventions
- **Comprehensive Reporting**: Generates detailed validation reports with pass/fail statistics

### CKAN Integration
- **Automated Dataset Creation**: Creates or updates CKAN datasets with rich metadata
- **Multi-format Upload**: Uploads files as both GeoJSON and CSV formats
- **Resource Management**: Handles resource creation, updates, and versioning
- **Error Handling**: Robust error handling with retry mechanisms
- **Upload Reporting**: Detailed upload logs and summary reports

## Installation

### 1. Install Dependencies

```bash
# Install required packages
pip install -r requirements_validation.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.template .env

# Edit .env with your CKAN credentials
nano .env
```

### 3. Environment Variables

Set the following in your `.env` file:

```env
CKAN_URL=https://reallocate-ckan.iti.gr
REALLOCATE_KEY=your_ckan_api_key_here
CKAN_ORG_ID=ORG_ID_HERE
```

## Usage

### Quick Start

Run the complete workflow (validation + upload):

```bash
python main_workflow.py
```

### Command Line Options

```bash
# Run validation only (skip upload)
python main_workflow.py --validation-only

# Use custom data directory
python main_workflow.py --data-dir /path/to/data

# Use custom configuration
python main_workflow.py --config my_config.json

# Dry run (validation + upload plan, no actual upload)
python main_workflow.py --dry-run

# Verbose logging
python main_workflow.py --verbose
```

### Configuration

The system uses a JSON configuration file. Copy and modify `config_template.json`:

```bash
cp config_template.json config.json
# Edit config.json as needed
python main_workflow.py --config config.json
```

#### Configuration Sections

**Validation Settings:**
```json
{
  "validation": {
    "coordinate_precision_digits": 6,
    "max_file_size_mb": 100,
    "european_bounds": {
      "min_lon": -31.0, "max_lon": 45.0,
      "min_lat": 34.0, "max_lat": 72.0
    }
  }
}
```

**Upload Settings:**
```json
{
  "upload": {
    "organization_id": "ORGANIZATION",
    "dataset_prefix": "reallocate-pilot",
    "resource_formats": ["GeoJSON", "CSV"],
    "only_upload_passed": true
  }
}
```

## File Requirements

### Input Files
- **Location**: `./data/` directory
- **Format**: GeoJSON files
- **Naming Convention**: `pilot[X]_[cityname].geojson`
  - Examples: `pilot1_barcelona.geojson`, `pilot2_utrecht.geojson`
- **Content**: Valid GeoJSON with WGS84 coordinates (EPSG:4326)

### Validation Tests

#### Geographic Validation
- **Primary Test**: Coordinates within city boundaries
- **Implementation**: Uses OpenStreetMap Nominatim API
- **Tolerance**: Features must intersect with city boundary

#### Structure Validation
- Valid JSON syntax
- GeoJSON format compliance
- Required fields: `type`, `features`, `geometry`, `coordinates`
- Coordinate Reference System: WGS84 (EPSG:4326)

#### Quality Validation
- **Coordinate Precision**: Reasonable decimal places (3-12 digits)
- **Geometry Validity**: No self-intersections or malformed shapes  
- **European Bounds**: Coordinates within European geographic range
- **Feature Count**: Between 1-10,000 features per file
- **File Size**: Maximum 100MB per file

## Output Files

### Reports
- **`validation_report.md`**: Detailed validation results for all files
- **`ckan_upload_report.md`**: Upload results and CKAN dataset links  
- **`workflow_summary.json`**: Machine-readable workflow summary
- **`workflow.log`**: Detailed execution logs

### Logs
- **`geojson_validation.log`**: Validation-specific logs
- **`ckan_upload.log`**: Upload-specific logs

## API Reference

### GeoJSONValidator Class

```python
from geojson_validator import GeoJSONValidator

validator = GeoJSONValidator(config)
reports = validator.validate_all_files(data_directory)
```

**Key Methods:**
- `validate_file(file_path)`: Validate single file
- `validate_all_files(directory)`: Validate all GeoJSON files
- `generate_validation_report(reports)`: Create markdown report

### CKANUploader Class

```python
from ckan_uploader import CKANUploader

uploader = CKANUploader(config)
summary = uploader.upload_validated_files(directory, reports)
```

**Key Methods:**
- `upload_validated_file(file_path, report)`: Upload single file
- `upload_validated_files(directory, reports)`: Upload multiple files
- `generate_upload_report(summary)`: Create upload report

### WorkflowOrchestrator Class

```python
from main_workflow import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator(config_path)
result = orchestrator.run_complete_workflow(data_dir)
```

## Error Handling

### Common Issues

**1. Geographic Validation Failures**
- **Cause**: Coordinates outside city boundaries
- **Solution**: Verify coordinate accuracy and city name spelling
- **Check**: Use validation report details for specific coordinate issues

**2. CKAN Connection Errors**
- **Cause**: Invalid API key or network issues
- **Solution**: Verify `REALLOCATE_KEY` in `.env` file
- **Check**: Test connection with `ckan.action.status_show()`

**3. File Format Issues**
- **Cause**: Invalid GeoJSON structure
- **Solution**: Validate JSON syntax and GeoJSON compliance
- **Check**: Use validation report for specific format errors

**4. Permission Errors**
- **Cause**: Insufficient CKAN permissions
- **Solution**: Verify organization membership and API key permissions
- **Check**: Contact CKAN administrator

### Troubleshooting

1. **Enable Verbose Logging**
   ```bash
   python main_workflow.py --verbose
   ```

2. **Check Log Files**
   ```bash
   tail -f workflow.log
   tail -f geojson_validation.log
   tail -f ckan_upload.log
   ```

3. **Run Validation Only**
   ```bash
   python main_workflow.py --validation-only
   ```

4. **Test Individual Components**
   ```python
   # Test validation
   python geojson_validator.py
   
   # Test upload (after setting environment)
   python ckan_uploader.py
   ```

## Best Practices

### Data Preparation
1. **Coordinate System**: Ensure all data uses WGS84 (EPSG:4326)
2. **File Naming**: Follow `pilot[X]_[city].geojson` convention
3. **File Size**: Keep files under 100MB for optimal performance
4. **Geometry**: Validate geometries are topologically correct

### Workflow Execution
1. **Test First**: Run with `--validation-only` before uploading
2. **Backup Data**: Keep original files backed up
3. **Check Reports**: Review validation reports before proceeding
4. **Monitor Logs**: Watch log files during execution

### CKAN Management
1. **API Keys**: Keep API keys secure and rotate regularly
2. **Organizations**: Ensure proper organization membership
3. **Resources**: Use meaningful names and descriptions
4. **Metadata**: Include comprehensive dataset metadata

## Security Considerations

- **API Keys**: Never commit API keys to version control
- **Environment Files**: Keep `.env` files private
- **Network**: Use HTTPS for all CKAN communications
- **Access Control**: Follow principle of least privilege for CKAN permissions

## Performance

### Optimization Tips
1. **Batch Processing**: Process files in configurable batches
2. **Caching**: Geographic boundary data is cached for performance
3. **Parallel Processing**: Validation tests run independently
4. **Rate Limiting**: Built-in delays prevent API overload

### Scaling
- **Large Datasets**: Configure batch sizes and timeouts
- **Network Issues**: Adjust retry attempts and delays  
- **Memory Usage**: Process files individually to minimize memory footprint

## Contributing

### Code Structure
- `geojson_validator.py`: Core validation logic
- `ckan_uploader.py`: CKAN integration and upload handling
- `main_workflow.py`: Workflow orchestration and CLI interface

### Testing
```bash
# Run validation tests
python -m pytest tests/test_validation.py

# Run upload tests (requires test CKAN instance)
python -m pytest tests/test_upload.py
```

### Adding Validation Tests
1. Extend `GeoJSONValidator.validate_geodataframe()`
2. Add test to validation pipeline
3. Update documentation and configuration options

## Support

### Getting Help
- **Issues**: Report bugs and feature requests on project repository
- **Documentation**: Check this README and inline code documentation
- **Logs**: Review log files for detailed error information

### Contact Information
- **Project**: REALLOCATE European Project
- **Documentation**: See `/docs` folder for additional resources
- **Technical Support**: Contact project technical team

## License

This validation and upload system is part of the REALLOCATE project. See project license for usage terms.

## Changelog

### Version 1.0.0
- Initial release with complete validation and upload workflow
- Geographic boundary validation using OpenStreetMap API
- CKAN integration with metadata generation
- Comprehensive reporting system
- Command-line interface with multiple operation modes
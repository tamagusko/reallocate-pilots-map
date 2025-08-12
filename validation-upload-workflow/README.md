# GeoJSON Validation and CKAN Upload Workflow

This folder contains a complete workflow system for validating European living labs GeoJSON data and uploading it to CKAN databases.

## Quick Start

### 1. Install Dependencies
```bash
cd validation-upload-workflow
pip install -r requirements_validation.txt
```

### 2. Configure Environment
```bash
# Copy and edit environment template
cp .env.template .env
# Edit .env with your CKAN credentials
```

### 3. Run Validation
```bash
# Test validation only (recommended first step)
python main_workflow.py --validation-only --data-dir ../data

# Run complete workflow (validation + upload)
python main_workflow.py --data-dir ../data
```

## Files Overview

### Core Scripts
- **`main_workflow.py`** - Main orchestration script with CLI interface
- **`geojson_validator.py`** - Comprehensive GeoJSON validation engine
- **`ckan_uploader.py`** - CKAN integration and upload handling

### Configuration
- **`config_template.json`** - Configuration template (copy to `config.json`)
- **`.env.template`** - Environment variables template (copy to `.env`)
- **`requirements_validation.txt`** - Python dependencies

### Documentation
- **`README_VALIDATION.md`** - Comprehensive documentation
- **`TROUBLESHOOTING.md`** - Troubleshooting guide and common issues

## Key Features

### Validation Capabilities
✅ **Geographic Boundary Validation** - Verifies coordinates within city limits  
✅ **GeoJSON Structure Validation** - Checks format compliance  
✅ **Data Quality Assessment** - Validates geometries and coordinates  
✅ **European Bounds Checking** - Ensures coordinates are within Europe  
✅ **File System Validation** - Checks naming conventions and file sizes  

### CKAN Integration
🔄 **Automated Dataset Creation** - Creates datasets with rich metadata  
📁 **Multi-format Upload** - Uploads as GeoJSON and CSV  
🔐 **Secure Authentication** - Uses API keys and environment variables  
📊 **Comprehensive Reporting** - Detailed upload logs and summaries  

## Usage Examples

```bash
# Basic validation
python main_workflow.py --validation-only --data-dir ../data

# Custom configuration
python main_workflow.py --config my_config.json --data-dir ../data

# Dry run (no actual upload)
python main_workflow.py --dry-run --data-dir ../data

# Verbose logging
python main_workflow.py --verbose --data-dir ../data
```

## Input Data Requirements

- **Location**: `../data/` folder (or specify with `--data-dir`)
- **Format**: GeoJSON files
- **Naming**: `pilot[X]_[cityname].geojson` (e.g., `pilot1_barcelona.geojson`)
- **Coordinate System**: WGS84 (EPSG:4326)

## Output Reports

After running, check these generated files:
- `validation_report.md` - Detailed validation results
- `ckan_upload_report.md` - Upload results and dataset links
- `workflow_summary.json` - Machine-readable summary
- `workflow.log` - Detailed execution logs

## Configuration

Copy `config_template.json` to `config.json` and adjust settings:

```json
{
  "validation": {
    "max_file_size_mb": 100,
    "european_bounds": {"min_lon": -31.0, "max_lon": 45.0}
  },
  "upload": {
    "organization_id": "ORGANIZATION_ID",
    "only_upload_passed": true,
    "private_datasets": true
  }
}
```

## Environment Setup

Copy `.env.template` to `.env` and add your credentials:

```env
CKAN_URL=https://reallocate-ckan.iti.gr
REALLOCATE_KEY=your_api_key_here
CKAN_ORG_ID=ORGANIZATION_ID
```

> ⚠️ **Security Note**: The `.env` file is automatically ignored by Git and will not be uploaded to GitHub, keeping your API keys secure.

## Need Help?

- 📖 **Detailed docs**: See `README_VALIDATION.md`
- 🔧 **Having issues?**: Check `TROUBLESHOOTING.md`
- 🐛 **Found a bug?**: Check logs in `*.log` files

## Project Structure

```
validation-upload-workflow/
├── README.md                    # This file - quick start guide
├── README_VALIDATION.md         # Comprehensive documentation
├── TROUBLESHOOTING.md          # Troubleshooting guide
├── main_workflow.py            # Main orchestration script
├── geojson_validator.py        # Validation engine
├── ckan_uploader.py           # CKAN integration
├── config_template.json       # Configuration template
├── .env.template              # Environment template
├── requirements_validation.txt # Python dependencies
└── [Generated files]
    ├── validation_report.md    # Validation results
    ├── ckan_upload_report.md  # Upload results
    ├── workflow_summary.json  # JSON summary
    └── *.log                  # Log files
```
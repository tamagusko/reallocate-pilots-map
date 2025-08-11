# Troubleshooting Guide

## Common Issues and Solutions

### 1. Geographic Boundary Validation Failures

#### Issue: "Coordinates fall outside city boundary"
**Symptoms:**
- Validation reports show geographic_boundary_check failures
- Files marked as FAIL status despite correct GeoJSON format

**Possible Causes:**
1. **Incorrect city name in filename**: The city name extraction from filename doesn't match OpenStreetMap data
2. **Coordinate system mismatch**: Data might be in wrong projection
3. **City boundary API issues**: OpenStreetMap Nominatim API unavailable or incorrect response

**Solutions:**

**A. Verify City Name Mapping**
```python
# Test city name extraction
from geojson_validator import GeoJSONValidator
validator = GeoJSONValidator()
city, pilot = validator.extract_city_and_pilot("pilot1_barcelona.geojson")
print(f"Extracted: city='{city}', pilot='{pilot}'")
```

**B. Test Boundary API Manually**
```python
from geojson_validator import CityBoundaryValidator
boundary_validator = CityBoundaryValidator()
boundary = boundary_validator.get_city_boundary("Barcelona")
print("Boundary data available:", boundary is not None)
```

**C. Check Coordinate System**
```python
import geopandas as gpd
gdf = gpd.read_file("data/pilot1_barcelona.geojson")
print("CRS:", gdf.crs)
print("Bounds:", gdf.total_bounds)
```

**D. Manual City Name Override**
If automatic extraction fails, modify the validator:
```python
# In geojson_validator.py, update extract_city_and_pilot method
def extract_city_and_pilot(self, filename: str) -> Tuple[str, str]:
    # Add manual mapping for problematic files
    manual_mapping = {
        "pilot2_ gothenburg.geojson": ("gothenburg", "2"),
        # Add other problematic files
    }
    if filename in manual_mapping:
        return manual_mapping[filename]
    # ... rest of method
```

#### Issue: "Could not retrieve boundary data for city"
**Symptoms:**
- API connection failures
- Empty boundary responses

**Solutions:**

**A. Check Internet Connection**
```bash
curl -s "https://nominatim.openstreetmap.org/search?q=Barcelona&format=json&limit=1"
```

**B. Increase API Timeout**
```python
# In geojson_validator.py, CityBoundaryValidator.__init__
def __init__(self, cache_timeout: int = 3600, api_timeout: int = 60):
    # Increase timeout from 30 to 60 seconds
```

**C. Use Alternative City Names**
```python
# Try different city name variations
alternative_names = {
    "barcelona": ["Barcelona, Spain", "Barcelona, Catalonia", "Barcelona"],
    "gothenburg": ["Gothenburg, Sweden", "Göteborg", "Goteborg"],
    # Add other alternatives
}
```

### 2. CKAN Connection and Upload Issues

#### Issue: "Failed to connect to CKAN"
**Symptoms:**
- ConnectionError during upload
- Authentication failures
- Network timeouts

**Solutions:**

**A. Verify Environment Variables**
```bash
# Check .env file exists and has correct values
cat .env | grep -v "^#" | grep -v "^$"

# Test environment loading
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('CKAN_URL:', os.getenv('CKAN_URL'))
print('API_KEY exists:', bool(os.getenv('REALLOCATE_KEY')))
"
```

**B. Test CKAN Connection Manually**
```python
from ckanapi import RemoteCKAN
import os
from dotenv import load_dotenv

load_dotenv()
ckan = RemoteCKAN(os.getenv('CKAN_URL'), apikey=os.getenv('REALLOCATE_KEY'))

# Test connection
try:
    status = ckan.action.status_show()
    print("Connection successful:", status.get('site_title', 'Unknown'))
except Exception as e:
    print("Connection failed:", str(e))
```

**C. Check API Key Permissions**
```python
# Test API key validity
try:
    user_info = ckan.action.user_show(id='me')  # Get current user info
    print("User:", user_info.get('name'))
    print("Organizations:", [org['name'] for org in user_info.get('organizations', [])])
except Exception as e:
    print("API key issue:", str(e))
```

#### Issue: "Organization not found" or Permission Denied
**Symptoms:**
- NotFound errors for organization
- Permission denied when creating datasets

**Solutions:**

**A. Check Organization Membership**
```python
try:
    org_info = ckan.action.organization_show(id='bsc')
    print("Organization exists:", org_info['name'])
    
    # Check if user is member
    user_orgs = ckan.action.organization_list_for_user(id='me')
    print("User organizations:", [org['name'] for org in user_orgs])
    
except Exception as e:
    print("Organization issue:", str(e))
```

**B. Create Datasets Without Organization**
```python
# In ckan_uploader.py, modify create_dataset_metadata
def create_dataset_metadata(self, validation_report):
    metadata = {
        # ... other fields
        # 'owner_org': self.org_info['id'],  # Comment out this line
    }
    return metadata
```

#### Issue: "Resource upload failed" or File Upload Errors
**Symptoms:**
- Resources created but files not uploaded
- Upload timeouts
- File format errors

**Solutions:**

**A. Check File Sizes and Formats**
```python
import os
for file_path in Path("data").glob("*.geojson"):
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"{file_path.name}: {size_mb:.2f} MB")
```

**B. Test Resource Upload Manually**
```python
# Simple resource upload test
with open("data/pilot1_barcelona.geojson", "rb") as f:
    resource = ckan.action.resource_create(
        package_id="test-dataset-id",
        name="Test Upload",
        format="GeoJSON",
        upload=f
    )
print("Upload successful:", resource['id'])
```

**C. Increase Upload Timeouts**
```json
// In config.json
{
  "upload": {
    "upload_timeout": 600,  // Increase from 300 to 600 seconds
    "retry_attempts": 5,    // Increase retry attempts
    "retry_delay": 10       // Increase delay between retries
  }
}
```

### 3. File Format and Structure Issues

#### Issue: "Invalid JSON" or GeoJSON Structure Errors
**Symptoms:**
- JSON parsing errors
- Missing required GeoJSON fields
- Geometry validation failures

**Solutions:**

**A. Validate JSON Syntax**
```bash
# Use Python to check JSON validity
python -c "
import json
with open('data/pilot1_barcelona.geojson') as f:
    try:
        data = json.load(f)
        print('Valid JSON')
    except json.JSONDecodeError as e:
        print('Invalid JSON:', str(e))
"
```

**B. Check GeoJSON Structure**
```python
import json
import geopandas as gpd

# Load and inspect structure
with open('data/pilot1_barcelona.geojson') as f:
    data = json.load(f)

print("Type:", data.get('type'))
print("Features count:", len(data.get('features', [])))

# Check with GeoPandas
try:
    gdf = gpd.read_file('data/pilot1_barcelona.geojson')
    print("GeoPandas load: OK")
    print("CRS:", gdf.crs)
    print("Geometry types:", gdf.geometry.type.value_counts().to_dict())
except Exception as e:
    print("GeoPandas error:", str(e))
```

**C. Fix Common GeoJSON Issues**
```python
# Fix missing CRS
gdf = gpd.read_file('problematic_file.geojson')
gdf.crs = 'EPSG:4326'  # Set to WGS84
gdf.to_file('fixed_file.geojson', driver='GeoJSON')

# Fix invalid geometries
from shapely.validation import make_valid
gdf['geometry'] = gdf['geometry'].apply(make_valid)
```

### 4. Performance and Memory Issues

#### Issue: "Memory Error" or Very Slow Processing
**Symptoms:**
- Process crashes with memory errors
- Extremely slow validation
- System becomes unresponsive

**Solutions:**

**A. Process Files Individually**
```python
# Instead of validating all files at once
for file_path in geojson_files:
    report = validator.validate_file(file_path)
    # Process report immediately
    # Clear memory if needed
```

**B. Reduce Coordinate Precision Sampling**
```python
# In geojson_validator.py, reduce coordinate sampling
# Change from coords_list[:100] to coords_list[:10]
for coord in coords_list[:10]:  # Sample fewer coordinates
```

**C. Configure Batch Processing**
```json
{
  "upload": {
    "batch_size": 5  // Reduce from 10 to 5
  }
}
```

#### Issue: Network Timeouts and Rate Limiting
**Symptoms:**
- Frequent timeout errors
- API rate limiting responses
- Slow external API responses

**Solutions:**

**A. Increase Cache Timeout**
```python
# Increase boundary cache timeout to reduce API calls
boundary_validator = CityBoundaryValidator(cache_timeout=7200)  # 2 hours
```

**B. Add Delays Between API Calls**
```python
import time
# Add delay in validation loop
time.sleep(2)  # 2 second delay between validations
```

**C. Use Offline Boundary Data**
```python
# Create manual boundary definitions for common cities
CITY_BOUNDARIES = {
    'barcelona': {
        'bounds': [2.0523, 41.3200, 2.2280, 41.4695],
        'polygon': None  # Could include actual polygon
    }
}
```

### 5. Configuration and Environment Issues

#### Issue: "Configuration not loaded" or Default Settings Used
**Symptoms:**
- Custom configuration ignored
- Default values used instead of specified config
- Environment variables not loaded

**Solutions:**

**A. Verify Configuration File Path**
```bash
# Check if config file exists and is readable
ls -la config.json
python -c "
import json
with open('config.json') as f:
    config = json.load(f)
print('Config loaded successfully')
print('Keys:', list(config.keys()))
"
```

**B. Debug Configuration Loading**
```python
# Add debug prints to main_workflow.py
def _load_config(self, config_path):
    print(f"Loading config from: {config_path}")
    print(f"Config file exists: {config_path and config_path.exists()}")
    # ... rest of method
```

**C. Check Environment File Location**
```bash
# Ensure .env is in correct directory
pwd
ls -la .env
# .env should be in same directory as Python scripts
```

### 6. Debugging Commands

#### Quick Health Check
```bash
# Run validation only to test system
python main_workflow.py --validation-only --verbose

# Test specific file
python -c "
from geojson_validator import GeoJSONValidator
validator = GeoJSONValidator()
report = validator.validate_file(Path('data/pilot1_barcelona.geojson'))
print('Status:', report.overall_status)
print('Tests:', f'{report.passed_tests}/{report.total_tests}')
"
```

#### Check All Dependencies
```bash
# Verify all required packages are installed
python -c "
packages = ['geopandas', 'shapely', 'requests', 'ckanapi', 'pandas', 'numpy']
for pkg in packages:
    try:
        __import__(pkg)
        print(f'{pkg}: OK')
    except ImportError as e:
        print(f'{pkg}: MISSING - {e}')
"
```

#### Test Individual Components
```bash
# Test validation only
python geojson_validator.py

# Test CKAN upload only (with .env configured)
python ckan_uploader.py

# Test with dry run
python main_workflow.py --dry-run --verbose
```

### 7. Log Analysis

#### Reading Log Files
```bash
# View latest errors
grep -i error workflow.log | tail -20

# View validation results
grep -i "validation complete" geojson_validation.log

# View upload results  
grep -i "upload" ckan_upload.log | tail -10

# Monitor real-time logs
tail -f workflow.log
```

#### Understanding Log Levels
- **INFO**: Normal operational messages
- **WARNING**: Issues that don't stop execution
- **ERROR**: Problems that cause operation failures
- **DEBUG**: Detailed debugging information (use --verbose)

### 8. Getting Additional Help

#### Enable Maximum Debugging
```bash
python main_workflow.py --verbose --validation-only > debug_output.txt 2>&1
```

#### Create Minimal Test Case
```python
# Create simple test file
import json

minimal_geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[2.15, 41.38], [2.16, 41.38], [2.16, 41.39], [2.15, 41.39], [2.15, 41.38]]]
            }
        }
    ]
}

with open('test_pilot1_barcelona.geojson', 'w') as f:
    json.dump(minimal_geojson, f)

# Test with minimal file
python main_workflow.py --data-dir . --validation-only
```

If issues persist after trying these solutions, please:
1. Save the full error output and log files
2. Note the exact command used and configuration
3. Include information about your system (OS, Python version)
4. Contact the technical support team with this information
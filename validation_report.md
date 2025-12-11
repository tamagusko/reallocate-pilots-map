# GeoJSON Validation Report

**Generated:** 2025-12-11 23:28:19
**Total Files:** 9
**Passed:** 7
**Failed:** 2
**Success Rate:** 77.8%

## Summary by City and Pilot

| File | City | Pilot | Status | Tests Passed | File Size | Processing Time |
|------|------|-------|--------|--------------|-----------|----------------|
| pilot1_barcelona.geojson | barcelona | 1 | PASS | 16/16 | 1.8KB | 0.98s |
| pilot1_budapest.geojson | budapest | 1 | PASS | 16/16 | 0.7KB | 1.00s |
| pilot1_gothenburg.geojson | gothenburg | 1 | FAIL | 15/16 | 0.3KB | 0.84s |
| pilot1_heidelberg.geojson | heidelberg | 1 | PASS | 16/16 | 1.1KB | 1.07s |
| pilot1_utrecht.geojson | utrecht | 1 | PASS | 16/16 | 0.3KB | 1.05s |
| pilot1_warsaw.geojson | warsaw | 1 | PASS | 16/16 | 0.3KB | 0.91s |
| pilot2_budapest.geojson | budapest | 2 | PASS | 16/16 | 1.0KB | 0.01s |
| pilot2_gothenburg.geojson | gothenburg | 2 | FAIL | 15/16 | 0.6KB | 0.00s |
| pilot2_utrecht.geojson | utrecht | 2 | PASS | 16/16 | 0.7KB | 0.00s |

## Detailed Results

### pilot1_barcelona.geojson

- **City:** barcelona
- **Pilot:** 1
- **Status:** PASS
- **Success Rate:** 100.0%

**✅ Passed Tests:**
- `file_existence`: File exists
- `file_size`: File size OK: 1.8KB
- `filename_convention`: Filename follows convention
- `json_validity`: Valid JSON structure
- `geojson_type_field`: Required field present: type
- `geojson_features_field`: Required field present: features
- `geojson_type`: Correct GeoJSON type: FeatureCollection
- `features_array`: Features array with 4 items
- `features_structure`: Features have required structure
- `feature_count`: Feature count OK: 4
- `coordinate_system`: Correct CRS: EPSG:4326
- `null_geometries`: No null geometries
- `empty_geometries`: No empty geometries
- `geometry_validity`: All geometries are valid
- `european_bounds`: Coordinates within European bounds
- `geographic_boundary_check`: All 4 features intersect with barcelona boundary

---

### pilot1_budapest.geojson

- **City:** budapest
- **Pilot:** 1
- **Status:** PASS
- **Success Rate:** 100.0%

**✅ Passed Tests:**
- `file_existence`: File exists
- `file_size`: File size OK: 0.7KB
- `filename_convention`: Filename follows convention
- `json_validity`: Valid JSON structure
- `geojson_type_field`: Required field present: type
- `geojson_features_field`: Required field present: features
- `geojson_type`: Correct GeoJSON type: FeatureCollection
- `features_array`: Features array with 1 items
- `features_structure`: Features have required structure
- `feature_count`: Feature count OK: 1
- `coordinate_system`: Correct CRS: EPSG:4326
- `null_geometries`: No null geometries
- `empty_geometries`: No empty geometries
- `geometry_validity`: All geometries are valid
- `european_bounds`: Coordinates within European bounds
- `geographic_boundary_check`: All 1 features intersect with budapest boundary

---

### pilot1_gothenburg.geojson

- **City:** gothenburg
- **Pilot:** 1
- **Status:** FAIL
- **Success Rate:** 93.8%

**❌ Failed Tests:**
- `geographic_boundary_check`: 1 of 1 features fall outside gothenburg boundary

**✅ Passed Tests:**
- `file_existence`: File exists
- `file_size`: File size OK: 0.3KB
- `filename_convention`: Filename follows convention
- `json_validity`: Valid JSON structure
- `geojson_type_field`: Required field present: type
- `geojson_features_field`: Required field present: features
- `geojson_type`: Correct GeoJSON type: FeatureCollection
- `features_array`: Features array with 1 items
- `features_structure`: Features have required structure
- `feature_count`: Feature count OK: 1
- `coordinate_system`: Correct CRS: EPSG:4326
- `null_geometries`: No null geometries
- `empty_geometries`: No empty geometries
- `geometry_validity`: All geometries are valid
- `european_bounds`: Coordinates within European bounds

---

### pilot1_heidelberg.geojson

- **City:** heidelberg
- **Pilot:** 1
- **Status:** PASS
- **Success Rate:** 100.0%

**✅ Passed Tests:**
- `file_existence`: File exists
- `file_size`: File size OK: 1.1KB
- `filename_convention`: Filename follows convention
- `json_validity`: Valid JSON structure
- `geojson_type_field`: Required field present: type
- `geojson_features_field`: Required field present: features
- `geojson_type`: Correct GeoJSON type: FeatureCollection
- `features_array`: Features array with 3 items
- `features_structure`: Features have required structure
- `feature_count`: Feature count OK: 3
- `coordinate_system`: Correct CRS: EPSG:4326
- `null_geometries`: No null geometries
- `empty_geometries`: No empty geometries
- `geometry_validity`: All geometries are valid
- `european_bounds`: Coordinates within European bounds
- `geographic_boundary_check`: All 3 features intersect with heidelberg boundary

---

### pilot1_utrecht.geojson

- **City:** utrecht
- **Pilot:** 1
- **Status:** PASS
- **Success Rate:** 100.0%

**✅ Passed Tests:**
- `file_existence`: File exists
- `file_size`: File size OK: 0.3KB
- `filename_convention`: Filename follows convention
- `json_validity`: Valid JSON structure
- `geojson_type_field`: Required field present: type
- `geojson_features_field`: Required field present: features
- `geojson_type`: Correct GeoJSON type: FeatureCollection
- `features_array`: Features array with 1 items
- `features_structure`: Features have required structure
- `feature_count`: Feature count OK: 1
- `coordinate_system`: Correct CRS: EPSG:4326
- `null_geometries`: No null geometries
- `empty_geometries`: No empty geometries
- `geometry_validity`: All geometries are valid
- `european_bounds`: Coordinates within European bounds
- `geographic_boundary_check`: All 1 features intersect with utrecht boundary

---

### pilot1_warsaw.geojson

- **City:** warsaw
- **Pilot:** 1
- **Status:** PASS
- **Success Rate:** 100.0%

**✅ Passed Tests:**
- `file_existence`: File exists
- `file_size`: File size OK: 0.3KB
- `filename_convention`: Filename follows convention
- `json_validity`: Valid JSON structure
- `geojson_type_field`: Required field present: type
- `geojson_features_field`: Required field present: features
- `geojson_type`: Correct GeoJSON type: FeatureCollection
- `features_array`: Features array with 1 items
- `features_structure`: Features have required structure
- `feature_count`: Feature count OK: 1
- `coordinate_system`: Correct CRS: EPSG:4326
- `null_geometries`: No null geometries
- `empty_geometries`: No empty geometries
- `geometry_validity`: All geometries are valid
- `european_bounds`: Coordinates within European bounds
- `geographic_boundary_check`: All 1 features intersect with warsaw boundary

---

### pilot2_budapest.geojson

- **City:** budapest
- **Pilot:** 2
- **Status:** PASS
- **Success Rate:** 100.0%

**✅ Passed Tests:**
- `file_existence`: File exists
- `file_size`: File size OK: 1.0KB
- `filename_convention`: Filename follows convention
- `json_validity`: Valid JSON structure
- `geojson_type_field`: Required field present: type
- `geojson_features_field`: Required field present: features
- `geojson_type`: Correct GeoJSON type: FeatureCollection
- `features_array`: Features array with 1 items
- `features_structure`: Features have required structure
- `feature_count`: Feature count OK: 1
- `coordinate_system`: Correct CRS: EPSG:4326
- `null_geometries`: No null geometries
- `empty_geometries`: No empty geometries
- `geometry_validity`: All geometries are valid
- `european_bounds`: Coordinates within European bounds
- `geographic_boundary_check`: All 1 features intersect with budapest boundary

---

### pilot2_gothenburg.geojson

- **City:** gothenburg
- **Pilot:** 2
- **Status:** FAIL
- **Success Rate:** 93.8%

**❌ Failed Tests:**
- `geographic_boundary_check`: 1 of 1 features fall outside gothenburg boundary

**✅ Passed Tests:**
- `file_existence`: File exists
- `file_size`: File size OK: 0.6KB
- `filename_convention`: Filename follows convention
- `json_validity`: Valid JSON structure
- `geojson_type_field`: Required field present: type
- `geojson_features_field`: Required field present: features
- `geojson_type`: Correct GeoJSON type: FeatureCollection
- `features_array`: Features array with 1 items
- `features_structure`: Features have required structure
- `feature_count`: Feature count OK: 1
- `coordinate_system`: Correct CRS: EPSG:4326
- `null_geometries`: No null geometries
- `empty_geometries`: No empty geometries
- `geometry_validity`: All geometries are valid
- `european_bounds`: Coordinates within European bounds

---

### pilot2_utrecht.geojson

- **City:** utrecht
- **Pilot:** 2
- **Status:** PASS
- **Success Rate:** 100.0%

**✅ Passed Tests:**
- `file_existence`: File exists
- `file_size`: File size OK: 0.7KB
- `filename_convention`: Filename follows convention
- `json_validity`: Valid JSON structure
- `geojson_type_field`: Required field present: type
- `geojson_features_field`: Required field present: features
- `geojson_type`: Correct GeoJSON type: FeatureCollection
- `features_array`: Features array with 2 items
- `features_structure`: Features have required structure
- `feature_count`: Feature count OK: 2
- `coordinate_system`: Correct CRS: EPSG:4326
- `null_geometries`: No null geometries
- `empty_geometries`: No empty geometries
- `geometry_validity`: All geometries are valid
- `european_bounds`: Coordinates within European bounds
- `geographic_boundary_check`: All 2 features intersect with utrecht boundary

---


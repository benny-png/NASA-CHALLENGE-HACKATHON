# Farm Analysis API Documentation

## 1. POST /upload_process_full_geojson

Upload and process a GeoJSON file containing farm boundaries.

**Request Body:**
- `file`: GeoJSON file (multipart/form-data)

**Example:**
```
curl -X 'POST' \
  'http://localhost:8000/upload_process_full_geojson' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@path/to/your/file.geojson;type=application/geo+json'
```

**Response:**
```json
{
  "message": "Successfully processed file.geojson",
  "regions": [
    {
      "region_id": 0,
      "properties": { "name": "Farm 1" },
      "image_date": "2023-05-15",
      "image_count": 10,
      "full_rgb_url": "https://earthengine.googleapis.com/...",
      "full_ndvi_url": "https://earthengine.googleapis.com/...",
      "clipped_rgb_url": "https://earthengine.googleapis.com/...",
      "clipped_ndvi_url": "https://earthengine.googleapis.com/...",
      "available_bands": ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]
    }
  ]
}
```

## 2. POST /inspect_geojson

Inspect the contents of a GeoJSON file without processing satellite imagery.

**Request Body:**
- `file`: GeoJSON file (multipart/form-data)
- `show_all_properties`: boolean (query parameter)
- `name_key`: string (query parameter, optional)

**Example:**
```
curl -X 'POST' \
  'http://localhost:8000/inspect_geojson?show_all_properties=true&name_key=NAME_1' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@path/to/your/file.geojson;type=application/geo+json'
```

**Response:**
```json
{
  "message": "GeoJSON file inspection results",
  "total_regions": 1,
  "regions": [
    {
      "id": "1",
      "name": "Farm 1",
      "type": "Agricultural",
      "country": "United States",
      "properties": { ... }
    }
  ]
}
```

## 3. POST /region_image/{region_name}

Get satellite imagery for a specific region.

**Path Parameters:**
- `region_name`: string

**Query Parameters:**
- `name_key`: string (optional)

**Request Body:**
- `file`: GeoJSON file (multipart/form-data, optional)

**Example:**
```
curl -X 'POST' \
  'http://localhost:8000/region_image/Farm%201?name_key=NAME_1' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@path/to/your/file.geojson;type=application/geo+json'
```

**Response:**
```json
{
  "region_name": "Farm 1",
  "properties": { ... },
  "rgb_image_url": "https://earthengine.googleapis.com/...",
  "ndvi_image_url": "https://earthengine.googleapis.com/..."
}
```

## 4. POST /hls_image

Get Harmonized Landsat Sentinel-2 (HLS) imagery for a specified area.

**Request Body:**
```json
{
  "aoi": {
    "type": "coordinates",
    "data": {
      "lon1": -95.5,
      "lat1": 42.5,
      "lon2": -95.3,
      "lat2": 42.7
    }
  }
}
```

**Example:**
```
curl -X 'POST' \
  'http://127.0.0.1:8000/hls_image' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "aoi": {
    "type": "coordinates",
    "data": {
      "lon1": -95.5,
      "lat1": 42.5,
      "lon2": -95.3,
      "lat2": 42.7
    }
  }
}'
```

**Response:**
```json
{
  "region_id": 0,
  "properties": {},
  "image_date": "2023-05-15",
  "image_count": 10,
  "full_rgb_url": "https://earthengine.googleapis.com/...",
  "full_ndvi_url": "https://earthengine.googleapis.com/...",
  "clipped_rgb_url": "https://earthengine.googleapis.com/...",
  "clipped_ndvi_url": "https://earthengine.googleapis.com/...",
  "available_bands": ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]
}
```

## 5. GET /dataset_info

Get information about the HLS dataset used in the API.

**Example:**
```
curl -X 'GET' \
  'http://localhost:8000/dataset_info' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "dataset_name": "NASA/HLS/HLSL30/v002",
  "description": "Harmonized Landsat Sentinel-2 (HLS) dataset",
  "resolution": "30 meters",
  "bands": [
    {"name": "B1", "description": "Coastal Aerosol"},
    {"name": "B2", "description": "Blue"},
    ...
  ],
  "fmask_description": { ... }
}
```

## 6. POST /analyze_farm

Analyze farm vegetation health and predict harvest.

**Query Parameters:**
- `crop_type`: string

**Request Body:**
```json
{
  "aoi": {
    "type": "geojson",
    "data": {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-95.5, 42.5], [-95.5, 42.7], [-95.3, 42.7], [-95.3, 42.5], [-95.5, 42.5]]]
      }
    }
  },
  "date_range": {
    "start_date": "2023-01-01",
    "end_date": "2023-06-01"
  }
}
```

**Example:**
```
curl -X 'POST' \
  'http://localhost:8000/analyze_farm?crop_type=corn' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "aoi": {
    "type": "geojson",
    "data": {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-95.5, 42.5], [-95.5, 42.7], [-95.3, 42.7], [-95.3, 42.5], [-95.5, 42.5]]]
      }
    }
  },
  "date_range": {
    "start_date": "2023-01-01",
    "end_date": "2023-06-01"
  }
}'
```

**Response:**
```json
{
  "ndvi_stats": [ ... ],
  "vegetation_health": {
    "current_ndvi": 0.65,
    "historical_average_ndvi": 0.62,
    "vegetation_health": "Good",
    "ndvi_min": 0.45,
    "ndvi_max": 0.85
  },
  "harvest_prediction": "Good yield expected",
  "ndvi_trend": "Increasing"
}
```

## 7. POST /analyze_climate

Analyze climate data for a specific region.

**Request Body:**
```json
{
  "aoi": {
    "type": "geojson",
    "data": {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-95.5, 42.5], [-95.5, 42.7], [-95.3, 42.7], [-95.3, 42.5], [-95.5, 42.5]]]
      }
    }
  },
  "date_range": {
    "start_date": "2023-01-01",
    "end_date": "2023-06-01"
  },
  "parameters": ["temperature", "precipitation"]
}
```

**Example:**
```
curl -X 'POST' \
  'http://localhost:8000/analyze_climate' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "aoi": {
    "type": "geojson",
    "data": {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-95.5, 42.5], [-95.5, 42.7], [-95.3, 42.7], [-95.3, 42.5], [-95.5, 42.5]]]
      }
    }
  },
  "date_range": {
    "start_date": "2023-01-01",
    "end_date": "2023-06-01"
  },
  "parameters": ["temperature", "precipitation"]
}'
```

**Response:**
```json
{
  "weather_data": [
    {
      "date": "2023-01-15",
      "temperature": 0.5,
      "precipitation": 1.2
    },
    ...
  ],
  "drought_status": "No drought",
  "climate_summary": {
    "average_temperature": 15.3,
    "total_precipitation": 250.5
  },
  "climate_trends": {
    "temperature_trend": "Increasing",
    "precipitation_trend": "Stable"
  }
}
```

## 8. POST /ndvi_trend

Get NDVI trend data for a specific region.

**Query Parameters:**
- `start_date`: date
- `end_date`: date

**Request Body:**
```json
{
  "type": "geojson",
  "data": {
    "type": "Feature",
    "properties": {},
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[-95.5, 42.5], [-95.5, 42.7], [-95.3, 42.7], [-95.3, 42.5], [-95.5, 42.5]]]
    }
  }
}
```

**Example:**
```
curl -X 'POST' \
  'http://localhost:8000/ndvi_trend?start_date=2023-01-01&end_date=2023-06-01' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "type": "geojson",
  "data": {
    "type": "Feature",
    "properties": {},
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[-95.5, 42.5], [-95.5, 42.7], [-95.3, 42.7], [-95.3, 42.5], [-95.5, 42.5]]]
    }
  }
}'
```

**Response:**
```json
{
  "ndvi_data": [
    {"date": "2023-01-01", "ndvi": 0.3},
    {"date": "2023-02-01", "ndvi": 0.35},
    ...
  ],
  "trendline": {
    "start": 0.3,
    "end": 0.6
  },
  "trend_direction": "Increasing"
}
```
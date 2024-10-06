# Farm Analysis API Documentation for Swagger UI

## 1. POST /upload_process_full_geojson

Upload and process a GeoJSON file containing farm boundaries.

**Request:**
- Use the "Try it out" button
- Click "Choose File" and select your GeoJSON file
- Click "Execute"

**Response Example:**
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

**Request:**
- Use the "Try it out" button
- Set `show_all_properties` to true or false
- Optionally set `name_key` (e.g., "NAME_1")
- Click "Choose File" and select your GeoJSON file
- Click "Execute"

**Response Example:**
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

**Request:**
- Use the "Try it out" button
- Enter the `region_name` (e.g., "Farm 1")
- Optionally set `name_key` (e.g., "NAME_1")
- Click "Choose File" and select your GeoJSON file (if needed)
- Click "Execute"

**Response Example:**
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

**Request:**
- Use the "Try it out" button
- Enter the following in the request body:

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

**Response Example:**
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

Alternatively, you can use a GeoJSON feature:

```json
{
  "aoi": {
    "type": "geojson",
    "data": {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-95.5, 42.5], [-95.5, 42.7], [-95.3, 42.7], [-95.3, 42.5], [-95.5, 42.5]]]
      }
    }
  }
}
```

- Click "Execute"

## 5. GET /dataset_info

Get information about the HLS dataset used in the API.

**Request:**
- Simply click "Execute"

**Response Example:**
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

**Request:**
- Use the "Try it out" button
- Set `crop_type` (e.g., "corn")
- Enter the following in the request body:

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

**Response Example:**
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

**Response Example:**
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

**Request:**
- Use the "Try it out" button
- Set `start_date` (e.g., "2023-01-01")
- Set `end_date` (e.g., "2023-06-01")
- Enter the following in the request body:

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

**Response Example:**
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
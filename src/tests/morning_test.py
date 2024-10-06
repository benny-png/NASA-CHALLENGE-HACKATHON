import ee
from fastapi import FastAPI, HTTPException, File, UploadFile, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Union, Dict, List, Optional
import json
import geopandas as gpd
import io
import logging

app = FastAPI()

# Initialize Earth Engine
ee.Initialize(project='ee-mazikuben2')

# Set up logging
logging.basicConfig(level=logging.INFO)

class Coordinates(BaseModel):
    lon1: float
    lat1: float
    lon2: float
    lat2: float

class GeoJSONFeature(BaseModel):
    type: str
    properties: Dict
    geometry: Dict

class GeoJSON(BaseModel):
    type: str
    features: List[GeoJSONFeature]

class AOIInput(BaseModel):
    type: str
    data: Union[Coordinates, GeoJSON]

# Global variable to store the last uploaded GeoJSON
last_uploaded_geojson = None

def get_hls_image(aoi):
    current_date = ee.Date(datetime.now())
    one_year_ago = current_date.advance(-1, 'year')

    image_collection = ee.ImageCollection('NASA/HLS/HLSL30/v002')
    filtered_collection = (image_collection
                           .filterBounds(aoi)
                           .filterDate(one_year_ago, current_date)
                           .sort('system:time_start', False))  # Sort by date, most recent first

    most_recent_image = filtered_collection.first()

    if most_recent_image:
        rgb_image = most_recent_image.select(['B4', 'B3', 'B2'])
        ndvi = most_recent_image.normalizedDifference(['B5', 'B4']).rename('NDVI')
        return rgb_image, ndvi, most_recent_image.date().format('YYYY-MM-dd').getInfo(), filtered_collection.size().getInfo()
    else:
        return None, None, None, 0

def calculate_ndvi(image):
    ndvi = image.normalizedDifference(['B5', 'B4']).rename('NDVI')
    return image.addBands(ndvi)

def process_geojson(geojson_data):
    if isinstance(geojson_data, dict):
        if geojson_data['type'] == 'FeatureCollection':
            return [ee.Feature(feature) for feature in geojson_data['features']]
        elif geojson_data['type'] == 'Feature':
            return [ee.Feature(geojson_data)]
        else:
            return [ee.Geometry(geojson_data)]
    else:
        raise ValueError("Invalid GeoJSON data")

def get_image_data(aoi, i, properties):
    rgb_image, ndvi_image, image_date, image_count = get_hls_image(aoi)
    if rgb_image is None:
        return None

    # Visualization parameters
    rgb_vis = {'min': 0, 'max': 0.3, 'gamma': 1.2}
    ndvi_vis = {'min': -1, 'max': 1, 'palette': ['blue', 'white', 'green']}

    # Get the bounds of the AOI
    bounds = aoi.bounds().getInfo()['coordinates'][0]
    lon_min, lat_min = bounds[0]
    lon_max, lat_max = bounds[2]

    # Generate URLs for full and clipped images
    full_rgb_url = rgb_image.getThumbURL({**rgb_vis, 'dimensions': 1024})
    full_ndvi_url = ndvi_image.getThumbURL({**ndvi_vis, 'dimensions': 1024})
    
    clipped_rgb_url = rgb_image.clip(aoi).getThumbURL({
        **rgb_vis, 
        'dimensions': 1024,
        'region': aoi
    })
    clipped_ndvi_url = ndvi_image.clip(aoi).getThumbURL({
        **ndvi_vis, 
        'dimensions': 1024,
        'region': aoi
    })

    return {
        "region_id": i,
        "properties": properties,
        "image_date": image_date,
        "image_count": image_count,
        "full_rgb_url": full_rgb_url,
        "full_ndvi_url": full_ndvi_url,
        "clipped_rgb_url": clipped_rgb_url,
        "clipped_ndvi_url": clipped_ndvi_url,
        "available_bands": rgb_image.bandNames().getInfo()
    }

def get_image_urls_for_region(region_geometry):
    now = datetime.now()
    one_year_ago = now - timedelta(days=365)

    ee_now = ee.Date(now)
    ee_one_year_ago = ee.Date(one_year_ago)

    hls_collection = ee.ImageCollection("NASA/HLS/HLSL30/v002")

    filtered_collection = hls_collection \
        .filterBounds(region_geometry) \
        .filterDate(ee_one_year_ago, ee_now) \
        .sort('CLOUD_COVERAGE', True)

    image_count = filtered_collection.size().getInfo()
    if image_count == 0:
        return None, None

    mosaic = filtered_collection.mosaic()

    rgb_image = mosaic.select(['B4', 'B3', 'B2'])

    ndvi_image = mosaic.normalizedDifference(['B5', 'B4']).rename('NDVI')

    rgb_vis = {'min': 0, 'max': 0.3, 'gamma': 1.2}
    ndvi_vis = {'min': -1, 'max': 1, 'palette': ['blue', 'white', 'green']}

    # Simplify the geometry
    simplified_geometry = region_geometry.simplify(maxError=100)

    logging.info(f"Simplified region geometry: {simplified_geometry.getInfo()}")

    full_rgb_url = rgb_image.getThumbURL({
        **rgb_vis,
        'region': simplified_geometry,
        'dimensions': 1024
    })

    full_ndvi_url = ndvi_image.getThumbURL({
        **ndvi_vis,
        'region': simplified_geometry,
        'dimensions': 1024
    })

    return full_rgb_url, full_ndvi_url

@app.post("/upload_process_full_geojson")
async def upload_geojson(file: UploadFile = File(...)):
    global last_uploaded_geojson
    if not file.filename.endswith('.geojson'):
        return JSONResponse(status_code=400, content={"message": "Invalid file type. Please upload a GeoJSON file."})
    
    content = await file.read()
    gdf = gpd.read_file(io.BytesIO(content))
    
    if gdf.crs and gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    
    geojson_dict = json.loads(gdf.to_json())
    last_uploaded_geojson = geojson_dict
    
    features = process_geojson(geojson_dict)
    
    results = []
    for i, feature in enumerate(features):
        result = await get_image_data(feature.geometry(), i, feature.getInfo()['properties'])
        if result:
            results.append(result)

    if not results:
        raise HTTPException(status_code=404, detail="No images found for any of the specified regions in the past year.")

    return {
        "message": f"Successfully processed {file.filename}",
        "regions": results
    }

@app.post("/inspect_geojson")
async def inspect_geojson(
    file: UploadFile = File(None),
    show_all_properties: bool = Query(False, description="Show all properties for each region"),
    name_key: Optional[str] = Query(None, description="Specify the key to use for region names")
):
    global last_uploaded_geojson
    
    if file:
        if not file.filename.endswith('.geojson'):
            return JSONResponse(status_code=400, content={"message": "Invalid file type. Please upload a GeoJSON file."})
        
        content = await file.read()
        gdf = gpd.read_file(io.BytesIO(content))
        
        if gdf.crs and gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        
        geojson_dict = json.loads(gdf.to_json())
        last_uploaded_geojson = geojson_dict
    elif last_uploaded_geojson is None:
        raise HTTPException(status_code=404, detail="No GeoJSON file has been uploaded yet. Please upload a file.")
    else:
        geojson_dict = last_uploaded_geojson
    
    regions = []
    common_name_keys = ['NAME_1', 'name', 'NAME', 'Name', 'id', 'ID', 'Id', 'region', 'REGION', 'Region']
    
    if name_key:
        common_name_keys.insert(0, name_key)
    
    for i, feature in enumerate(geojson_dict['features']):
        properties = feature['properties']
        
        name = next((properties.get(key) for key in common_name_keys if key in properties), None)
        
        if name is None:
            name = f"Unnamed Region {i + 1}"
        
        region_info = {
            "id": properties.get('ID_1') or properties.get('id') or i,
            "name": name,
            "type": properties.get('TYPE_1') or properties.get('ENGTYPE_1'),
            "country": properties.get('NAME_0')
        }
        
        if show_all_properties:
            region_info["properties"] = properties
        
        regions.append(region_info)
    
    return {
        "message": "GeoJSON file inspection results",
        "total_regions": len(regions),
        "regions": regions
    }

@app.post("/region_image/{region_name}")
async def get_region_image(
    region_name: str = Path(..., description="Name of the region to process"),
    file: UploadFile = File(None),
    name_key: Optional[str] = Query(None, description="Specify the key to use for region names")
):
    global last_uploaded_geojson
    
    if file:
        if not file.filename.endswith('.geojson'):
            return JSONResponse(status_code=400, content={"message": "Invalid file type. Please upload a GeoJSON file."})
        
        content = await file.read()
        gdf = gpd.read_file(io.BytesIO(content))
        
        if gdf.crs and gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        
        geojson_dict = json.loads(gdf.to_json())
        last_uploaded_geojson = geojson_dict
    elif last_uploaded_geojson is None:
        raise HTTPException(status_code=404, detail="No GeoJSON file has been uploaded yet. Please upload a file.")
    else:
        geojson_dict = last_uploaded_geojson
    
    common_name_keys = ['NAME_1', 'name', 'NAME', 'Name', 'id', 'ID', 'Id', 'region', 'REGION', 'Region']
    if name_key:
        common_name_keys.insert(0, name_key)
    
    target_feature = None
    for feature in geojson_dict['features']:
        properties = feature['properties']
        feature_name = next((properties.get(key) for key in common_name_keys if key in properties), None)
        if feature_name == region_name:
            target_feature = feature
            break
    
    if target_feature is None:
        raise HTTPException(status_code=404, detail=f"Region '{region_name}' not found in the uploaded GeoJSON.")
    
    logging.info(f"Processing region: {region_name}")
    logging.info(f"Geometry type: {target_feature['geometry']['type']}")
    #logging.info(f"Coordinates: {target_feature['geometry']['coordinates']}")

    # Handle both Polygon and MultiPolygon
    if target_feature['geometry']['type'] == 'Polygon':
        aoi = ee.Geometry.Polygon(target_feature['geometry']['coordinates'])
    elif target_feature['geometry']['type'] == 'MultiPolygon':
        aoi = ee.Geometry.MultiPolygon(target_feature['geometry']['coordinates'])
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported geometry type: {target_feature['geometry']['type']}")
    
    rgb_url, ndvi_url = get_image_urls_for_region(aoi)
    
    if rgb_url is None or ndvi_url is None:
        raise HTTPException(status_code=404, detail=f"No image found for region '{region_name}' in the past year.")
    
    return {
        "region_name": region_name,
        "properties": target_feature['properties'],
        "rgb_image_url": rgb_url,
        "ndvi_image_url": ndvi_url
    }

@app.post("/hls_image")
async def get_hls_image_api(aoi_input: AOIInput):
    if aoi_input.type == "coordinates":
        coords = aoi_input.data
        aoi = ee.Geometry.Rectangle([coords.lon1, coords.lat1, coords.lon2, coords.lat2])
    elif aoi_input.type == "geojson":
        geojson = aoi_input.data
        if geojson.type != "FeatureCollection" or len(geojson.features) == 0:
            raise HTTPException(status_code=400, detail="Invalid GeoJSON. Expected a FeatureCollection with at least one feature.")
        geometry = geojson.features[0].geometry
        aoi = ee.Geometry(geometry)
    else:
        raise HTTPException(status_code=400, detail="Invalid AOI type. Use 'coordinates' or 'geojson'.")
    
    result = get_image_data(aoi, 0, {})

    if result is None:
        raise HTTPException(status_code=404, detail="No image found for the specified location in the past year.")

    return result




@app.get("/dataset_info")
async def get_dataset_info():
    return {
        "dataset_name": "NASA/HLS/HLSL30/v002",
        "description": "Harmonized Landsat Sentinel-2 (HLS) dataset",
        "resolution": "30 meters",
        "bands": [
            {"name": "B1", "description": "Coastal Aerosol"},
            {"name": "B2", "description": "Blue"},
            {"name": "B3", "description": "Green"},
            {"name": "B4", "description": "Red"},
            {"name": "B5", "description": "NIR"},
            {"name": "B6", "description": "SWIR1"},
            {"name": "B7", "description": "SWIR2"},
            {"name": "B9", "description": "Cirrus"},
            {"name": "B10", "description": "TIRS1"},
            {"name": "B11", "description": "TIRS2"},
            {"name": "Fmask", "description": "Quality Bits"},
            {"name": "SZA", "description": "Sun Zenith Angle", "units": "deg"},
            {"name": "SAA", "description": "Sun Azimuth Angle", "units": "deg"},
            {"name": "VZA", "description": "View Zenith Angle", "units": "deg"},
            {"name": "VAA", "description": "View Azimuth Angle", "units": "deg"}
        ],
        "fmask_description": {
            "Bit 0: Cirrus": ["0: Reserved but not used", "1: Reserved but not used"],
            "Bit 1: Cloud": ["0: No", "1: Yes"],
            "Bit 2: Adjacent to cloud/shadow": ["0: No", "1: Yes"],
            "Bit 3: Cloud shadow": ["0: No", "1: Yes"],
            "Bit 4: Snow/ice": ["0: No", "1: Yes"],
            "Bit 5: Water": ["0: No", "1: Yes"],
            "Bits 6-7: Aerosol level": ["0: Climatology aerosol", "1: Low aerosol", "2: Moderate aerosol", "3: High aerosol"]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
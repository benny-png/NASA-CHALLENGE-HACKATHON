from fastapi import APIRouter, HTTPException, File, UploadFile, Query, Path, Depends, Body
from fastapi.responses import JSONResponse
from datetime import date, datetime
from typing import Optional, List, Dict
import json
import geopandas as gpd
import numpy as np
import io
import logging
import ee

from .models import AOIInput, FarmAnalysisRequest, WeatherAnalysisRequest, GeoJSONFeature, GeoJSON, HLSImageRequest
from .earth_engine import get_image_data, get_image_urls_for_region
from .geojson_utils import process_geojson, find_feature_by_name, create_aoi_from_feature
from .farm_analysis import analyze_farm, get_ndvi_trend, CROP_NDVI_THRESHOLDS
from .weather_analysis import analyze_climate

router = APIRouter()



# Global variable to store the last uploaded GeoJSON
last_uploaded_geojson = None

#@router.post("/upload_process_full_geojson")
#async def upload_geojson(file: UploadFile = File(...)):
#    global last_uploaded_geojson
#    if not file.filename.endswith('.geojson'):
#        return JSONResponse(status_code=400, content={"message": "Invalid file type. Please upload a GeoJSON file."})
#    
#    content = await file.read()
#    gdf = gpd.read_file(io.BytesIO(content))
#    
#    if gdf.crs and gdf.crs != "EPSG:4326":
#        gdf = gdf.to_crs("EPSG:4326")
#    
#    geojson_dict = json.loads(gdf.to_json())
#    last_uploaded_geojson = geojson_dict
#    
#    features = process_geojson(geojson_dict)
#    
#    results = []
#    for i, feature in enumerate(features):
#        result = await get_image_data(feature.geometry(), i, feature.getInfo()['properties'])
#        if result:
#            results.append(result)
#
#    if not results:
#        raise HTTPException(status_code=404, detail="No images found for any of the specified regions in the past year.")
#
#    return {
#        "message": f"Successfully processed {file.filename}",
#        "regions": results
#    }


@router.post("/inspect_geojson")
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

@router.post("/region_image/{region_name}")
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
    
    target_feature = find_feature_by_name(geojson_dict, region_name, common_name_keys)
    
    if target_feature is None:
        raise HTTPException(status_code=404, detail=f"Region '{region_name}' not found in the uploaded GeoJSON.")
    
    logging.info(f"Processing region: {region_name}")
    logging.info(f"Geometry type: {target_feature['geometry']['type']}")

    aoi = create_aoi_from_feature(target_feature)
    
    rgb_url, ndvi_url = get_image_urls_for_region(aoi)
    
    if rgb_url is None or ndvi_url is None:
        raise HTTPException(status_code=404, detail=f"No image found for region '{region_name}' in the past year.")
    
    return {
        "region_name": region_name,
        "properties": target_feature['properties'],
        "rgb_image_url": rgb_url,
        "ndvi_image_url": ndvi_url
    }

@router.post("/hls_image")
async def get_hls_image_api(request: HLSImageRequest):
    try:
        aoi_input = request.aoi
        if aoi_input.type == "coordinates":
            coords = aoi_input.data
            aoi = ee.Geometry.Rectangle([coords.lon1, coords.lat1, coords.lon2, coords.lat2])
        elif aoi_input.type == "geojson":
            if isinstance(aoi_input.data, GeoJSONFeature):
                aoi = ee.Geometry(aoi_input.data.geometry.dict())
            elif isinstance(aoi_input.data, GeoJSON):
                aoi = ee.FeatureCollection(aoi_input.data.dict()).geometry()
            else:
                raise HTTPException(status_code=400, detail="Invalid GeoJSON data")
        else:
            raise HTTPException(status_code=400, detail="Invalid AOI type. Use 'coordinates' or 'geojson'.")
        
        result = get_image_data(aoi, 0, {})

        if result is None:
            raise HTTPException(status_code=404, detail="No image found for the specified location in the past year.")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
    

@router.get("/dataset_info")
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
    
    

def validate_crop_type(crop_type: str = Query(..., description="Type of crop")) -> str:
    if crop_type not in CROP_NDVI_THRESHOLDS:
        raise HTTPException(status_code=400, detail=f"Unsupported crop type: {crop_type}")
    return crop_type


def create_aoi(aoi_input: AOIInput) -> ee.Geometry:
    if aoi_input.type == "coordinates":
        coords = aoi_input.data
        return ee.Geometry.Rectangle([coords.lon1, coords.lat1, coords.lon2, coords.lat2])
    elif aoi_input.type == "geojson":
        if isinstance(aoi_input.data, GeoJSONFeature):
            return ee.Geometry(aoi_input.data.geometry.dict())
        elif isinstance(aoi_input.data, GeoJSON):
            return ee.FeatureCollection(aoi_input.data.dict()).geometry()
    raise HTTPException(status_code=400, detail="Invalid AOI input")

@router.post("/analyze_farm")
async def analyze_farm_route(request: FarmAnalysisRequest, crop_type: str = Depends(validate_crop_type)):
    try:
        aoi = create_aoi(request.aoi)
        result = analyze_farm(aoi, request.date_range.start_date.isoformat(), request.date_range.end_date.isoformat(), crop_type)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error in analyze_farm_route: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred while analyzing the farm: {str(e)}")



@router.post("/analyze_climate")
async def analyze_climate_route(request: WeatherAnalysisRequest):
    try:
        aoi = create_aoi(request.aoi)
        result = analyze_climate(aoi, request.date_range.start_date.isoformat(), request.date_range.end_date.isoformat(), request.parameters)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error in analyze_climate_route: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred while analyzing the climate: {str(e)}")
    
    
    


@router.post("/ndvi_trend")
async def get_ndvi_trend_route(
    aoi: Dict = Body(..., example={
        "type": "geojson",
        "data": {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-95.5, 42.5], [-95.5, 42.7], [-95.3, 42.7], [-95.3, 42.5], [-95.5, 42.5]]]
            }
        }
    }),
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    try:
        aoi_input = AOIInput(**aoi)
        ee_aoi = create_aoi(aoi_input)
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()
        
        logging.info(f"Fetching NDVI trend for AOI: {aoi}, Start Date: {start_date_str}, End Date: {end_date_str}")
        
        ndvi_data = get_ndvi_trend(ee_aoi, start_date_str, end_date_str)
        
        if not ndvi_data:
            logging.warning("No NDVI data found for the specified parameters")
            return JSONResponse(
                status_code=404,
                content={
                    "message": "No NDVI data found for the specified area and date range.",
                    "ndvi_data": [],
                    "trendline": {"start": None, "end": None},
                    "trend_direction": "Insufficient data"
                }
            )
        
        # Calculate simple linear regression for trendline
        dates = [datetime.strptime(d['date'], '%Y-%m-%d').timestamp() for d in ndvi_data]
        ndvi_values = [d['ndvi'] for d in ndvi_data]
        
        if len(dates) > 1:
            coeffs = np.polyfit(dates, ndvi_values, 1)
            trendline = np.poly1d(coeffs)
            trend_start = float(trendline(dates[0]))
            trend_end = float(trendline(dates[-1]))
            
            trend_direction = "Increasing" if coeffs[0] > 0 else "Decreasing" if coeffs[0] < 0 else "Stable"
        else:
            trend_start = trend_end = ndvi_values[0] if ndvi_values else None
            trend_direction = "Insufficient data"
        
        logging.info(f"NDVI trend calculated successfully. Direction: {trend_direction}")
        
        return {
            "ndvi_data": ndvi_data,
            "trendline": {
                "start": trend_start,
                "end": trend_end
            },
            "trend_direction": trend_direction
        }
    except HTTPException as he:
        logging.error(f"HTTP Exception in get_ndvi_trend_route: {str(he)}")
        raise he
    except Exception as e:
        logging.error(f"Unexpected error in get_ndvi_trend_route: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while fetching NDVI trend: {str(e)}")
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import ee
import geemap
import numpy as np
from datetime import date, datetime, timedelta
import json

app = FastAPI(title="Enhanced Agricultural Monitoring API")

ee.Initialize(project='ee-mazikuben2')

class Region(BaseModel):
    name: str
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

def get_hls_collection(region: Region, start_date: str, end_date: str):
    aoi = ee.Geometry.Rectangle([region.min_lon, region.min_lat, region.max_lon, region.max_lat])
    return ee.ImageCollection("NASA/HLS/HLSL30/v002") \
        .filterBounds(aoi) \
        .filterDate(start_date, end_date) \
        .sort('system:time_start', False)

def calculate_ndvi(image):
    return image.normalizedDifference(['B5', 'B4']).rename('NDVI')

def get_map_id(image, vis_params):
    map_id = image.getMapId(vis_params)
    return f"https://earthengine.googleapis.com/v1alpha/{map_id['mapid']}/tiles/{{z}}/{{x}}/{{y}}"

@app.get("/drought_status/{region_name}")
async def get_drought_status(
    region_name: str,
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    try:
        region = Region(name=region_name, min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat)
        end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        start_date = start_date or (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
        
        collection = get_hls_collection(region, start_date, end_date)
        recent_image = collection.first()
        
        if recent_image is None:
            raise HTTPException(status_code=404, detail="No data available for this region and time range")
        
        ndvi = calculate_ndvi(recent_image)
        aoi = ee.Geometry.Rectangle([region.min_lon, region.min_lat, region.max_lon, region.max_lat])
        
        ndvi_stats = ndvi.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), None, True)
                .combine(ee.Reducer.minMax(), None, True)
                .combine(ee.Reducer.percentile([10, 25, 50, 75, 90]), None, True),
            geometry=aoi,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        
        mean_ndvi = ndvi_stats['NDVI_mean']
        
        if mean_ndvi < 0.1:
            status = "Extreme Drought"
        elif mean_ndvi < 0.2:
            status = "Severe Drought"
        elif mean_ndvi < 0.3:
            status = "Moderate Drought"
        elif mean_ndvi < 0.4:
            status = "Mild Drought"
        elif mean_ndvi < 0.5:
            status = "Abnormally Dry"
        else:
            status = "No Drought"
        
        ndvi_vis = {'min': 0, 'max': 1, 'palette': ['red', 'yellow', 'green']}
        ndvi_url = get_map_id(ndvi, ndvi_vis)
        
        return {
            "non_technical_summary": {
                "region": region_name,
                "drought_status": status,
                "average_vegetation_health": f"{mean_ndvi:.2f}",
                "interpretation": f"The region is experiencing {status.lower()} conditions. "
                                  f"The average vegetation health index is {mean_ndvi:.2f} out of 1.00, "
                                  f"where higher values indicate healthier vegetation."
            },
            "technical_details": {
                "ndvi_statistics": ndvi_stats,
                "analysis_period": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "data_source": "NASA Harmonized Landsat Sentinel-2 (HLS) dataset"
            },
            "visualization": {
                "ndvi_map_url": ndvi_url,
                "legend": "Red (Low NDVI) to Green (High NDVI)"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/crop_health/{region_name}")
async def get_crop_health(
    region_name: str,
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    try:
        region = Region(name=region_name, min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat)
        end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        start_date = start_date or (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
        
        collection = get_hls_collection(region, start_date, end_date)
        recent_image = collection.first()
        
        if recent_image is None:
            raise HTTPException(status_code=404, detail="No data available for this region and time range")
        
        ndvi = calculate_ndvi(recent_image)
        aoi = ee.Geometry.Rectangle([region.min_lon, region.min_lat, region.max_lon, region.max_lat])
        
        ndvi_stats = ndvi.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), None, True)
                .combine(ee.Reducer.minMax(), None, True)
                .combine(ee.Reducer.percentile([10, 25, 50, 75, 90]), None, True),
            geometry=aoi,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        
        mean_ndvi = ndvi_stats['NDVI_mean']
        
        if mean_ndvi < 0.2:
            health_status = "Very Poor"
        elif mean_ndvi < 0.4:
            health_status = "Poor"
        elif mean_ndvi < 0.6:
            health_status = "Moderate"
        elif mean_ndvi < 0.8:
            health_status = "Good"
        else:
            health_status = "Excellent"
        
        ndvi_vis = {'min': 0, 'max': 1, 'palette': ['red', 'yellow', 'green']}
        ndvi_url = get_map_id(ndvi, ndvi_vis)
        
        return {
            "non_technical_summary": {
                "region": region_name,
                "crop_health_status": health_status,
                "average_vegetation_index": f"{mean_ndvi:.2f}",
                "interpretation": f"The crops in this region are in {health_status.lower()} health. "
                                  f"The average vegetation index is {mean_ndvi:.2f} out of 1.00, "
                                  f"where higher values indicate healthier vegetation."
            },
            "technical_details": {
                "ndvi_statistics": ndvi_stats,
                "analysis_period": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "data_source": "NASA Harmonized Landsat Sentinel-2 (HLS) dataset"
            },
            "visualization": {
                "ndvi_map_url": ndvi_url,
                "legend": "Red (Low NDVI) to Green (High NDVI)"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vegetation_trend/{region_name}")
async def get_vegetation_trend(
    region_name: str,
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    interval: str = Query("month", description="Interval for trend analysis: 'week', 'month', or 'year'")
):
    try:
        region = Region(name=region_name, min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat)
        end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            if interval == 'week':
                start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(weeks=12)).strftime('%Y-%m-%d')
            elif interval == 'month':
                start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=365)).strftime('%Y-%m-%d')
            else:  # year
                start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=1825)).strftime('%Y-%m-%d')
        
        collection = get_hls_collection(region, start_date, end_date)
        aoi = ee.Geometry.Rectangle([region.min_lon, region.min_lat, region.max_lon, region.max_lat])
        
        def add_ndvi_and_date(image):
            ndvi = calculate_ndvi(image)
            return image.addBands(ndvi).set('system:time_start', image.date().millis())
        
        ndvi_collection = collection.map(add_ndvi_and_date)
        
        # Perform linear regression
        linear_fit = ndvi_collection.select(['system:time_start', 'NDVI']).reduce(ee.Reducer.linearFit())
        
        # Get the slope of the trend
        slope = linear_fit.select('scale').multiply(1000)  # Convert to change per 1000 days for easier interpretation
        
        trend_stats = slope.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        
        slope_value = trend_stats['scale']
        
        if slope_value > 0.05:
            trend_status = "Strongly Improving"
        elif slope_value > 0.01:
            trend_status = "Slightly Improving"
        elif slope_value > -0.01:
            trend_status = "Stable"
        elif slope_value > -0.05:
            trend_status = "Slightly Declining"
        else:
            trend_status = "Strongly Declining"
        
        # Create a time series of NDVI values
        time_series = ndvi_collection.aggregate_array('system:time_start').getInfo()
        ndvi_values = ndvi_collection.aggregate_array('NDVI').getInfo()
        
        # Prepare GeoJSON for the trend
        trend_image = slope.clip(aoi)
        trend_geojson = geemap.ee_to_geojson(trend_image)
        
        return {
            "non_technical_summary": {
                "region": region_name,
                "vegetation_trend": trend_status,
                "interpretation": f"The vegetation in this region is {trend_status.lower()}. "
                                  f"The average change in vegetation index is {slope_value:.4f} per 1000 days."
            },
            "technical_details": {
                "trend_slope": slope_value,
                "analysis_period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "interval": interval
                },
                "data_source": "NASA Harmonized Landsat Sentinel-2 (HLS) dataset",
                "time_series": [
                    {"date": datetime.fromtimestamp(t/1000).strftime('%Y-%m-%d'), "ndvi": v}
                    for t, v in zip(time_series, ndvi_values)
                ]
            },
            "visualization": {
                "trend_geojson": json.loads(trend_geojson),
                "legend": "Red (Declining) to Green (Improving)"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
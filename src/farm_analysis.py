import ee
from datetime import datetime
import numpy as np
from typing import List, Dict, Any
from fastapi import HTTPException
import logging


# Define crop-specific NDVI thresholds
CROP_NDVI_THRESHOLDS = {
    "corn": {"poor": 0.3, "fair": 0.5, "good": 0.7},
    "wheat": {"poor": 0.3, "fair": 0.4, "good": 0.6},
    "soybeans": {"poor": 0.3, "fair": 0.5, "good": 0.7},
    "rice": {"poor": 0.3, "fair": 0.5, "good": 0.7},
    "cotton": {"poor": 0.3, "fair": 0.4, "good": 0.6},
}

def calculate_ndvi_stats(aoi: ee.Geometry, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    try:
        collection = ee.ImageCollection('MODIS/006/MOD13Q1') \
            .filterDate(start_date, end_date) \
            .filterBounds(aoi)
        
        if collection.size().getInfo() == 0:
            raise ValueError("No MODIS data available for the specified date range and location.")

        def calc_stats(image):
            ndvi = image.select('NDVI').divide(10000)  # Scale NDVI values
            stats = ndvi.reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), None, True)
                    .combine(ee.Reducer.minMax(), None, True),
                geometry=aoi,
                scale=250,
                maxPixels=1e9
            )
            return ee.Feature(None, {
                'mean': stats.get('NDVI_mean'),
                'stdDev': stats.get('NDVI_stdDev'),
                'min': stats.get('NDVI_min'),
                'max': stats.get('NDVI_max'),
                'date': image.date().format('YYYY-MM-dd')
            })

        stats = collection.map(calc_stats).getInfo()
        return stats['features']
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating NDVI stats: {str(e)}")

def analyze_vegetation_health(ndvi_stats: List[Dict[str, Any]], crop_type: str) -> Dict[str, Any]:
    if not ndvi_stats:
        raise ValueError("No NDVI statistics available for analysis.")

    if crop_type not in CROP_NDVI_THRESHOLDS:
        raise ValueError(f"Unsupported crop type: {crop_type}")

    means = [feature['properties']['mean'] for feature in ndvi_stats]
    current_mean = means[-1]
    historical_mean = np.mean(means[:-1]) if len(means) > 1 else current_mean

    thresholds = CROP_NDVI_THRESHOLDS[crop_type]
    
    if current_mean > thresholds["good"]:
        health = "Excellent"
    elif current_mean > thresholds["fair"]:
        health = "Good"
    elif current_mean > thresholds["poor"]:
        health = "Fair"
    else:
        health = "Poor"
    
    return {
        "current_ndvi": current_mean,
        "historical_average_ndvi": historical_mean,
        "vegetation_health": health,
        "ndvi_min": min(feature['properties']['min'] for feature in ndvi_stats),
        "ndvi_max": max(feature['properties']['max'] for feature in ndvi_stats)
    }

def predict_harvest(ndvi_stats: List[Dict[str, Any]], crop_type: str) -> str:
    if not ndvi_stats:
        raise ValueError("No NDVI statistics available for prediction.")

    if crop_type not in CROP_NDVI_THRESHOLDS:
        raise ValueError(f"Unsupported crop type: {crop_type}")

    current_ndvi = ndvi_stats[-1]['properties']['mean']
    thresholds = CROP_NDVI_THRESHOLDS[crop_type]

    if current_ndvi > thresholds["good"]:
        return "Excellent yield expected"
    elif current_ndvi > thresholds["fair"]:
        return "Good yield expected"
    elif current_ndvi > thresholds["poor"]:
        return "Fair yield expected"
    else:
        return "Poor yield expected"

def analyze_farm(aoi: ee.Geometry, start_date: str, end_date: str, crop_type: str) -> Dict[str, Any]:
    try:
        ndvi_stats = calculate_ndvi_stats(aoi, start_date, end_date)
        vegetation_health = analyze_vegetation_health(ndvi_stats, crop_type)
        harvest_prediction = predict_harvest(ndvi_stats, crop_type)
        
        # Calculate NDVI trend
        ndvi_values = [stat['properties']['mean'] for stat in ndvi_stats]
        ndvi_trend = np.polyfit(range(len(ndvi_values)), ndvi_values, 1)[0]
        
        return {
            "ndvi_stats": ndvi_stats,
            "vegetation_health": vegetation_health,
            "harvest_prediction": harvest_prediction,
            "ndvi_trend": "Increasing" if ndvi_trend > 0 else "Decreasing" if ndvi_trend < 0 else "Stable"
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing farm: {str(e)}")
    
    


def get_ndvi_trend(aoi: ee.Geometry, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    try:
        start = ee.Date(start_date)
        end = ee.Date(end_date)

        collection = ee.ImageCollection('MODIS/006/MOD13Q1') \
            .filterDate(start, end) \
            .filterBounds(aoi)

        # Log the size of the collection
        collection_size = collection.size().getInfo()
        logging.info(f"Collection size: {collection_size}")

        if collection_size == 0:
            logging.warning(f"No images found for the given date range and area. Start: {start_date}, End: {end_date}")
            return []

        def calculate_ndvi(image):
            date = image.date().format('YYYY-MM-dd')
            ndvi = image.select('NDVI').multiply(0.0001)  # Scale factor for MODIS NDVI
            mean_ndvi = ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi,
                scale=250,
                maxPixels=1e9
            ).get('NDVI')
            return ee.Feature(None, {'date': date, 'ndvi': mean_ndvi})

        ndvi_trend = collection.map(calculate_ndvi).getInfo()
        
        # Log the number of features returned
        logging.info(f"Number of NDVI data points: {len(ndvi_trend['features'])}")

        return [
            {
                'date': feature['properties']['date'],
                'ndvi': feature['properties']['ndvi']
            }
            for feature in ndvi_trend['features']
        ]
    except Exception as e:
        logging.error(f"Error calculating NDVI trend: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error calculating NDVI trend: {str(e)}")
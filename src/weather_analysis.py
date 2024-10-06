import ee
from typing import List, Dict, Any
from fastapi import HTTPException

def analyze_weather(aoi: ee.Geometry, start_date: str, end_date: str, parameters: List[str]) -> List[Dict[str, Any]]:
    try:
        collection = ee.ImageCollection('NASA/GDDP-CMIP6') \
            .filterDate(start_date, end_date) \
            .filterBounds(aoi)
        
        def calc_stats(image):
            stats = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi,
                scale=27830,  # approximate scale for CMIP6 data
                maxPixels=1e9
            )
            return ee.Feature(None, {
                'date': image.date().format('YYYY-MM-dd'),
                'temperature': stats.get('tas'),
                'precipitation': stats.get('pr')
            })

        stats = collection.map(calc_stats).getInfo()
        return stats['features']
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing weather: {str(e)}")

def detect_drought(precipitation_data: List[Dict[str, Any]]) -> str:
    if not precipitation_data:
        return "Insufficient data for drought analysis"

    # Convert precipitation from kg/m^2/s to mm/day
    precip_values = [feature['properties']['precipitation'] * 86400 for feature in precipitation_data]
    
    mean_precip = sum(precip_values) / len(precip_values)
    if mean_precip == 0:
        return "Extreme drought conditions"
    
    std_precip = (sum((p - mean_precip) ** 2 for p in precip_values) / len(precip_values)) ** 0.5
    
    if std_precip == 0:
        return "Uniform precipitation, unable to calculate SPI"

    current_precip = precip_values[-1]
    spi = (current_precip - mean_precip) / std_precip
    
    if spi < -2:
        return "Extreme drought"
    elif spi < -1.5:
        return "Severe drought"
    elif spi < -1:
        return "Moderate drought"
    elif spi < 0:
        return "Mild drought"
    else:
        return "No drought"

def analyze_climate(aoi: ee.Geometry, start_date: str, end_date: str, parameters: List[str]) -> Dict[str, Any]:
    try:
        weather_data = analyze_weather(aoi, start_date, end_date, parameters)
        drought_status = detect_drought(weather_data)
        
        # Calculate climate summary
        temp_values = [feature['properties']['temperature'] for feature in weather_data]
        precip_values = [feature['properties']['precipitation'] * 86400 for feature in weather_data]  # Convert to mm/day

        climate_summary = {
            "average_temperature": sum(temp_values) / len(temp_values) - 273.15,  # Convert from Kelvin to Celsius
            "total_precipitation": sum(precip_values),
        }

        # Calculate climate trends
        temp_trend = "Increasing" if temp_values[-1] > temp_values[0] else "Decreasing"
        precip_trend = "Increasing" if precip_values[-1] > precip_values[0] else "Decreasing"

        climate_trends = {
            "temperature_trend": temp_trend,
            "precipitation_trend": precip_trend,
        }

        return {
            "weather_data": weather_data,
            "drought_status": drought_status,
            "climate_summary": climate_summary,
            "climate_trends": climate_trends
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing climate: {str(e)}")
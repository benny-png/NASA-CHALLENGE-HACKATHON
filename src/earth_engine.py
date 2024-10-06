import ee
from datetime import datetime, timedelta
import logging

def get_hls_image(aoi):
    current_date = ee.Date(datetime.now())
    one_year_ago = current_date.advance(-1, 'year')

    image_collection = ee.ImageCollection('NASA/HLS/HLSL30/v002')
    filtered_collection = (image_collection
                           .filterBounds(aoi)
                           .filterDate(one_year_ago, current_date)
                           .sort('system:time_start', False))

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
    if isinstance(region_geometry, ee.geometry.Geometry):
        simplified_geometry = region_geometry.simplify(maxError=100)
    else:
        # If it's a MultiPolygon or other complex geometry, simplify each part
        simplified_geometry = ee.Geometry.MultiPolygon(region_geometry.geometries().map(
            lambda geom: geom.simplify(maxError=100)
        ))

    #logging.info(f"Simplified region geometry: {simplified_geometry.getInfo()}")

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

def get_image_data(aoi, i, properties):
    rgb_image, ndvi_image, image_date, image_count = get_hls_image(aoi)
    if rgb_image is None:
        return None

    rgb_vis = {'min': 0, 'max': 0.3, 'gamma': 1.2}
    ndvi_vis = {'min': -1, 'max': 1, 'palette': ['blue', 'white', 'green']}

    bounds = aoi.bounds().getInfo()['coordinates'][0]
    lon_min, lat_min = bounds[0]
    lon_max, lat_max = bounds[2]

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
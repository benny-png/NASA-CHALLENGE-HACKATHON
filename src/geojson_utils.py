import ee

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

def find_feature_by_name(geojson_dict, region_name, name_keys):
    for feature in geojson_dict['features']:
        properties = feature['properties']
        feature_name = next((properties.get(key) for key in name_keys if key in properties), None)
        if feature_name == region_name:
            return feature
    return None

def create_aoi_from_feature(feature):
    if feature['geometry']['type'] == 'Polygon':
        return ee.Geometry.Polygon(feature['geometry']['coordinates'])
    elif feature['geometry']['type'] == 'MultiPolygon':
        return ee.Geometry.MultiPolygon(feature['geometry']['coordinates'])
    else:
        raise ValueError(f"Unsupported geometry type: {feature['geometry']['type']}")
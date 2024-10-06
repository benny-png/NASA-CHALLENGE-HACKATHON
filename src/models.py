from pydantic import BaseModel, Field
from typing import Union, Dict, List, Optional
from datetime import date

class Coordinates(BaseModel):
    lon1: float
    lat1: float
    lon2: float
    lat2: float

class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: List[List[List[float]]]

class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    properties: Dict = Field(default_factory=dict)
    geometry: GeoJSONGeometry

class GeoJSON(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]

class AOIInput(BaseModel):
    type: str
    data: Union[Coordinates, GeoJSONFeature, GeoJSON]

class DateRange(BaseModel):
    start_date: date
    end_date: date

class FarmAnalysisRequest(BaseModel):
    aoi: AOIInput
    date_range: DateRange

class WeatherAnalysisRequest(BaseModel):
    aoi: AOIInput
    date_range: DateRange
    parameters: List[str]
    
    
class HLSImageRequest(BaseModel):
    aoi: AOIInput
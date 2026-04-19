from geoalchemy2.shape import from_shape
from shapely.geometry import Point

def create_point(longitude: float, latitude: float):
    return from_shape(
        Point(longitude, latitude),
        srid=4326
    )
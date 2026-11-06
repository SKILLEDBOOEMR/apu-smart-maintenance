
import json
from shapely.geometry import Point, shape, MultiPoint
# ---------------------------------------------------------------------------
# Build the Shapely shapes once. Shapely wants (x, y) = (longitude, latitude),
# so we flip each pair here.
# ---------------------------------------------------------------------------
def _poly(points):
    return MultiPoint([(lng, lat) for lat, lng in points]).convex_hull
NEAR_BUFFER = 0.0001

# ---------------------------------------------------------------------------
# The feature
# ---------------------------------------------------------------------------
def locate_user_one_building(latitude, longitude, polygon_data, name=None, tolerance=NEAR_BUFFER):
    """
    Checks the point against ONE polygon (a building, or the whole campus).
    Returns:
      zone:      "building" | "near_building" | "outside"
      buildings: [name] if the point is in or beside the polygon, else []
      message:   human-readable summary
    """
    label = name or "the selected area"

    if not polygon_data:
        return {"zone": "outside", "buildings": [],
                "message": f"No boundary data for {label}."}

    data = json.loads(polygon_data) if isinstance(polygon_data, str) else polygon_data
    poly = shape(data)
    if not poly.is_valid:
        poly = poly.buffer(0)

    point = Point(longitude, latitude)  # longitude first

    if poly.covers(point):
        return {"zone": "building", "buildings": [label],
                "message": f"You are inside {label}."}

    if poly.distance(point) <= tolerance:
        return {"zone": "near_building", "buildings": [label],
                "message": f"You are right next to {label}."}

    return {"zone": "outside", "buildings": [],
            "message": f"You are not at {label}."}


# ---------------------------------------------------------------------------
# Try it: python locate.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    lat = float(input("Latitude:  "))
    lng = float(input("Longitude: "))
    result = locate_user_one_building(lat, lng, polygon_data=None, name="Test Building")
    print(result["message"])
    print(result)
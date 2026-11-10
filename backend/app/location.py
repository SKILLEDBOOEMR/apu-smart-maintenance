
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

def locate_user_one_building(
    latitude: float,
    longitude: float,
    floor: int,
    zones: list[dict],
    tolerance: float = NEAR_BUFFER,
) -> dict:
    """Find zones on the given floor that contain or are near the coordinates."""
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")
    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")
    if tolerance < 0:
        raise ValueError("Tolerance cannot be negative.")

    point = Point(longitude, latitude)  # Shapely uses (longitude, latitude).
    inside = []
    nearby = []

    for zone in zones:
        floor_min = int(zone["floor_min"])
        floor_max = int(zone["floor_max"])
        if not floor_min <= floor <= floor_max:
            continue

        polygon_data = zone["polygon_data"]
        if isinstance(polygon_data, str):
            polygon_data = json.loads(polygon_data)

        polygon = shape(polygon_data)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if polygon.is_empty:
            raise ValueError(f"Invalid or empty polygon for {zone['feature_name']}.")

        name = zone["feature_name"]
        if polygon.covers(point):
            inside.append(name)
        elif polygon.distance(point) <= tolerance:
            nearby.append(name)

    def prefer_specific_zone(candidates: list[str]) -> list[str]:
        if len(candidates) <= 1:
            return candidates

        specific = [
            name for name in candidates
            if name.strip().casefold() != "the whole school"
        ]
        return specific or candidates

    inside = prefer_specific_zone(inside)
    nearby = prefer_specific_zone(nearby)

    if len(inside) == 1:
        return {
            "zone": "building",
            "buildings": inside,
            "message": f"You are inside {inside[0]} on floor {floor}.",
        }

    if len(inside) > 1:
        return {
            "zone": "ambiguous",
            "buildings": inside,
            "message": f"Your location matches multiple areas on floor {floor}.",
        }

    if len(nearby) == 1:
        return {
            "zone": "near_building",
            "buildings": nearby,
            "message": f"You are near {nearby[0]}, but not inside its mapped area.",
        }

    if len(nearby) > 1:
        return {
            "zone": "ambiguous",
            "buildings": nearby,
            "message": "Your location is near multiple areas; the location is uncertain.",
        }

    return {
        "zone": "outside",
        "buildings": [],
        "message": f"No mapped area was found at these coordinates on floor {floor}.",
    }


# ---------------------------------------------------------------------------
# Try it: python locate.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    lat = float(input("Latitude:  "))
    lng = float(input("Longitude: "))
    result = locate_user_one_building(lat, lng, polygon_data=None, name="Test Building")
    print(result["message"])
    print(result)
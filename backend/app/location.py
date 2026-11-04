
from shapely.geometry import Point, MultiPoint

# The general area: the whole campus boundary
CAMPUS = [
    (3.0548813155619268, 101.6993123615807), (3.056651734782864, 101.69858548300478),
    (3.0550259490109526, 101.7008546316791), (3.0570695640127754, 101.70068833472592),
]

# The individual buildings
BUILDINGS = {
    "Tower A": [(3.0553071806557157, 101.70055422426103), (3.055449135652179, 101.7004335248665),
                (3.055682156077376, 101.70071247457828), (3.0555402011117256, 101.70083317397281)],
    "Tower B": [(3.0550110830239587, 101.69985129743542), (3.055176777491983, 101.69970045172211),
                (3.055623650323712, 101.70008259419583), (3.0554228086246065, 101.70025355267092)],
    "Tower C": [(3.0555643066792646, 101.70044157148578), (3.05581071905494, 101.70022163036687),
                (3.055786613498953, 101.70076880095537), (3.056142839993524, 101.70062932609947)],
    "Tower D": [(3.0551946880096805, 101.69950279841721), (3.055312537454393, 101.69941160331915),
                (3.0557223320136564, 101.70001778250054), (3.055840181400419, 101.69990244752356)],
    "Tower E": [(3.055331286228484, 101.69938478123146), (3.0553955677372016, 101.69928285729831),
                (3.055987493115689, 101.69972542174492), (3.056070523346286, 101.69957253584518)],
}
NEAR_BUFFER = 0.0001


# ---------------------------------------------------------------------------
# Build the Shapely shapes once. Shapely wants (x, y) = (longitude, latitude),
# so we flip each pair here.
# ---------------------------------------------------------------------------
def _poly(points):
    return MultiPoint([(lng, lat) for lat, lng in points]).convex_hull


campus_shape = _poly(CAMPUS)
building_shapes = {name: _poly(pts) for name, pts in BUILDINGS.items()}


# ---------------------------------------------------------------------------
# The feature
# ---------------------------------------------------------------------------
def locate_user(latitude, longitude):
    """
    Returns a dict:
      zone:      "building" | "near_building" | "campus_grounds" | "outside_campus"
      buildings: list of building names the point is in or near
      message:   human readable summary
    """
    point = Point(longitude, latitude)  # longitude first

    # 1. Inside a building? (a list, because polygons can overlap)
    inside = [n for n, shape in building_shapes.items() if shape.contains(point)]
    if inside:
        return {"zone": "building", "buildings": inside,
                "message": f"You are inside {', '.join(inside)}."}

    # 2. Just outside a building (GPS drift)?
    near = [n for n, shape in building_shapes.items() if shape.distance(point) <= NEAR_BUFFER]
    if near:
        return {"zone": "near_building", "buildings": near,
                "message": f"You are right next to {', '.join(near)}."}

    # 3. Somewhere on campus, but not at a building?
    if campus_shape.contains(point):
        nearest = min(building_shapes, key=lambda n: building_shapes[n].distance(point))
        return {"zone": "campus_grounds", "buildings": [nearest],
                "message": f"You are on campus grounds. Nearest building: {nearest}."}

    # 4. Not on campus
    return {"zone": "outside_campus", "buildings": [],
            "message": "You are outside the campus area."}


# ---------------------------------------------------------------------------
# Try it: python locate.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    lat = float(input("Latitude:  "))
    lng = float(input("Longitude: "))
    result = locate_user(lat, lng)
    print(result["message"])
    print(result)
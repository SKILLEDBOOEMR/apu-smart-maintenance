"""
test_locate.py - tests for locate.py, based on your real campus data.

Put this file next to locate.py, then run:
    pip install pytest
    pytest -v

Test points were calculated from your polygons:
  - CENTERS:  the middle of each tower
  - NEAR:     about 4 m outside the edge of each tower (inside NEAR_BUFFER)
  - GROUNDS:  on campus, away from every tower
  - OUTSIDE:  nowhere near campus

If you change your polygons, update these points to match.
"""
import pytest

from app.location import (
    BUILDINGS,
    NEAR_BUFFER,
    building_shapes,
    campus_shape,
    locate_user,
)

# (building name, latitude, longitude)
CENTERS = [
    ("Tower A", 3.0554947, 101.7006333),
    ("Tower B", 3.0553086, 101.6999720),
    ("Tower C", 3.0558261, 101.7005153),
    ("Tower D", 3.0555174, 101.6997087),
    ("Tower E", 3.0556962, 101.6994914),
]

NEAR = [
    ("Tower A", 3.0553551, 101.7004662),
    ("Tower B", 3.0550674, 101.6997516),
    ("Tower C", 3.0556658, 101.7003029),
    ("Tower D", 3.0552276, 101.6994324),
    ("Tower E", 3.0560615, 101.6996644),
]

# (nearest building, latitude, longitude)
GROUNDS = [
    ("Tower E", 3.0562, 101.6998),
    ("Tower C", 3.0561, 101.7003),
]

OUTSIDE = [
    (3.0000, 101.0000),   # far away
    (3.0600, 101.7100),   # same area, but well outside the campus boundary
    (0.0, 0.0),           # nonsense coordinates
]


# ---------------------------------------------------------------------------
# 1. The polygons themselves
# ---------------------------------------------------------------------------
def test_campus_polygon_is_valid():
    # Catches the "bowtie" problem (corners in the wrong order)
    assert campus_shape.is_valid


@pytest.mark.parametrize("name", list(BUILDINGS))
def test_building_polygon_is_valid(name):
    assert building_shapes[name].is_valid


@pytest.mark.parametrize("name", list(BUILDINGS))
def test_building_polygon_has_area(name):
    assert building_shapes[name].area > 0


# ---------------------------------------------------------------------------
# 2. Inside a building
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name,lat,lng", CENTERS)
def test_center_of_tower_is_inside_that_tower_only(name, lat, lng):
    result = locate_user(lat, lng)
    assert result["zone"] == "building"
    # exactly one building: also proves your towers do not overlap each other
    assert result["buildings"] == [name]


# ---------------------------------------------------------------------------
# 3. Just outside a building (GPS drift)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name,lat,lng", NEAR)
def test_point_just_outside_tower_is_near_building(name, lat, lng):
    result = locate_user(lat, lng)
    assert result["zone"] == "near_building"
    assert result["buildings"] == [name]


def test_point_on_a_building_corner_counts_as_near():
    # Shapely's contains() is False for points exactly on the edge,
    # so a corner should fall through to near_building, not outside_campus.
    lat, lng = BUILDINGS["Tower A"][3]  # Tower A, east corner
    result = locate_user(lat, lng)
    assert result["zone"] == "near_building"
    assert result["buildings"] == ["Tower A"]


# ---------------------------------------------------------------------------
# 4. Campus grounds (on campus, not at a building)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("nearest,lat,lng", GROUNDS)
def test_point_between_towers_is_campus_grounds(nearest, lat, lng):
    result = locate_user(lat, lng)
    assert result["zone"] == "campus_grounds"
    assert result["buildings"] == [nearest]


# ---------------------------------------------------------------------------
# 5. Outside the campus
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("lat,lng", OUTSIDE)
def test_far_away_point_is_outside_campus(lat, lng):
    result = locate_user(lat, lng)
    assert result["zone"] == "outside_campus"
    assert result["buildings"] == []


# ---------------------------------------------------------------------------
# 6. Result format and mix-ups
# ---------------------------------------------------------------------------
def test_result_has_expected_keys():
    result = locate_user(*CENTERS[0][1:])
    assert set(result) == {"zone", "buildings", "message"}
    assert isinstance(result["message"], str) and result["message"]


def test_message_mentions_the_building():
    name, lat, lng = CENTERS[1]
    assert name in locate_user(lat, lng)["message"]


def test_swapped_latitude_and_longitude_is_not_on_campus():
    # The most common mistake: passing (longitude, latitude).
    name, lat, lng = CENTERS[0]
    assert locate_user(lng, lat)["zone"] == "outside_campus"


def test_near_buffer_is_small():
    # Guard against accidentally setting a huge buffer (0.001 deg is about 110 m)
    assert 0 < NEAR_BUFFER <= 0.0005
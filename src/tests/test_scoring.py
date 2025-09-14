"""
pixel_per_pixel_tests.py

Tests scoring logic using pixel-by-pixel expected time calculation.
"""

from math import sqrt, isclose

# --- CONFIG ---
CLIMB_SPEED = 300        # seconds per foot
PX_PER_FOOT = 8.27532
MOVE_MULT = 0.64         # mph
DEBRIS_SPEED = 0.06      # mph
ground_colors = {"CLEAR": 0.0, "ORANGE": 1, "PURPLE": 2.5, "BLUE": 4, "GRAY": 10}

def mph_to_ft_per_sec(mph):
    return mph * 5280 / 3600

MOVE_MULT_FTPS = mph_to_ft_per_sec(MOVE_MULT)
DEBRIS_SPEED_FTPS = mph_to_ft_per_sec(DEBRIS_SPEED)

# --- SCORING FUNCTION TO TEST ---
def score_line(terrain_line):
    total_time = 0
    prev_tile = terrain_line[0]

    for i in range(1, len(terrain_line)):
        feet_dist = 1 / PX_PER_FOOT
        tile = terrain_line[i]

        speed = MOVE_MULT_FTPS if tile == "CLEAR" else DEBRIS_SPEED_FTPS
        climb_time = CLIMB_SPEED * max(0, ground_colors[tile] - ground_colors[prev_tile])
        move_time = feet_dist / speed

        total_time += climb_time + move_time
        prev_tile = tile

    return total_time

# --- HELPER TO CALCULATE EXPECTED PIXEL-BY-PIXEL ---
def pixel_by_pixel_expected(terrain_line):
    total_time = 0
    prev_tile = terrain_line[0]
    for i in range(1, len(terrain_line)):
        feet_dist = 1 / PX_PER_FOOT
        tile = terrain_line[i]
        speed = MOVE_MULT_FTPS if tile == "CLEAR" else DEBRIS_SPEED_FTPS
        climb_time = CLIMB_SPEED * max(0, ground_colors[tile] - ground_colors[prev_tile])
        move_time = feet_dist / speed
        total_time += climb_time + move_time
        prev_tile = tile
    return total_time

# --- TEST SCENARIOS ---
def test_clear_to_orange():
    terrain_line = ["CLEAR"]*5 + ["ORANGE"]*5
    total_time = score_line(terrain_line)
    expected_time = pixel_by_pixel_expected(terrain_line)
    assert isclose(total_time, expected_time, rel_tol=1e-9)
    print("test_clear_to_orange passed.")

def test_orange_to_clear():
    terrain_line = ["ORANGE"]*5 + ["CLEAR"]*5
    total_time = score_line(terrain_line)
    expected_time = pixel_by_pixel_expected(terrain_line)
    assert isclose(total_time, expected_time, rel_tol=1e-9)
    print("test_orange_to_clear passed.")

def test_single_pixel_climb():
    terrain_line = ["CLEAR", "ORANGE", "CLEAR"]
    total_time = score_line(terrain_line)
    expected_time = pixel_by_pixel_expected(terrain_line)
    assert isclose(total_time, expected_time, rel_tol=1e-9)
    print("test_single_pixel_climb passed.")

def test_multiple_sequential_climbs():
    terrain_line = ["CLEAR", "ORANGE", "PURPLE", "BLUE"]
    total_time = score_line(terrain_line)
    expected_time = pixel_by_pixel_expected(terrain_line)
    assert isclose(total_time, expected_time, rel_tol=1e-9)
    print("test_multiple_sequential_climbs passed.")

def test_start_on_colored_terrain():
    terrain_line = ["ORANGE", "ORANGE", "CLEAR"]
    total_time = score_line(terrain_line)
    expected_time = pixel_by_pixel_expected(terrain_line)
    assert isclose(total_time, expected_time, rel_tol=1e-9)
    print("test_start_on_colored_terrain passed.")

def test_no_movement():
    terrain_line = ["CLEAR"]
    total_time = score_line(terrain_line)
    expected_time = pixel_by_pixel_expected(terrain_line)
    assert isclose(total_time, expected_time, rel_tol=1e-9)
    print("test_no_movement passed.")

def test_gray_penalty():
    terrain_line = ["CLEAR", "GRAY"]
    total_time = score_line(terrain_line)
    expected_time = pixel_by_pixel_expected(terrain_line)
    assert isclose(total_time, expected_time, rel_tol=1e-9)
    print("test_gray_penalty passed.")

# --- RUN ALL TESTS ---
if __name__ == "__main__":
    test_clear_to_orange()
    test_orange_to_clear()
    test_single_pixel_climb()
    test_multiple_sequential_climbs()
    test_start_on_colored_terrain()
    test_no_movement()
    test_gray_penalty()
    print("All tests passed!")

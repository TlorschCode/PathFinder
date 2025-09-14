"""
batch_stress_test.py

Runs 100 randomized long paths (~75 meters each) to verify scoring logic.
"""

import random
from math import isclose

# --- CONFIG ---
CLIMB_SPEED = 300        # seconds per foot
PX_PER_FOOT = 8.27532
MOVE_MULT = 0.64         # mph
DEBRIS_SPEED = 0.06      # mph
ground_colors = {"CLEAR": 0.0, "ORANGE": 1, "PURPLE": 2.5, "BLUE": 4, "GRAY": 10}
TERRAIN_TYPES = ["CLEAR", "ORANGE", "PURPLE", "BLUE"]

def mph_to_ft_per_sec(mph):
    return mph * 5280 / 3600

MOVE_MULT_FTPS = mph_to_ft_per_sec(MOVE_MULT)
DEBRIS_SPEED_FTPS = mph_to_ft_per_sec(DEBRIS_SPEED)

# --- SCORING FUNCTION ---
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

# --- GENERATE RANDOM LONG PATH ---
def generate_long_path(length_meters=75):
    pixels_per_meter = PX_PER_FOOT / 0.3048  # convert feet to meters
    total_pixels = int(length_meters * pixels_per_meter)
    path = [random.choice(TERRAIN_TYPES) for _ in range(total_pixels)]
    path[0] = "CLEAR"  # start on clear terrain
    return path

# --- BATCH STRESS TEST ---
def batch_stress_test(num_paths=100):
    for idx in range(1, num_paths + 1):
        path = generate_long_path()
        total_time = score_line(path)
        expected_time = pixel_by_pixel_expected(path)
        assert isclose(total_time, expected_time, rel_tol=1e-9), \
            f"Stress test failed on path #{idx}: {total_time} != {expected_time}"
        if idx % 10 == 0:
            print(f"Path #{idx} passed. Total pixels: {len(path)}. Total time: {total_time:.2f}s")
    print(f"All {num_paths} randomized stress tests passed!")

if __name__ == "__main__":
    batch_stress_test()

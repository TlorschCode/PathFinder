from random import randint
from math import *

CLIMB_SPEED = 300       # Seconds per foot
ORANGE_HEIGHT = 1       # In feet
PURPLE_HEIGHT = 2.5     # In feet
BLUE_HEIGHT = 4         # In feet
PX_PER_FOOT = 9.143999  # Pixels per foot
MOVE_MULT = 1.46667     # Conversion rate of feet per second from mph

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 800


class Location:
    def __init__(self, x, y):
        self.x = x
        self.y = y


RECOVERY_A = Location(820, 88)
RECOVERY_B = Location(929, 659)

facing_away_penalty = 0.000001
distance_penalty = 0.000000001

ground_types = {"CLEAR": 0.64, "DEBRIS": 0.06}

ground_colors = {
    "ORANGE": 1,
    "PURPLE": 2.5,
    "BLUE": 4,
    "GRAY": 10  # impassable
}

ray_penalties = {
    "CLEAR": 0,
    "ORANGE": 0,
    "PURPLE": 0,
    "BLUE": 0,
    "GRAY": -1,
}


def get_distance(x1, y1, x2, y2):
    return sqrt(((x2 - x1) ** 2) + ((y2 - y1) ** 2))


class Runner:
    def __init__(self, x_, y_, terrain_):
        # self.target = RECOVERY_A if randint(0, 1) == 1 else RECOVERY_B
        self.target = RECOVERY_A
        self.terrain = terrain_
        self.x = x_
        self.y = y_
        self.dir = self.towards(self.target.x, self.target.y)
        self.path = []
        self.time = 0
        self.score = 0
        self.ground_type = list(ground_types.keys())[0]
        self.ground_color = "CLEAR"

    def towards(self, x, y):
        dx = x - self.x
        dy = y - self.y
        angle_rad = atan2(dy, dx)
        angle_deg = degrees(angle_rad)
        return angle_deg % 360

    def get_cur_ground(self):
        return self.terrain[self.x + self.y * SCREEN_WIDTH]

    def move(self):
        if get_distance(self.x, self.y, self.target.x, self.target.y) > 10:
            old_x, old_y = self.x, self.y
            # convert dir to radians for trig
            rad = radians(self.dir)
            self.x += round(cos(rad) * 2)
            self.y += round(sin(rad) * 2)

            # clamp to screen bounds
            self.x = max(0, min(SCREEN_WIDTH - 1, self.x))
            self.y = max(0, min(SCREEN_HEIGHT - 1, self.y))

            # Bounce off impassible gray
            collision_choice = 5 if randint(0, 1) == 1 else -5
            while self.get_cur_ground() == "GRAY":
                self.dir += collision_choice
                rad = radians(self.dir)
                self.x, self.y = old_x, old_y
                self.x += round(cos(rad) * 2)
                self.y += round(sin(rad) * 2)
                # clamp after bounce
                self.x = max(0, min(SCREEN_WIDTH - 1, self.x))
                self.y = max(0, min(SCREEN_HEIGHT - 1, self.y))

            new_ground = self.get_cur_ground()
            old_ground = self.ground_color

            # Check if ground type changed
            if new_ground != old_ground:
                if ground_colors.get(new_ground, 0) > ground_colors.get(old_ground, 0):
                    climb_height = ground_colors[new_ground] - ground_colors.get(old_ground, 0)
                    self.time += CLIMB_SPEED * climb_height
                self.ground_color = new_ground

            # Always add movement time
            distance = get_distance(self.x, self.y, old_x, old_y) / PX_PER_FOOT
            self.time += distance / MOVE_MULT

    def cast_ray(self, angle_deg, max_dist=200, safe_margin=5):
        """
        Cast a ray at angle_deg (absolute) and return a score.
        Terrain penalties are accumulated gradually.
        Gray tiles are penalized more as they get closer, but facing them is allowed.
        """
        angle_rad = radians(angle_deg)
        dx = cos(angle_rad)
        dy = sin(angle_rad)

        x, y = self.x, self.y
        dist = 0
        step = 2  # pixels per step
        score = 0

        while dist < max_dist:
            x += dx * step
            y += dy * step
            dist += step

            # Stay inside screen
            if not (0 <= int(x) < 1024 and 0 <= int(y) < 800):
                break

            tile = self.terrain[int(x) + int(y) * 1024]

            # Soft gray avoidance
            if tile == "GRAY":
                proximity_penalty = ray_penalties["GRAY"] / max(dist, 1)
                score += proximity_penalty
                if dist <= safe_margin:
                    break
            else:
                terrain_penalty = ray_penalties.get(tile, 0)
                score += step * (1 + terrain_penalty / 10)  # smooth accumulation

        return score

    def choose_direction(self, max_turn=5):
        """
        Decide which way to turn based on 360° raycasts with smooth scoring.
        Gradually rotates toward the best-scoring ray to avoid jitter.
        """
        target_angle = self.towards(self.target.x, self.target.y)
        # Cast ray to target with a small bonus
        target_score = self.cast_ray(target_angle) + 20

        rays = 36
        step_angle = 360 / rays
        best_angle = target_angle
        best_score = target_score

        for i in range(rays):
            angle = i * step_angle
            score = self.cast_ray(angle)

            # Small bias toward the target direction
            angle_diff = abs((angle - target_angle + 180) % 360 - 180)
            bias = max(0, 10 - angle_diff)
            score += bias

            if score > best_score:
                best_score = score
                best_angle = angle

        # Also check forward-facing ray to prevent jitter
        forward_score = self.cast_ray(self.dir)
        if forward_score > best_score:
            best_score = forward_score
            best_angle = self.dir

        # Gradually turn toward the best angle
        angle_diff = (best_angle - self.dir + 180) % 360 - 180
        if abs(angle_diff) > max_turn:
            angle_diff = max_turn * (1 if angle_diff > 0 else -1)

        self.dir = (self.dir + angle_diff) % 360


    def update_score(self):
        self.score -= get_distance(self.x, self.y, self.target.x, self.target.y) * distance_penalty
        self.score -= abs(self.towards(self.target.x, self.target.y) - self.dir) * facing_away_penalty

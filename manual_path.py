import sys
import numpy as np
from PIL import Image
from math import sqrt
import pygame

# --- CONFIG ---
IMAGE_FILE = "CrashSite.png"

CLIMB_SPEED = 300       # Seconds per foot (used for gray penalty)
PX_PER_FOOT = 9.143999
MOVE_MULT = 0.64        # Normal speed on clear ground (mph)
DEBRIS_SPEED = 0.06     # Speed on debris (mph)

ground_colors = {"CLEAR": 0.0, "ORANGE": 1, "PURPLE": 2.5, "BLUE": 4, "GRAY": 10}

COLOR_MAP = {
    (250, 110, 51): "ORANGE",
    (142, 59, 230): "PURPLE",
    (43, 186, 247): "BLUE",
    (63, 63, 63): "GRAY"
}

paths = [
    {"path_pt1": None, "path_pt2": None, "control_pts": [], "locked": False}
]

ctrl_pt_size = 5
line_size = 2
dragging_point = None


# --- CLASSES ---
class Location:
    def __init__(self, x_, y_):
        self.x = x_
        self.y = y_


# --- UTILITY FUNCTIONS ---
def distance(x1, y1, x2, y2):
    return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def closest_color(rgb, color_map, max_dist=5):
    """Return terrain type if within max_dist in RGB, else CLEAR."""
    r, g, b = map(int, rgb)
    best_match = "CLEAR"
    min_dist = float("inf")

    for k, terrain_type in color_map.items():
        rk, gk, bk = k
        dist = (r - rk) ** 2 + (g - gk) ** 2 + (b - bk) ** 2
        if dist < min_dist:
            min_dist = dist
            best_match = terrain_type

    return best_match if min_dist <= max_dist ** 2 else "CLEAR"


def load_image_as_terrain(image_file):
    img = Image.open(image_file).convert("RGB")
    w, h = img.size
    arr = np.array(img, dtype=np.uint8)
    flat_pixels = arr.reshape(-1, 3)
    terrain = [closest_color(tuple(rgb), COLOR_MAP) for rgb in flat_pixels]
    surface_ = pygame.image.load(image_file)
    return terrain, w, h, surface_


def get_bezier_loc(level_, t_) -> Location:
    lvl = level_
    while len(lvl) > 1:
        next_level = []
        for j in range(len(lvl) - 1):
            x0, y0 = lvl[j].x, lvl[j].y
            x1, y1 = lvl[j + 1].x, lvl[j + 1].y
            x = x0 + (x1 - x0) * t_
            y = y0 + (y1 - y0) * t_
            next_level.append(Location(x, y))
        lvl = next_level
    return Location(int(round(lvl[0].x)), int(round(lvl[0].y)))


def path_score(path, terrain, width=1024, height=800, curve_steps=500):
    ctrl_pts = path["control_pts"]
    pt1 = path["path_pt1"]
    pt2 = path["path_pt2"]

    if not (pt1 and pt2) or len(ctrl_pts) == 0:
        return 0

    full_path = [pt1] + ctrl_pts + [pt2]
    total_time = 0
    prev_px, prev_py = None, None

    for s in range(curve_steps + 1):
        t = s / curve_steps
        loc = get_bezier_loc(full_path, t)
        px, py = loc.x, loc.y

        if not (prev_px is None or prev_py is None):
            dx, dy = px - prev_px, py - prev_py
            steps = max(abs(dx), abs(dy))
            for i in range(1, steps + 1):
                x = int(round(prev_px + dx * i / steps))
                y = int(round(prev_py + dy * i / steps))

                if not (0 <= x < width and 0 <= y < height):
                    continue

                tile = terrain[x + y * width]

                step_dx = x - prev_px
                step_dy = y - prev_py
                pixel_dist = (step_dx ** 2 + step_dy ** 2) ** 0.5
                feet_dist = pixel_dist / PX_PER_FOOT

                speed = MOVE_MULT if tile == "CLEAR" else DEBRIS_SPEED
                climb_time = feet_dist * 999999 if tile == "GRAY" else 0
                move_time = feet_dist / speed

                total_time += climb_time + move_time

                prev_px, prev_py = x, y
        else:
            prev_px, prev_py = px, py

    return total_time


# --- DRAWING FUNCTIONS ---
def draw_bezier(screen):
    global ctrl_pt_size, line_size, paths
    prev_p = Location(0, 0)
    for path in paths:
        pt1 = path["path_pt1"]
        pt2 = path["path_pt2"]
        ctrl_pts = path["control_pts"]
        if not (pt1 is None or pt2 is None):
            # Draw control points
            pygame.draw.circle(screen, (100, 100, 100), (pt1.x, pt1.y), ctrl_pt_size)
            pygame.draw.circle(screen, (100, 100, 100), (pt2.x, pt2.y), ctrl_pt_size)

            try:
                prev_p = ctrl_pts[0]
            except IndexError:
                pass
            else:
                pygame.draw.line(screen, (160, 160, 160), (pt1.x, pt1.y), (ctrl_pts[0].x, ctrl_pts[0].y), line_size)
                pygame.draw.line(screen, (160, 160, 160), (pt2.x, pt2.y),
                                 (ctrl_pts[-1].x, ctrl_pts[-1].y), line_size)

            for p in ctrl_pts:
                pygame.draw.circle(screen, (150, 150, 150), (p.x, p.y), ctrl_pt_size)
                pygame.draw.line(screen, (160, 160, 160), (prev_p.x, prev_p.y), (p.x, p.y), line_size)
                prev_p = p

            # Draw Bezier curve
            full_path = [pt1] + ctrl_pts + [pt2]
            steps = 200
            for s in range(steps + 1):
                t = s / steps
                draw_pos = get_bezier_loc(full_path, t)
                pygame.draw.circle(screen, (0, 200, 0), (draw_pos.x, draw_pos.y), line_size)


def add_path_point(pos: Location, click: str):
    global ctrl_pt_size, dragging_point

    for path in paths:
        pt1 = path["path_pt1"]
        pt2 = path["path_pt2"]
        ctrl_pts = path["control_pts"]

        if click.lower() == "left":
            # Grab existing points
            for p in ([pt1, pt2] + ctrl_pts):
                if p and distance(p.x, p.y, pos.x, pos.y) <= ctrl_pt_size + 3:
                    dragging_point = p
                    return

            # Add new point
            if pt1 is None:
                path["path_pt1"] = pos
            elif pt2 is None:
                path["path_pt2"] = pos
            elif not path["locked"]:
                path["control_pts"].append(pos)

        elif click.lower() == "right":
            paths.append({"path_pt1": pos, "path_pt2": None, "control_pts": [], "locked": False})
            paths[-2]["locked"] = True
            return


# --- MAIN ---
def main():
    global dragging_point
    terrain, width, height, surface = load_image_as_terrain(IMAGE_FILE)
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Path Visualizer")
    clock = pygame.time.Clock()
    font_obj = pygame.font.SysFont(None, 24)

    hover_point = None
    score = None

    running = True
    while running:
        for evnt in pygame.event.get():
            if evnt.type == pygame.QUIT:
                running = False
            elif evnt.type == pygame.MOUSEBUTTONDOWN:
                if evnt.button == 1:
                    add_path_point(Location(evnt.pos[0], evnt.pos[1]), "left")
                elif evnt.button == 3:
                    add_path_point(Location(evnt.pos[0], evnt.pos[1]), "right")
            elif evnt.type == pygame.MOUSEBUTTONUP:
                if evnt.button == 1:
                    dragging_point = None
            elif evnt.type == pygame.MOUSEMOTION:
                hover_point = evnt.pos
                if dragging_point:
                    dragging_point.x = evnt.pos[0]
                    dragging_point.y = evnt.pos[1]
            elif evnt.type == pygame.KEYDOWN:
                if evnt.key == pygame.K_SPACE and paths:
                    score = path_score(paths[0], terrain, width, height)
                    print(f"Path score: {score:.2f} seconds")

        screen.blit(surface, (0, 0))
        draw_bezier(screen)

        # Display score next to cursor
        if hover_point and score is not None:
            text_surf = font_obj.render(f"{score:.2f} s", True, (0, 0, 0))
            text_bg = pygame.Surface((text_surf.get_width() + 6, text_surf.get_height() + 4))
            text_bg.fill((255, 255, 255))
            text_bg.blit(text_surf, (3, 2))
            screen.blit(text_bg, (hover_point[0] + 10, hover_point[1] + 10))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

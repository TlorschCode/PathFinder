from pygame import *
import sys
import numpy as np
from PIL import Image
from math import sqrt

class Location:
    def __init__(self, x_, y_):
        self.x = x_
        self.y = y_
    def getx(self):
        return self.x
    def gety(self):
        return self.y

# --- CONFIG ---
IMAGE_FILE = "CrashSite.png"

CLIMB_SPEED = 300       # Seconds per foot
PX_PER_FOOT = 9.143999
MOVE_MULT = 0.64        # Normal speed on clear ground (mph)
DEBRIS_SPEED = 0.06     # Speed on debris (mph)

ground_colors = {"CLEAR": 0.0, "ORANGE": 1, "PURPLE": 2.5, "BLUE": 4, "GRAY": 10}

# Exact RGB mapping for terrain types
COLOR_MAP = {
    (227, 117, 64): "ORANGE",
    (134, 61, 230): "PURPLE",
    (106, 184, 245): "BLUE",
    (63, 63, 63): "GRAY"
}

paths = [
    {
        "path_pt1": None,
        "path_pt2": None,
        "control_pts": [],
        "locked": False
    }
]
ctrl_pt_size = 5
line_size = 2
dragging_point = None

def distance(x1, y1, x2, y2):
    return sqrt(abs((x2 -x1)**2) + abs((y2 - y1)**2))

def closest_color(rgb, color_map, max_dist=5):
    """Return terrain type if within max_dist in RGB, else CLEAR."""
    r, g, b = map(int, rgb)
    best_match = "CLEAR"
    min_dist = float("inf")

    for k, terrain_type in color_map.items():
        rk, gk, bk = k
        dist = (r - rk)**2 + (g - gk)**2 + (b - bk)**2
        if dist < min_dist:
            min_dist = dist
            best_match = terrain_type

    # compare squared distance with threshold^2
    if min_dist <= max_dist**2:
        return best_match
    return "CLEAR"


def load_image_as_terrain(image_file):
    img = Image.open(image_file).convert("RGB")
    w, h = img.size
    arr = np.array(img, dtype=np.uint8)
    flat_pixels = arr.reshape(-1, 3)
    terrain = [closest_color(tuple(rgb), COLOR_MAP) for rgb in flat_pixels]
    surface_ = image.load(image_file)
    return terrain, w, h, surface_

def path_score(path, terrain, width=1024, step_size=1):
    """Calculate total time along the path, pixel by pixel."""
    if len(path) < 2:
        return 0

    total_time = 0
    for i in range(1, len(path)):
        x0, y0 = path[i-1]
        x1, y1 = path[i]

        dx = x1 - x0
        dy = y1 - y0
        distance = sqrt(dx**2 + dy**2)
        steps = max(int(distance / step_size), 1)

        for s in range(steps):
            t = s / steps
            px = int(round(x0 + dx * t))
            py = int(round(y0 + dy * t))

            # Clamp to screen bounds
            px = max(0, min(width-1, px))
            py = max(0, min(800-1, py))

            tile = terrain[px + py * width]
            height = ground_colors.get(tile, 0)

            # Climb penalty only for gray
            climb_time = CLIMB_SPEED * height if tile == "GRAY" else 0

            # Movement speed penalty for any debris (orange/purple/blue)
            speed = DEBRIS_SPEED if tile in ("ORANGE", "PURPLE", "BLUE") else MOVE_MULT
            move_time = (step_size / PX_PER_FOOT) / speed

            total_time += climb_time + move_time
    return total_time

def log(*args):
    print(f"DEBUG: {args}")

def draw_bezier(screen):
    global ctrl_pt_size
    global line_size
    global paths
    prev_p = Location(0, 0)
    for path in paths:
        pt1 = path["path_pt1"]
        pt2 = path["path_pt2"]
        ctrl_pts = path["control_pts"]
        if not (pt1 is None or pt2 is None):
            t = 0
            # Draw control points
            draw.circle(screen, (100, 100, 100), (pt1.getx(), pt1.gety()), ctrl_pt_size)
            draw.circle(screen, (100, 100, 100), (pt2.getx(), pt2.gety()), ctrl_pt_size)
            try:
                prev_p = ctrl_pts[0]
            except IndexError:
                pass
            else:
                draw.line(screen, (160, 160, 160), (pt1.getx(), pt1.gety()), (ctrl_pts[0].getx(), ctrl_pts[0].gety()), line_size)
                draw.line(screen, (160, 160, 160), (pt2.getx(), pt2.gety()), (ctrl_pts[len(ctrl_pts) - 1].getx(), ctrl_pts[len(ctrl_pts) - 1].gety()), line_size)
            for p in ctrl_pts:
                draw.circle(screen, (150, 150, 150), (p.getx(), p.gety()), ctrl_pt_size)
                draw.line(screen, (160, 160, 160), (prev_p.getx(), prev_p.gety()), (p.getx(), p.gety()), line_size)
                prev_p = p
            # Set up a temporary path containing the control points
            full_path = [pt1]
            for p in ctrl_pts:
                full_path.append(p)
            full_path.append(pt2)
            # Draw Bezier curve
            steps = 200  # number of samples
            for s in range(steps + 1):
                t = s / steps  # 0..1

                level = full_path[:]  # copy
                while len(level) > 1:
                    next_level = []
                    for j in range(len(level) - 1):
                        x0, y0 = level[j].x, level[j].y
                        x1, y1 = level[j+1].x, level[j+1].y
                        # linear interpolation
                        x = x0 + (x1 - x0) * t
                        y = y0 + (y1 - y0) * t
                        next_level.append(Location(x, y))
                    level = next_level

                # Draw the final interpolated point
                px, py = int(round(level[0].x)), int(round(level[0].y))
                draw.circle(screen, (0, 200, 0), (px, py), line_size)


def add_path_point(pos: Location, click: str):
    global ctrl_pt_size, dragging_point

    for path in paths:
        pt1 = path["path_pt1"]
        pt2 = path["path_pt2"]
        ctrl_pts = path["control_pts"]

        if click.lower() == "left":
            # Check for grabbing existing points
            if pt1 and distance(pt1.x, pt1.y, pos.x, pos.y) <= ctrl_pt_size + 3:
                dragging_point = pt1
                return
            if pt2 and distance(pt2.x, pt2.y, pos.x, pos.y) <= ctrl_pt_size + 3:
                dragging_point = pt2
                return
            for p in ctrl_pts:
                if distance(p.x, p.y, pos.x, pos.y) <= ctrl_pt_size + 3:
                    dragging_point = p
                    return

            # If no grab, add new point
            if pt1 is None:
                path["path_pt1"] = pos
                return
            elif pt2 is None:
                path["path_pt2"] = pos
                return
            else:
                if not path["locked"]:
                    path["control_pts"].append(pos)
                    return

        elif click.lower() == "right":
            # Start a new path, independent of the others
            paths.append({
                "path_pt1": pos,
                "path_pt2": None,
                "control_pts": [],
                "locked": False
            })
            paths[len(paths) - 2]["locked"] = True  # Lock last active path
            return

    



# --- Main ---
def main():
    global dragging_point
    terrain, width, height, surface = load_image_as_terrain(IMAGE_FILE)
    init()
    screen = display.set_mode((width, height))
    display.set_caption("Path Visualizer")
    clock = time.Clock()

    hover_point = None

    running = True
    while running:
        for evnt in event.get():
            if evnt.type == QUIT:
                running = False
            elif evnt.type == MOUSEBUTTONDOWN:
                if evnt.button == 1:  # left click
                    add_path_point(Location(evnt.pos[0], evnt.pos[1]), "left")
                elif evnt.button == 3:
                    add_path_point(Location(evnt.pos[0], evnt.pos[1]), "right")
            elif evnt.type == MOUSEBUTTONUP:
                if evnt.button == 1:
                    dragging_point = None  # release
            elif evnt.type == MOUSEMOTION:
                hover_point = evnt.pos
                if dragging_point:
                    # update dragged point
                    dragging_point.x = evnt.pos[0]
                    dragging_point.y = evnt.pos[1]
        screen.blit(surface, (0, 0))
        draw_bezier(screen)
        display.flip()
        clock.tick(60)
    quit()
    sys.exit()

if __name__ == "__main__":
    main()

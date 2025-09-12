import sys
import numpy as np
from PIL import Image
from math import sqrt
import pygame
from path_save import saved
from bezier_classes import Path, Location

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

paths = [Path(None, None)]

ctrl_pt_size = 5
line_size = 2
dragging_point = None


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


def path_score(path: Path, terrain, width, height, curve_steps=500):
    ctrl_pts = path.control_pts
    pt1 = path.path_pt1
    pt2 = path.path_pt2

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
                pixel_dist = sqrt(step_dx ** 2 + step_dy ** 2)
                feet_dist = pixel_dist / PX_PER_FOOT

                speed = MOVE_MULT if tile == "CLEAR" else DEBRIS_SPEED
                climb_time = feet_dist * 999999 if tile == "GRAY" else 0
                move_time = feet_dist / speed

                total_time += climb_time + move_time

                prev_px, prev_py = x, y
        else:
            prev_px, prev_py = px, py

    return total_time


def score_all_paths(terrain, width=1024, height=800, curve_steps=500):
    total_time = 0
    for p in paths:
        total_time += path_score(p, terrain, width, height)
    return total_time

# --- DRAWING FUNCTIONS ---
def draw_bezier(screen):
    global ctrl_pt_size, line_size, paths
    prev_p = Location(0, 0)
    main_points_color = (100, 100, 100)
    control_line_color = (160, 160, 160)
    control_point_color = (160, 160, 160)
    for path in paths:
        pt1 = path.path_pt1
        pt2 = path.path_pt2
        ctrl_pts = path.control_pts
        if not (pt1 is None or pt2 is None):
            # Draw main control points  vvv
            pygame.draw.circle(screen, main_points_color, (pt1.x, pt1.y), ctrl_pt_size)
            pygame.draw.circle(screen, main_points_color, (pt2.x, pt2.y), ctrl_pt_size)
            # vvv  Draw control point lines  vvv
            try:
                prev_p = ctrl_pts[0]
            except IndexError:
                pass
            else:
                pygame.draw.line(screen, control_line_color, (pt1.x, pt1.y), (ctrl_pts[0].x, ctrl_pts[0].y), line_size)
                pygame.draw.line(screen, control_line_color, (pt2.x, pt2.y),
                                 (ctrl_pts[-1].x, ctrl_pts[-1].y), line_size)
            # vvv  Draw extra control points  vvv
            for p in ctrl_pts:
                pygame.draw.circle(screen, (150, 150, 150), (p.x, p.y), ctrl_pt_size)
                pygame.draw.line(screen, control_line_color, (prev_p.x, prev_p.y), (p.x, p.y), line_size)
                prev_p = p

            # vvv  Draw Bezier curve  vvv
            full_path = [pt1] + ctrl_pts + [pt2]
            steps = 200
            for s in range(steps + 1):
                t = s / steps
                draw_pos = get_bezier_loc(full_path, t)
                pygame.draw.circle(screen, (0, 200, 0), (draw_pos.x, draw_pos.y), line_size)


def add_path_point(pos: Location, click: str):
    global ctrl_pt_size, dragging_point

    for path in paths:
        pt1 = path.path_pt1
        pt2 = path.path_pt2
        ctrl_pts = path.control_pts

        if click.lower() == "left":
            # Grab existing points
            for p in ([pt1, pt2] + ctrl_pts):
                if p and distance(p.x, p.y, pos.x, pos.y) <= ctrl_pt_size + 3:
                    dragging_point = p
                    return

            # Add new point
            if pt1 is None:
                path.setPt1(pos)
            elif pt2 is None:
                path.setPt2(pos)
            elif not path.locked:
                path.addCtrlPt(pos)

        elif click.lower() == "right":
            paths.append(Path(pos, None))
            paths[-2].lock() # Lock previous path (wraps by using a negative index)
            return


def remove_path_pts(pos: Location):
    for path in paths:
        pt1 = path.path_pt1
        pt2 = path.path_pt2
        ctrl_pts = path.control_pts
        # Grab existing points
        for p in ([pt1, pt2] + ctrl_pts):
            if p and distance(p.x, p.y, pos.x, pos.y) <= ctrl_pt_size + 3:
                if p == pt1 or p == pt2:
                    paths.remove(path)
                    return
                path.control_pts.remove(p)
                return


def save_path() -> str:
    output = "["
    for path in paths:
        ctrl_pts_text = "["
        if len(path.control_pts) > 0:
            for pt in path.control_pts:
                if path.control_pts.index(pt) != len(path.control_pts) - 1:
                    ctrl_pts_text += f"Location({pt.x}, {pt.y}), "
                else:
                    ctrl_pts_text += f"Location({pt.x}, {pt.y})]"
        else:
            ctrl_pts_text = "[]"
        try:
            if paths.index(path) != len(paths) - 1:
                output += f"Path(Location({path.path_pt1.x}, {path.path_pt1.y}), Location({path.path_pt2.x}, {path.path_pt2.y}), {ctrl_pts_text}, {path.locked}), " # type: ignore
            else:
                output += f"Path(Location({path.path_pt1.x}, {path.path_pt1.y}), Location({path.path_pt2.x}, {path.path_pt2.y}), {ctrl_pts_text}, {path.locked})]" # type: ignore
        except ValueError:
            pass
    return output


# --- MAIN ---
def main():
    global dragging_point
    global paths
    paths = saved
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
        mouse_click = ""
        mouse_pos = Location(None, None)
        for evnt in pygame.event.get():
            if evnt.type == pygame.QUIT:
                running = False
            elif evnt.type == pygame.MOUSEBUTTONDOWN:
                mods = pygame.key.get_mods()
                if evnt.button == 1:  # Left click
                    if mods & pygame.KMOD_CTRL:  # Ctrl held
                        remove_path_pts(Location(evnt.pos[0], evnt.pos[1]))
                    else:
                        add_path_point(Location(evnt.pos[0], evnt.pos[1]), "left")
                elif evnt.button == 3:  # Right click
                    add_path_point(Location(evnt.pos[0], evnt.pos[1]), "right")
            elif evnt.type == pygame.MOUSEBUTTONUP:
                mouse_click = ""
                if evnt.button == 1:
                    dragging_point = None
            elif evnt.type == pygame.MOUSEMOTION:
                mouse_pos = Location(evnt.pos[0], evnt.pos[1])
                hover_point = evnt.pos
                if dragging_point:
                    dragging_point.x = evnt.pos[0]
                    dragging_point.y = evnt.pos[1]
            elif evnt.type == pygame.KEYDOWN:  # Calculate path times
                if evnt.key == pygame.K_SPACE and paths:
                    score = score_all_paths(terrain, width, height)
                    print(f"Path score: {score:.2f} seconds")
                elif evnt.key == pygame.K_s and paths:
                    with open("path_save.py", "w") as file:
                        file.write(f"from bezier_classes import Path, Location\nsaved = {save_path()}")
                if evnt.key == pygame.K_LCTRL:
                    if mouse_click != "":
                        print("REMOVING PT")
                        remove_path_pts(mouse_pos)

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

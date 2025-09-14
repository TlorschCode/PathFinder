import sys
import numpy as np
from PIL import Image
from math import sqrt
import pygame
from path_save import saved_paths
from bezier_classes import Path, Location
import copy


#|  --- INFO ---  |#
'''
The size of one meter (one grid square) is ~27.15px, with ~0.02px of imprecision
There are 8.27531973 pixels per foot, with ~0.000000005px of imprecision

Clear ground has a movement speed of        0.64mph, or 0.9386667ft/s
Terrain with debris has a movement speed of 0.06mph, or 0.088ft/s

Orange terrain is 1 foot high
Purple terrain is 2.5 feet high
Blue terrain is   4 feet high
Gray terrain is impassible

Orange terrain has an RGB identifier of:  (250, 110, 51)
Purple terrain has an RGB identfier of:   (142, 59, 230)
Blue terrain has an RGB identifier of:    (43, 186, 247)
Gray terrain has an RGB identifier of:    (63, 63, 63)

Given that no robot width was specified, no robot width is taken into account
'''


# --- CONFIG ---
IMAGE_FILE = "src/CrashSite.png"
PATH_SAVE_FILE = "src/path_save.py"
BEST_PATH_FILE = "src/best_path.py"

CLIMB_SPEED = 300       # Seconds per foot
PX_PER_FOOT = 8.27531973
MOVE_MULT = 0.64        # Normal speed on clear ground (mph)
DEBRIS_SPEED = 0.06     # Speed on debris (mph)

ground_colors = {"CLEAR": 0.0, "ORANGE": 1, "PURPLE": 2.5, "BLUE": 4, "GRAY": 9999}

COLOR_MAP = {
    (250, 110, 51): "ORANGE",
    (142, 59, 230): "PURPLE",
    (43, 186, 247): "BLUE",
    (63, 63, 63): "GRAY"
}

paths = [Path(None, None)]
running = True
remember_graph = False
calculate_graph = False
prev_paths = []
terrain = []
width = 1024
height = 800
surface = 0
score = 0
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Path Visualizer")

ctrl_pt_size = 5
dragging_point = None


#|  --- UTILITY FUNCTIONS ---  |#
def distance(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def map_value(x, in_min, in_max, out_min, out_max):
    """Maps a value x from one range to another."""
    if in_max - in_min == 0:  # avoid divide by zero
        raise ValueError("in_min and in_max cannot be the same")
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def get_key(val_, dict_: dict):
    for key, value in dict_.items():
        if value == val_:
            return key
    return None


#|  --- TERRAIN FUNCTIONS ---  |#
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


#|  --- BEZIER FUNCTIONS ---  |#
def get_bezier_loc(level_, t_) -> Location:
    lvl = level_
    while len(lvl) > 1:
        next_level = []
        for j in range(len(lvl) - 1):
            x0, y0 = lvl[j]
            x1, y1 = lvl[j+1]
            x = x0 + (x1 - x0) * t_
            y = y0 + (y1 - y0) * t_
            next_level.append(Location(x, y))
        lvl = next_level
    return Location(int(round(lvl[0].x)), int(round(lvl[0].y)))

def get_pixel_status(prev_tile, current_tile):
    """
    Returns the color of the current tile
    """

    if current_tile == "GRAY":
        status = "IMPASSIBLE"
    elif ground_colors[current_tile] - ground_colors[prev_tile] > 0:
        status = "CLIMB"
    elif current_tile == "CLEAR":
        status = "CLEAR"
    else:
        status = "TERRAIN"

    return status

def get_pixel_score(prev_tile, current_tile, feet_dist):
    """
    Calculate movement and climb info for a single pixel.

    Returns:
        move_time: time in seconds for this pixel
        climb_time: climbing penalty in seconds
        status: one of 'CLEAR', 'TERRAIN', 'CLIMB', 'IMPASSIBLE'
    """
    speed = MOVE_MULT if current_tile == "CLEAR" else DEBRIS_SPEED
    climb_time = max(0, CLIMB_SPEED * (ground_colors[current_tile] - ground_colors[prev_tile]))
    move_time = feet_dist / speed

    return move_time, climb_time, get_pixel_status(prev_tile, current_tile)


def path_score(path: Path, curve_steps=500) -> float:
    """
    Score a path in seconds and optionally draw a highlight overlay on a surface.
    """
    ctrl_pts = path.control_pts
    pt1 = path.path_pt1
    pt2 = path.path_pt2

    if not (pt1 and pt2) or len(ctrl_pts) == 0:
        return 0

    full_path = [pt1] + ctrl_pts + [pt2]
    total_time = 0
    prev_px, prev_py = None, None
    prev_tile = "CLEAR"
    tile = "CLEAR"

    for s in range(curve_steps + 1):
        t = s / curve_steps
        loc = get_bezier_loc(full_path, t)
        px, py = loc

        if prev_px is not None and prev_py is not None:
            dx, dy = px - prev_px, py - prev_py
            steps = max(abs(dx), abs(dy))

            for i in range(1, steps + 1):
                x = int(round(prev_px + dx * i / steps))
                y = int(round(prev_py + dy * i / steps))
                if not (0 <= x < width and 0 <= y < height):
                    continue

                tile = terrain[x + y * width]
                pixel_dist = sqrt((x - prev_px) ** 2 + (y - prev_py) ** 2) / PX_PER_FOOT

                move_time, climb_time, status = get_pixel_score(prev_tile, tile, pixel_dist)
                total_time += move_time + climb_time

            prev_tile = tile
            prev_px, prev_py = px, py
        else:
            prev_px, prev_py = px, py

    return total_time



def score_all_paths(path_list, curve_steps=500):
    global terrain, width, height
    total_time = 0
    for p in path_list:
        p.score = path_score(p)
        total_time += p.score
    return total_time


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

def _normalize_color_tuple(col):
    # Accepts tuples with 3 or 4 elements, floats or ints.
    # Returns a tuple of ints clamped to 0..255 and length 3 or 4.
    if col is None:
        return (0, 0, 0)
    col_list = list(col)
    # if user passed a single int or something odd, try to coerce to 3-tuple
    if len(col_list) == 1:
        col_list = [col_list[0], col_list[0], col_list[0]]
    # round and clamp
    col_list = [int(round(c)) if isinstance(c, (int, float)) else int(c) for c in col_list]
    col_list = [_clamp(c, 0, 255) for c in col_list]
    if len(col_list) >= 4:
        return tuple(col_list[:4])
    return tuple(col_list[:3])

def draw_bezier(path_list, path_color=(0, 200, 0, 255), line_size=3, draw_controllers=True, show_terrain=False):
    """
    Draw Bezier curves and control points with defensive checks:
     - coerce coords to ints
     - clamp coordinates to surface bounds
     - normalize color tuple to valid ints 0..255
     - skip drawing when coords outside surface or terrain index invalid
    """
    global ctrl_pt_size, screen, width, height

    # Defensive: normalize incoming path_color
    path_color = _normalize_color_tuple(path_color)

    # Create a temporary surface with per-pixel alpha
    temp_surf = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)

    main_points_color = _normalize_color_tuple((100, 100, 100, 255))
    control_line_color = _normalize_color_tuple((160, 160, 160, 255))
    control_point_color = _normalize_color_tuple((150, 150, 150, 255))

    for path in path_list:
        prev_tile = "CLEAR"
        pt1 = path.path_pt1
        pt2 = path.path_pt2
        ctrl_pts = path.control_pts

        if not (pt1 is None or pt2 is None):
            # Draw control points and lines (coerce coords)
            if draw_controllers:
                try:
                    pygame.draw.circle(temp_surf, main_points_color, (int(pt1.x), int(pt1.y)), ctrl_pt_size)
                    pygame.draw.circle(temp_surf, main_points_color, (int(pt2.x), int(pt2.y)), ctrl_pt_size)
                except Exception:
                    # defensive fallback in case pt1/pt2 are tuples instead of Location
                    try:
                        pygame.draw.circle(temp_surf, main_points_color, (int(pt1[0]), int(pt1[1])), ctrl_pt_size)
                        pygame.draw.circle(temp_surf, main_points_color, (int(pt2[0]), int(pt2[1])), ctrl_pt_size)
                    except Exception:
                        pass

                if ctrl_pts:
                    # draw connector lines safely
                    cp0 = ctrl_pts[0]
                    try:
                        start0 = (int(cp0.x), int(cp0.y))
                    except Exception:
                        start0 = (int(cp0[0]), int(cp0[1]))
                    try:
                        pygame.draw.line(temp_surf, control_line_color, (int(pt1.x), int(pt1.y)), start0, line_size)
                    except Exception:
                        pass

                    cplast = ctrl_pts[-1]
                    try:
                        end_last = (int(cplast.x), int(cplast.y))
                    except Exception:
                        end_last = (int(cplast[0]), int(cplast[1]))
                    try:
                        pygame.draw.line(temp_surf, control_line_color, (int(pt2.x), int(pt2.y)), end_last, line_size)
                    except Exception:
                        pass

                    prev_p = ctrl_pts[0]
                    for p in ctrl_pts[1:]:
                        try:
                            pygame.draw.line(temp_surf, control_line_color, (int(prev_p.x), int(prev_p.y)), (int(p.x), int(p.y)), line_size)
                        except Exception:
                            try:
                                pygame.draw.line(temp_surf, control_line_color, (int(prev_p[0]), int(prev_p[1])), (int(p[0]), int(p[1])), line_size)
                            except Exception:
                                pass
                        prev_p = p

                    for p in ctrl_pts:
                        try:
                            pygame.draw.circle(temp_surf, control_point_color, (int(p.x), int(p.y)), ctrl_pt_size)
                        except Exception:
                            try:
                                pygame.draw.circle(temp_surf, control_point_color, (int(p[0]), int(p[1])), ctrl_pt_size)
                            except Exception:
                                pass

            # Draw Bezier curve
            full_path = [pt1] + ctrl_pts + [pt2]
            steps = 200
            tile = "CLEAR"
            for s in range(steps + 1):
                t = s / steps
                draw_pos = get_bezier_loc(full_path, t)
                # coerce to ints safely
                # try:
                dx = int(round(draw_pos.x))
                dy = int(round(draw_pos.y))
                # except Exception:
                #     # fallback if draw_pos is a tuple (x,y)
                #     try:
                #         dx = int(round(draw_pos[0]))
                #         dy = int(round(draw_pos[1]))
                #     except Exception:
                #         continue  # skip this point if we can't coerce coordinates

                # bounds check: skip drawing points outside the screen
                if dx < 0 or dy < 0 or dx >= screen.get_width() or dy >= screen.get_height():
                    continue

                if show_terrain:
                    # safe terrain lookup
                    idx = dx + (dy * width)
                    if idx < 0 or idx >= len(terrain):
                        color_key = "CLEAR"
                    else:
                        tile = terrain[idx]
                        color_key = get_pixel_status(prev_tile, tile)
                        prev_tile = tile

                    # pick color mapping safely
                    draw_col = (0, 0, 0)
                    if color_key == "TERRAIN":
                        base_color = get_key(tile, COLOR_MAP) if get_key(tile, COLOR_MAP) is not None else (0, 0, 0)
                        if base_color:
                            draw_col = (base_color[0] // 2, base_color[1] // 2, base_color[2] // 2)
                    elif color_key == "CLIMB":
                        draw_col = (255, 0, 0)
                    elif color_key == "IMPASSIBLE":
                        draw_col = (0, 0, 0)
                    else:
                        draw_col = (0, 200, 0)

                    draw_col = _normalize_color_tuple(draw_col)
                    pygame.draw.circle(temp_surf, draw_col, (dx, dy), line_size)
                else:
                    pygame.draw.circle(temp_surf, path_color, (dx, dy), line_size)

    # Blit the temp surface onto the main screen
    screen.blit(temp_surf, (0, 0))


def add_path_point(pos: Location | None, click: str):
    global ctrl_pt_size, dragging_point
    if pos is None:  # Exit the function if pos is None
        return
    for path in paths:
        pt1 = path.path_pt1
        pt2 = path.path_pt2
        ctrl_pts = path.control_pts
        # vvv Check for correct click vvv
        if click.lower() == "left":
            # vvv Grab existing points vv
            for p in ([pt1, pt2] + ctrl_pts):
                if p and distance(p, pos) <= ctrl_pt_size + 3:
                    dragging_point = p
                    return
            # vvv Add new point vvv
            if pt1 is None:
                path.setPt1(pos)
            elif pt2 is None:
                path.setPt2(pos)
            elif not path.locked:
                path.addCtrlPt(pos)
        # vvv Make new path vvv
        elif click.lower() == "right":
            paths.append(Path(pos, None))
            paths[-2].lock() # Lock previous path (wraps by using a negative index)
            return


def remove_path_pts(pos: Location | None):
    if pos is None:
        return
    for path in paths:
        pt1 = path.path_pt1
        pt2 = path.path_pt2
        ctrl_pts = path.control_pts
        # Grab existing points
        for p in ([pt1, pt2] + ctrl_pts):
            if p and distance(p, pos) <= ctrl_pt_size + 3:
                if p == pt1 or p == pt2:
                    paths.remove(path)
                    return
                path.control_pts.remove(p)
                return


#|  --- SAVE PATH FUNCTIONS ---  |#
def format_path_save(paths_) -> str:
    output = "["
    for path in paths_:
        ctrl_pts_text = "["
        if len(path.control_pts) > 0:
            for pt in path.control_pts:
                if path.control_pts.index(pt) != len(path.control_pts) - 1:
                    ctrl_pts_text += f"Location{tuple(pt)}, "
                else:
                    ctrl_pts_text += f"Location{tuple(pt)}]"
        else:
            ctrl_pts_text = "[]"
        if path.path_pt1 and path.path_pt2:
            try:
                if paths_.index(path) != len(paths_) - 1:
                    output += f"Path(Location{tuple(path.path_pt1)}, Location{tuple(path.path_pt2)}, {ctrl_pts_text}, {path.locked}), " # type: ignore
                else:
                    output += f"Path(Location{tuple(path.path_pt1)}, Location{tuple(path.path_pt2)}, {ctrl_pts_text}, {path.locked})]" # type: ignore
            except TypeError:
                pass
        else:
            output = "[Path(None, None)]"
    return output


def save_paths():
    global paths
    try:
        with open(PATH_SAVE_FILE, "w") as file:
            file.write(f"from bezier_classes import Path, Location\nsaved_paths = {format_path_save(paths)}")
        print("Paths saved.")
    except Exception as e:
        print("Failed to save paths:", e)


def load_paths():
    global paths
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("path_save", PATH_SAVE_FILE)
        if spec:
            path_save = importlib.util.module_from_spec(spec)
            if spec.loader:
                spec.loader.exec_module(path_save)
            paths = path_save.saved_paths
            print("Paths loaded.")
        else:
            print("\"saved_paths\"  could not be found")
    except Exception as e:
        print("Failed to load paths:", e)


def reset_paths():
    global paths, prev_paths
    # Reset runtime paths to a single empty path
    prev_paths = []
    paths = [Path(None, None)]
    print("Paths reset (runtime only).")


#|  --- USER INTERACTION ---  |#
def check_events():
    global dragging_point, paths, score, running, hover_point, remember_graph, calculate_graph
    global terrain, width, height
    for evnt in pygame.event.get():
        pos = getattr(evnt, "pos", None)   # only mouse events have .pos
        loc = Location(*pos) if pos else None
        mods = pygame.key.get_mods()
        # vvv Checks vvv
        if evnt.type == pygame.QUIT:
            running = False
        # vvv Mouse Button Pressed vvv
        elif evnt.type == pygame.MOUSEBUTTONDOWN:
            if evnt.button == 1:  # Left click
                if mods & pygame.KMOD_CTRL:
                    remove_path_pts(loc)
                else:
                    add_path_point(loc, "left")
            elif evnt.button == 3:  # Right click
                add_path_point(loc, "right")
        # vvv Mouse Button Released vvv
        elif evnt.type == pygame.MOUSEBUTTONUP:
            if evnt.button == 1:
                dragging_point = None
        # vvv Mouse Moved vvv
        elif evnt.type == pygame.MOUSEMOTION:
            mouse_pos = loc
            hover_point = evnt.pos
            if dragging_point:
                dragging_point.x, dragging_point.y = evnt.pos
        # vvv Key Pressed vvv
        elif evnt.type == pygame.KEYDOWN:
            ctrl_pressed = (evnt.mod & pygame.KMOD_CTRL) != 0
            key = evnt.key
            if ctrl_pressed:
                if key == pygame.K_r:
                    reset_paths()
                elif key == pygame.K_l:
                    load_paths()
                elif key == pygame.K_s:
                    save_paths()
                elif key == pygame.K_d:
                    remember_graph = True
                elif key == pygame.K_b:
                    remember_graph = False
                    calculate_graph = not calculate_graph
            else:
                if key == pygame.K_SPACE:
                    score = score_all_paths(paths)


#|  --- GRAPH FUNCTIONS ---  |#
def store_graph():
    global prev_paths, paths
    snapshot = copy.deepcopy(paths)
    if not prev_paths or snapshot != prev_paths[-1]:
        prev_paths.append(snapshot)
        print(f"Stored graph snapshot #{len(prev_paths)}")


# saved_paths = [Path(Location(32, 769), Location(199, 485), [Location(161, 485)], True), Path(Location(199, 485), Location(420, 483), [Location(356, 490)], True), Path(Location(420, 482), Location(582, 349), [Location(486, 423), Location(550, 366)], True), Path(Location(582, 349), Location(764, 416), [Location(758, 282), Location(680, 368)], True), Path(Location(763, 416), Location(820, 89), [Location(879, 325), Location(717, 232), Location(842, 211), Location(953, 370), Location(784, 188)], True), Path(Location(818, 87), Location(1005, 338), [Location(804, 265)], True), Path(Location(1005, 339), Location(879, 630), [Location(902, 512), Location(862, 578)], True), Path(Location(879, 630), Location(929, 660), [Location(904, 644)], False)]
def render_graph():
    global prev_paths
    # --- Find score bounds ---
    max_score = 0
    min_score = 10000
    best_path = []
    for path_list in prev_paths:
        cur_score = score_all_paths(path_list)
        if 5 < cur_score < 10000:
            if cur_score < min_score:
                best_path = path_list
            max_score = max(max_score, cur_score)
            min_score = min(min_score, cur_score)
    with open(BEST_PATH_FILE, "w") as file:
        print("SAVING BEST PATH")
        file.write(f"from bezier_classes import Path, Location\nsaved_paths = {format_path_save(best_path)}")
    # --- Draw paths with normalized color ---
    for path_list in prev_paths:
        total_score = sum(path.score for path in path_list)
        if min_score != max_score:
            green_val = int(map_value(total_score, min_score, max_score, 0, 255))
        else:
            green_val = 128  # fallback if all scores are the same
        display_color = (0, green_val, 0, green_val)
        draw_bezier(path_list, display_color, 1, False)


#|  --- MAIN ---  |#
def main():
    global dragging_point, paths, terrain, width, height, surface, screen, score
    terrain, width, height, surface = load_image_as_terrain(IMAGE_FILE)
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Path Visualizer")
    clock = pygame.time.Clock()
    font_obj = pygame.font.SysFont(None, 24)

    hover_point = pygame.mouse.get_pos()
    score = 0

    while running:
        check_events()
        screen.blit(surface, (0, 0))
        score = score_all_paths(paths)
        hover_point = pygame.mouse.get_pos()

        # Display score next to cursor
        if hover_point and score is not None:
            formatted_time = f"{int(score)//3600:02}:{(int(score)%3600)//60:02}:{int(score)%60:02}"
            text_surf = font_obj.render(f"{formatted_time}", True, (0, 0, 0))
            text_bg = pygame.Surface((text_surf.get_width() + 6, text_surf.get_height() + 4))
            text_bg.fill((255, 255, 255))
            text_bg.blit(text_surf, (3, 2))
            screen.blit(text_bg, (hover_point[0] + 10, hover_point[1] + 10))
        if remember_graph:
            store_graph()
            draw_bezier(paths, line_size=2, show_terrain=True)
        elif calculate_graph:
            print("CALCULATING GRAPH")
            render_graph()
            while calculate_graph and running:
                check_events()
                pygame.display.flip()
                clock.tick(60)
        else:
            draw_bezier(paths, line_size=2, show_terrain=True)
        
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

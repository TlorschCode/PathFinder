import pygame
import sys
import numpy as np
from PIL import Image
from runner import Runner  # <-- import your Runner class here

# === CONFIG ===
IMAGE_FILE = "CrashSite.png"

# Color mapping: RGB -> string labels
COLOR_MAP = {
    (227, 117, 64): "ORANGE",   # Orange ~1' debris
    (134, 61, 230): "PURPLE",   # Purple ~2.5' debris
    (106, 184, 245): "BLUE",    # Blue ~4' debris
    (63, 63, 63): "GRAY"        # Gray = impassible
}

def load_image_as_list(image_file):
    # Load with PIL and convert to RGB
    img = Image.open(image_file).convert("RGB")
    w, h = img.size

    arr = np.array(img, dtype=np.uint8)
    flat_pixels = arr.reshape(-1, 3)

    # Map each pixel to a ground type (string) or "CLEAR"
    data_list = [COLOR_MAP.get(tuple(rgb), "CLEAR") for rgb in flat_pixels]

    surface = pygame.image.load(image_file)

    return data_list, w, h, surface

def main():
    # === Load terrain data ===
    terrain, width, height, surface = load_image_as_list(IMAGE_FILE)
    print(f"Image loaded: {len(terrain)} entries ({width} x {height})")

    # === Setup Pygame ===
    pygame.init()
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Crash Site Terrain with Runner")
    clock = pygame.time.Clock()

    # === Create Runner ===
    runner = Runner(767, 415, terrain)

    # === Main Loop ===
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- Runner logic ---
        runner.choose_direction()
        runner.move()
        runner.update_score()

        # --- Draw everything ---
        screen.blit(surface, (0, 0))

        # Draw runner as red dot
        pygame.draw.circle(screen, (255, 0, 0), (runner.x, runner.y), 3)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

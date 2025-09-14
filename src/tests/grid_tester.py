import pygame
import sys

# --- CONFIG --- #
IMAGE_FILE = "CrashSite.png"
grid_size = 50.0      # initial size of squares in pixels (float for fine tuning)
offset_x = 0          # initial x offset
offset_y = 0          # initial y offset
GRID_COLOR = (255, 0, 0, 150)  # red, semi-transparent

# --- PYGAME SETUP --- #
pygame.init()
image = pygame.image.load(IMAGE_FILE)
width, height = image.get_size()
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Grid Overlay Tool")
clock = pygame.time.Clock()

font = pygame.font.SysFont(None, 24)
running = True

while running:
    keys = pygame.key.get_pressed()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            # Determine fine tuning if shift is held
            shift_held = pygame.key.get_mods() & pygame.KMOD_SHIFT

            # Adjust grid size
            if event.key == pygame.K_UP:
                grid_size += 0.01 if shift_held else 1
            elif event.key == pygame.K_DOWN:
                grid_size -= 0.01 if shift_held else 1
                grid_size = max(0.01, grid_size)  # prevent negative/zero

            # Adjust offset
            elif event.key == pygame.K_LEFT:
                offset_x -= 1
            elif event.key == pygame.K_RIGHT:
                offset_x += 1
            elif event.key == pygame.K_w:
                offset_y -= 1
            elif event.key == pygame.K_s:
                offset_y += 1

    # Draw image
    screen.blit(image, (0, 0))

    # Draw grid
    x = offset_x
    while x < width:
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, height))
        x += grid_size
    y = offset_y
    while y < height:
        pygame.draw.line(screen, GRID_COLOR, (0, y), (width, y))
        y += grid_size

    # Display info with black background
    info_text = f"Grid Size: {grid_size:.2f} px | Offset: ({offset_x}, {offset_y})"
    text_surf = font.render(info_text, True, (255, 255, 255))
    bg_surf = pygame.Surface((text_surf.get_width() + 4, text_surf.get_height() + 4))
    bg_surf.fill((0, 0, 0))
    bg_surf.blit(text_surf, (2, 2))
    screen.blit(bg_surf, (10, 10))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()

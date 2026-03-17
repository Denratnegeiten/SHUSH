import pygame
import sys
from settings import *
from level import Level
from utils import Camera

def run_editor():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("SHUSH - Editor Mode")
    clock = pygame.time.Clock()
    
    level = Level()
    camera = Camera(MAP_WIDTH, MAP_HEIGHT)
    brush = WALL
    
    font = pygame.font.SysFont("Arial", 26, bold=True)
    brush_names = {WALL: "WALL", FLOOR: "FLOOR", LOOT: "LOOT", HIDING_SPOT: "BUSH", ENTRANCE: "EXIT"}

    while True:
        mouse_pos = pygame.mouse.get_pos()
        world_x = mouse_pos[0] - camera.camera.x
        world_y = mouse_pos[1] - camera.camera.y
        gx, gy = world_x // TILE_SIZE, world_y // TILE_SIZE

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: brush = WALL
                if event.key == pygame.K_2: brush = FLOOR
                if event.key == pygame.K_3: brush = LOOT
                if event.key == pygame.K_4: brush = HIDING_SPOT
                if event.key == pygame.K_5: brush = ENTRANCE
                if event.key == pygame.K_s: level.save_to_json("level_1.json")
                if event.key == pygame.K_ESCAPE: return

        if pygame.mouse.get_pressed()[0]:
            if brush == ENTRANCE:
                level.entrance_rect.x, level.entrance_rect.y = gx*TILE_SIZE, gy*TILE_SIZE
            else:
                level.grid[(gx, gy)] = brush
        if pygame.mouse.get_pressed()[2]:
            if (gx, gy) in level.grid: del level.grid[(gx, gy)]

        # Камера
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]: camera.camera.x += 25
        if keys[pygame.K_RIGHT]: camera.camera.x -= 25
        if keys[pygame.K_UP]: camera.camera.y += 25
        if keys[pygame.K_DOWN]: camera.camera.y -= 25

        screen.fill(BG_COLOR)
        level.draw(screen, camera)
        
        # UI Редактора
        pygame.draw.rect(screen, (20, 20, 30), (0, 0, 320, 250))
        txts = [f"BRUSH: {brush_names[brush]}", "S: Save Level", "Arrows: Move", "ESC: Exit"]
        for i, t in enumerate(txts):
            screen.blit(font.render(t, True, UI_COLOR), (20, 20 + i * 40))

        pygame.display.flip()
        clock.tick(FPS)
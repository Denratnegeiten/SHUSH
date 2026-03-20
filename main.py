import pygame
import sys
import math
import os
from settings import *
from level import Level
from entities import Player, Guard
from utils import Camera, check_vision, has_line_of_sight

pygame.init()

# 1. Глобальные поверхности
display_screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("SHUSH - Ultimate Stealth")
clock = pygame.time.Clock()

game_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))

is_fullscreen = False

font = pygame.font.SysFont("Arial", 40, bold=True)
large_font = pygame.font.SysFont("Arial", 120, bold=True)
ui_font = pygame.font.SysFont("Arial", 32)

def draw_ui(surf, player, game_state, panic_timer):
    s_w, s_h = 400, 35
    sx, sy = LOGICAL_WIDTH - s_w - 60, 60
    pygame.draw.rect(surf, (30, 30, 40), (sx, sy, s_w, s_h))
    
    bar_color = (255, 60, 60) if player.exhausted else (0, 255, 200)
    current_w = (player.stamina / STAMINA_MAX) * s_w
    pygame.draw.rect(surf, bar_color, (sx, sy, current_w, s_h))
    pygame.draw.rect(surf, UI_COLOR, (sx, sy, s_w, s_h), 4)
    surf.blit(ui_font.render("STAMINA", True, UI_COLOR), (sx + 10, sy + 45))

    loot_txt = font.render(f"LOOT COLLECTED: {player.score}", True, LOOT_COLOR)
    surf.blit(loot_txt, (60, 60))

    if game_state == "PANIC":
        sec = max(0, math.ceil(panic_timer / FPS))
        t_img = large_font.render(str(sec), True, (255, 50, 50))
        surf.blit(t_img, (LOGICAL_WIDTH // 2 - t_img.get_width() // 2, 60))

    controls = ["WASD: Move", "L-SHIFT: Run (Loud)", "L-CTRL: Sneak", "E: Grab Loot", "ESC: Menu", "F11: Fullscreen"]
    start_y = LOGICAL_HEIGHT - 250
    for i, txt in enumerate(controls):
        img = ui_font.render(txt, True, (180, 180, 180))
        surf.blit(img, (60, start_y + i * 35))

def handle_game_events(player, level, guards, game_state):
    global is_fullscreen, display_screen
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT: 
            pygame.quit()
            sys.exit()
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: 
                return False 
            
            if event.key == pygame.K_F11:
                is_fullscreen = not is_fullscreen
                if is_fullscreen:
                    display_screen = pygame.display.set_mode(FULLSCREEN_RES, pygame.FULLSCREEN | pygame.NOFRAME)
                else:
                    display_screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.NOFRAME)
            
            if event.key == pygame.K_e and game_state in ["STEALTH", "PANIC"]:
                for item in level.loot[:]:
                    if player.rect.inflate(60, 60).colliderect(item):
                        level.loot.remove(item)
                        # Удаляем из объектов JSON, чтобы перестало рисоваться
                        if hasattr(level, 'level_data') and 'objects' in level.level_data:
                            for obj in level.level_data['objects']:
                                if 'rect' in obj and obj['rect'] == item:
                                    level.level_data['objects'].remove(obj)
                                    break
                        player.score += 1
            
            if (game_state == "WIN" or game_state == "LOSE") and event.key == pygame.K_RETURN:
                return False

    return True

def run_game(level_id):
    level = Level(f'assets/levels/level_{level_id}.json')
    
    player = Player(level.entrance_rect.centerx, level.entrance_rect.centery)
    camera = Camera(MAP_WIDTH, MAP_HEIGHT)
    
    guards = [Guard(g['type'], g.get('x', 0), g.get('y', 0), g.get('waypoints'), g.get('bounds')) 
              for g in level.guards_data]
    
    transparent_surf = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
    panic_overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
    
    game_state = "STEALTH"
    panic_timer = 45 * FPS
    swat_spawned = False

    while True:
        if not handle_game_events(player, level, guards, game_state): 
            return 

        if game_state in ["STEALTH", "PANIC"]:
            keys = pygame.key.get_pressed()
            obstacles = level.walls + level.hiding_spots
            
            player.update(keys, level.walls, level.hiding_spots)
            camera.update(player.rect)
            
            if player.rect.colliderect(level.entrance_rect) and player.score > 0:
                game_state = "WIN"

            for g in guards:
                if game_state == "STEALTH":
                    g.update(obstacles)
                else:
                    if g.type == 'swat' or (has_line_of_sight(g.rect.center, player.rect.center, level.walls) and not player.is_hidden):
                        g.chase(player.rect, obstacles)
                    else:
                        g.update(obstacles)
                
                for b in g.bullets[:]:
                    b.update()
                    if b.rect.colliderect(player.rect) and not player.is_hidden:
                        player.slow_timer = 180 
                        g.bullets.remove(b)
                    elif any(b.rect.colliderect(w) for w in level.walls):
                        g.bullets.remove(b)

            if game_state == "STEALTH":
                for g in guards:
                    if check_vision(player.rect, player.is_hidden, g.rect, g.angle, 450, 1.2, level.walls):
                        game_state = "PANIC"
                    for noise in player.active_noises:
                        if math.hypot(noise['pos'][0] - g.rect.centerx, noise['pos'][1] - g.rect.centery) < noise['r']:
                            game_state = "PANIC"

            elif game_state == "PANIC":
                panic_timer -= 1
                if panic_timer <= 0 and not swat_spawned:
                    swat_spawned = True
                    for _ in range(4):
                        guards.append(Guard('swat', level.entrance_rect.centerx, level.entrance_rect.centery))
                
                if any(player.rect.colliderect(g.rect) for g in guards):
                    game_state = "LOSE"

        game_surface.fill(BG_COLOR)
        transparent_surf.fill((0, 0, 0, 0))
        
        level.draw(game_surface, camera)
        player.draw(game_surface, transparent_surf, camera)
        
        for g in guards:
            if game_state in ["STEALTH", "PANIC"]:
                g.draw_vision(transparent_surf, level.walls, camera)
            g.draw(game_surface, camera)
            for b in g.bullets:
                b.draw(game_surface, camera)

        game_surface.blit(transparent_surf, (0, 0))

        if game_state == "PANIC":
            p = int(80 + 80 * math.sin(pygame.time.get_ticks() * 0.007))
            panic_overlay.fill((255, 0, 0, p))
            game_surface.blit(panic_overlay, (0, 0))

        draw_ui(game_surface, player, game_state, panic_timer)

        if game_state == "WIN":
            txt = large_font.render("MISSION SUCCESS", True, LOOT_COLOR)
            game_surface.blit(txt, (LOGICAL_WIDTH//2 - txt.get_width()//2, LOGICAL_HEIGHT//2 - 100))
            sub = font.render("Press ENTER to continue", True, UI_COLOR)
            game_surface.blit(sub, (LOGICAL_WIDTH//2 - sub.get_width()//2, LOGICAL_HEIGHT//2 + 50))
        elif game_state == "LOSE":
            txt = large_font.render("BUSTED", True, (255, 50, 50))
            game_surface.blit(txt, (LOGICAL_WIDTH//2 - txt.get_width()//2, LOGICAL_HEIGHT//2 - 100))
            sub = font.render("Press ENTER to try again", True, UI_COLOR)
            game_surface.blit(sub, (LOGICAL_WIDTH//2 - sub.get_width()//2, LOGICAL_HEIGHT//2 + 50))

        scaled_surf = pygame.transform.scale(game_surface, display_screen.get_size())
        display_screen.blit(scaled_surf, (0, 0))

        pygame.display.flip()
        clock.tick(FPS)

def main_menu():
    global is_fullscreen, display_screen
    
    while True:
        game_surface.fill((15, 15, 20))
        logo = large_font.render("SHUSH", True, (80, 150, 255))
        game_surface.blit(logo, (LOGICAL_WIDTH//2 - logo.get_width()//2, 250))
        
        t1 = font.render("Press 1, 2 or 3 to play Levels", True, UI_COLOR)
        t2 = font.render("Press P for Level Editor", True, LOOT_COLOR)
        game_surface.blit(t1, (LOGICAL_WIDTH//2 - t1.get_width()//2, 550))
        game_surface.blit(t2, (LOGICAL_WIDTH//2 - t2.get_width()//2, 650))
        
        scaled_surf = pygame.transform.scale(game_surface, display_screen.get_size())
        display_screen.blit(scaled_surf, (0, 0))
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: run_game(1)
                if event.key == pygame.K_2: run_game(2)
                if event.key == pygame.K_3: run_game(3)
                
                if event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        display_screen = pygame.display.set_mode(FULLSCREEN_RES, pygame.FULLSCREEN | pygame.NOFRAME)
                    else:
                        display_screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.NOFRAME)
                        
                if event.key == pygame.K_p:
                    try:
                        import editor
                        editor.run_editor()
                    except ImportError:
                        pass

if __name__ == "__main__":
    main_menu()
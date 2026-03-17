import pygame
import sys
import math
from settings import *
from level import Level
from entities import Player, Guard
from utils import Camera, check_vision, has_line_of_sight

pygame.init()
# Принудительный Full HD
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SHUSH - Ultimate Stealth")
clock = pygame.time.Clock()

# Шрифты (крупные для 1080p)
font = pygame.font.SysFont("Arial", 36, bold=True)
large_font = pygame.font.SysFont("Arial", 110, bold=True)
ui_font = pygame.font.SysFont("Arial", 28)

def draw_ui(player, game_state, panic_timer):
    # 1. Полоска стамины
    s_w, s_h = 400, 35
    sx, sy = WIDTH - s_w - 60, 60
    pygame.draw.rect(screen, (30, 30, 40), (sx, sy, s_w, s_h))
    
    # Цвет: красный если устал, бирюзовый если в норме
    bar_color = (255, 60, 60) if player.exhausted else (0, 255, 200)
    current_w = (player.stamina / STAMINA_MAX) * s_w
    pygame.draw.rect(screen, bar_color, (sx, sy, current_w, s_h))
    pygame.draw.rect(screen, UI_COLOR, (sx, sy, s_w, s_h), 4)
    screen.blit(ui_font.render("STAMINA", True, UI_COLOR), (sx, sy + 45))

    # 2. Счет лута
    loot_txt = font.render(f"LOOT COLLECTED: {player.score}", True, LOOT_COLOR)
    screen.blit(loot_txt, (60, 60))

    # 3. Таймер паники
    if game_state == "PANIC":
        sec = max(0, math.ceil(panic_timer / FPS))
        t_img = large_font.render(str(sec), True, (255, 50, 50))
        screen.blit(t_img, (WIDTH // 2 - t_img.get_width() // 2, 60))

    # 4. Подсказки управления
    controls = ["WASD: Move", "L-SHIFT: Run (Loud)", "L-CTRL: Sneak", "E: Grab Loot", "ESC: Menu"]
    for i, txt in enumerate(controls):
        img = ui_font.render(txt, True, (180, 180, 180))
        screen.blit(img, (60, HEIGHT - 220 + i * 35))

def run_game(level_id):
    level = Level(level_id)
    player = Player(level.entrance_rect.centerx, level.entrance_rect.centery)
    camera = Camera(MAP_WIDTH, MAP_HEIGHT)
    
    # Загружаем охранников из данных уровня
    guards = [Guard(g['type'], g.get('x', 0), g.get('y', 0), g.get('waypoints'), g.get('bounds')) 
              for g in level.guards_data]
    
    # Поверхности для прозрачности (тени, свет, шум)
    transparent_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    panic_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    
    game_state = "STEALTH" # STEALTH, PANIC, WIN, LOSE
    panic_timer = 45 * FPS
    swat_spawned = False

    while True:
        # --- 1. СОБЫТИЯ ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: return # Назад в меню
                if event.key == pygame.K_e and game_state in ["STEALTH", "PANIC"]:
                    for item in level.loot[:]:
                        if player.rect.inflate(60, 60).colliderect(item):
                            level.loot.remove(item)
                            level.refresh_physics()
                            player.score += 1
                if (game_state == "WIN" or game_state == "LOSE") and event.key == pygame.K_RETURN:
                    return

        # --- 2. ЛОГИКА ---
        if game_state in ["STEALTH", "PANIC"]:
            keys = pygame.key.get_pressed()
            obstacles = level.walls + level.hiding_spots
            
            player.update(keys, level.walls, level.hiding_spots)
            camera.update(player.rect)
            
            # Побег (вернуться к фургону с лутом)
            if player.rect.colliderect(level.entrance_rect) and player.score > 0:
                game_state = "WIN"

            for g in guards:
                if game_state == "STEALTH":
                    g.update(obstacles)
                else:
                    # В режиме паники ИИ агрессивнее
                    if g.type == 'swat' or (has_line_of_sight(g.rect.center, player.rect.center, level.walls) and not player.is_hidden):
                        g.chase(player.rect, obstacles)
                    else:
                        g.update(obstacles)
                
                # Пули шокера
                for b in g.bullets[:]:
                    b.update()
                    if b.rect.colliderect(player.rect) and not player.is_hidden:
                        player.slow_timer = 180 # Замедление на 3 сек
                        g.bullets.remove(b)
                    elif any(b.rect.colliderect(w) for w in level.walls):
                        g.bullets.remove(b)

        # --- 3. ОБНАРУЖЕНИЕ ---
        if game_state == "STEALTH":
            for g in guards:
                # Фонарик
                if check_vision(player.rect, player.is_hidden, g.rect, g.angle, 450, 1.2, level.walls):
                    game_state = "PANIC"
                # Звук шагов
                for noise in player.active_noises:
                    if math.hypot(noise['pos'][0] - g.rect.centerx, noise['pos'][1] - g.rect.centery) < noise['r']:
                        game_state = "PANIC"

        elif game_state == "PANIC":
            panic_timer -= 1
            if panic_timer <= 0 and not swat_spawned:
                swat_spawned = True
                # SWAT выезжает из фургона
                for _ in range(4):
                    guards.append(Guard('swat', level.entrance_rect.centerx, level.entrance_rect.centery))
            
            # Конец игры если догнали
            if any(player.rect.colliderect(g.rect) for g in guards):
                game_state = "LOSE"

        # --- 4. ОТРИСОВКА ---
        screen.fill(BG_COLOR)
        transparent_surf.fill((0, 0, 0, 0))
        
        # Рисуем уровень (пол, стены, лут)
        level.draw(screen, camera)
        # Рисуем игрока и его звуковые волны
        player.draw(screen, transparent_surf, camera)
        
        # Рисуем врагов и их зрение
        for g in guards:
            if game_state in ["STEALTH", "PANIC"]:
                g.draw_vision(transparent_surf, level.walls, camera)
            g.draw(screen, camera)
            for b in g.bullets:
                b.draw(screen, camera)

        # Накладываем слой прозрачности (свет фонариков и круги шума)
        screen.blit(transparent_surf, (0, 0))

        # Эффект тревоги (пульсация)
        if game_state == "PANIC":
            p = int(80 + 80 * math.sin(pygame.time.get_ticks() * 0.007))
            panic_overlay.fill((255, 0, 0, p))
            screen.blit(panic_overlay, (0, 0))

        draw_ui(player, game_state, panic_timer)

        # Экраны финала
        if game_state == "WIN":
            txt = large_font.render("MISSION SUCCESS", True, LOOT_COLOR)
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 100))
            sub = font.render("Press ENTER to continue", True, UI_COLOR)
            screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 + 50))
        elif game_state == "LOSE":
            txt = large_font.render("BUSTED", True, (255, 50, 50))
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 100))
            sub = font.render("Press ENTER to try again", True, UI_COLOR)
            screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 + 50))

        pygame.display.flip()
        clock.tick(FPS)

def main_menu():
    while True:
        screen.fill((15, 15, 20))
        logo = large_font.render("SHUSH", True, (80, 150, 255))
        screen.blit(logo, (WIDTH//2 - logo.get_width()//2, 250))
        
        t1 = font.render("Press 1, 2 or 3 to play Levels", True, UI_COLOR)
        t2 = font.render("Press P for Level Editor", True, LOOT_COLOR)
        screen.blit(t1, (WIDTH//2 - t1.get_width()//2, 550))
        screen.blit(t2, (WIDTH//2 - t2.get_width()//2, 650))
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: run_game(1)
                if event.key == pygame.K_2: run_game(2)
                if event.key == pygame.K_3: run_game(3)
                if event.key == pygame.K_p:
                    import editor
                    editor.run_editor()

if __name__ == "__main__":
    main_menu()
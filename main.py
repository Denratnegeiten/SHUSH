import pygame
import sys
import math
import os

from src.settings import *
from src.level import Level
from src.entities import Player, Guard
from src.utils import Camera, check_vision, has_line_of_sight

pygame.init()

display_screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)
pygame.display.set_caption("SHUSH - Ultimate Stealth")
clock = pygame.time.Clock()

game_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))

is_fullscreen = True

try:
    font_path = os.path.join(ASSETS_DIR, 'ui', 'Arimo-VariableFont_wght.ttf')
    
    font = pygame.font.Font(font_path, 30)
    money_font = pygame.font.Font(font_path, 26) 
    large_font = pygame.font.Font(font_path, 120)
    ui_font = pygame.font.Font(font_path, 20)
    loot_font = pygame.font.Font(font_path, 36)
    stamina_txt_font = pygame.font.Font(font_path, 24)
except FileNotFoundError:
    print("Шрифт Arimo-VariableFont_wght.ttf не найден в assets/ui/! Использую стандартный.")
    font = pygame.font.SysFont("Arial", 30, bold=True)
    money_font = pygame.font.SysFont("Arial", 26, bold=True) 
    large_font = pygame.font.SysFont("Arial", 120, bold=True)
    ui_font = pygame.font.SysFont("Arial", 20)
    loot_font = pygame.font.SysFont("Arial", 36, bold=True)
    stamina_txt_font = pygame.font.SysFont("Arial", 24)

def draw_ui(surf, player, game_state, panic_timer):
    s_w, s_h = 200, 20
    sx, sy = LOGICAL_WIDTH - s_w - 20, 20 
    
    stamina_text = ui_font.render("ВЫНОСЛИВОСТЬ", True, (255, 50, 50))
    
    stam_box_w = max(s_w, stamina_text.get_width()) + 20
    stam_box_h = s_h + stamina_text.get_height() + 20
    stam_bg = pygame.Surface((stam_box_w, stam_box_h), pygame.SRCALPHA)
    stam_bg.fill((0, 0, 0, 150))
    
    surf.blit(stam_bg, (sx - 10, sy - 10))
    
    pygame.draw.rect(surf, (40, 10, 10), (sx, sy, s_w, s_h))
    current_w = (player.stamina / STAMINA_MAX) * s_w
    
    pygame.draw.rect(surf, (255, 50, 50), (sx, sy, current_w, s_h))
    pygame.draw.rect(surf, (255, 50, 50), (sx, sy, s_w, s_h), 3)
    
    surf.blit(stamina_text, (sx + (s_w - stamina_text.get_width()) // 2, sy + 25))


    loot_txt = font.render(f"КОЛИЧЕСТВО ПРЕДМЕТОВ: {player.score}", True, (255, 50, 50))
    money_txt = money_font.render(f"${player.total_money_value:,}", True, (255, 50, 50))
    
    lx, ly = 20, 20
    
    box_width = max(loot_txt.get_width(), money_txt.get_width()) + 20
    box_height = loot_txt.get_height() + money_txt.get_height() + 20
    bg_box = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
    bg_box.fill((0, 0, 0, 150))
    
    surf.blit(bg_box, (lx - 10, ly - 10))
    
    surf.blit(loot_txt, (lx, ly))
    surf.blit(money_txt, (lx, ly + loot_txt.get_height() + 5))


    if game_state == "PANIC":
        sec = max(0, math.ceil(panic_timer / FPS))
        t_img = large_font.render(str(sec), True, (255, 50, 50))
        surf.blit(t_img, (LOGICAL_WIDTH // 2 - t_img.get_width() // 2, 20))


def run_game(level_id):
    pygame.mouse.set_visible(False)
    
    level_path = os.path.join(LEVELS_DIR, f'level_{level_id}.json')
    level = Level(level_path)
    
    player = Player(level.entrance_rect.centerx, level.entrance_rect.centery)
    camera = Camera(MAP_WIDTH, MAP_HEIGHT)
    
    guards = [Guard(g['type'], g.get('x', 0), g.get('y', 0), g.get('waypoints'), g.get('bounds')) 
              for g in level.guards_data if g['type'] != 'swat']
    
    transparent_surf = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
    panic_overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
    
    game_state = "STEALTH"
    panic_timer = 45 * FPS
    swat_spawned = False

    while True:
        if not handle_game_events(player, level, guards, game_state): 
            pygame.mouse.set_visible(True)
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
                            if has_line_of_sight(noise['pos'], g.rect.center, level.walls):
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
            txt = large_font.render("Миссия пройдена", True, LOOT_COLOR)
            game_surface.blit(txt, (LOGICAL_WIDTH//2 - txt.get_width()//2, LOGICAL_HEIGHT//2 - 100))
            sub = font.render("Нажмите 'ENTER' для продолжения", True, UI_COLOR)
            game_surface.blit(sub, (LOGICAL_WIDTH//2 - sub.get_width()//2, LOGICAL_HEIGHT//2 + 50))
        elif game_state == "LOSE":
            txt = large_font.render("Провал", True, (255, 50, 50))
            game_surface.blit(txt, (LOGICAL_WIDTH//2 - txt.get_width()//2, LOGICAL_HEIGHT//2 - 100))
            sub = font.render("Нажмите 'ENTER' для повторной попытки", True, UI_COLOR)
            game_surface.blit(sub, (LOGICAL_WIDTH//2 - sub.get_width()//2, LOGICAL_HEIGHT//2 + 50))

        scaled_surf = pygame.transform.smoothscale(game_surface, display_screen.get_size())
        display_screen.blit(scaled_surf, (0, 0))

        pygame.display.flip()
        clock.tick(FPS)

def handle_game_events(player, level, guards, game_state):
    global is_fullscreen, display_screen, game_surface
    
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
                    display_screen = pygame.display.set_mode((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.FULLSCREEN | pygame.NOFRAME)
                    game_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
                else:
                    display_screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.NOFRAME)
                    game_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
            
            if event.key == pygame.K_e and game_state in ["STEALTH", "PANIC"]:
                interaction_rect = player.rect.inflate(60, 60)
                for obj in level.loot[:]:
                    if interaction_rect.colliderect(obj['rect']):
                        level.loot.remove(obj)
                        
                        if hasattr(level, 'level_data') and 'objects' in level.level_data:
                            for level_obj in level.level_data['objects']:
                                if level_obj['name'] == obj['name']:
                                    level.level_data['objects'].remove(level_obj)
                                    break
                                    
                        player.score += 1
                        if 'value' in obj:
                            player.total_money_value += obj['value']
                        break
            
            if (game_state == "WIN" or game_state == "LOSE") and event.key == pygame.K_RETURN:
                return False

    return True

def main_menu():
    global is_fullscreen, display_screen, game_surface
    
    try:
        wallpaper_path = os.path.join(ASSETS_DIR, 'ui', 'wallpaper.png')
        bg_image = pygame.image.load(wallpaper_path).convert()
        bg_image = pygame.transform.scale(bg_image, (LOGICAL_WIDTH, LOGICAL_HEIGHT))
    except FileNotFoundError:
        bg_image = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
        bg_image.fill((15, 15, 20))

    level_buttons = []
    box_size = 100      
    margin_x = 40       
    margin_y = 40       
    start_x = LOGICAL_WIDTH // 2 - (5 * box_size + 4 * margin_x) // 2
    start_y = 400

    for i in range(10):
        row = i // 5
        col = i % 5
        x = start_x + col * (box_size + margin_x)
        y = start_y + row * (box_size + margin_y)
        rect = pygame.Rect(x, y, box_size, box_size)
        level_buttons.append({"level": i + 1, "rect": rect})

    editor_btn_w = 600
    editor_btn_h = 60
    editor_btn_rect = pygame.Rect(
        LOGICAL_WIDTH // 2 - editor_btn_w // 2, 
        LOGICAL_HEIGHT - 150, 
        editor_btn_w, 
        editor_btn_h
    )

    custom_btn_w = 5 * box_size + 4 * margin_x 
    custom_btn_h = 60
    custom_btn_rect = pygame.Rect(
        LOGICAL_WIDTH // 2 - custom_btn_w // 2, 
        start_y + 250, 
        custom_btn_w, 
        custom_btn_h
    )

    menu_msg = ""
    msg_timer = 0

    while True:
        game_surface.blit(bg_image, (0, 0))
        
        mx, my = pygame.mouse.get_pos()
        screen_w, screen_h = display_screen.get_size()
        scale_x = LOGICAL_WIDTH / screen_w
        scale_y = LOGICAL_HEIGHT / screen_h
        logical_mx = int(mx * scale_x)
        logical_my = int(my * scale_y)

        for btn in level_buttons:
            rect = btn["rect"]
            color = (200, 200, 200) if rect.collidepoint(logical_mx, logical_my) else (255, 255, 255)
            
            pygame.draw.rect(game_surface, color, rect, border_radius=15)
            pygame.draw.rect(game_surface, (50, 50, 50), rect, 4, border_radius=15) 
            
            lvl_txt = font.render(str(btn["level"]), True, (10, 10, 10))
            game_surface.blit(lvl_txt, (rect.centerx - lvl_txt.get_width()//2, rect.centery - lvl_txt.get_height()//2))

        ed_color = (200, 50, 50) if editor_btn_rect.collidepoint(logical_mx, logical_my) else (150, 40, 40)
        pygame.draw.rect(game_surface, ed_color, editor_btn_rect, border_radius=10)
        pygame.draw.rect(game_surface, (255, 255, 255), editor_btn_rect, 3, border_radius=10)
        ed_txt = ui_font.render("Запуск редактора", True, (255, 255, 255))
        game_surface.blit(ed_txt, (editor_btn_rect.centerx - ed_txt.get_width()//2, editor_btn_rect.centery - ed_txt.get_height()//2))

        custom_color = (200, 200, 200) if custom_btn_rect.collidepoint(logical_mx, logical_my) else (255, 255, 255)
        pygame.draw.rect(game_surface, custom_color, custom_btn_rect, border_radius=10)
        pygame.draw.rect(game_surface, (50, 50, 50), custom_btn_rect, 4, border_radius=10) 
        c_txt = font.render("Собственный уровень", True, (10, 10, 10)) 
        game_surface.blit(c_txt, (custom_btn_rect.centerx - c_txt.get_width()//2, custom_btn_rect.centery - c_txt.get_height()//2))

        if msg_timer > 0:
            err_surf = font.render(menu_msg, True, (255, 50, 50))
            game_surface.blit(err_surf, (LOGICAL_WIDTH//2 - err_surf.get_width()//2, 320))
            msg_timer -= 1

        scaled_surf = pygame.transform.smoothscale(game_surface, display_screen.get_size())
        display_screen.blit(scaled_surf, (0, 0))
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                
                for btn in level_buttons:
                    if btn["rect"].collidepoint(logical_mx, logical_my):
                        if os.path.exists(os.path.join(LEVELS_DIR, f"level_{btn['level']}.json")):
                            run_game(btn["level"])
                        else:
                            menu_msg = f"Уровень {btn['level']} еще не создан в редакторе!"
                            msg_timer = 120

                if editor_btn_rect.collidepoint(logical_mx, logical_my):
                    try:
                        from src import editor
                        editor.run_editor()
                    except ImportError as e:
                        print(e)

                if custom_btn_rect.collidepoint(logical_mx, logical_my):
                    if os.path.exists(os.path.join(LEVELS_DIR, "level_custom.json")):
                        run_game("custom")
                    else:
                        menu_msg = "Собственный уровень еще не создан!"
                        msg_timer = 120

            if event.type == pygame.KEYDOWN:
                if pygame.K_0 <= event.key <= pygame.K_9:
                    lvl = event.key - pygame.K_0
                    if lvl == 0: lvl = 10
                    
                    if os.path.exists(os.path.join(LEVELS_DIR, f"level_{lvl}.json")):
                        run_game(lvl)
                    else:
                        menu_msg = f"Уровень {lvl} еще не создан!"
                        msg_timer = 120
                
                if event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        display_screen = pygame.display.set_mode((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.FULLSCREEN | pygame.NOFRAME)
                    else:
                        display_screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.NOFRAME)
                        
                if event.key == pygame.K_p:
                    try:
                        from src import editor
                        editor.run_editor()
                    except ImportError as e:
                        print(e)

if __name__ == "__main__":
    main_menu()
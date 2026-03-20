import pygame
import json
import os
from settings import WINDOW_WIDTH, WINDOW_HEIGHT

def run_editor():
    pygame.init()
    screen = pygame.display.set_mode((1536, 768)) 
    pygame.display.set_caption("SHUSH - Ultimate Level Editor")
    clock = pygame.time.Clock()

    MAP_COLS, MAP_ROWS = 100, 100
    
    base_tiles = ["home_floor_96x64.png", "street_floor_96x64.png", "walls_96x64.png"]
    tiles_dict = {"0": base_tiles[0], "1": base_tiles[1], "2": base_tiles[2]}
    t_idx = 3
    for file in sorted(os.listdir('assets/tiles')):
        if file.endswith('.png') and file not in base_tiles:
            tiles_dict[str(t_idx)] = file
            t_idx += 1

    sprites_dict = {}
    s_idx = 0
    for file in sorted(os.listdir('assets/sprites')):
        if file.endswith('.png') and not file.startswith('cop_') and not file.startswith('omon_'):
            sprites_dict[f"spr_{s_idx}"] = file
            s_idx += 1

    tile_imgs = {}
    for k, v in tiles_dict.items():
        raw_img = pygame.image.load(os.path.join('assets/tiles', v)).convert_alpha()
        tile_imgs[k] = pygame.transform.scale(raw_img, (64, 64))
    sprite_imgs = {}
    for k, v in sprites_dict.items():
        img = pygame.image.load(os.path.join('assets/sprites', v)).convert_alpha()
        sprite_imgs[k] = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))

    def get_scaled_imgs(z):
        t = {k: pygame.transform.scale(img, (int(img.get_width()*z), int(img.get_height()*z))) for k, img in tile_imgs.items()}
        s = {k: pygame.transform.scale(img, (int(img.get_width()*z), int(img.get_height()*z))) for k, img in sprite_imgs.items()}
        return t, s

    level_map = [[0 for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
    objects = []
    guards = []
    entrance_pos = [64, 64] # По умолчанию ставим на клетку 64x64

    modes = ['tiles', 'objects', 'guards', 'entrance']
    mode_idx = 0
    tile_keys, sprite_keys = list(tiles_dict.keys()), list(sprites_dict.keys())
    guard_types = ['normal', 'fast', 'taser', 'random', 'swat']
    guard_colors = {'normal': (100, 100, 255), 'fast': (255, 255, 0), 'taser': (255, 100, 100), 'random': (200, 0, 200), 'swat': (50, 50, 50)}
    c_idx = {'tiles': 0, 'objects': 0, 'guards': 0}

    camera_x, camera_y = 0, 0
    zoom = 1.0
    scaled_tiles, scaled_sprites = get_scaled_imgs(zoom)
    dragging, box_filling = False, False
    last_mouse_pos, box_start, box_end = (0, 0), (0, 0), (0, 0)

    font = pygame.font.SysFont("Arial", 22)
    running = True
    save_msg, save_msg_timer, msg_color = "", 0, (0, 255, 0)

    while running:
        screen.fill((30, 30, 35))
        keys = pygame.key.get_pressed()
        shift_held = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        ctrl_held = keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]
        mouse_pressed = pygame.mouse.get_pressed()
        
        mx, my = pygame.mouse.get_pos()
        world_x, world_y = (mx - camera_x) / zoom, (my - camera_y) / zoom
        
        # СЕТКА ТЕПЕРЬ СТРОГО 64x64
        grid_x = max(0, min(MAP_COLS - 1, int(world_x // 64)))
        grid_y = max(0, min(MAP_ROWS - 1, int(world_y // 64)))

        if mouse_pressed[0] and not box_filling and not dragging:
            if modes[mode_idx] == 'tiles' and not shift_held:
                level_map[grid_y][grid_x] = int(tile_keys[c_idx['tiles']])

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.MOUSEWHEEL:
                old_zoom = zoom
                zoom = max(0.2, min(zoom + event.y * 0.1, 3.0))
                if zoom != old_zoom:
                    camera_x, camera_y = mx - world_x * zoom, my - world_y * zoom
                    scaled_tiles, scaled_sprites = get_scaled_imgs(zoom)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                if event.key == pygame.K_m: mode_idx = (mode_idx + 1) % 4
                
                cur_mode = modes[mode_idx]
                if event.key == pygame.K_q and cur_mode in c_idx: 
                    c_idx[cur_mode] = max(0, c_idx[cur_mode] - 1)
                if event.key == pygame.K_e and cur_mode in c_idx: 
                    max_l = len(tile_keys) if cur_mode == 'tiles' else (len(sprite_keys) if cur_mode == 'objects' else len(guard_types))
                    c_idx[cur_mode] = min(max_l - 1, c_idx[cur_mode] + 1)
                    
                # Добавили pygame.K_0 в список
                if event.key in [pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]:
                    lvl_id = event.key - pygame.K_0
                    if lvl_id == 0: 
                        lvl_id = 10 # Если нажали 0, считаем, что это 10-й уровень
                        
                    if ctrl_held:
                        try:
                            with open(f"assets/levels/level_{lvl_id}.json", "r") as f: data = json.load(f)
                            level_map = [[0 for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
                            loaded_map = data.get("map", [])
                            for r in range(min(MAP_ROWS, len(loaded_map))):
                                for c in range(min(MAP_COLS, len(loaded_map[r]))): level_map[r][c] = loaded_map[r][c]
                            objects = data.get("objects", [])
                            guards = [{"type": g["type"], "pos": [g["x"], g["y"]]} for g in data.get("guards_data", [])]
                            entrance_pos = data.get("entrance_pos", [64, 64])
                            save_msg, msg_color, save_msg_timer = f"📂 ЗАГРУЖЕН LEVEL {lvl_id}!", (0, 200, 255), 120
                        except FileNotFoundError:
                            save_msg, msg_color, save_msg_timer = f"❌ ФАЙЛ LEVEL {lvl_id} НЕ НАЙДЕН!", (255, 50, 50), 120
                    else:
                        guards_data = [{"type": g["type"], "x": g["pos"][0], "y": g["pos"][1]} for g in guards]
                        data = {"entrance_pos": entrance_pos, "tiles": tiles_dict, "sprites": sprites_dict, "map": level_map, "objects": objects, "guards_data": guards_data}
                        with open(f"assets/levels/level_{lvl_id}.json", "w") as f: json.dump(data, f, indent=2)
                        save_msg, msg_color, save_msg_timer = f"✅ СОХРАНЕНО КАК LEVEL {lvl_id}!", (0, 255, 0), 120

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2: dragging, last_mouse_pos = True, event.pos
                elif event.button == 1:
                    cur_mode = modes[mode_idx]
                    if cur_mode == 'tiles' and shift_held: box_filling, box_start, box_end = True, (grid_x, grid_y), (grid_x, grid_y)
                    elif cur_mode == 'objects' and sprite_keys:
                        spr_id = sprite_keys[c_idx['objects']]
                        # ПРИВЯЗКА ОБЪЕКТОВ ПО СЕТКЕ 32x32 (чтобы плотно ставить к стене)
                        snap_x, snap_y = round(world_x / 32) * 32, round(world_y / 32) * 32
                        objects.append({"name": f"obj_{len(objects)}", "sprite_id": spr_id, "pos": [snap_x, snap_y]})
                    elif cur_mode == 'guards': guards.append({"type": guard_types[c_idx['guards']], "pos": [world_x, world_y]})
                    elif cur_mode == 'entrance': entrance_pos = [grid_x * 64, grid_y * 64]
                elif event.button == 3:
                    cur_mode = modes[mode_idx]
                    if cur_mode == 'objects':
                        for obj in reversed(objects):
                            if abs(world_x - obj['pos'][0]) < 32 and abs(world_y - obj['pos'][1]) < 32:
                                objects.remove(obj); break
                    elif cur_mode == 'guards':
                        for g in reversed(guards):
                            if abs(world_x - g['pos'][0]) < 30 and abs(world_y - g['pos'][1]) < 30:
                                guards.remove(g); break

            if event.type == pygame.MOUSEMOTION:
                if dragging:
                    camera_x += event.pos[0] - last_mouse_pos[0]
                    camera_y += event.pos[1] - last_mouse_pos[1]
                    last_mouse_pos = event.pos
                elif box_filling: box_end = (grid_x, grid_y)

            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2: dragging = False
                elif event.button == 1 and box_filling:
                    x1, x2 = min(box_start[0], box_end[0]), max(box_start[0], box_end[0])
                    y1, y2 = min(box_start[1], box_end[1]), max(box_start[1], box_end[1])
                    for r in range(y1, y2 + 1):
                        for c in range(x1, x2 + 1): level_map[r][c] = int(tile_keys[c_idx['tiles']])
                    box_filling = False

        # ОТРИСОВКА С УЧЕТОМ НОВОЙ СЕТКИ 64x64
        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                tid = str(level_map[r][c])
                if tid in scaled_tiles: screen.blit(scaled_tiles[tid], (c*64*zoom + camera_x, r*64*zoom + camera_y))

        for obj in objects:
            sid = obj['sprite_id']
            if sid in scaled_sprites: screen.blit(scaled_sprites[sid], (obj['pos'][0]*zoom + camera_x, obj['pos'][1]*zoom + camera_y))
                
        for g in guards:
            pygame.draw.circle(screen, guard_colors[g['type']], (g['pos'][0]*zoom + camera_x, g['pos'][1]*zoom + camera_y), int(20*zoom))
            
        ex, ey = entrance_pos[0]*zoom + camera_x, entrance_pos[1]*zoom + camera_y
        pygame.draw.rect(screen, (0, 255, 0), (ex, ey, 64*zoom, 64*zoom), max(1, int(4*zoom)))
        screen.blit(font.render("SPAWN", True, (0, 255, 0)), (ex, ey - 20))

        if box_filling:
            x1, x2, y1, y2 = min(box_start[0], box_end[0]), max(box_start[0], box_end[0]), min(box_start[1], box_end[1]), max(box_start[1], box_end[1])
            pygame.draw.rect(screen, (255, 255, 0), (x1*64*zoom + camera_x, y1*64*zoom + camera_y, (x2-x1+1)*64*zoom, (y2-y1+1)*64*zoom), max(1, int(4*zoom)))

        # ОТРИСОВКА ПОЛУПРОЗРАЧНОЙ КИСТИ ДЛЯ ТАЙЛОВ И ОБЪЕКТОВ
        cur_mode = modes[mode_idx]
        if not dragging:
            if cur_mode == 'objects' and sprite_keys:
                ghost_img = scaled_sprites[sprite_keys[c_idx['objects']]].copy()
                ghost_img.set_alpha(150) 
                snap_x = round(world_x / 32) * 32 * zoom + camera_x
                snap_y = round(world_y / 32) * 32 * zoom + camera_y
                screen.blit(ghost_img, (snap_x, snap_y))
            elif cur_mode == 'tiles' and tile_keys:
                # Призрак для тайлов (по сетке 64x64)
                ghost_img = scaled_tiles[tile_keys[c_idx['tiles']]].copy()
                ghost_img.set_alpha(150)
                screen.blit(ghost_img, (grid_x * 64 * zoom + camera_x, grid_y * 64 * zoom + camera_y))

        txt = ""
        if cur_mode == 'tiles': txt = f"ТАЙЛЫ | {tiles_dict[tile_keys[c_idx['tiles']]]} | ЛКМ: Кисть | SHIFT: Заливка"
        elif cur_mode == 'objects': txt = f"ОБЪЕКТЫ | {sprites_dict[sprite_keys[c_idx['objects']]]} | ЛКМ/ПКМ"
        elif cur_mode == 'guards': txt = f"ВРАГИ | {guard_types[c_idx['guards']]} | ЛКМ/ПКМ"
        elif cur_mode == 'entrance': txt = "СПАВН | ЛКМ: Поставить точку"

        surf = font.render(f"[M] Режим: {txt} | СОХРАНИТЬ: 1-0 (0=10) | ЗАГРУЗИТЬ: CTRL + 1-0", True, (255, 255, 0))
        pygame.draw.rect(screen, (0, 0, 0), (5, 5, surf.get_width() + 10, surf.get_height() + 10))
        screen.blit(surf, (10, 10))

        if save_msg_timer > 0:
            msg_surf = font.render(save_msg, True, msg_color)
            pygame.draw.rect(screen, (0, 0, 0), (5, 45, msg_surf.get_width() + 10, msg_surf.get_height() + 10))
            screen.blit(msg_surf, (10, 50))
            save_msg_timer -= 1

        pygame.display.flip()
        clock.tick(60)
        
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.NOFRAME)

if __name__ == "__main__":
    run_editor()
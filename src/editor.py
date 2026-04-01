import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame
import json
import math
from src.settings import WINDOW_WIDTH, WINDOW_HEIGHT, TILES_DIR, PROPS_DIR, LEVELS_DIR

def run_editor():
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)
    pygame.display.set_caption("SHUSH - Ultimate Level Editor")
    clock = pygame.time.Clock()

    MAP_COLS, MAP_ROWS = 100, 100
    
    base_tiles = ["home_floor_96x64.png", "street_floor_96x64.png", "walls_96x64.png"]
    tiles_dict = {"0": base_tiles[0], "1": base_tiles[1], "2": base_tiles[2]}
    t_idx = 3
    for file in sorted(os.listdir(TILES_DIR)):
        if file.endswith('.png') and file not in base_tiles:
            tiles_dict[str(t_idx)] = file
            t_idx += 1

    sprites_dict = {}
    s_idx = 0
    for file in sorted(os.listdir(PROPS_DIR)):
        if file.endswith('.png'):
            sprites_dict[f"spr_{s_idx}"] = file
            s_idx += 1

    tile_imgs = {}
    for k, v in tiles_dict.items():
        raw_img = pygame.image.load(os.path.join(TILES_DIR, v)).convert_alpha()
        tile_imgs[k] = pygame.transform.scale(raw_img, (64, 64))
        
    sprite_imgs = {}
    for k, v in sprites_dict.items():
        img = pygame.image.load(os.path.join(PROPS_DIR, v)).convert_alpha()
        sprite_imgs[k] = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))

    def get_scaled_imgs(z):
        t = {k: pygame.transform.scale(img, (int(img.get_width()*z), int(img.get_height()*z))) for k, img in tile_imgs.items()}
        s = {k: pygame.transform.scale(img, (int(img.get_width()*z), int(img.get_height()*z))) for k, img in sprite_imgs.items()}
        return t, s

    level_map = [[-1 for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
    objects = []
    guards = []
    entrance_pos = [64, 64]

    modes = ['tiles', 'objects', 'guards', 'entrance']
    mode_idx = 0
    tile_keys, sprite_keys = list(tiles_dict.keys()), list(sprites_dict.keys())
    guard_types = ['normal', 'fast', 'taser', 'random', 'swat']
    guard_colors = {'normal': (100, 100, 255), 'fast': (255, 255, 0), 'taser': (255, 100, 100), 'random': (200, 0, 200), 'swat': (50, 50, 50)}
    c_idx = {'tiles': 0, 'objects': 0, 'guards': 0}

    camera_x, camera_y = 0, 0
    zoom = 1.0
    current_level_id = "edit"
    scaled_tiles, scaled_sprites = get_scaled_imgs(zoom)
    
    dragging, box_filling, box_del_filling = False, False, False
    drawing_lmb, drawing_rmb = False, False 
    last_mouse_pos, box_start, box_end = (0, 0), (0, 0), (0, 0)
    box_del_start, box_del_end = (0, 0), (0, 0)

    font = pygame.font.SysFont("Arial", 22)
    running = True
    is_fullscreen = True
    save_msg, save_msg_timer, msg_color = "", 0, (0, 255, 0)

    while running:
        screen.fill((30, 30, 35))
        keys = pygame.key.get_pressed()
        shift_held = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        ctrl_held = keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]
        
        mx, my = pygame.mouse.get_pos()
        world_x, world_y = (mx - camera_x) / zoom, (my - camera_y) / zoom
        
        grid_x = max(0, min(MAP_COLS - 1, int(world_x // 64)))
        grid_y = max(0, min(MAP_ROWS - 1, int(world_y // 64)))

        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                running = False
                
            if event.type == pygame.MOUSEWHEEL:
                old_zoom = zoom
                zoom = max(0.2, min(zoom + event.y * 0.1, 3.0))
                if zoom != old_zoom:
                    camera_x, camera_y = mx - world_x * zoom, my - world_y * zoom
                    scaled_tiles, scaled_sprites = get_scaled_imgs(zoom)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                if event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)
                    else:
                        screen = pygame.display.set_mode((1536, 768))
                
                if event.key == pygame.K_m: mode_idx = (mode_idx + 1) % 4
                
                cur_mode = modes[mode_idx]
                if event.key == pygame.K_q and cur_mode in c_idx: 
                    c_idx[cur_mode] = max(0, c_idx[cur_mode] - 1)
                if event.key == pygame.K_e and not ctrl_held and cur_mode in c_idx: 
                    max_l = len(tile_keys) if cur_mode == 'tiles' else (len(sprite_keys) if cur_mode == 'objects' else len(guard_types))
                    c_idx[cur_mode] = min(max_l - 1, c_idx[cur_mode] + 1)
                    
                if event.key in [pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]:
                    if ctrl_held:
                        lvl_id = event.key - pygame.K_0
                        if lvl_id == 0: lvl_id = 10
                        
                        filepath = os.path.join(LEVELS_DIR, f"level_{lvl_id}.json")
                        try:
                            with open(filepath, "r") as f: 
                                data = json.load(f)
                            
                            file_tiles = data.get("tiles", {})
                            stone_id = 0
                            for k, v in tiles_dict.items():
                                if "wall_stone" in v.lower():
                                    stone_id = int(k)
                                    break
                            
                            level_map = [[-1 for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
                            loaded_map = data.get("map", [])
                            for r in range(min(MAP_ROWS, len(loaded_map))):
                                for c in range(min(MAP_COLS, len(loaded_map[r]))): 
                                    file_val = str(loaded_map[r][c])
                                    if file_val == "-1":
                                        level_map[r][c] = -1
                                    else:
                                        filename = file_tiles.get(file_val, "")
                                        real_tile_id = stone_id 
                                        for real_k, real_v in tiles_dict.items():
                                            if real_v == filename:
                                                real_tile_id = int(real_k)
                                                break
                                        level_map[r][c] = real_tile_id
                            
                            objects = data.get("objects", [])
                            file_sprites = data.get("sprites", {})
                            for obj in objects:
                                filename = file_sprites.get(obj.get("sprite_id"), "")
                                for real_id, real_filename in sprites_dict.items():
                                    if real_filename == filename:
                                        obj["sprite_id"] = real_id
                                        break
                            
                            guards = [{"type": g["type"], "pos": [g.get("x", 0), g.get("y", 0)]} for g in data.get("guards_data", [])]
                            entrance_pos = data.get("entrance_pos", [64, 64])
                            camera_x = (1536 // 2) - (entrance_pos[0] * zoom)
                            camera_y = (768 // 2) - (entrance_pos[1] * zoom)
                            
                            current_level_id = str(lvl_id)
                            save_msg, msg_color, save_msg_timer = f"Загружен уровень {lvl_id}.", (0, 200, 255), 120
                        except FileNotFoundError:
                            save_msg, msg_color, save_msg_timer = f"Файл уровня {lvl_id} не найден.", (255, 50, 50), 120

                if event.key == pygame.K_e and ctrl_held:
                    filepath = os.path.join(LEVELS_DIR, "level_custom.json")
                    try:
                        with open(filepath, "r") as f: 
                            data = json.load(f)
                            
                        file_tiles = data.get("tiles", {})
                        stone_id = 0
                        for k, v in tiles_dict.items():
                            if "wall_stone" in v.lower(): stone_id = int(k); break
                        level_map = [[-1 for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
                        loaded_map = data.get("map", [])
                        for r in range(min(MAP_ROWS, len(loaded_map))):
                            for c in range(min(MAP_COLS, len(loaded_map[r]))): 
                                file_val = str(loaded_map[r][c])
                                if file_val == "-1":
                                    level_map[r][c] = -1
                                else:
                                    filename = file_tiles.get(file_val, "")
                                    real_tile_id = stone_id 
                                    for real_k, real_v in tiles_dict.items():
                                        if real_v == filename:
                                            real_tile_id = int(real_k)
                                            break
                                    level_map[r][c] = real_tile_id
                                
                        objects = data.get("objects", [])
                        file_sprites = data.get("sprites", {})
                        for obj in objects:
                            filename = file_sprites.get(obj.get("sprite_id"), "")
                            for real_id, real_filename in sprites_dict.items():
                                if real_filename == filename: obj["sprite_id"] = real_id; break
                                
                        guards = [{"type": g["type"], "pos": [g.get("x", 0), g.get("y", 0)]} for g in data.get("guards_data", [])]
                        entrance_pos = data.get("entrance_pos", [64, 64])
                        camera_x = (1536 // 2) - (entrance_pos[0] * zoom)
                        camera_y = (768 // 2) - (entrance_pos[1] * zoom)
                        
                        current_level_id = "edit"
                        save_msg, msg_color, save_msg_timer = f"Загружен собственный уровень.", (0, 200, 255), 120
                    except FileNotFoundError:
                        save_msg, msg_color, save_msg_timer = f"Файл собственного уровня не найден.", (255, 50, 50), 120

                if event.key == pygame.K_s and ctrl_held:
                    guards_data = [{"type": g["type"], "x": g["pos"][0], "y": g["pos"][1]} for g in guards]
                    data = {
                        "entrance_pos": entrance_pos, 
                        "tiles": tiles_dict, 
                        "sprites": sprites_dict, 
                        "map": level_map, 
                        "objects": objects, 
                        "guards_data": guards_data
                    }
                    
                    filepath = os.path.join(LEVELS_DIR, "level_custom.json")
                    with open(filepath, "w") as f: 
                        json.dump(data, f, indent=2)
                        
                    save_msg, msg_color, save_msg_timer = f"Сохранено как 'Собственный уровень'.", (0, 255, 0), 120

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2: dragging, last_mouse_pos = True, event.pos
                elif event.button == 1:
                    drawing_lmb = True
                    cur_mode = modes[mode_idx]
                    if cur_mode == 'tiles' and not shift_held and not ctrl_held:
                        level_map[grid_y][grid_x] = int(tile_keys[c_idx['tiles']])
                    elif cur_mode == 'tiles' and shift_held: 
                        box_filling, box_start, box_end = True, (grid_x, grid_y), (grid_x, grid_y)
                    elif cur_mode == 'objects' and sprite_keys:
                        spr_id = sprite_keys[c_idx['objects']]
                        alt_held = keys[pygame.K_LALT] or keys[pygame.K_RALT]
                        snap_x, snap_y = (round(world_x / 8) * 8, round(world_y / 8) * 8) if alt_held else (round(world_x / 32) * 32, round(world_y / 32) * 32)
                        objects.append({"name": f"obj_{len(objects)}", "sprite_id": spr_id, "pos": [snap_x, snap_y]})
                    elif cur_mode == 'guards': guards.append({"type": guard_types[c_idx['guards']], "pos": [world_x, world_y]})
                    elif cur_mode == 'entrance': entrance_pos = [grid_x * 64, grid_y * 64]
                
                elif event.button == 3:
                    drawing_rmb = True
                    cur_mode = modes[mode_idx]
                    if cur_mode == 'tiles' and not shift_held and not ctrl_held:
                        level_map[grid_y][grid_x] = -1
                    elif cur_mode == 'tiles' and shift_held:
                        box_del_filling, box_del_start, box_del_end = True, (grid_x, grid_y), (grid_x, grid_y)
                    elif cur_mode == 'objects':
                        for obj in reversed(objects):
                            sid = obj['sprite_id']
                            if sid in sprite_imgs:
                                img = sprite_imgs[sid]
                                if pygame.Rect(obj['pos'][0], obj['pos'][1], img.get_width(), img.get_height()).collidepoint(world_x, world_y):
                                    objects.remove(obj); break
                    elif cur_mode == 'guards':
                        for g in reversed(guards):
                            if math.hypot(world_x - g['pos'][0], world_y - g['pos'][1]) < 30:
                                guards.remove(g); break

            if event.type == pygame.MOUSEMOTION:
                if dragging:
                    camera_x += event.pos[0] - last_mouse_pos[0]
                    camera_y += event.pos[1] - last_mouse_pos[1]
                    last_mouse_pos = event.pos
                elif box_filling: box_end = (grid_x, grid_y)
                elif box_del_filling: box_del_end = (grid_x, grid_y)
                else:
                    if drawing_lmb and not ctrl_held and modes[mode_idx] == 'tiles' and not shift_held:
                        level_map[grid_y][grid_x] = int(tile_keys[c_idx['tiles']])
                    elif drawing_rmb and not ctrl_held and modes[mode_idx] == 'tiles' and not shift_held:
                        level_map[grid_y][grid_x] = -1

            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2: dragging = False
                elif event.button == 1:
                    drawing_lmb = False
                    if box_filling:
                        x1, x2 = min(box_start[0], box_end[0]), max(box_start[0], box_end[0])
                        y1, y2 = min(box_start[1], box_end[1]), max(box_start[1], box_end[1])
                        for r in range(y1, y2 + 1):
                            for c in range(x1, x2 + 1): level_map[r][c] = int(tile_keys[c_idx['tiles']])
                        box_filling = False
                elif event.button == 3:
                    drawing_rmb = False
                    if box_del_filling:
                        x1, x2 = min(box_del_start[0], box_del_end[0]), max(box_del_start[0], box_del_end[0])
                        y1, y2 = min(box_del_start[1], box_del_end[1]), max(box_del_start[1], box_del_end[1])
                        for r in range(y1, y2 + 1):
                            for c in range(x1, x2 + 1): level_map[r][c] = -1
                        box_del_filling = False

        start_c = max(0, int(-camera_x / (64 * zoom)))
        end_c = min(MAP_COLS, int((screen.get_width() - camera_x) / (64 * zoom)) + 1)
        start_r = max(0, int(-camera_y / (64 * zoom)))
        end_r = min(MAP_ROWS, int((screen.get_height() - camera_y) / (64 * zoom)) + 1)

        for r in range(start_r, end_r):
            for c in range(start_c, end_c):
                tid = str(level_map[r][c])
                if tid != "-1" and tid in scaled_tiles: 
                    screen.blit(scaled_tiles[tid], (c*64*zoom + camera_x, r*64*zoom + camera_y))

        for obj in objects:
            sid = obj['sprite_id']
            if sid in scaled_sprites: screen.blit(scaled_sprites[sid], (obj['pos'][0]*zoom + camera_x, obj['pos'][1]*zoom + camera_y))
                
        for g in guards:
            pygame.draw.circle(screen, guard_colors[g['type']], (g['pos'][0]*zoom + camera_x, g['pos'][1]*zoom + camera_y), int(20*zoom))
            
        ex, ey = entrance_pos[0]*zoom + camera_x, entrance_pos[1]*zoom + camera_y
        pygame.draw.rect(screen, (0, 255, 0), (ex, ey, 64*zoom, 64*zoom), max(1, int(4*zoom)))
        screen.blit(font.render("SPAWN", True, (0, 255, 0)), (ex, ey - 20))

        if box_del_filling:
            x1, x2, y1, y2 = min(box_del_start[0], box_del_end[0]), max(box_del_start[0], box_del_end[0]), min(box_del_start[1], box_del_end[1]), max(box_del_start[1], box_del_end[1])
            pygame.draw.rect(screen, (255, 50, 50), (x1*64*zoom + camera_x, y1*64*zoom + camera_y, (x2-x1+1)*64*zoom, (y2-y1+1)*64*zoom), max(1, int(4*zoom)))

        cur_mode = modes[mode_idx]
        if not dragging:
            if cur_mode == 'objects' and sprite_keys:
                ghost_img = scaled_sprites[sprite_keys[c_idx['objects']]].copy()
                ghost_img.set_alpha(150) 
                
                alt_held = keys[pygame.K_LALT] or keys[pygame.K_RALT]
                if alt_held:
                    snap_x = round(world_x / 8) * 8 * zoom + camera_x
                    snap_y = round(world_y / 8) * 8 * zoom + camera_y
                else:
                    snap_x = round(world_x / 32) * 32 * zoom + camera_x
                    snap_y = round(world_y / 32) * 32 * zoom + camera_y
                    
                screen.blit(ghost_img, (snap_x, snap_y))
            elif cur_mode == 'tiles' and tile_keys:
                ghost_img = scaled_tiles[tile_keys[c_idx['tiles']]].copy()
                ghost_img.set_alpha(150)
                screen.blit(ghost_img, (grid_x * 64 * zoom + camera_x, grid_y * 64 * zoom + camera_y))

        txt = ""
        if cur_mode == 'tiles': txt = f"Тайтлы | {tiles_dict[tile_keys[c_idx['tiles']]]} | ЛКМ: Кисть | ПКМ: Ластик | SHIFT: Заливка"
        elif cur_mode == 'objects': txt = f"Объекты | {sprites_dict[sprite_keys[c_idx['objects']]]} | Зажми ALT для точной установки"
        elif cur_mode == 'guards': txt = f"Полиция | {guard_types[c_idx['guards']]} | ЛКМ/ПКМ"
        elif cur_mode == 'entrance': txt = "Точка спавна | ЛКМ: Поставить точку"

        surf = font.render(f"[M] Режим: {txt} | Сохранить собственный уровень: CTRL+S | Загрузить: CTRL+1-0 или CTRL+E", True, (255, 255, 0))
        pygame.draw.rect(screen, (0, 0, 0), (5, 5, surf.get_width() + 10, surf.get_height() + 10))
        screen.blit(surf, (10, 10))

        if save_msg_timer > 0:
            msg_surf = font.render(save_msg, True, msg_color)
            pygame.draw.rect(screen, (0, 0, 0), (5, 45, msg_surf.get_width() + 10, msg_surf.get_height() + 10))
            screen.blit(msg_surf, (10, 50))
            save_msg_timer -= 1

        pygame.display.flip()
        clock.tick(60)
        
    pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)

if __name__ == "__main__":
    run_editor()
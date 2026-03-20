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
    
    tiles_dict = {"0": "home_floor_96x64.png", "1": "street_floor_96x64.png", "2": "walls_96x64.png"}
    sprites_dict = {f"spr_{i}": file for i, file in enumerate(sorted(os.listdir('assets/sprites'))) if file.endswith('.png')}

    tile_imgs = {k: pygame.image.load(os.path.join('assets/tiles', v)).convert_alpha() for k, v in tiles_dict.items()}
    
    sprite_imgs = {}
    for k, v in sprites_dict.items():
        img = pygame.image.load(os.path.join('assets/sprites', v)).convert_alpha()
        sprite_imgs[k] = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))

    def get_scaled_imgs(z):
        t = {k: pygame.transform.scale(img, (int(96*z), int(64*z))) for k, img in tile_imgs.items()}
        s = {k: pygame.transform.scale(img, (int(img.get_width()*z), int(img.get_height()*z))) for k, img in sprite_imgs.items()}
        return t, s

    level_map = [[0 for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
    objects = []
    guards = []
    entrance_pos = [96, 64]

    modes = ['tiles', 'objects', 'guards', 'entrance']
    mode_idx = 0
    tile_keys, sprite_keys = list(tiles_dict.keys()), list(sprites_dict.keys())
    guard_types = ['normal', 'fast', 'taser', 'random', 'swat']
    guard_colors = {'normal': (100, 100, 255), 'fast': (255, 255, 0), 'taser': (255, 100, 100), 'random': (200, 0, 200), 'swat': (50, 50, 50)}
    c_idx = {'tiles': 0, 'objects': 0, 'guards': 0}

    camera_x, camera_y = 0, 0
    zoom = 1.0
    scaled_tiles, scaled_sprites = get_scaled_imgs(zoom)
    dragging = False
    last_mouse_pos = (0, 0)

    box_filling = False
    box_start = (0, 0)
    box_end = (0, 0)

    font = pygame.font.SysFont("Arial", 22)
    running = True
    save_msg = ""
    save_msg_timer = 0
    msg_color = (0, 255, 0)

    while running:
        screen.fill((30, 30, 35))
        keys = pygame.key.get_pressed()
        shift_held = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        ctrl_held = keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]
        mouse_pressed = pygame.mouse.get_pressed()
        
        mx, my = pygame.mouse.get_pos()
        world_x = (mx - camera_x) / zoom
        world_y = (my - camera_y) / zoom
        grid_x = max(0, min(MAP_COLS - 1, int(world_x // 96)))
        grid_y = max(0, min(MAP_ROWS - 1, int(world_y // 64)))

        if mouse_pressed[0] and not box_filling and not dragging:
            if modes[mode_idx] == 'tiles' and not shift_held:
                level_map[grid_y][grid_x] = int(tile_keys[c_idx['tiles']])

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            
            if event.type == pygame.MOUSEWHEEL:
                old_zoom = zoom
                zoom += event.y * 0.1
                zoom = max(0.2, min(zoom, 3.0))
                if zoom != old_zoom:
                    camera_x = mx - world_x * zoom
                    camera_y = my - world_y * zoom
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
                    
                # СОХРАНЕНИЕ И ЗАГРУЗКА
                if event.key in [pygame.K_1, pygame.K_2, pygame.K_3]:
                    lvl_id = event.key - pygame.K_0
                    
                    if ctrl_held:
                        # --- ЗАГРУЗКА ---
                        try:
                            with open(f"assets/levels/level_{lvl_id}.json", "r") as f:
                                data = json.load(f)
                            
                            # Очищаем карту
                            level_map = [[0 for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
                            loaded_map = data.get("map", [])
                            for r in range(min(MAP_ROWS, len(loaded_map))):
                                for c in range(min(MAP_COLS, len(loaded_map[r]))):
                                    level_map[r][c] = loaded_map[r][c]
                            
                            objects = data.get("objects", [])
                            
                            guards.clear()
                            for g in data.get("guards_data", []):
                                guards.append({"type": g["type"], "pos": [g["x"], g["y"]]})
                            
                            entrance_pos = data.get("entrance_pos", [96, 64])
                            
                            save_msg = f"📂 ЗАГРУЖЕН LEVEL {lvl_id}!"
                            msg_color = (0, 200, 255) # Голубой цвет для загрузки
                            save_msg_timer = 120
                        except FileNotFoundError:
                            save_msg = f"❌ ФАЙЛ LEVEL {lvl_id} НЕ НАЙДЕН!"
                            msg_color = (255, 50, 50)
                            save_msg_timer = 120
                    else:
                        # --- СОХРАНЕНИЕ ---
                        guards_data = [{"type": g["type"], "x": g["pos"][0], "y": g["pos"][1]} for g in guards]
                        data = {"entrance_pos": entrance_pos, "tiles": tiles_dict, "sprites": sprites_dict, "map": level_map, "objects": objects, "guards_data": guards_data}
                        with open(f"assets/levels/level_{lvl_id}.json", "w") as f:
                            json.dump(data, f, indent=2)
                        save_msg = f"✅ СОХРАНЕНО КАК LEVEL {lvl_id}!"
                        msg_color = (0, 255, 0)
                        save_msg_timer = 120 

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2:
                    dragging = True
                    last_mouse_pos = event.pos
                
                elif event.button == 1:
                    cur_mode = modes[mode_idx]
                    if cur_mode == 'tiles':
                        if shift_held:
                            box_filling = True
                            box_start = (grid_x, grid_y)
                            box_end = (grid_x, grid_y)
                    elif cur_mode == 'objects' and sprite_keys:
                        spr_id = sprite_keys[c_idx['objects']]
                        t = "vase" if "vase" in sprites_dict[spr_id].lower() or "picture" in sprites_dict[spr_id].lower() else "bush"
                        snap_x = round(world_x / 48) * 48
                        snap_y = round(world_y / 32) * 32
                        objects.append({"name": f"obj_{len(objects)}", "type": t, "sprite_id": spr_id, "pos": [snap_x, snap_y]})
                        
                    elif cur_mode == 'guards':
                        guards.append({"type": guard_types[c_idx['guards']], "pos": [world_x, world_y]})
                    elif cur_mode == 'entrance':
                        entrance_pos = [grid_x * 96, grid_y * 64]
                        
                elif event.button == 3:
                    cur_mode = modes[mode_idx]
                    if cur_mode == 'objects':
                        for obj in reversed(objects):
                            if abs(world_x - obj['pos'][0]) < 48 and abs(world_y - obj['pos'][1]) < 48:
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
                elif box_filling:
                    box_end = (grid_x, grid_y)

            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    dragging = False
                elif event.button == 1 and box_filling:
                    x1, x2 = min(box_start[0], box_end[0]), max(box_start[0], box_end[0])
                    y1, y2 = min(box_start[1], box_end[1]), max(box_start[1], box_end[1])
                    for r in range(y1, y2 + 1):
                        for c in range(x1, x2 + 1):
                            level_map[r][c] = int(tile_keys[c_idx['tiles']])
                    box_filling = False

        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                tid = str(level_map[r][c])
                if tid in scaled_tiles:
                    screen.blit(scaled_tiles[tid], (c*96*zoom + camera_x, r*64*zoom + camera_y))

        for obj in objects:
            sid = obj['sprite_id']
            if sid in scaled_sprites:
                screen.blit(scaled_sprites[sid], (obj['pos'][0]*zoom + camera_x, obj['pos'][1]*zoom + camera_y))
                
        for g in guards:
            pygame.draw.circle(screen, guard_colors[g['type']], (g['pos'][0]*zoom + camera_x, g['pos'][1]*zoom + camera_y), int(20*zoom))
            
        ex, ey = entrance_pos[0]*zoom + camera_x, entrance_pos[1]*zoom + camera_y
        pygame.draw.rect(screen, (0, 255, 0), (ex, ey, 96*zoom, 64*zoom), max(1, int(4*zoom)))
        txt_e = font.render("SPAWN", True, (0, 255, 0))
        screen.blit(txt_e, (ex, ey - 20))

        if box_filling:
            x1, x2 = min(box_start[0], box_end[0]), max(box_start[0], box_end[0])
            y1, y2 = min(box_start[1], box_end[1]), max(box_start[1], box_end[1])
            px = x1 * 96 * zoom + camera_x
            py = y1 * 64 * zoom + camera_y
            pw = (x2 - x1 + 1) * 96 * zoom
            ph = (y2 - y1 + 1) * 64 * zoom
            pygame.draw.rect(screen, (255, 255, 0), (px, py, pw, ph), max(1, int(4*zoom)))

        cur_mode = modes[mode_idx]
        if cur_mode == 'objects' and sprite_keys and not dragging:
            spr_id = sprite_keys[c_idx['objects']]
            ghost_img = scaled_sprites[spr_id].copy()
            ghost_img.set_alpha(150) 
            snap_x = round(world_x / 48) * 48
            snap_y = round(world_y / 32) * 32
            screen.blit(ghost_img, (snap_x*zoom + camera_x, snap_y*zoom + camera_y))

        if cur_mode == 'tiles': txt = f"ТАЙЛЫ | {tiles_dict[tile_keys[c_idx['tiles']]]} | ЛКМ: Кисть | SHIFT+ЛКМ: Заливка"
        elif cur_mode == 'objects': txt = f"ОБЪЕКТЫ | {sprites_dict[sprite_keys[c_idx['objects']]]} | ЛКМ/ПКМ (По Сетке)"
        elif cur_mode == 'guards': txt = f"ВРАГИ | {guard_types[c_idx['guards']]} | ЛКМ/ПКМ"
        elif cur_mode == 'entrance': txt = "СПАВН | ЛКМ: Поставить точку появления"

        ui_txt = f"[M] Режим: {txt} | СОХРАНИТЬ: 1, 2, 3 | ЗАГРУЗИТЬ: CTRL + 1, 2, 3"
        surf = font.render(ui_txt, True, (255, 255, 0))
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
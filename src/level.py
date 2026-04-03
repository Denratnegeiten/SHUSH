import pygame
import json
import os
import math
from src.settings import TILES_DIR, PROPS_DIR, CHARS_DIR

class Level:
    def __init__(self, level_path):
        self.tile_images = {}
        self.sprite_images = {}
        
        self.walls = []
        self.hiding_spots = []
        self.loot = []
        self.doors = []
        self.lasers = []
        
        self.level_data = self.load_data(level_path)
        
        self.guards_data = self.level_data.get('guards_data', [])
        
        epos = self.level_data.get('entrance_pos', [96, 64])
        self.entrance_rect = pygame.Rect(epos[0], epos[1], 96, 64) 

        self.build_physics()

    def load_data(self, path):
        with open(path, 'r') as f:
            data = json.load(f)

        for tile_id, filename in data['tiles'].items():
            img_path = os.path.join(TILES_DIR, filename)
            raw_img = pygame.image.load(img_path).convert_alpha()
            self.tile_images[int(tile_id)] = pygame.transform.scale(raw_img, (64, 64))

        for sprite_id, filename in data.get('sprites', {}).items():
            prop_path = os.path.join(PROPS_DIR, filename)
            char_path = os.path.join(CHARS_DIR, filename)

            if os.path.exists(prop_path):
                img_path = prop_path
            elif os.path.exists(char_path):
                img_path = char_path
            else:
                print(f"Внимание: файл {filename} не найден ни в props, ни в characters!")
                continue

            img = pygame.image.load(img_path).convert_alpha()
            self.sprite_images[sprite_id] = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))

        return data
    
    def build_physics(self):
        self.walls = []
        self.hiding_spots = []
        self.loot = []
        self.doors = []
        self.lasers = []
        
        map_data = self.level_data.get('map', [])
        max_rows = len(map_data)
        
        for row_index, row in enumerate(map_data):
            max_cols = len(row)
            for col_index, tile_id in enumerate(row):
                if tile_id == -1:
                    is_solid = True
                else:
                    filename = self.level_data.get('tiles', {}).get(str(tile_id), "").lower()
                    is_solid = "wall" in filename
                
                if is_solid:
                    is_border = False
                    
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            if dr == 0 and dc == 0:
                                continue
                            
                            nr = row_index + dr
                            nc = col_index + dc
                            
                            if 0 <= nr < max_rows and 0 <= nc < max_cols:
                                neighbor_id = map_data[nr][nc]
                                if neighbor_id != -1:
                                    neighbor_filename = self.level_data.get('tiles', {}).get(str(neighbor_id), "").lower()
                                    if "wall" not in neighbor_filename:
                                        is_border = True
                                        break
                                        
                        if is_border:
                            break
                    
                    if is_border:
                        rect = pygame.Rect(col_index * 64, row_index * 64, 64, 64)
                        self.walls.append(rect)

        for obj in self.level_data.get('objects', []):
            x, y = obj['pos']
            filename = self.level_data.get('sprites', {}).get(obj['sprite_id'], "").lower()
            
            img = self.sprite_images.get(obj['sprite_id'])
            w = img.get_width() if img else 64
            h = img.get_height() if img else 64
            rect = pygame.Rect(x, y, w, h)
            
            if "table" in filename:
                obj['type'] = 'hiding_spot_passable'
                obj['value'] = 0
                
            elif "vase" in filename:
                obj['type'] = 'vase'
                obj['value'] = 1000
                obj['weight'] = 15
                
            elif "picture" in filename:
                obj['type'] = 'picture'
                obj['value'] = 5000
                obj['weight'] = 35
            
            elif "bush" in filename or "tree" in filename or "flower" in filename or "chair" in filename or "sofa" in filename or "couch" in filename or "bench" in filename:
                obj['type'] = 'hiding_spot_passable'
                obj['value'] = 0
                
            else:
                obj['type'] = 'decor' 
                obj['value'] = 0
                
            obj['rect'] = rect

            if obj['type'] in ['vase', 'picture']:
                self.loot.append(obj) 
                
            elif obj['type'] == 'hiding_spot_passable':
                self.hiding_spots.append(rect)
                
            elif obj['type'] == 'hiding_spot_solid':
                self.hiding_spots.append(rect)
                wall_rect = pygame.Rect(x, y + h - (h // 3), w, h // 3)
                self.walls.append(wall_rect)
                
            elif obj['type'] == 'solid_decor':
                self.walls.append(rect)

        for d in self.level_data.get('doors', []):
            x = int(d.get('x', 0))
            y = int(d.get('y', 0))
            w = int(d.get('w', 64))
            h = int(d.get('h', 64))
            locked = bool(d.get('locked', True))
            requires_keycard = bool(d.get('requires_keycard', d.get('locked', False)))
            rect = pygame.Rect(x, y, w, h)
            door = {'rect': rect, 'locked': locked, 'requires_keycard': requires_keycard}
            self.doors.append(door)
            if locked:
                self.walls.append(rect)

        for lz in self.level_data.get('lasers', []):
            x = float(lz.get('x', 0))
            y = float(lz.get('y', 0))
            angle_deg = float(lz.get('angle', 0))
            max_distance = max(16, int(lz.get('length', 2400)))
            on_duration = max(1, int(lz.get('on_duration', 120)))
            off_duration = max(1, int(lz.get('off_duration', 90)))
            phase = int(lz.get('phase', 0))
            ex, ey = self._cast_laser_to_wall(x, y, angle_deg, max_distance)
            self.lasers.append({
                'x1': x,
                'y1': y,
                'x2': ex,
                'y2': ey,
                'angle': angle_deg,
                'length': math.hypot(ex - x, ey - y),
                'on_duration': on_duration,
                'off_duration': off_duration,
                'timer': phase % (on_duration + off_duration),
                'active': (phase % (on_duration + off_duration)) < on_duration,
            })

    def refresh_physics(self):
        pass

    def _cast_laser_to_wall(self, x, y, angle_deg, max_distance):
        angle_rad = math.radians(angle_deg)
        dx = math.cos(angle_rad)
        dy = math.sin(angle_rad)
        step = 4

        last_x, last_y = x, y
        dist = 0
        while dist < max_distance:
            nx = x + dx * dist
            ny = y + dy * dist
            if any(w.collidepoint(nx, ny) for w in self.walls):
                return last_x, last_y
            last_x, last_y = nx, ny
            dist += step

        return x + dx * max_distance, y + dy * max_distance

    def update_lasers(self):
        for laser in self.lasers:
            total = laser['on_duration'] + laser['off_duration']
            laser['timer'] = (laser['timer'] + 1) % total
            laser['active'] = laser['timer'] < laser['on_duration']

    def draw_doors(self, screen, camera):
        def draw_door_skin(rect, dark=False, unlocked=False):
            if unlocked:
                base = (82, 110, 82)
                border = (150, 190, 150)
                panel = (70, 95, 70)
                handle = (215, 215, 150)
            elif dark:
                base = (62, 48, 42)
                border = (115, 95, 82)
                panel = (52, 38, 33)
                handle = (185, 165, 105)
            else:
                base = (176, 142, 96)
                border = (235, 210, 165)
                panel = (156, 122, 80)
                handle = (245, 225, 150)

            pygame.draw.rect(screen, base, rect, border_radius=5)
            pygame.draw.rect(screen, border, rect, 2, border_radius=5)

            inset = max(4, rect.width // 10)
            panel_rect = rect.inflate(-inset * 2, -inset * 2)
            pygame.draw.rect(screen, panel, panel_rect, border_radius=4)
            pygame.draw.rect(screen, border, panel_rect, 1, border_radius=4)

            handle_x = panel_rect.right - max(5, rect.width // 8)
            handle_y = panel_rect.centery
            pygame.draw.circle(screen, handle, (handle_x, handle_y), max(2, rect.width // 16))

        for door in self.doors:
            door_rect = camera.apply(door['rect'])
            if door['locked']:
                draw_door_skin(door_rect, dark=door.get('requires_keycard', False), unlocked=False)
            else:
                draw_door_skin(door_rect, unlocked=True)

    def try_toggle_nearby_door(self, player_rect, has_keycard=False, blockers=None):
        interaction_rect = player_rect.inflate(90, 90)
        blockers = blockers or []
        candidates = [d for d in self.doors if interaction_rect.colliderect(d['rect'])]
        candidates.sort(
            key=lambda d: (d['rect'].centerx - player_rect.centerx) ** 2 + (d['rect'].centery - player_rect.centery) ** 2
        )

        for door in candidates:

            # Opening
            if door['locked']:
                if door.get('requires_keycard', False) and not has_keycard:
                    continue
                door['locked'] = False
                if door['rect'] in self.walls:
                    self.walls.remove(door['rect'])
                return True

            # Closing (only if no one stands in doorway)
            else:
                if any(door['rect'].colliderect(b) for b in blockers):
                    continue
                door['locked'] = True
                if door['rect'] not in self.walls:
                    self.walls.append(door['rect'])
                return True

        return False

    def draw_lasers(self, screen, camera):
        for laser in self.lasers:
            start = camera.apply_point((laser['x1'], laser['y1']))
            end = camera.apply_point((laser['x2'], laser['y2']))

            if laser['active']:
                color = (255, 40, 40)
                width = 3
            else:
                color = (120, 30, 30)
                width = 1

            pygame.draw.line(screen, color, start, end, width)
            pygame.draw.circle(screen, (180, 180, 180), (int(start[0]), int(start[1])), 5)

    def player_hits_active_laser(self, player_rect):
        for laser in self.lasers:
            if not laser['active']:
                continue

            if player_rect.clipline((laser['x1'], laser['y1']), (laser['x2'], laser['y2'])):
                return True

        return False

    def draw(self, screen, camera):
        screen_w, screen_h = screen.get_size()
        
        start_col = max(0, int(-camera.camera.x // 64))
        end_col = start_col + int(screen_w // 64) + 3 
        
        start_row = max(0, int(-camera.camera.y // 64))
        end_row = start_row + int(screen_h // 64) + 3

        map_data = self.level_data.get('map', [])
        for row_index in range(start_row, min(end_row, len(map_data))):
            row = map_data[row_index]
            for col_index in range(start_col, min(end_col, len(row))):
                tile_id = row[col_index]
                if tile_id in self.tile_images:
                    x = col_index * 64
                    y = row_index * 64
                    screen.blit(self.tile_images[tile_id], camera.apply_point((x, y)))

        for obj in self.level_data.get('objects', []):
            if obj['sprite_id'] in self.sprite_images:
                screen.blit(self.sprite_images[obj['sprite_id']], camera.apply_point(obj['pos']))
import pygame
import json
import os

class Level:
    def __init__(self, level_path):
        self.tile_images = {}
        self.sprite_images = {}
        
        self.walls = []
        self.hiding_spots = []
        self.loot = []
        
        self.level_data = self.load_data(level_path)
        
        self.guards_data = self.level_data.get('guards_data', [])
        
        epos = self.level_data.get('entrance_pos', [96, 64])
        self.entrance_rect = pygame.Rect(epos[0], epos[1], 96, 64) 

        self.build_physics()

    def load_data(self, path):
        with open(path, 'r') as f:
            data = json.load(f)

        for tile_id, filename in data['tiles'].items():
            img_path = os.path.join('assets', 'tiles', filename)
            raw_img = pygame.image.load(img_path).convert_alpha()
            self.tile_images[int(tile_id)] = pygame.transform.scale(raw_img, (64, 64))

        for sprite_id, filename in data.get('sprites', {}).items():
            img_path = os.path.join('assets', 'sprites', filename)
            img = pygame.image.load(img_path).convert_alpha()
            self.sprite_images[sprite_id] = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))

        return data

    def build_physics(self):
        self.walls = []
        self.hiding_spots = []
        self.loot = []
        
        map_data = self.level_data.get('map', [])
        max_rows = len(map_data)
        
        for row_index, row in enumerate(map_data):
            max_cols = len(row)
            for col_index, tile_id in enumerate(row):
                filename = self.level_data.get('tiles', {}).get(str(tile_id), "").lower()
                
                if "wall" in filename:
                    is_border = False
                    
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            if dr == 0 and dc == 0:
                                continue
                            
                            nr = row_index + dr
                            nc = col_index + dc
                            
                            if 0 <= nr < max_rows and 0 <= nc < max_cols:
                                neighbor_id = map_data[nr][nc]
                                neighbor_filename = self.level_data.get('tiles', {}).get(str(neighbor_id), "").lower()
                                
                                if "wall" not in neighbor_filename:
                                    is_border = True
                                    break
                            else:
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
                
            elif "picture" in filename:
                obj['type'] = 'picture'
                obj['value'] = 5000
            
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

    def refresh_physics(self):
        pass

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
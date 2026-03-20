import pygame
import json
import os

class Level:
    def __init__(self, level_path):
        self.tile_images = {}
        self.sprite_images = {}
        
        # Списки для физики и логики
        self.walls = []
        self.hiding_spots = []
        self.loot = []
        
        # 1. СНАЧАЛА ЗАГРУЖАЕМ ДАННЫЕ УРОВНЯ
        self.level_data = self.load_data(level_path)
        
        # 2. ТЕПЕРЬ БЕРЕМ ИЗ НИХ ЗНАЧЕНИЯ
        self.guards_data = self.level_data.get('guards_data', [])
        
        epos = self.level_data.get('entrance_pos', [96, 64])
        self.entrance_rect = pygame.Rect(epos[0], epos[1], 96, 64) 

        # 3. СТРОИМ ФИЗИКУ СТЕН И УКРЫТИЙ
        self.build_physics()

    def load_data(self, path):
        with open(path, 'r') as f:
            data = json.load(f)

        for tile_id, filename in data['tiles'].items():
            img_path = os.path.join('assets', 'tiles', filename)
            self.tile_images[int(tile_id)] = pygame.image.load(img_path).convert_alpha()

        for sprite_id, filename in data.get('sprites', {}).items():
            img_path = os.path.join('assets', 'sprites', filename)
            img = pygame.image.load(img_path).convert_alpha()
            # УВЕЛИЧИВАЕМ КАРТИНКИ В 2 РАЗА ПРИ ЗАГРУЗКЕ
            self.sprite_images[sprite_id] = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))

        return data

    def build_physics(self):
        # Коллизии для стен
        for row_index, row in enumerate(self.level_data.get('map', [])):
            for col_index, tile_id in enumerate(row):
                if tile_id == 2:
                    rect = pygame.Rect(col_index * 96, row_index * 64, 96, 64)
                    self.walls.append(rect)

        # Хитбоксы для объектов
        for obj in self.level_data.get('objects', []):
            x, y = obj['pos']
            
            # Получаем реальные размеры увеличенного спрайта
            img = self.sprite_images.get(obj['sprite_id'])
            w = img.get_width() if img else 64
            h = img.get_height() if img else 64
            
            rect = pygame.Rect(x, y, w, h)
            obj['rect'] = rect 

            if obj['type'] in ['vase', 'picture']:
                self.loot.append(rect)
            elif obj['type'] in ['bush', 'sofa']:
                self.hiding_spots.append(rect) # Вся зона укрытия
                
                # ХИТРОСТЬ: Делаем твердой только НИЖНЮЮ ТРЕТЬ объекта
                # Теперь игрок может зайти "за спинку" дивана
                wall_rect = pygame.Rect(x, y + h - (h // 3), w, h // 3)
                self.walls.append(wall_rect)

    def refresh_physics(self):
        pass

    def draw(self, screen, camera):
        # ОПТИМИЗАЦИЯ (Culling): Вычисляем, какие тайлы видит камера, чтобы не рисовать все 10000 штук
        start_col = max(0, int(-camera.camera.x // 96))
        # Используем 1536 (примерная ширина экрана), чтобы рисовать с запасом
        end_col = start_col + int(1536 // 96) + 2 
        
        start_row = max(0, int(-camera.camera.y // 64))
        end_row = start_row + int(768 // 64) + 2

        # 1. Рисуем только видимый кусок пола и стен
        map_data = self.level_data.get('map', [])
        for row_index in range(start_row, min(end_row, len(map_data))):
            row = map_data[row_index]
            for col_index in range(start_col, min(end_col, len(row))):
                tile_id = row[col_index]
                if tile_id in self.tile_images:
                    x = col_index * 96
                    y = row_index * 64
                    # СДВИГАЕМ ТАЙЛ КАМЕРОЙ
                    screen.blit(self.tile_images[tile_id], camera.apply_point((x, y)))

        # 2. Рисуем объекты (диваны, картины) со сдвигом камеры
        for obj in self.level_data.get('objects', []):
            if obj['sprite_id'] in self.sprite_images:
                screen.blit(self.sprite_images[obj['sprite_id']], camera.apply_point(obj['pos']))
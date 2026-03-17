import pygame
import json
import os
from settings import *
from utils import get_tile

class Level:
    def __init__(self, level_id=1):
        self.grid = {}
        self.walls = []
        self.loot = []
        self.hiding_spots = []
        self.guards_data = []
        
        # Точка входа (синий фургон)
        self.entrance_rect = pygame.Rect(0, 0, TILE_SIZE * 2, TILE_SIZE * 2)
        
        # Загрузка текстур
        self.tileset = None
        self.wall_img = None
        self.floor_img = None
        self.loot_img = None
        self.load_assets()
        
        # Загружаем конкретный уровень
        self.load_level_layout(level_id)

    def load_assets(self):
        """Загружает текстуры из твоего тайлсета 48x48."""
        path = os.path.join(TILES_DIR, TILESET_FILE)
        if os.path.exists(path):
            self.tileset = pygame.image.load(path).convert_alpha()
            # Берем разные тайлы из листа (координаты X, Y в сетке 48x48)
            self.wall_img = get_tile(self.tileset, 1, 1)   # Стена
            self.floor_img = get_tile(self.tileset, 0, 5)  # Пол (паркет)
            self.loot_img = get_tile(self.tileset, 4, 10)  # Объект (сейф/картина)
        else:
            # Заглушки, если файла нет
            self.wall_img = pygame.Surface((TILE_SIZE, TILE_SIZE)); self.wall_img.fill(WALL_COLOR)
            self.floor_img = pygame.Surface((TILE_SIZE, TILE_SIZE)); self.floor_img.fill(BUILDING_COLOR)
            self.loot_img = pygame.Surface((TILE_SIZE, TILE_SIZE)); self.loot_img.fill(LOOT_COLOR)

    def load_level_layout(self, level_id):
        self.grid = {}
        self.guards_data = []

        if level_id == 1:
            # --- УРОВЕНЬ 1: ПАРАДНЫЙ ХОЛЛ ---
            self.entrance_rect.topleft = (1800, 1800)
            # Внешние стены
            for x in range(20, 60):
                for y in range(15, 35):
                    if x == 20 or x == 59 or y == 15 or y == 34:
                        if not (x == 40 and y == 34): # Проход снизу
                            self.grid[(x, y)] = WALL
                    else:
                        self.grid[(x, y)] = FLOOR
            # Внутренние колонны
            for cx, cy in [(30, 20), (50, 20), (30, 30), (50, 30)]:
                self.grid[(cx, cy)] = WALL
            self.grid[(40, 20)] = LOOT
            self.guards_data = [
                {'type': 'normal', 'waypoints': [(1500, 900), (2400, 900)]},
                {'type': 'random', 'bounds': pygame.Rect(1200, 800, 1000, 500)}
            ]

        elif level_id == 2:
            # --- УРОВЕНЬ 2: КОРИДОРЫ ---
            self.entrance_rect.topleft = (200, 1800)
            for x in range(5, 70):
                for y in range(10, 40):
                    if x == 5 or x == 69 or y == 10 or y == 39:
                        if not (x == 10 and y == 39): self.grid[(x, y)] = WALL
                    else: self.grid[(x, y)] = FLOOR
            # Перегородки
            for y in range(10, 30): self.grid[(35, y)] = WALL
            for y in range(20, 40): self.grid[(50, y)] = WALL
            self.grid[(60, 15)] = LOOT
            self.grid[(10, 15)] = LOOT
            self.guards_data = [
                {'type': 'fast', 'waypoints': [(500, 700), (500, 1500)]},
                {'type': 'taser', 'waypoints': [(2000, 1500), (2800, 1500)]}
            ]

        elif level_id == 3:
            # --- УРОВЕНЬ 3: ХРАНИЛИЩЕ ---
            self.entrance_rect.topleft = (1800, 100)
            for x in range(30, 50):
                for y in range(5, 45):
                    self.grid[(x, y)] = FLOOR
                    if x == 30 or x == 49 or y == 5 or y == 44:
                        if not (x == 40 and y == 5): self.grid[(x, y)] = WALL
            # Центр
            self.grid[(40, 25)] = LOOT
            self.guards_data = [
                {'type': 'taser', 'waypoints': [(1600, 500), (2200, 500)]},
                {'type': 'fast', 'waypoints': [(1600, 1800), (2200, 1800)]},
                {'type': 'normal', 'waypoints': [(1900, 400), (1900, 2000)]}
            ]

        self.refresh_physics()

    def refresh_physics(self):
        self.walls = []; self.loot = []; self.hiding_spots = []
        for (tx, ty), t_type in self.grid.items():
            rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if t_type == WALL: self.walls.append(rect)
            elif t_type == LOOT: self.loot.append(rect)
            elif t_type == HIDING_SPOT: self.hiding_spots.append(rect)

    def draw(self, screen, camera):
        # 1. Отрисовка пола (сначала все клетки пола, чтобы не было дырок)
        for (tx, ty), t_type in self.grid.items():
            if t_type != WALL:
                rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                screen.blit(self.floor_img, camera.apply(rect))

        # 2. Отрисовка теней от стен
        for wall in self.walls:
            shadow = camera.apply(wall).move(SHADOW_OFFSET, SHADOW_OFFSET)
            pygame.draw.rect(screen, SHADOW_COLOR, shadow)

        # 3. Отрисовка стен и объектов
        for (tx, ty), t_type in self.grid.items():
            rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            draw_rect = camera.apply(rect)
            
            if t_type == WALL:
                screen.blit(self.wall_img, draw_rect)
            elif t_type == LOOT:
                screen.blit(self.loot_img, draw_rect)
            elif t_type == HIDING_SPOT:
                pygame.draw.rect(screen, HIDE_COLOR, draw_rect)

        # 4. Вход
        pygame.draw.rect(screen, EXIT_COLOR, camera.apply(self.entrance_rect), 4)
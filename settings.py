# --- settings.py ---
import pygame
import os

# --- ОКНО И ЛОГИЧЕСКИЙ РАЗМЕР ИГРЫ ---
# Логическое разрешение игры. Все координаты (игрок, UI, тайлы) 
# рассчитываются относительно этого размера.
LOGICAL_WIDTH, LOGICAL_HEIGHT = 1760, 960 

# Начальный размер окна при запуске (в оконном режиме)
WINDOW_WIDTH, WINDOW_HEIGHT = LOGICAL_WIDTH, LOGICAL_HEIGHT

# Разрешение для настоящего полного экрана
FULLSCREEN_RES = (1920, 1080)

TILE_SIZE = 48              # Размер клетки игрового мира
FPS = 60

# Размер игрового мира (80x50 клеток)
MAP_WIDTH = 9600   # (100 тайлов * 96 пикселей)
MAP_HEIGHT = 6400  # (100 тайлов * 64 пикселей)

# --- ПУТИ К АССЕТАМ ---
BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SPRITES_DIR = os.path.join(ASSETS_DIR, "sprites")
TILES_DIR = os.path.join(ASSETS_DIR, "tiles")
LEVELS_DIR = os.path.join(ASSETS_DIR, "levels")

# Создаем папку уровней, если её нет
if not os.path.exists(LEVELS_DIR):
    os.makedirs(LEVELS_DIR)

# --- ТЕКСТУРЫ ---
TILESET_FILE = "Interiors_free_48x48.png"
PLAYER_SHEET = "Adam_idle_16x16.png" 

# --- ЦВЕТА ---
BG_COLOR = (10, 10, 12)          # Цвет улицы
BUILDING_COLOR = (30, 25, 25)    # Цвет пола здания
UI_COLOR = (240, 240, 240)
SHADOW_COLOR = (0, 0, 0, 150)
VISION_COLOR = (255, 255, 100, 40) # Свет фонарика
NOISE_COLOR = (255, 255, 255, 80)
BULLET_COLOR = (255, 255, 0)
WALL_COLOR = (80, 80, 85)
LOOT_COLOR = (50, 255, 50)
EXIT_COLOR = (50, 50, 255)
HIDE_COLOR = (20, 60, 20)
CAM_COLOR = (150, 150, 150)
LASER_COLOR = (255, 0, 0)

SHADOW_OFFSET = 8                # Смещение теней для 2.5D эффекта

# --- ИДЕНТИФИКАТОРЫ ОБЪЕКТОВ ---
EMPTY = 0
WALL = 1
FLOOR = 2
LOOT = 3
GUARD = 4
HIDING_SPOT = 5
CAMERA = 6
ENTRANCE = 7

# --- ПАРАМЕТРЫ ПЕРСОНАЖЕЙ ---
STAMINA_MAX = 100.0
STAMINA_REGEN = 0.4
STAMINA_DRAIN = 0.9

SPEED_SNEAK = 2.2
SPEED_WALK = 4.8
SPEED_RUN = 8.5

# --- ТИПЫ ОХРАННИКОВ ---
GUARD_NORMAL = (255, 50, 50)
GUARD_FAST = (255, 165, 0)
GUARD_TASER = (0, 255, 255)
GUARD_RANDOM = (180, 50, 255)
GUARD_SWAT = (30, 30, 30)

# --- ИНТЕРФЕЙС МЕНЮ ---
BUTTON_COLOR = (40, 40, 60)
BUTTON_HOVER = (60, 60, 90)
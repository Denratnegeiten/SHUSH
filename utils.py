import pygame
import math
import os
from settings import *

class Camera:
    """Система слежения за игроком для Full HD."""
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, rect):
        """Сдвигает Rect объекта относительно камеры."""
        return rect.move(self.camera.topleft)

    def apply_point(self, point):
        """Сдвигает точку координат относительно камеры."""
        return (point[0] + self.camera.x, point[1] + self.camera.y)

    def update(self, target_rect):
        """Центрирует камеру на игроке с ограничением по краям карты."""
        x = -target_rect.centerx + int(WIDTH / 2)
        y = -target_rect.centery + int(HEIGHT / 2)

        # Не даем камере показывать пустоту за границами карты
        x = min(0, max(-(self.width - WIDTH), x))
        y = min(0, max(-(self.height - HEIGHT), y))
        
        self.camera = pygame.Rect(x, y, self.width, self.height)

def load_image(path, size=None):
    """Безопасная загрузка изображения. Если файла нет — вернет розовый квадрат."""
    if not os.path.exists(path):
        fallback = pygame.Surface((TILE_SIZE, TILE_SIZE))
        fallback.fill((255, 0, 255))
        return fallback
    
    img = pygame.image.load(path).convert_alpha()
    if size:
        return pygame.transform.scale(img, (size[0], size[1]))
    return img

def get_tile(sheet, x, y, tw=48, th=48):
    """
    Вырезает тайл 48x48 из листа. 
    Используем blit на чистую поверхность, чтобы избежать швов и артефактов.
    """
    rect = pygame.Rect(x * tw, y * th, tw, th)
    surf = pygame.Surface((tw, th), pygame.SRCALPHA)
    surf.blit(sheet, (0, 0), rect)
    # Масштабируем до игрового TILE_SIZE (48)
    return pygame.transform.scale(surf, (TILE_SIZE, TILE_SIZE))

def get_animation_frames(sheet, row, count, fw=16, fh=32):
    """
    Нарезает персонажа (16x32) и увеличивает его.
    Чтобы персонаж не был 'мелким', мы масштабируем его 
    с сохранением пропорций (в 3 раза: 48x96).
    """
    frames = []
    for i in range(count):
        rect = pygame.Rect(i * fw, row * fh, fw, fh)
        frame = pygame.Surface((fw, fh), pygame.SRCALPHA)
        frame.blit(sheet, (0, 0), rect)
        
        # Умножаем на 3, чтобы соответствовать TILE_SIZE=48
        # Ширина: 16*3=48, Высота: 32*3=96
        scaled_frame = pygame.transform.scale(frame, (TILE_SIZE, TILE_SIZE * 2))
        frames.append(scaled_frame)
    return frames

def has_line_of_sight(p1, p2, walls):
    """Проверка на наличие препятствий между точками."""
    for wall in walls:
        if wall.clipline(p1, p2):
            return False
    return True

def check_vision(player_rect, is_hidden, source_rect, angle, dist, fov, walls):
    """Логика зрения охранников и камер."""
    if is_hidden: return False
    
    px, py = player_rect.center
    sx, sy = source_rect.center
    
    # Расстояние
    d = math.hypot(px - sx, py - sy)
    if d > dist: return False
    
    # Угол
    angle_to_p = math.atan2(py - sy, px - sx)
    diff = abs(angle_to_p - angle)
    if diff > math.pi: diff = 2 * math.pi - diff
    if diff > fov / 2: return False
    
    # Стены
    return has_line_of_sight(source_rect.center, player_rect.center, walls)
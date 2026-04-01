import pygame
import os
import math
from src.settings import LOGICAL_WIDTH, LOGICAL_HEIGHT, TILE_SIZE

class Camera:
    def __init__(self, world_width, world_height):
        self.camera = pygame.Rect(0, 0, world_width, world_height)
        self.world_width = world_width
        self.world_height = world_height

    def apply(self, entity_rect):
        return entity_rect.move(self.camera.topleft)

    def apply_point(self, point):
        return (point[0] + self.camera.x, point[1] + self.camera.y)

    def update(self, target_rect):
        x = -target_rect.centerx + int(LOGICAL_WIDTH / 2)
        y = -target_rect.centery + int(LOGICAL_HEIGHT / 2)

        x = min(0, x)
        y = min(0, y)
        x = max(-(self.world_width - LOGICAL_WIDTH), x)
        y = max(-(self.world_height - LOGICAL_HEIGHT), y)

        self.camera = pygame.Rect(x, y, self.world_width, self.world_height)


def load_image(path, size=None):
    if not os.path.exists(path):
        fallback = pygame.Surface((TILE_SIZE, TILE_SIZE))
        fallback.fill((255, 0, 255))
        return fallback
    
    img = pygame.image.load(path).convert_alpha()
    if size:
        return pygame.transform.scale(img, (size[0], size[1]))
    return img

def get_tile(sheet, x, y, tw=16, th=16):
    rect = pygame.Rect(x * tw, y * th, tw, th)
    surf = pygame.Surface((tw, th), pygame.SRCALPHA)
    surf.blit(sheet, (0, 0), rect)
    return pygame.transform.scale(surf, (TILE_SIZE, TILE_SIZE))

def load_simple_poses(sheet, fw=16, fh=24):
    poses = {}
    mapping = {
        "right": 0,
        "up":    1,
        "left":  2,
        "down":  3
    }
    
    scale_factor = TILE_SIZE // 16
    target_w = fw * scale_factor
    target_h = fh * scale_factor
    
    for name, idx in mapping.items():
        rect = pygame.Rect(idx * fw, 0, fw, fh)
        
        snip_surf = pygame.Surface((fw, fh), pygame.SRCALPHA).convert_alpha()
        snip_surf.blit(sheet, (0, 0), rect)
        
        scaled_frame = pygame.transform.scale(snip_surf, (target_w, target_h))
        
        final_surf = pygame.Surface((target_w, target_h), pygame.SRCALPHA).convert_alpha()
        final_surf.blit(scaled_frame, (0, 0))
        
        poses[name] = final_surf
        
    return poses

def has_line_of_sight(p1, p2, walls):
    x1, y1 = p1
    x2, y2 = p2
    line_rect = pygame.Rect(min(x1, x2), min(y1, y2), abs(x1 - x2) or 1, abs(y1 - y2) or 1)
    
    for wall in walls:
        if line_rect.colliderect(wall):
            if wall.clipline(p1, p2):
                return False
                
    return True

def check_vision(player_rect, is_hidden, source_rect, angle, dist, fov, walls):
    if is_hidden: return False
    
    px, py = player_rect.center
    sx, sy = source_rect.center
    
    d = math.hypot(px - sx, py - sy)
    if d > dist: return False
    
    angle_to_p = math.atan2(py - sy, px - sx)
    diff = abs(angle_to_p - angle)
    if diff > math.pi: diff = 2 * math.pi - diff
    if diff > fov / 2: return False
    
    return has_line_of_sight(source_rect.center, player_rect.center, walls)
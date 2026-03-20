import pygame
import math
import random
import os
from settings import *
from utils import load_image, check_vision, has_line_of_sight

class TaserBullet:
    def __init__(self, x, y, tx, ty):
        self.rect = pygame.Rect(x, y, 12, 12)
        angle = math.atan2(ty - y, tx - x)
        self.dx, self.dy = math.cos(angle) * 14, math.sin(angle) * 14

    def update(self):
        self.rect.x += int(self.dx)
        self.rect.y += int(self.dy)

    def draw(self, screen, camera):
        pygame.draw.circle(screen, BULLET_COLOR, camera.apply_point(self.rect.center), 6)

class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, TILE_SIZE - 12, TILE_SIZE - 12)
        self.x, self.y = float(self.rect.x), float(self.rect.y)
        
        # Загружаем файлы НАПРЯМУЮ, минуя utils.py
        # Если файла нет, игра моментально вылетит с ошибкой FileNotFoundError
        def load_and_scale(filename):
            path = os.path.join(SPRITES_DIR, filename)
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(img, (img.get_width() * 3, img.get_height() * 3))

        self.poses = {
            "right": load_and_scale("player_right.png"),
            "up":    load_and_scale("player_up.png"),
            "left":  load_and_scale("player_left.png"),
            "down":  load_and_scale("player_down.png")
        }
        
        self.cur_pose = "down" 
        self.stamina = STAMINA_MAX
        self.exhausted = False
        self.slow_timer = 0
        self.score = 0
        self.is_hidden = False
        self.active_noises = []
        self.step_dist = 0

    def update(self, keys, walls, hiding_spots):
        up = keys[pygame.K_w] or keys[pygame.K_UP]
        down = keys[pygame.K_s] or keys[pygame.K_DOWN]
        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        moving = any([up, down, left, right])
        
        speed, noise_r = 0, 0
        if moving:
            if keys[pygame.K_LCTRL]: 
                speed = SPEED_SNEAK
                self.stamina = min(STAMINA_MAX, self.stamina + STAMINA_REGEN)
            elif keys[pygame.K_LSHIFT] and not self.exhausted:
                speed, noise_r = SPEED_RUN, 260
                self.stamina -= STAMINA_DRAIN
                if self.stamina <= 0: self.exhausted = True
            else:
                speed, noise_r = SPEED_WALK, 140
                self.stamina = min(STAMINA_MAX, self.stamina + STAMINA_REGEN)
        else:
            self.stamina = min(STAMINA_MAX, self.stamina + STAMINA_REGEN)

        if self.stamina > 25: self.exhausted = False
        if self.slow_timer > 0: speed *= 0.4; self.slow_timer -= 1

        dx, dy = 0, 0
        if up: dy -= speed; self.cur_pose = "up"
        if down: dy += speed; self.cur_pose = "down"
        if left: dx -= speed; self.cur_pose = "left"
        if right: dx += speed; self.cur_pose = "right"
        if dx != 0 and dy != 0: dx *= 0.707; dy *= 0.707

        self.x += dx
        self.rect.x = int(self.x)
        for w in walls:
            if self.rect.colliderect(w):
                if dx > 0: self.rect.right = w.left
                else: self.rect.left = w.right
                self.x = float(self.rect.x)

        self.y += dy
        self.rect.y = int(self.y)
        for w in walls:
            if self.rect.colliderect(w):
                if dy > 0: self.rect.bottom = w.top
                else: self.rect.top = w.bottom
                self.y = float(self.rect.y)

        if moving:
            self.step_dist += speed
            if self.step_dist >= 80 and noise_r > 0 and not self.is_hidden:
                self.step_dist = 0
                self.active_noises.append({'pos': self.rect.center, 'r': 10, 'max': noise_r, 'a': 200})

        self.is_hidden = any(s.collidepoint(self.rect.center) for s in hiding_spots)

    def draw(self, screen, t_surf, camera):
        # Если не спрятался - рисуем обычную тень
        if not self.is_hidden:
            pygame.draw.ellipse(screen, (30, 30, 30), camera.apply(self.rect).move(0, 20))
        
        # КОПИРУЕМ кадр, чтобы не испортить оригинал
        img = self.poses[self.cur_pose].copy() 
        
        # ЭФФЕКТ МАСКИРОВКИ: Если спрятался, делаем полупрозрачным
        if self.is_hidden:
            img.set_alpha(100) 
            
        pos = camera.apply(self.rect)
        offset_x = (self.rect.width - img.get_width()) // 2
        offset_y = self.rect.height - img.get_height()
        
        screen.blit(img, (pos.x + offset_x, pos.y + offset_y))
        
        for n in self.active_noises[:]:
            pygame.draw.circle(t_surf, (255,255,255, n['a']), camera.apply_point(n['pos']), int(n['r']), 2)
            n['r'] += 7; n['a'] -= 8
            if n['a'] <= 0: self.active_noises.remove(n)

class Guard:
    def __init__(self, g_type, x, y, waypoints=None, bounds=None):
        self.rect = pygame.Rect(x, y, TILE_SIZE - 8, TILE_SIZE - 8)
        self.type = g_type
        self.angle = 0
        self.bullets = []
        self.timer = 0
        self.wp = waypoints; self.idx = 0; self.bounds = bounds
        self.target = self.wp[0] if self.wp else (x, y)
        
        stats = {
            'normal': (2.2, 4.5, GUARD_NORMAL),
            'fast':   (3.8, 7.0, GUARD_FAST),
            'taser':  (1.8, 3.5, GUARD_TASER),
            'random': (2.0, 4.5, GUARD_RANDOM),
            'swat':   (5.0, 5.0, GUARD_SWAT)
        }
        self.spd, self.chase_spd, self.color = stats.get(g_type, stats['normal'])

    def update(self, obstacles):
        if self.type == 'swat': return
        dx, dy = self.target[0] - self.rect.centerx, self.target[1] - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist < 5:
            if self.type == 'random' and self.bounds:
                self.target = (random.randint(self.bounds.left, self.bounds.right), 
                               random.randint(self.bounds.top, self.bounds.bottom))
            elif self.wp:
                self.idx = (self.idx + 1) % len(self.wp)
                self.target = self.wp[self.idx]
        else:
            self.rect.x += int((dx/dist)*self.spd)
            self.rect.y += int((dy/dist)*self.spd)
            self.angle = math.atan2(dy, dx)

    def chase(self, p_rect, obstacles):
        dx, dy = p_rect.centerx - self.rect.centerx, p_rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0:
            vx, vy = (dx/dist)*self.chase_spd, (dy/dist)*self.chase_spd
            self.angle = math.atan2(dy, dx)
            self.rect.x += int(vx)
            for o in obstacles:
                if self.rect.colliderect(o):
                    if vx > 0: self.rect.right = o.left
                    else: self.rect.left = o.right
            self.rect.y += int(vy)
            for o in obstacles:
                if self.rect.colliderect(o):
                    if vy > 0: self.rect.bottom = o.top
                    else: self.rect.top = o.bottom
        
        if self.type == 'taser':
            self.timer -= 1
            if self.timer <= 0 and dist < 450:
                self.bullets.append(TaserBullet(self.rect.centerx, self.rect.centery, p_rect.centerx, p_rect.centery))
                self.timer = 100

    def draw_vision(self, surf, walls, camera):
        if self.type == 'swat': return
        gx, gy = self.rect.center
        pts = [(gx, gy)]
        start, fov, dist = self.angle - 0.6, 1.2, 400
        for i in range(20):
            ang = start + (i/19)*fov
            ex, ey = gx + dist*math.cos(ang), gy + dist*math.sin(ang)
            for w in walls:
                cl = w.clipline((gx, gy), (ex, ey))
                if cl:
                    d = math.hypot(cl[0][0]-gx, cl[0][1]-gy)
                    if d < dist: ex, ey = cl[0]
            pts.append((ex, ey))
        pygame.draw.polygon(surf, VISION_COLOR, [camera.apply_point(p) for p in pts])

    def draw(self, screen, camera):
        pygame.draw.rect(screen, self.color, camera.apply(self.rect))
        pygame.draw.rect(screen, (255,255,255), camera.apply(self.rect), 2)
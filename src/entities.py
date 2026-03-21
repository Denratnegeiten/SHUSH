import pygame
import math
import random
import os
from src.settings import *
from src.utils import load_image, check_vision, has_line_of_sight

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
        
        self.total_money_value = 0
        
        def load_and_scale(filename):
            path = os.path.join(CHARS_DIR, filename)
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
        if not self.is_hidden:
            pygame.draw.ellipse(screen, (30, 30, 30), camera.apply(self.rect).move(0, 20))
        
        img = self.poses[self.cur_pose].copy() 
        
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

class Bullet:
    def __init__(self, x, y, angle):
        self.rect = pygame.Rect(x, y, 8, 8)
        self.x, self.y = float(x), float(y)
        self.angle = angle
        self.speed = 12

    def update(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.rect.x, self.rect.y = int(self.x), int(self.y)

    def draw(self, screen, camera):
        pygame.draw.circle(screen, (0, 255, 255), camera.apply_point(self.rect.center), 5)

class Guard:
    def __init__(self, g_type, x, y, waypoints=None, bounds=None):
        self.type = g_type
        self.rect = pygame.Rect(x, y, 40, 40)
        self.x, self.y = float(x), float(y)
        
        self.speed = 2.0
        self.vision_range = 450
        self.vision_fov = 1.2
        
        if self.type == 'fast': self.speed, self.vision_range = 3.5, 350
        elif self.type == 'taser': self.speed = 1.6
        elif self.type == 'random': self.speed = 2.5
        elif self.type == 'swat': self.speed, self.vision_range = 3.2, 550

        self.poses = {}
        prefix = "omon" if self.type == "swat" else "cop"
        for d in ["up", "down", "left", "right"]:
            try:
                img = pygame.image.load(os.path.join(CHARS_DIR, f"{prefix}_{d}.png")).convert_alpha()
                self.poses[d] = pygame.transform.scale(img, (img.get_width() * 3, img.get_height() * 3))
            except FileNotFoundError:
                surf = pygame.Surface((40, 40))
                surf.fill((255,0,0) if self.type=='taser' else (100,100,255))
                self.poses[d] = surf

        self.cur_pose = "down"
        self.angle = random.uniform(0, math.pi * 2)
        self.bullets = []
        self.shoot_cooldown = 0
        self.wait_timer = 0
        self.target_pos = self.get_new_target()

    def get_new_target(self):
        ang = random.uniform(0, math.pi * 2)
        dist = random.uniform(150, 400)
        return (self.x + math.cos(ang) * dist, self.y + math.sin(ang) * dist)

    def update(self, obstacles):
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        dx = self.target_pos[0] - self.x
        dy = self.target_pos[1] - self.y
        dist = math.hypot(dx, dy)
        
        if dist < 10:
            self.wait_timer -= 1
            if self.wait_timer <= 0:
                self.target_pos = self.get_new_target()
                self.wait_timer = random.randint(30, 120)
        else:
            self.angle = math.atan2(dy, dx)
            self.move(math.cos(self.angle) * self.speed, math.sin(self.angle) * self.speed, obstacles)

    def chase(self, player_rect, obstacles):
        dx = player_rect.centerx - self.x
        dy = player_rect.centery - self.y
        self.angle = math.atan2(dy, dx)
        
        if self.type == 'taser' and math.hypot(dx, dy) < 350 and self.shoot_cooldown <= 0:
            self.bullets.append(Bullet(self.rect.centerx, self.rect.centery, self.angle))
            self.shoot_cooldown = 60
        
        self.move(math.cos(self.angle) * self.speed, math.sin(self.angle) * self.speed, obstacles)

    def move(self, dx, dy, walls):
        self.x += dx
        self.rect.x = int(self.x)
        hit_wall = False
        
        for w in walls:
            if self.rect.colliderect(w):
                if dx > 0: self.rect.right = w.left
                else: self.rect.left = w.right
                self.x = float(self.rect.x)
                hit_wall = True

        self.y += dy
        self.rect.y = int(self.y)
        for w in walls:
            if self.rect.colliderect(w):
                if dy > 0: self.rect.bottom = w.top
                else: self.rect.top = w.bottom
                self.y = float(self.rect.y)
                hit_wall = True
                
        if hit_wall:
            self.target_pos = self.get_new_target()

    def draw(self, screen, camera):
        deg = math.degrees(self.angle) % 360
        if 45 <= deg < 135: self.cur_pose = "down"
        elif 135 <= deg < 225: self.cur_pose = "left"
        elif 225 <= deg < 315: self.cur_pose = "up"
        else: self.cur_pose = "right"
        
        img = self.poses[self.cur_pose]
        pos = camera.apply(self.rect)
        
        offset_x = (self.rect.width - img.get_width()) // 2
        offset_y = self.rect.height - img.get_height()
        screen.blit(img, (pos.x + offset_x, pos.y + offset_y))

    def draw_vision(self, surf, walls, camera):
        points = [camera.apply_point(self.rect.center)]
        
        for i in range(-3, 4):
            ang = self.angle + (i * (self.vision_fov / 6))
            rx, ry = self.rect.center
            for step in range(0, int(self.vision_range), 25):
                nx = rx + math.cos(ang) * 25
                ny = ry + math.sin(ang) * 25
                
                if any(w.collidepoint(nx, ny) for w in walls):
                    break
                rx, ry = nx, ny
            points.append(camera.apply_point((rx, ry)))
            
        if len(points) > 2:
            pygame.draw.polygon(surf, (255, 255, 100, 60), points)
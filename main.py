import pygame
import sys
import math
import random

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 960, 540
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("STICKVERSE: NEON AI — Ultimate Momentum Edition")
CLOCK = pygame.time.Clock()
FPS = 60


BG_DARK = (6, 5, 14)
GRID_CYAN = (0, 230, 255)
P1_RED = (255, 45, 85)
AI_BLUE = (0, 170, 255)
ENERGY_GOLD = (255, 215, 0)
FLAME_ORANGE = (255, 100, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_PANEL = (12, 14, 25)
KO_RED = (255, 30, 60)
NEON_PINK = (255, 0, 150)
NEON_PURPLE = (160, 32, 240)
BUILDING_DARK = (14, 16, 28)
BUILDING_MID = (20, 24, 42)

FONT_SM = pygame.font.SysFont("Consolas", 14, bold=True)
FONT_MD = pygame.font.SysFont("Trebuchet MS", 18, bold=True)
FONT_LG = pygame.font.SysFont("Trebuchet MS", 22, bold=True)
FONT_TITLE = pygame.font.SysFont("Impact", 65, italic=True)
##FONT_KO = pygame.font.SysFont("Impact", 95, bold=True)
#FONT_KO = pygame.font.SysFont("Comic Sans MS", 100, bold=True)
FONT_KO = pygame.font.SysFont("Cambria", 100, bold=True)


class Particle:
    def __init__(self, x, y, vx, vy, color, radius, life, gravity=0.15, glow=False):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.radius = radius
        self.life = life
        self.max_life = life
        self.gravity = gravity
        self.glow = glow

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= 1
        self.radius = max(0, self.radius * 0.92)

    def draw(self, surface):
        if self.life > 0 and self.radius > 0:
            alpha = int(255 * (self.life / self.max_life))
            if self.glow and self.radius > 2:
                glow_surf = pygame.Surface((int(self.radius * 4), int(self.radius * 4)), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*self.color[:3], int(alpha * 0.25)), (int(self.radius * 2), int(self.radius * 2)), int(self.radius * 2))
                surface.blit(glow_surf, (self.x - self.radius * 2, self.y - self.radius * 2))
                
            s = pygame.Surface((int(self.radius * 2), int(self.radius * 2)), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color[:3], alpha), (int(self.radius), int(self.radius)), int(self.radius))
            surface.blit(s, (self.x - self.radius, self.y - self.radius))


class Projectile:
    def __init__(self, x, y, direction, owner_is_ai):
        self.x = x
        self.y = y
        self.vx = 14 * direction
        self.radius = 20
        self.owner_is_ai = owner_is_ai
        self.active = True
        self.particles = []
        self.angle = 0

    def update(self):
        self.x += self.vx
        self.angle += 20
        if self.x < -60 or self.x > WIDTH + 60:
            self.active = False

        color = AI_BLUE if self.owner_is_ai else ENERGY_GOLD
        for _ in range(3):
            self.particles.append(Particle(
                self.x + random.uniform(-12, 12), self.y + random.uniform(-12, 12),
                random.uniform(-2, 2) + (self.vx * -0.25), random.uniform(-3, 3), 
                color, random.uniform(6, 14), 18, gravity=0, glow=True
            ))

        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)

        color = AI_BLUE if self.owner_is_ai else ENERGY_GOLD
        glow_s = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(glow_s, (*color[:3], 100), (30, 30), 28)
        surface.blit(glow_s, (int(self.x) - 30, int(self.y) - 30))

        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius - 6)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.radius, 4)

        for r_angle in [self.angle, self.angle + 120, self.angle + 240]:
            rad = math.radians(r_angle)
            rx = int(self.x + math.cos(rad) * (self.radius + 8))
            ry = int(self.y + math.sin(rad) * (self.radius + 8))
            pygame.draw.circle(surface, WHITE, (rx, ry), 4)
            pygame.draw.circle(surface, color, (rx, ry), 6, 2)


def evaluate_state(state):
    score = (state['ai_hp'] - state['player_hp']) * 12
    dist = abs(state['ai_x'] - state['player_x'])
    if dist < 90: score += 35
    elif dist > 280 and state['ai_energy'] >= 30: score += 45
    else: score -= dist * 0.15
    return score

def simulate_action(state, action, is_ai):
    ns = state.copy()
    actor, target = ('ai', 'player') if is_ai else ('player', 'ai')
    dist = abs(ns['ai_x'] - ns['player_x'])

    if action == 'APPROACH':
        ns[f'{actor}_x'] += 28 if ns[f'{actor}_x'] < ns[f'{target}_x'] else -28
    elif action == 'RETREAT':
        ns[f'{actor}_x'] -= 28 if ns[f'{actor}_x'] < ns[f'{target}_x'] else -28
    elif action == 'PUNCH' and dist <= 85:
        ns[f'{target}_hp'] -= 2 if ns[f'{target}_blocking'] else 10
    elif action == 'KICK' and dist <= 120:
        ns[f'{target}_hp'] -= 3 if ns[f'{target}_blocking'] else 16
    elif action == 'SPECIAL' and ns[f'{actor}_energy'] >= 30:
        ns[f'{actor}_energy'] -= 30
        if not ns[f'{target}_blocking']: ns[f'{target}_hp'] -= 22
    elif action == 'BLOCK':
        ns[f'{actor}_blocking'] = True
    return ns

def minimax(state, depth, alpha, beta, is_maximizing):
    if depth == 0 or state['ai_hp'] <= 0 or state['player_hp'] <= 0:
        return evaluate_state(state), None

    actions = ['PUNCH', 'KICK', 'APPROACH', 'RETREAT', 'BLOCK']
    if state['ai_energy'] >= 30: actions.append('SPECIAL')

    best_action = None
    if is_maximizing:
        max_eval = -float('inf')
        for action in actions:
            eval_score, _ = minimax(simulate_action(state, action, True), depth - 1, alpha, beta, False)
            if eval_score > max_eval:
                max_eval, best_action = eval_score, action
            alpha = max(alpha, eval_score)
            if beta <= alpha: break
        return max_eval, best_action
    else:
        min_eval = float('inf')
        for action in actions:
            eval_score, _ = minimax(simulate_action(state, action, False), depth - 1, alpha, beta, True)
            if eval_score < min_eval:
                min_eval, best_action = eval_score, action
            beta = min(beta, eval_score)
            if beta <= alpha: break
        return min_eval, best_action


class AnimeFighter:
    def __init__(self, x, y, color, is_ai=False):
        self.x = x
        self.y = y
        self.base_y = y
        self.color = color
        self.is_ai = is_ai

        self.hp = 100
        self.display_hp = 100
        self.energy = 0
        
        self.vx = 0.0
        self.target_vx = 0.0
        self.vy = 0.0

        self.state = 'IDLE' 
        self.facing_right = True
        self.is_blocking = False
        self.is_grounded = True
        self.is_dead = False

        self.state_timer = 0
        self.attack_cooldown = 0
        self.particles = []
        self.scarf_history = [(x, y - 75) for _ in range(9)]
        self.trail_ghosts = [] 
        self.ko_rot = 0
        self.anim_offset = random.uniform(0, 100)

    def get_hitbox(self):
        if self.state in ['KO', 'HIT', 'WIN']: return None
        direction = 1 if self.facing_right else -1
        if self.state == 'PUNCH' and 4 <= self.state_timer <= 16:
            return pygame.Rect(self.x + (15 * direction) - (35 if direction < 0 else 0), self.y - 75, 80, 32)
        elif self.state == 'KICK' and 4 <= self.state_timer <= 18:
            return pygame.Rect(self.x + (20 * direction) - (45 if direction < 0 else 0), self.y - 60, 100, 38)
        return None

    def get_hurtbox(self):
        if self.state == 'KO': return pygame.Rect(0, 0, 0, 0)
        return pygame.Rect(self.x - 25, self.y - 95, 50, 95)

    def trigger_death(self, direction):
        self.state = 'KO'
        self.is_dead = True
        self.vx = direction * 10
        self.vy = -12
        self.is_grounded = False

    def take_damage(self, amount, direction):
        if self.is_dead or self.state == 'WIN': return

        if self.is_blocking:
            amount *= 0.2  
            for _ in range(12):
                self.particles.append(Particle(
                    self.x + (25 if direction < 0 else -25), self.y - 50,
                    random.uniform(-6, 6), random.uniform(-6, 6),
                    GRID_CYAN if self.is_ai else ENERGY_GOLD, random.uniform(4, 9), 18, gravity=0.1, glow=True
                ))
        else:
            self.state = 'HIT'
            self.state_timer = 18
            self.vx = direction * 7
            for _ in range(20):
                self.particles.append(Particle(
                    self.x, self.y - 50, random.uniform(-10, 10), random.uniform(-10, 10),
                    WHITE, random.uniform(4, 9), 22, gravity=0.3, glow=True
                ))

        self.hp = max(0, self.hp - amount)
        self.energy = min(100, self.energy + 15)
        if self.hp <= 0: self.trigger_death(direction)

    def update(self, opponent, projectiles):
        facing_dir = -1 if self.facing_right else 1
        
        self.vx += (self.target_vx - self.vx) * 0.25
        self.x += self.vx
        self.target_vx = 0

        scarf_shake = random.uniform(-2, 2) if self.state == 'WIN' else 0
        neck_pos = (self.x + (10 * facing_dir) + scarf_shake, self.y - 75 + scarf_shake)
        self.scarf_history.insert(0, neck_pos)
        if len(self.scarf_history) > 9:
            self.scarf_history.pop()

        if abs(self.vx) > 2.5 or self.state in ['PUNCH', 'KICK', 'SPECIAL', 'WIN']:
            if random.random() < 0.5:
                self.trail_ghosts.append({'x': self.x, 'y': self.y, 'alpha': 150, 'state': self.state, 'facing': self.facing_right})
        
        for g in self.trail_ghosts[:]:
            g['alpha'] -= 15
            if g['alpha'] <= 0:
                self.trail_ghosts.remove(g)

        if self.state == 'KO':
            if not self.is_grounded:
                self.vy += 0.9
                self.y += self.vy
                self.x += self.vx
                self.ko_rot = min(90, self.ko_rot + 7)
                if self.y >= self.base_y + 15:
                    self.y = self.base_y + 15
                    self.vy = -self.vy * 0.35
                    self.vx *= 0.5
                    if abs(self.vy) < 2:
                        self.is_grounded = True
                        self.vy, self.vx = 0, 0
        else:
            if not self.is_grounded:
                self.vy += 1.1
                self.y += self.vy
                if self.y >= self.base_y:
                    self.y, self.vy, self.is_grounded = self.base_y, 0, True

            self.x = max(50, min(WIDTH - 50, self.x))

            if self.state not in ['PUNCH', 'KICK', 'SPECIAL', 'WIN'] and opponent:
                self.facing_right = self.x < opponent.x

            if self.attack_cooldown > 0: self.attack_cooldown -= 1
            if self.state_timer > 0 and self.state not in ['WIN', 'KO']:
                self.state_timer -= 1
                if self.state_timer == 0: self.state = 'IDLE'

            self.energy = min(100, self.energy + 0.08)
            self.display_hp += (self.hp - self.display_hp) * 0.15

        if self.energy >= 60 and random.random() < 0.6:
            self.particles.append(Particle(
                self.x + random.uniform(-25, 25), self.y - random.uniform(0, 90),
                random.uniform(-1, 1), random.uniform(-4, -2),
                self.color, random.uniform(3, 7), 18, gravity=-0.12, glow=True
            ))

        for p in self.particles[:]:
            p.update()
            if p.life <= 0: self.particles.remove(p)

    def _get_skeleton_pose(self, x_pos, y_pos, facing_bool, state_str, timer_val):
        facing = 1 if facing_bool else -1
        t = (pygame.time.get_ticks() * 0.0035) + self.anim_offset

        breath_y = math.sin(t * 2.2) * 2.5 if state_str == 'IDLE' else 0
        hip_x, hip_y = x_pos, y_pos - 38 + breath_y
        shoulder_x, shoulder_y = x_pos, y_pos - 72 + (breath_y * 1.2)
        head_x, head_y = x_pos, y_pos - 94 + (breath_y * 1.4)

        l_knee, r_knee = (hip_x - 14 * facing, hip_y + 20), (hip_x + 12 * facing, hip_y + 20)
        l_foot, r_foot = (hip_x - 18 * facing, y_pos), (hip_x + 16 * facing, y_pos)
        l_elbow, r_elbow = (shoulder_x - 16 * facing, shoulder_y + 15), (shoulder_x + 16 * facing, shoulder_y + 15)
        l_hand, r_hand = (shoulder_x - 20 * facing, shoulder_y + 30), (shoulder_x + 20 * facing, shoulder_y + 30)

        if state_str == 'IDLE':
            r_elbow = (shoulder_x + 20 * facing, shoulder_y + 10)
            r_hand = (shoulder_x + 28 * facing, shoulder_y - 10 + math.sin(t*2)*2)
            l_elbow = (shoulder_x - 14 * facing, shoulder_y + 14)
            l_hand = (shoulder_x - 12 * facing, shoulder_y + 28)

        elif state_str == 'WALK':
            leg_s = math.sin(t * 4.5) * 22
            shoulder_y += abs(math.cos(t * 4.5)) * 3
            r_knee = (hip_x + (leg_s + 10) * facing, hip_y + 18 - abs(leg_s)*0.2)
            r_foot = (hip_x + (leg_s * 1.3) * facing, y_pos - abs(leg_s)*0.3)
            l_knee = (hip_x - (leg_s - 10) * facing, hip_y + 18 - abs(leg_s)*0.2)
            l_foot = (hip_x - (leg_s * 1.3) * facing, y_pos - abs(leg_s)*0.3)
            r_hand = (shoulder_x - (leg_s)*1.2 * facing, shoulder_y + 25)
            l_hand = (shoulder_x + (leg_s)*1.2 * facing, shoulder_y + 25)

        elif state_str == 'PUNCH':
            prog = (20 - timer_val) / 20.0
            reach = math.sin(prog * math.pi) * 65
            r_elbow = (shoulder_x + (30 + reach * 0.5) * facing, shoulder_y - 8)
            r_hand = (shoulder_x + (40 + reach) * facing, shoulder_y - 10)
            head_x += reach * 0.25 * facing
            shoulder_x += reach * 0.35 * facing

        elif state_str == 'KICK':
            prog = (22 - timer_val) / 22.0
            reach = math.sin(prog * math.pi) * 78
            r_knee = (hip_x + (32 + reach * 0.5) * facing, hip_y - 16)
            r_foot = (hip_x + (28 + reach) * facing, hip_y - 22)
            head_x -= 12 * facing
            shoulder_x -= 8 * facing

        elif state_str == 'BLOCK':
            r_elbow = (shoulder_x + 16 * facing, shoulder_y - 14)
            r_hand = (shoulder_x + 24 * facing, shoulder_y - 32)
            l_elbow = (shoulder_x + 12 * facing, shoulder_y - 10)
            l_hand = (shoulder_x + 18 * facing, shoulder_y - 26)
            head_x -= 5 * facing

        elif state_str == 'WIN':
            dance_t = t * 4.5
            hip_x += math.sin(dance_t) * 12 * facing
            hip_y += abs(math.cos(dance_t)) * 10
            shoulder_x -= math.sin(dance_t) * 8 * facing
            shoulder_y += abs(math.cos(dance_t)) * 6
            head_x -= math.sin(dance_t) * 12 * facing
            
            l_elbow = (shoulder_x - 24 * facing, shoulder_y - 10 + math.sin(dance_t*1.5)*20)
            l_hand = (shoulder_x - 35 * facing, shoulder_y - 25 + math.sin(dance_t*2)*25)
            r_elbow = (shoulder_x + 24 * facing, shoulder_y - 10 - math.sin(dance_t*1.5)*20)
            r_hand = (shoulder_x + 35 * facing, shoulder_y - 25 - math.sin(dance_t*2)*25)
            
            l_knee = (hip_x - 18 * facing, hip_y + 14 - math.cos(dance_t)*10)
            l_foot = (hip_x - 20 * facing, y_pos - math.cos(dance_t)*15)
            r_knee = (hip_x + 18 * facing, hip_y + 14 + math.cos(dance_t)*10)
            r_foot = (hip_x + 20 * facing, y_pos + math.cos(dance_t)*15)

        elif state_str == 'KO':
            angle = math.radians(self.ko_rot * facing)
            head_x = x_pos - math.sin(angle) * 50 * facing
            head_y = y_pos - math.cos(angle) * 50
            shoulder_x = x_pos - math.sin(angle) * 30 * facing
            shoulder_y = y_pos - math.cos(angle) * 30
            hip_x, hip_y = x_pos, y_pos - 15
            l_foot, r_foot = (x_pos - 25 * facing, y_pos), (x_pos + 10 * facing, y_pos)

        return {
            'head': (head_x, head_y), 'shoulder': (shoulder_x, shoulder_y), 'hip': (hip_x, hip_y),
            'l_knee': l_knee, 'r_knee': r_knee, 'l_foot': l_foot, 'r_foot': r_foot,
            'l_elbow': l_elbow, 'r_elbow': r_elbow, 'l_hand': l_hand, 'r_hand': r_hand,
            'facing': facing
        }

    def draw(self, surface):
        for g in self.trail_ghosts:
            ghost_pose = self._get_skeleton_pose(g['x'], g['y'], g['facing'], g['state'], 10)
            g_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            col = (*self.color[:3], int(g['alpha'] * 0.4))
            pygame.draw.line(g_surf, col, ghost_pose['shoulder'], ghost_pose['hip'], 8)
            pygame.draw.line(g_surf, col, ghost_pose['shoulder'], ghost_pose['r_hand'], 6)
            pygame.draw.line(g_surf, col, ghost_pose['hip'], ghost_pose['r_foot'], 6)
            surface.blit(g_surf, (0, 0))

        for p in self.particles: p.draw(surface)

        pose = self._get_skeleton_pose(self.x, self.y, self.facing_right, self.state, self.state_timer)
        facing = pose['facing']

        for i in range(len(self.scarf_history) - 1):
            p1 = self.scarf_history[i]
            p2 = self.scarf_history[i + 1]
            w = max(1, 10 - i)
            pygame.draw.line(surface, self.color, p1, p2, w)
            pygame.draw.line(surface, WHITE, p1, p2, max(1, w - 4))

        gi_color = (25, 30, 45)

        def draw_armored_line(surf, c1, start, end, width, glow=True):
            pygame.draw.line(surf, gi_color, start, end, width + 6)
            pygame.draw.line(surf, c1, start, end, width)
            if glow:
                pygame.draw.line(surf, WHITE, start, end, max(1, width - 4))

        exhaust_x = pose['shoulder'][0] - 12 * facing
        exhaust_y = pose['shoulder'][1] + 10
        pygame.draw.circle(surface, self.color, (int(exhaust_x), int(exhaust_y)), 6)
        pygame.draw.circle(surface, WHITE, (int(exhaust_x), int(exhaust_y)), 3)

        draw_armored_line(surface, gi_color, pose['hip'], pose['l_knee'], 9, False)
        draw_armored_line(surface, gi_color, pose['l_knee'], pose['l_foot'], 8, False)
        draw_armored_line(surface, gi_color, pose['hip'], pose['r_knee'], 9, False)
        draw_armored_line(surface, gi_color, pose['r_knee'], pose['r_foot'], 8, False)
        
        draw_armored_line(surface, self.color, pose['shoulder'], pose['hip'], 14)
        core_x = (pose['shoulder'][0] + pose['hip'][0]) / 2
        core_y = (pose['shoulder'][1] + pose['hip'][1]) / 2
        pygame.draw.circle(surface, WHITE, (int(core_x), int(core_y)), 5)
        pygame.draw.circle(surface, self.color, (int(core_x), int(core_y)), 9, 2)
        pygame.draw.circle(surface, GRID_CYAN, (int(core_x), int(core_y)), 12, 1)

        draw_armored_line(surface, self.color, pose['shoulder'], pose['l_elbow'], 8)
        draw_armored_line(surface, self.color, pose['l_elbow'], pose['l_hand'], 7)
        draw_armored_line(surface, self.color, pose['shoulder'], pose['r_elbow'], 9)
        draw_armored_line(surface, self.color, pose['r_elbow'], pose['r_hand'], 8)

        hx, hy = int(pose['head'][0]), int(pose['head'][1])
        pygame.draw.circle(surface, gi_color, (hx, hy), 16)
        pygame.draw.circle(surface, WHITE, (hx, hy), 11)

        hair_pts = [(hx - 18 * facing, hy - 4), (hx - 26 * facing, hy - 24),
                    (hx - 12 * facing, hy - 22), (hx - 6 * facing, hy - 36),
                    (hx + 8 * facing, hy - 24), (hx + 22 * facing, hy - 28), (hx + 16 * facing, hy - 2)]
        pygame.draw.polygon(surface, self.color, hair_pts)
        pygame.draw.polygon(surface, WHITE, hair_pts, 2)

        if self.is_blocking or self.state == 'BLOCK':
            shield_surf = pygame.Surface((150, 180), pygame.SRCALPHA)
            t_shield = pygame.time.get_ticks() * 0.003
            cx, cy = 75, 90
            pulse = math.sin(t_shield * 3) * 6
            pygame.draw.ellipse(shield_surf, (*self.color[:3], int(60 + pulse*3)), (cx - 55 - pulse/2, cy - 70 - pulse/2, 110 + pulse, 140 + pulse))
            pygame.draw.ellipse(shield_surf, (*WHITE[:3], 150), (cx - 50, cy - 65, 100, 130), 2)
            sx = self.x + (15 if facing > 0 else -165)
            surface.blit(shield_surf, (sx, self.y - 135))


class BackgroundFX:
    def __init__(self):
        self.embers = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), random.uniform(0.6, 2.2)] for _ in range(60)]
        self.far_spires = []
        for i in range(10):
            x = i * 110 - 20
            w = random.randint(65, 95)
            h = random.randint(220, 360)
            self.far_spires.append({'rect': pygame.Rect(x, 420 - h, w, h), 'spire_h': random.randint(40, 90)})

        self.mid_monoliths = []
        for i in range(7):
            x = i * 160 + 15
            w = random.randint(80, 115)
            h = random.randint(140, 240)
            windows = []
            for wx in range(10, w - 15, 18):
                for wy in range(15, h - 20, 25):
                    if random.random() < 0.6:
                        windows.append((wx, wy))
            self.mid_monoliths.append({'rect': pygame.Rect(x, 420 - h, w, h), 'windows': windows})

    def draw(self, surface, t, speed_multiplier=1.0):
        surface.fill(BG_DARK)
        moon_x, moon_y = 760, 120
        for r in range(70, 0, -10):
            alpha = int(35 * (1 - r / 70))
            m_surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(m_surf, (*GRID_CYAN[:3], alpha), (r, r), r)
            surface.blit(m_surf, (moon_x - r, moon_y - r))
        pygame.draw.circle(surface, WHITE, (moon_x, moon_y), 18)

        for spire in self.far_spires:
            r = spire['rect']
            pygame.draw.rect(surface, BUILDING_DARK, r)
            pts = [(r.x, r.y), (r.x + r.width // 2, r.y - spire['spire_h']), (r.x + r.width, r.y)]
            pygame.draw.polygon(surface, BUILDING_DARK, pts)

        for mono in self.mid_monoliths:
            r = mono['rect']
            pygame.draw.rect(surface, BUILDING_MID, r)
            pygame.draw.rect(surface, NEON_PURPLE, r, 1)
            for wx, wy in mono['windows']:
                win_rect = pygame.Rect(r.x + wx, r.y + wy, 8, 12)
                pygame.draw.rect(surface, GRID_CYAN, win_rect)

        for ember in self.embers:
            ember[1] -= ember[2] * speed_multiplier
            ember[0] += math.sin(t * 2 + ember[1] * 0.01) * 1.5
            if ember[1] < -10:
                ember[1] = HEIGHT + 10
                ember[0] = random.randint(0, WIDTH)
            pygame.draw.circle(surface, GRID_CYAN, (int(ember[0]), int(ember[1])), int(ember[2] * 1.2))

        grid_y = 420
        pygame.draw.rect(surface, (10, 12, 22), (0, grid_y, WIDTH, HEIGHT - grid_y))
        pygame.draw.line(surface, GRID_CYAN, (0, grid_y), (WIDTH, grid_y), 4)

def main():
    bg_fx = BackgroundFX()
    state = "MENU"
    
    p1 = AnimeFighter(220, 420, P1_RED)
    ai = AnimeFighter(740, 420, AI_BLUE, is_ai=True)
    projectiles = []
    flame_particles = []
    
    m_p1 = AnimeFighter(280, 420, P1_RED)
    m_p2 = AnimeFighter(680, 420, AI_BLUE)
    m_p2.facing_right = False
    
    ai_timer = 0
    shake = 0
    impact_flash = 0
    

    btn_start = pygame.Rect(WIDTH//2 - 130, HEIGHT//2 - 10, 260, 46)
    btn_instr = pygame.Rect(WIDTH//2 - 130, HEIGHT//2 + 48, 260, 46)
    btn_exit = pygame.Rect(WIDTH//2 - 130, HEIGHT//2 + 106, 260, 46)
    btn_back = pygame.Rect(WIDTH//2 - 130, HEIGHT//2 + 150, 260, 46)

    running = True
    while running:
        t = pygame.time.get_ticks() * 0.001
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if state == "MENU":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_start.collidepoint(event.pos):
                        state = "GAME"
                        p1 = AnimeFighter(220, 420, P1_RED)
                        ai = AnimeFighter(740, 420, AI_BLUE, is_ai=True)
                        projectiles.clear()
                        flame_particles.clear()
                    elif btn_instr.collidepoint(event.pos):
                        state = "INSTRUCTIONS"
                    elif btn_exit.collidepoint(event.pos):
                        running = False
            elif state == "INSTRUCTIONS":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_back.collidepoint(event.pos):
                        state = "MENU"
            elif state == "GAME":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    if p1.is_dead or ai.is_dead:
                        state = "MENU"

        if state == "MENU":
            m_p1.energy = 100
            m_p2.energy = 100
            
            if random.random() < 0.02 and m_p1.state == 'IDLE':
                m_p1.state = random.choice(['PUNCH', 'KICK'])
                m_p1.state_timer = 20
            if random.random() < 0.02 and m_p2.state == 'IDLE':
                m_p2.state = random.choice(['PUNCH', 'KICK', 'BLOCK'])
                m_p2.state_timer = 20
                m_p2.is_blocking = (m_p2.state == 'BLOCK')

            m_p1.update(None, [])
            m_p2.update(None, [])
            
            bg_fx.draw(SCREEN, t, speed_multiplier=0.4)
            m_p1.draw(SCREEN)
            m_p2.draw(SCREEN)
            
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((4, 6, 14, 150))
            SCREEN.blit(overlay, (0, 0))
            
            title_text = "STICKVERSE: NEON AI"
            title_y = 80 + math.sin(t * 3) * 8
            
            title_cyan = FONT_TITLE.render(title_text, True, GRID_CYAN)
            title_pink = FONT_TITLE.render(title_text, True, NEON_PINK)
            title_white = FONT_TITLE.render(title_text, True, WHITE)
            tx = WIDTH//2 - title_white.get_width()//2
            
            SCREEN.blit(title_cyan, (tx - 3, title_y))
            SCREEN.blit(title_pink, (tx + 3, title_y + 2))
            SCREEN.blit(title_white, (tx, title_y))

            sub_txt = FONT_MD.render("— ULTIMATE MOMENTUM EDITION —", True, ENERGY_GOLD)
            SCREEN.blit(sub_txt, (WIDTH//2 - sub_txt.get_width()//2, title_y + 65))

            mx, my = pygame.mouse.get_pos()
            
         
            is_hover_start = btn_start.collidepoint(mx, my)
            pygame.draw.rect(SCREEN, NEON_PINK if is_hover_start else DARK_PANEL, btn_start, border_radius=10)
            pygame.draw.rect(SCREEN, GRID_CYAN if is_hover_start else WHITE, btn_start, 2, border_radius=10)
            start_txt = FONT_LG.render("START GAME", True, WHITE)
            SCREEN.blit(start_txt, (btn_start.centerx - start_txt.get_width()//2, btn_start.centery - start_txt.get_height()//2))

           
            is_hover_instr = btn_instr.collidepoint(mx, my)
            pygame.draw.rect(SCREEN, NEON_PURPLE if is_hover_instr else DARK_PANEL, btn_instr, border_radius=10)
            pygame.draw.rect(SCREEN, GRID_CYAN if is_hover_instr else WHITE, btn_instr, 2, border_radius=10)
            instr_txt = FONT_LG.render("HOW TO PLAY", True, WHITE)
            SCREEN.blit(instr_txt, (btn_instr.centerx - instr_txt.get_width()//2, btn_instr.centery - instr_txt.get_height()//2))

      
            is_hover_exit = btn_exit.collidepoint(mx, my)
            pygame.draw.rect(SCREEN, KO_RED if is_hover_exit else DARK_PANEL, btn_exit, border_radius=10)
            pygame.draw.rect(SCREEN, WHITE if is_hover_exit else (150, 150, 150), btn_exit, 2, border_radius=10)
            exit_txt = FONT_LG.render("EXIT GAME", True, WHITE)
            SCREEN.blit(exit_txt, (btn_exit.centerx - exit_txt.get_width()//2, btn_exit.centery - exit_txt.get_height()//2))

        elif state == "INSTRUCTIONS":
            bg_fx.draw(SCREEN, t, speed_multiplier=0.2)
            
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((6, 8, 20, 210))
            SCREEN.blit(overlay, (0, 0))

            
            panel_rect = pygame.Rect(WIDTH//2 - 380, HEIGHT//2 - 200, 760, 340)
            pygame.draw.rect(SCREEN, DARK_PANEL, panel_rect, border_radius=16)
            pygame.draw.rect(SCREEN, GRID_CYAN, panel_rect, 3, border_radius=16)

            title_instruct = FONT_LG.render("COMMAND CONTROLS & INSTRUCTIONS", True, ENERGY_GOLD)
            SCREEN.blit(title_instruct, (panel_rect.centerx - title_instruct.get_width()//2, panel_rect.y + 20))

            instructions_list = [
                "• A / D Keys : Move Left / Move Right smoothly across the arena",
                "• W Key      : Jump / Leap into the air",
                "• S Key      : Hold to Block incoming attacks and reduce damage",
                "• J Key      : Fast Light Punch attack",
                "• K Key      : Heavy Kick attack",
                "• L Key      : Fire Energy Special Projectile (Requires Energy Bar ≥ 30)",
                "• R Key      : Return to Main Menu after a K.O. match conclusion"
            ]

            start_y = panel_rect.y + 70
            for line in instructions_list:
                txt_surf = FONT_MD.render(line, True, WHITE)
                SCREEN.blit(txt_surf, (panel_rect.x + 35, start_y))
                start_y += 32

            
            mx, my = pygame.mouse.get_pos()
            is_hover_back = btn_back.collidepoint(mx, my)
            pygame.draw.rect(SCREEN, NEON_PINK if is_hover_back else DARK_PANEL, btn_back, border_radius=10)
            pygame.draw.rect(SCREEN, GRID_CYAN if is_hover_back else WHITE, btn_back, 2, border_radius=10)
            back_txt = FONT_LG.render("BACK TO MENU", True, WHITE)
            SCREEN.blit(back_txt, (btn_back.centerx - back_txt.get_width()//2, btn_back.centery - back_txt.get_height()//2))

        elif state == "GAME":
            if ai.state == 'KO' and p1.state != 'WIN':
                p1.state = 'WIN'
                p1.target_vx = 0
            elif p1.state == 'KO' and ai.state != 'WIN':
                ai.state = 'WIN'
                ai.target_vx = 0

            keys = pygame.key.get_pressed()
            if p1.state not in ['HIT', 'KO', 'PUNCH', 'KICK', 'SPECIAL', 'WIN'] and not p1.is_dead and not ai.is_dead:
                p1.is_blocking = False
                if keys[pygame.K_s]:
                    p1.is_blocking = True
                    p1.state = 'BLOCK'
                elif keys[pygame.K_a]:
                    p1.target_vx = -5.0
                    p1.state = 'WALK'
                elif keys[pygame.K_d]:
                    p1.target_vx = 5.0
                    p1.state = 'WALK'
                else:
                    p1.state = 'IDLE'

                if keys[pygame.K_w] and p1.is_grounded:
                    p1.vy = -17.5
                    p1.is_grounded = False

                if not p1.is_blocking and p1.attack_cooldown == 0:
                    if keys[pygame.K_j]: p1.state, p1.state_timer, p1.attack_cooldown = 'PUNCH', 20, 26
                    elif keys[pygame.K_k]: p1.state, p1.state_timer, p1.attack_cooldown = 'KICK', 22, 32
                    elif keys[pygame.K_l] and p1.energy >= 30:
                        p1.state, p1.state_timer, p1.attack_cooldown, p1.energy = 'SPECIAL', 25, 45, p1.energy - 30
                        facing = 1 if p1.facing_right else -1
                        projectiles.append(Projectile(p1.x + (40 * facing), p1.y - 65, facing, False))

            ai_timer += 1
            if ai_timer >= 12 and ai.state not in ['HIT', 'KO', 'PUNCH', 'KICK', 'SPECIAL', 'WIN'] and not ai.is_dead and not p1.is_dead:
                ai_timer = 0
                state_snap = {
                    'ai_x': ai.x, 'player_x': p1.x, 'ai_hp': ai.hp, 'player_hp': p1.hp,
                    'ai_energy': ai.energy, 'player_energy': p1.energy,
                    'ai_blocking': ai.is_blocking, 'player_blocking': p1.is_blocking
                }
                _, best_move = minimax(state_snap, depth=3, alpha=-float('inf'), beta=float('inf'), is_maximizing=True)

                ai.is_blocking = False
                if best_move == 'APPROACH': ai.target_vx, ai.state = (-4.2 if ai.x > p1.x else 4.2), 'WALK'
                elif best_move == 'RETREAT': ai.target_vx, ai.state = (4.2 if ai.x > p1.x else -4.2), 'WALK'
                elif best_move == 'BLOCK': ai.is_blocking, ai.state = True, 'BLOCK'
                elif best_move == 'PUNCH' and ai.attack_cooldown == 0: ai.state, ai.state_timer, ai.attack_cooldown = 'PUNCH', 20, 26
                elif best_move == 'KICK' and ai.attack_cooldown == 0: ai.state, ai.state_timer, ai.attack_cooldown = 'KICK', 22, 32
                elif best_move == 'SPECIAL' and ai.attack_cooldown == 0 and ai.energy >= 30:
                    ai.state, ai.state_timer, ai.attack_cooldown, ai.energy = 'SPECIAL', 25, 45, ai.energy - 30
                    facing = 1 if ai.facing_right else -1
                    projectiles.append(Projectile(ai.x + (40 * facing), ai.y - 65, facing, True))

            p1.update(ai, projectiles)
            ai.update(p1, projectiles)

            for proj in projectiles[:]:
                proj.update()
                target = p1 if proj.owner_is_ai else ai
                if proj.active and target.get_hurtbox().collidepoint(proj.x, proj.y) and target.state != 'WIN':
                    proj.active = False
                    target.take_damage(20, 1 if proj.vx > 0 else -1)
                    shake, impact_flash = 12, 2
                if not proj.active: projectiles.remove(proj)

            for attacker, defender in [(p1, ai), (ai, p1)]:
                hitbox = attacker.get_hitbox()
                if hitbox and hitbox.colliderect(defender.get_hurtbox()) and defender.state not in ['HIT', 'WIN']:
                    dmg = 10 if attacker.state == 'PUNCH' else 16
                    defender.take_damage(dmg, 1 if attacker.facing_right else -1)
                    attacker.energy = min(100, attacker.energy + 10)
                    shake, impact_flash = 10, 1

            sx = random.randint(-shake, shake) if shake > 0 else 0
            sy = random.randint(-shake, shake) if shake > 0 else 0
            if shake > 0: shake -= 1

            if impact_flash > 0:
                SCREEN.fill(WHITE)
                impact_flash -= 1
            else:
                bg_fx.draw(SCREEN, t, speed_multiplier=2.0)

                if sx != 0 or sy != 0:
                    shake_surf = SCREEN.copy()
                    SCREEN.fill(BG_DARK)
                    SCREEN.blit(shake_surf, (sx, sy))

                for proj in projectiles: proj.draw(SCREEN)
                p1.draw(SCREEN)
                ai.draw(SCREEN)

          
                pygame.draw.rect(SCREEN, (60, 15, 25), (40, 20, 320, 22), border_radius=4)
                pygame.draw.rect(SCREEN, ENERGY_GOLD, (40, 20, 3.2 * p1.display_hp, 22), border_radius=4)
                pygame.draw.rect(SCREEN, P1_RED, (40, 20, 3.2 * p1.hp, 22), border_radius=4)
                pygame.draw.rect(SCREEN, (30, 35, 50), (40, 46, 200, 8), border_radius=2)
                pygame.draw.rect(SCREEN, ENERGY_GOLD, (40, 46, 2 * p1.energy, 8), border_radius=2)

                pygame.draw.rect(SCREEN, (60, 15, 25), (WIDTH - 360, 20, 320, 22), border_radius=4)
                pygame.draw.rect(SCREEN, ENERGY_GOLD, (WIDTH - 360 + (3.2 * (100 - ai.display_hp)), 20, 3.2 * ai.display_hp, 22), border_radius=4)
                pygame.draw.rect(SCREEN, AI_BLUE, (WIDTH - 360 + (3.2 * (100 - ai.hp)), 20, 3.2 * ai.hp, 22), border_radius=4)
                pygame.draw.rect(SCREEN, (30, 35, 50), (WIDTH - 240, 46, 200, 8), border_radius=2)
                pygame.draw.rect(SCREEN, ENERGY_GOLD, (WIDTH - 240 + (200 - 2 * ai.energy), 46, 2 * ai.energy, 8), border_radius=2)

                SCREEN.blit(FONT_MD.render("PLAYER", True, WHITE), (40, 2))
                SCREEN.blit(FONT_MD.render("AI BOT", True, WHITE), (WIDTH - 90, 2))
                SCREEN.blit(FONT_SM.render("A/D: Move | W: Jump | S: Block | J: Punch | K: Kick | L: Special", True, GRID_CYAN), (40, 60))

                
                if p1.state == 'KO' or ai.state == 'KO':
                    dark_s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    dark_s.fill((0, 0, 0, 180))
                    SCREEN.blit(dark_s, (0, 0))

                    winner_str = "PLAYER WINS!" if ai.state == 'KO' else "AI WINS!"
                    winner_col = P1_RED if ai.state == 'KO' else AI_BLUE
                    
                    
                    for _ in range(15):
                        flame_particles.append(Particle(
                            random.randint(WIDTH//2 - 320, WIDTH//2 + 320), HEIGHT//2 + 10 + random.randint(-30, 30),
                            random.uniform(-2.5, 2.5), random.uniform(-8, -3),
                            random.choice([FLAME_ORANGE, ENERGY_GOLD, KO_RED, WHITE, winner_col]), 
                            random.uniform(12, 36), 45, gravity=-0.22, glow=True
                        ))
                    
                    for p in flame_particles[:]:
                        p.update()
                        p.draw(SCREEN)
                        if p.life <= 0: flame_particles.remove(p)

                    
                    ring_r = int(90 + (math.sin(t * 10) * 25))
                    pygame.draw.circle(SCREEN, FLAME_ORANGE, (WIDTH//2, HEIGHT//2 - 90), ring_r + 15, 4)
                    pygame.draw.circle(SCREEN, ENERGY_GOLD, (WIDTH//2, HEIGHT//2 - 90), ring_r, 2)

                    pulse_scale = 1.1 + math.sin(t * 10) * 0.15

                    
                    ko_txt = FONT_KO.render("K. O.", True, WHITE)
                    w, h = ko_txt.get_size()
                    scaled_ko = pygame.transform.smoothscale(ko_txt, (int(w * pulse_scale), int(h * pulse_scale)))
                    
                    ko_shadow_fire = FONT_KO.render("K. O.", True, FLAME_ORANGE)
                    ko_shadow_gold = FONT_KO.render("K. O.", True, ENERGY_GOLD)
                    scaled_fire = pygame.transform.smoothscale(ko_shadow_fire, (int(w * pulse_scale), int(h * pulse_scale)))
                    scaled_gold = pygame.transform.smoothscale(ko_shadow_gold, (int(w * pulse_scale), int(h * pulse_scale)))

                    ko_pos_x = WIDTH//2 - scaled_ko.get_width()//2
                    ko_pos_y = HEIGHT//2 - 130 - scaled_ko.get_height()//2

                    
                    SCREEN.blit(scaled_fire, (ko_pos_x - 6, ko_pos_y - 3))
                    SCREEN.blit(scaled_gold, (ko_pos_x + 6, ko_pos_y + 3))
                    SCREEN.blit(scaled_ko, (ko_pos_x, ko_pos_y))

                    
                    win_txt = FONT_TITLE.render(winner_str, True, winner_col)
                    ww, wh = win_txt.get_size()
                    pulse_win = 1.0 + abs(math.cos(t * 6)) * 0.1
                    scaled_win = pygame.transform.smoothscale(win_txt, (int(ww * pulse_win), int(wh * pulse_win)))
                    
                    win_glow = FONT_TITLE.render(winner_str, True, WHITE)
                    glow_w = pygame.transform.smoothscale(win_glow, (int(ww * pulse_win) + 6, int(wh * pulse_win) + 6))
                    SCREEN.blit(glow_w, (WIDTH//2 - glow_w.get_width()//2, HEIGHT//2 + 15 - glow_w.get_height()//2))
                    SCREEN.blit(scaled_win, (WIDTH//2 - scaled_win.get_width()//2, HEIGHT//2 + 15 - scaled_win.get_height()//2))

                    SCREEN.blit(FONT_LG.render("Press 'R' to return to Menu", True, GRID_CYAN), (WIDTH//2 - 130, HEIGHT//2 + 95))

        pygame.display.flip()
        CLOCK.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
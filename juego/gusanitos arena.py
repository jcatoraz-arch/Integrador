"""
Requisitos:
    pip install pygame

Ejecutar:
    python gusanitos_arena.py

Controles:
    Mouse                    -> mover
    Clic izquierdo / Espacio -> boost
    F                        -> pantalla completa
    Esc                      -> pausa
    Enter (en el menú)       -> comenzar a jugar
"""

import math
import random
import sys
from typing import List, Optional, Tuple

import pygame

# =============================================================================
# CONSTANTES
# =============================================================================
WORLD_RADIUS = 2600
WORLD_CENTER = (WORLD_RADIUS, WORLD_RADIUS)

SEG_RADIUS_BASE = 12
SEG_DIST_BASE = 6
INITIAL_LENGTH = 30
BASE_SPEED = 3.0
BOOST_SPEED = 5.5
BOOST_DRAIN_PER_SEC = 7.0  # segmentos por segundo
TURN_RATE = 0.18
BOT_TURN_RATE = 0.12
MIN_LEN_FOR_BOOST = 12

FOOD_COUNT = 700
FOOD_RADIUS = 5
BIG_FOOD_CHANCE = 0.08

BOT_COUNT = 18
BOT_MIN_LEN = 25
BOT_MAX_LEN = 130
BOT_SIGHT = 560
BOT_DANGER_RADIUS = 85  # menor = más valientes
BOT_EDGE_ENTER = 260    # cuando dc > R - ENTER -> modo escape
BOT_EDGE_EXIT = 460     # cuando dc < R - EXIT -> sale del modo escape

PALETTE_HEX = [
    '#e84b3c', '#facb46', '#52c57a', '#439cec',
    '#9b59b6', '#e67e22', '#3498db', '#1abc9c',
    '#ec7063', '#f1c40f', '#ff78b4', '#78dcff',
    '#b4ff78', '#ffb450', '#c878ff',
]

BOT_NAMES = [
    'Viborita', 'Slither', 'RoboGusi', 'Kiko', 'NoobMaster', 'BigWorm',
    'Veloz', 'Tiburon', 'Nachito', 'Locura', 'Zzz', 'Pro', 'Pelu', 'Dante',
    'Maxi', 'Pancho', 'Lucky', 'Dragon', 'Rey', 'Bicho', 'Capo', 'Shadow',
    'Neo', 'Furia', 'Tromba',
]

BG_COLOR = (10, 12, 18)
GRID_COLOR = (23, 26, 40)
BORDER_COLOR = (200, 56, 56)
YELLOW = (240, 200, 64)

INITIAL_WIDTH, INITIAL_HEIGHT = 1280, 720
FPS = 60


# =============================================================================
# UTILS
# =============================================================================
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def rand_range(a, b):
    return a + random.random() * (b - a)


def dist2(ax, ay, bx, by):
    dx = ax - bx
    dy = ay - by
    return dx * dx + dy * dy


def angle_diff(a, b):
    d = (a - b) % (math.pi * 2)
    if d > math.pi:
        d -= math.pi * 2
    if d < -math.pi:
        d += math.pi * 2
    return d


def dist_from_center(x, y):
    return math.hypot(x - WORLD_CENTER[0], y - WORLD_CENTER[1])


def random_point_in_world():
    r = WORLD_RADIUS * math.sqrt(random.random()) * 0.97
    a = random.random() * math.pi * 2
    return (WORLD_CENTER[0] + r * math.cos(a),
            WORLD_CENTER[1] + r * math.sin(a))


def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def mix(color, other, t):
    return (
        int(color[0] + (other[0] - color[0]) * t),
        int(color[1] + (other[1] - color[1]) * t),
        int(color[2] + (other[2] - color[2]) * t),
    )


def lighten(color, amt=0.3):
    return mix(color, (255, 255, 255), amt)


def darken(color, amt=0.3):
    return mix(color, (0, 0, 0), amt)


PALETTE = [hex_to_rgb(c) for c in PALETTE_HEX]


# =============================================================================
# CAMERA
# =============================================================================
class Camera:
    def __init__(self, x, y, w, h):
        self.wx = x
        self.wy = y
        self.w = w
        self.h = h
        self.zoom = 1.0
        self.target_zoom = 1.0

    def resize(self, w, h):
        self.w = w
        self.h = h

    def follow(self, x, y, dt):
        k = min(1.0, dt * 6)
        self.wx += (x - self.wx) * k
        self.wy += (y - self.wy) * k
        self.zoom += (self.target_zoom - self.zoom) * min(1.0, dt * 3)

    def set_zoom_for_snake(self, s):
        f = 1 - min(0.45, (s.length - INITIAL_LENGTH) / 900)
        self.target_zoom = max(0.55, f)

    def world_to_screen(self, x, y):
        return ((x - self.wx) * self.zoom + self.w / 2,
                (y - self.wy) * self.zoom + self.h / 2)

    def screen_to_world(self, sx, sy):
        return ((sx - self.w / 2) / self.zoom + self.wx,
                (sy - self.h / 2) / self.zoom + self.wy)


# =============================================================================
# SPATIAL GRID
# =============================================================================
class SpatialGrid:
    def __init__(self, cell_size=140):
        self.cs = cell_size
        self.cells = {}

    def _key(self, x, y):
        return (int(x // self.cs), int(y // self.cs))

    def rebuild(self, items):
        self.cells.clear()
        cs = self.cs
        cells = self.cells
        for it in items:
            k = (int(it.x // cs), int(it.y // cs))
            arr = cells.get(k)
            if arr is None:
                arr = []
                cells[k] = arr
            arr.append(it)

    def query(self, x, y, r):
        rc = int(r // self.cs) + 1
        cx = int(x // self.cs)
        cy = int(y // self.cs)
        out = []
        cells = self.cells
        for dx in range(-rc, rc + 1):
            for dy in range(-rc, rc + 1):
                arr = cells.get((cx + dx, cy + dy))
                if arr:
                    out.extend(arr)
        return out


# =============================================================================
# COMIDA
# =============================================================================
class Food:
    __slots__ = ('x', 'y', 'color', 'big', 'phase')

    def __init__(self, x, y, color, big=False):
        self.x = x
        self.y = y
        self.color = color
        self.big = big
        self.phase = random.random() * math.pi * 2

    @property
    def radius(self):
        return FOOD_RADIUS + (4 if self.big else 0)

    @property
    def gain(self):
        return 3 if self.big else 1

    def update(self, dt):
        self.phase += dt * 4

    def draw(self, surf, cam):
        sx, sy = cam.world_to_screen(self.x, self.y)
        if sx < -20 or sx > cam.w + 20 or sy < -20 or sy > cam.h + 20:
            return
        pulse = 0.85 + 0.15 * math.sin(self.phase)
        r = self.radius * pulse * cam.zoom
        pygame.draw.circle(surf, self.color, (int(sx), int(sy)), max(2, int(r + 2)))
        inner_r = max(1, int(r - 1))
        pygame.draw.circle(surf, lighten(self.color, 0.5), (int(sx), int(sy)), inner_r)


# =============================================================================
# SNAKE
# =============================================================================
class Snake:
    def __init__(self, x, y, length=INITIAL_LENGTH, color=None, name='???', is_bot=False):
        self.color = color if color is not None else random.choice(PALETTE)
        self.highlight = lighten(self.color, 0.35)
        self.outline = darken(self.color, 0.45)
        self.name = name
        self.is_bot = is_bot
        self.alive = True
        self.angle = random.random() * math.pi * 2
        self.target_angle = self.angle
        self.boost = False
        self.boost_accum = 0.0
        self.growth_pending = 0
        self.kills = 0
        self.time_alive = 0.0

        self.ai_target: Optional[Food] = None
        self.ai_retarget = 0.0
        self.edge_escape = False
        self.ai_wander_phase = random.random() * math.pi * 2

        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        self.segments: List[List[float]] = [
            [x - i * SEG_DIST_BASE * cos_a, y - i * SEG_DIST_BASE * sin_a]
            for i in range(length)
        ]

    @property
    def head(self):
        return self.segments[0]

    @property
    def length(self):
        return len(self.segments)

    @property
    def score(self):
        return len(self.segments)

    @property
    def seg_radius(self):
        extra = min(6, (self.length - INITIAL_LENGTH) / 80)
        return SEG_RADIUS_BASE + extra

    @property
    def seg_dist(self):
        extra = min(3, (self.length - INITIAL_LENGTH) / 120)
        return SEG_DIST_BASE + extra

    def can_boost(self):
        return self.length > MIN_LEN_FOR_BOOST

    def die(self, world):
        if not self.alive:
            return
        self.alive = False
        for i in range(0, len(self.segments), 2):
            s = self.segments[i]
            big = random.random() < 0.25
            world.foods.append(Food(
                s[0] + rand_range(-6, 6),
                s[1] + rand_range(-6, 6),
                self.highlight, big
            ))

    def grow(self, n):
        self.growth_pending += n

    def apply_turn(self, rate):
        d = angle_diff(self.target_angle, self.angle)
        if abs(d) <= rate:
            self.angle = self.target_angle
        else:
            self.angle += rate if d > 0 else -rate
        if self.angle > math.pi * 2:
            self.angle -= math.pi * 2
        if self.angle < 0:
            self.angle += math.pi * 2

    def update(self, dt, world):
        if not self.alive:
            return
        self.time_alive += dt

        self.apply_turn(BOT_TURN_RATE if self.is_bot else TURN_RATE)

        boosting = self.boost and self.can_boost()
        speed = BOOST_SPEED if boosting else BASE_SPEED
        sd = self.seg_dist

        hx, hy = self.segments[0]
        nhx = hx + math.cos(self.angle) * speed
        nhy = hy + math.sin(self.angle) * speed

        if dist_from_center(nhx, nhy) >= WORLD_RADIUS - 5:
            self.die(world)
            return

        # Rope follow
        segs = self.segments
        new_segs = [[nhx, nhy]]
        for i in range(1, len(segs)):
            px, py = new_segs[i - 1]
            cx, cy = segs[i]
            dx = cx - px
            dy = cy - py
            d = math.hypot(dx, dy) or 1.0
            new_segs.append([px + dx / d * sd, py + dy / d * sd])
        self.segments = new_segs

        while self.growth_pending > 0:
            t = self.segments[-1]
            self.segments.append([t[0], t[1]])
            self.growth_pending -= 1

        if boosting:
            self.boost_accum += BOOST_DRAIN_PER_SEC * dt
            while self.boost_accum >= 1 and self.length > MIN_LEN_FOR_BOOST:
                t = self.segments.pop()
                world.foods.append(Food(
                    t[0] + rand_range(-4, 4),
                    t[1] + rand_range(-4, 4),
                    self.highlight, False
                ))
                self.boost_accum -= 1

    def head_collides_with(self, other):
        hx, hy = self.segments[0]
        r = other.seg_radius + self.seg_radius - 2
        skip = 4 if other is self else 0
        r2 = r * r
        segs = other.segments
        for i in range(skip, len(segs)):
            sx, sy = segs[i]
            dx = hx - sx
            dy = hy - sy
            if dx * dx + dy * dy <= r2:
                return True
        return False

    def draw(self, surf, cam, font_small):
        if not self.alive:
            return
        sr = self.seg_radius * cam.zoom
        segs = self.segments
        half_w = cam.w / 2
        half_h = cam.h / 2
        zoom = cam.zoom
        wx = cam.wx
        wy = cam.wy

        visible: List[Optional[Tuple[float, float]]] = []
        for sx, sy in segs:
            px = (sx - wx) * zoom + half_w
            py = (sy - wy) * zoom + half_h
            if -40 < px < cam.w + 40 and -40 < py < cam.h + 40:
                visible.append((px, py))
            else:
                visible.append(None)

        r_out = int(sr + 2)
        r_main = int(sr)
        if r_out < 1:
            return

        # Contorno
        outline = self.outline
        for i in range(len(segs) - 1, -1, -1):
            v = visible[i]
            if v is None:
                continue
            pygame.draw.circle(surf, outline, (int(v[0]), int(v[1])), r_out)

        # Franjas
        color = self.color
        highlight = self.highlight
        for i in range(len(segs) - 1, -1, -1):
            v = visible[i]
            if v is None:
                continue
            c = color if (i // 6) % 2 == 0 else highlight
            pygame.draw.circle(surf, c, (int(v[0]), int(v[1])), max(1, r_main))

        head = visible[0]
        if head is not None:
            hx, hy = head
            pygame.draw.circle(surf, self.highlight, (int(hx), int(hy)), max(1, int(sr * 0.9)))
            pygame.draw.circle(surf, self.color, (int(hx), int(hy)), max(1, int(sr * 0.7)))
            self._draw_eyes(surf, hx, hy, sr)

            if (not self.is_bot) or self.length >= 40:
                label = font_small.render(self.name, True, (255, 255, 255))
                rect = label.get_rect(center=(int(hx), int(hy - sr - 10)))
                surf.blit(label, rect)

            if not self.is_bot:
                self._draw_direction_arrow(surf, hx, hy, sr)

    def _draw_direction_arrow(self, surf, hx, hy, sr):
        length = sr * 2.6
        tip_x = hx + math.cos(self.angle) * length
        tip_y = hy + math.sin(self.angle) * length
        base_x = hx + math.cos(self.angle) * sr * 1.2
        base_y = hy + math.sin(self.angle) * sr * 1.2

        line_w = max(2, int(sr * 0.18))
        pygame.draw.line(surf, (230, 230, 230),
                         (int(base_x), int(base_y)),
                         (int(tip_x), int(tip_y)), line_w)

        head_len = sr * 0.75
        wing = self.angle + math.pi - 0.45
        wing2 = self.angle + math.pi + 0.45
        p1 = (tip_x, tip_y)
        p2 = (tip_x + math.cos(wing) * head_len, tip_y + math.sin(wing) * head_len)
        p3 = (tip_x + math.cos(wing2) * head_len, tip_y + math.sin(wing2) * head_len)
        pygame.draw.polygon(surf, (245, 245, 245),
                            [(int(p1[0]), int(p1[1])),
                             (int(p2[0]), int(p2[1])),
                             (int(p3[0]), int(p3[1]))])

    def _draw_eyes(self, surf, hx, hy, sr):
        perp = self.angle + math.pi / 2
        off = sr * 0.55
        eye = max(2.5, sr * 0.38)
        pup = max(1, sr * 0.2)
        pdx = math.cos(self.angle) * pup * 0.8
        pdy = math.sin(self.angle) * pup * 0.8

        for sign in (1, -1):
            ex = hx + math.cos(perp) * off * sign
            ey = hy + math.sin(perp) * off * sign
            pygame.draw.circle(surf, (255, 255, 255), (int(ex), int(ey)), int(eye))
            pygame.draw.circle(surf, (21, 21, 32),
                               (int(ex + pdx), int(ey + pdy)), max(1, int(pup)))


# =============================================================================
# BOT AI
# =============================================================================
def update_bot_ai(bot: Snake, world: "World", dt: float):
    if not bot.alive:
        return
    hx, hy = bot.head
    dc = dist_from_center(hx, hy)

    # 1) Escape del borde con histéresis (evita quedar circulando)
    if dc > WORLD_RADIUS - BOT_EDGE_ENTER:
        bot.edge_escape = True
    elif dc < WORLD_RADIUS - BOT_EDGE_EXIT:
        bot.edge_escape = False

    if bot.edge_escape:
        center_angle = math.atan2(WORLD_CENTER[1] - hy, WORLD_CENTER[0] - hx)
        # Pequeño offset sinusoidal para que no se choquen todos en el centro
        bot.ai_wander_phase += dt * 0.8
        offset = 0.25 * math.sin(bot.ai_wander_phase)
        bot.target_angle = center_angle + offset
        # Boost si está muy cerca del borde, para salir rápido
        bot.boost = bot.can_boost() and dc > WORLD_RADIUS - 140
        return

    # 2) Evitar cabezas enemigas (más valientes: solo escapan si es más grande real)
    threat = None
    threat_d2 = BOT_DANGER_RADIUS * BOT_DANGER_RADIUS
    for o in world.snakes:
        if o is bot or not o.alive:
            continue
        d = dist2(hx, hy, o.head[0], o.head[1])
        if d < threat_d2 and o.length >= bot.length - 3:
            threat = o
            threat_d2 = d
    if threat is not None:
        # Lateralizar el escape: evadir con ángulo perpendicular a la amenaza
        away = math.atan2(hy - threat.head[1], hx - threat.head[0])
        side = 0.35 if random.random() < 0.5 else -0.35
        bot.target_angle = away + side
        bot.boost = bot.can_boost() and random.random() < 0.06
        return

    # 3) Cazar con predicción de liderazgo (más agresivos)
    if bot.length > 28 and random.random() < 0.09:
        prey = None
        best_d = 520 * 520
        for o in world.snakes:
            if o is bot or not o.alive:
                continue
            if o.length >= bot.length - 6:
                continue
            d = dist2(hx, hy, o.head[0], o.head[1])
            if d < best_d:
                prey = o
                best_d = d
        if prey is not None:
            # Lead: apuntar por delante de la presa proporcional a la distancia
            d_prey = math.sqrt(best_d)
            speed_factor = BOOST_SPEED if prey.boost else BASE_SPEED
            lead = min(260.0, d_prey * 0.5 + 60)
            tx = prey.head[0] + math.cos(prey.angle) * lead
            ty = prey.head[1] + math.sin(prey.angle) * lead
            # Si el bot es mucho mayor, intentar cortar más adelante
            if bot.length > prey.length + 25:
                lead2 = min(360.0, d_prey * 0.75 + 100)
                tx = prey.head[0] + math.cos(prey.angle) * lead2
                ty = prey.head[1] + math.sin(prey.angle) * lead2
            bot.target_angle = math.atan2(ty - hy, tx - hx)
            bot.boost = bot.can_boost() and random.random() < 0.55
            return

    # 4) Buscar comida
    bot.ai_retarget -= dt
    needs_new = (bot.ai_target is None
                 or bot.ai_retarget <= 0
                 or bot.ai_target not in world.foods_set)
    if needs_new:
        best = None
        best_d = BOT_SIGHT * BOT_SIGHT
        near = world.foods_grid.query(hx, hy, BOT_SIGHT)
        for f in near:
            d = dist2(hx, hy, f.x, f.y) * (0.35 if f.big else 1)
            if d < best_d:
                best = f
                best_d = d
        bot.ai_target = best
        bot.ai_retarget = rand_range(0.3, 1.0)
    if bot.ai_target is not None:
        bot.target_angle = math.atan2(bot.ai_target.y - hy, bot.ai_target.x - hx)
    else:
        # Sin objetivo: enfilar suavemente hacia el centro (área con más comida)
        if random.random() < 0.12:
            ca = math.atan2(WORLD_CENTER[1] - hy, WORLD_CENTER[0] - hx)
            bot.target_angle = ca + rand_range(-0.6, 0.6)
        else:
            bot.target_angle = bot.angle + rand_range(-0.2, 0.2)
    # Boost ocasional cuando está buscando comida (más vivo)
    bot.boost = bot.can_boost() and random.random() < 0.003


# =============================================================================
# WORLD
# =============================================================================
class World:
    def __init__(self, player_names):
        if isinstance(player_names, str):
            player_names = [player_names]
        self.foods: List[Food] = []
        self.foods_grid = SpatialGrid(140)
        self.foods_set: set = set()
        self.snakes: List[Snake] = []
        self.players: List[Snake] = []
        self.death_events: List[dict] = []
        self.time = 0.0

        for _ in range(FOOD_COUNT):
            px, py = random_point_in_world()
            big = random.random() < BIG_FOOD_CHANCE
            c = random.choice(PALETTE)
            self.foods.append(Food(px, py, c, big))

        used_colors = []
        for name in player_names:
            # Asegurar colores distintos entre jugadores
            avail = [c for c in PALETTE if c not in used_colors] or PALETTE
            col = random.choice(avail)
            used_colors.append(col)
            px, py = random_point_in_world()
            snake = Snake(px, py,
                          length=INITIAL_LENGTH,
                          color=col,
                          name=name,
                          is_bot=False)
            self.players.append(snake)
            self.snakes.append(snake)
        # alias de compatibilidad (primer jugador)
        self.player = self.players[0]

        for _ in range(BOT_COUNT):
            self._spawn_bot()

    def _spawn_bot(self):
        # Spawnear en el 80% interior del mundo para evitar que nazcan atrapados
        r = WORLD_RADIUS * math.sqrt(random.random()) * 0.80
        a = random.random() * math.pi * 2
        px = WORLD_CENTER[0] + r * math.cos(a)
        py = WORLD_CENTER[1] + r * math.sin(a)
        length = int(rand_range(BOT_MIN_LEN, BOT_MAX_LEN))
        s = Snake(px, py,
                  length=length,
                  color=random.choice(PALETTE),
                  name=random.choice(BOT_NAMES),
                  is_bot=True)
        # Orientar inicialmente hacia el centro con algo de dispersión
        center_angle = math.atan2(WORLD_CENTER[1] - py, WORLD_CENTER[0] - px)
        s.angle = center_angle + rand_range(-0.9, 0.9)
        s.target_angle = s.angle
        # Reconstruir segmentos desde la cabeza con el nuevo ángulo
        cos_a = math.cos(s.angle)
        sin_a = math.sin(s.angle)
        s.segments = [
            [px - i * SEG_DIST_BASE * cos_a, py - i * SEG_DIST_BASE * sin_a]
            for i in range(length)
        ]
        self.snakes.append(s)

    def update(self, dt, mouse_world=None, input_boost=None):
        self.time += dt

        # Input legacy single player (opcional, solo si se pasó)
        if mouse_world is not None and self.player.alive:
            dx = mouse_world[0] - self.player.head[0]
            dy = mouse_world[1] - self.player.head[1]
            if dx * dx + dy * dy > 4:
                self.player.target_angle = math.atan2(dy, dx)
            if input_boost is not None:
                self.player.boost = input_boost

        self.foods_grid.rebuild(self.foods)
        self.foods_set = set(self.foods)

        for s in self.snakes:
            if s.is_bot and s.alive:
                update_bot_ai(s, self, dt)
        for s in self.snakes:
            s.update(dt, self)
        for f in self.foods:
            f.update(dt)

        # Comer
        for s in self.snakes:
            if not s.alive:
                continue
            hx, hy = s.head
            r = s.seg_radius + FOOD_RADIUS + 2
            near = self.foods_grid.query(hx, hy, r + 12)
            eaten = None
            for f in near:
                rr = s.seg_radius + f.radius
                dx = hx - f.x
                dy = hy - f.y
                if dx * dx + dy * dy <= rr * rr:
                    s.grow(f.gain)
                    if eaten is None:
                        eaten = set()
                    eaten.add(f)
            if eaten:
                self.foods = [f for f in self.foods if f not in eaten]

        # Respawn de comida
        missing = FOOD_COUNT - len(self.foods)
        if missing > 0:
            n = min(missing, 14)
            for _ in range(n):
                px, py = random_point_in_world()
                big = random.random() < BIG_FOOD_CHANCE
                c = random.choice(PALETTE)
                self.foods.append(Food(px, py, c, big))

        # Colisión cabeza vs cuerpo
        alive_snakes = [s for s in self.snakes if s.alive]
        for s in alive_snakes:
            for o in alive_snakes:
                if o is s or not s.alive or not o.alive:
                    continue
                if s.head_collides_with(o):
                    s.die(self)
                    o.kills += 1
                    self.death_events.append({
                        'msg': f'{s.name} murio vs {o.name}',
                        't': self.time,
                    })
                    break

        # Mantener lista (conservar jugadores muertos para mostrar Game Over)
        self.snakes = [s for s in self.snakes if s.alive or s in self.players]

        # Respawn de bots
        while sum(1 for s in self.snakes if s.is_bot and s.alive) < BOT_COUNT:
            self._spawn_bot()

        self.death_events = [e for e in self.death_events if self.time - e['t'] < 3.5]

    def draw_background(self, surf, cam):
        surf.fill(BG_COLOR)

        cs = 120
        tlx, tly = cam.screen_to_world(0, 0)
        brx, bry = cam.screen_to_world(cam.w, cam.h)
        sx0 = math.floor(tlx / cs) * cs
        sy0 = math.floor(tly / cs) * cs

        x = sx0
        while x < brx:
            ax, _ = cam.world_to_screen(x, tly)
            pygame.draw.line(surf, GRID_COLOR, (int(ax), 0), (int(ax), cam.h), 1)
            x += cs
        y = sy0
        while y < bry:
            _, ay = cam.world_to_screen(tlx, y)
            pygame.draw.line(surf, GRID_COLOR, (0, int(ay)), (cam.w, int(ay)), 1)
            y += cs

        cx, cy = cam.world_to_screen(WORLD_CENTER[0], WORLD_CENTER[1])
        radius = int(WORLD_RADIUS * cam.zoom)
        if radius > 0:
            pygame.draw.circle(surf, BORDER_COLOR, (int(cx), int(cy)), radius, 4)

    def draw_entities(self, surf, cam, font_small):
        for f in self.foods:
            f.draw(surf, cam)
        ordered = sorted(self.snakes, key=lambda s: s.length)
        for s in ordered:
            s.draw(surf, cam, font_small)


# =============================================================================
# HUD
# =============================================================================
def draw_rounded_rect(surf, color, rect, radius=10, alpha=None):
    if alpha is None:
        pygame.draw.rect(surf, color, rect, border_radius=radius)
    else:
        tmp = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        pygame.draw.rect(tmp, (*color, alpha), (0, 0, rect[2], rect[3]), border_radius=radius)
        surf.blit(tmp, (rect[0], rect[1]))


def draw_hud(surf, world: World, cam: Camera, fonts, player: Optional[Snake] = None):
    p = player if player is not None else world.player
    f_big, f_med, f_small, f_tiny = fonts

    # Score abajo izquierda
    draw_rounded_rect(surf, (0, 0, 0), (16, cam.h - 86, 240, 72), 10, alpha=128)
    score_txt = f_med.render(f'Score: {p.score}', True, (255, 255, 255))
    surf.blit(score_txt, (30, cam.h - 76))
    info_txt = f_tiny.render(
        f'Kills: {p.kills}   Tiempo: {int(p.time_alive)}s',
        True, (187, 187, 204))
    surf.blit(info_txt, (30, cam.h - 38))

    # Leaderboard
    lb = sorted([s for s in world.snakes if s.alive],
                key=lambda s: -s.length)[:10]
    lb_w = 230
    lb_h = 28 + 22 * len(lb)
    draw_rounded_rect(surf, (0, 0, 0), (cam.w - lb_w - 16, 16, lb_w, lb_h), 10, alpha=128)
    title = f_small.render('Leaderboard', True, YELLOW)
    surf.blit(title, (cam.w - lb_w - 8, 22))
    for i, s in enumerate(lb):
        if s is p:
            color = YELLOW
        elif i < 3:
            color = (255, 255, 255)
        else:
            color = (187, 187, 204)
        name = s.name[:12] if len(s.name) > 12 else s.name
        name_txt = f_small.render(f'{i + 1}. {name}', True, color)
        surf.blit(name_txt, (cam.w - lb_w - 8, 48 + i * 22))
        len_txt = f_small.render(str(s.length), True, color)
        len_rect = len_txt.get_rect(right=cam.w - 24, top=48 + i * 22)
        surf.blit(len_txt, len_rect)

    # Minimapa
    mm_s = 150
    mm_x = 16
    mm_y = 16
    draw_rounded_rect(surf, (0, 0, 0), (mm_x, mm_y, mm_s, mm_s), 10, alpha=128)
    pygame.draw.circle(surf, (58, 64, 90),
                       (mm_x + mm_s // 2, mm_y + mm_s // 2),
                       mm_s // 2 - 4, 2)
    scale = (mm_s / 2 - 6) / WORLD_RADIUS
    for s in world.snakes:
        if not s.alive:
            continue
        rx = (s.head[0] - WORLD_CENTER[0]) * scale + mm_x + mm_s / 2
        ry = (s.head[1] - WORLD_CENTER[1]) * scale + mm_y + mm_s / 2
        col = YELLOW if s is p else s.color
        rad = 4 if s is p else 2
        pygame.draw.circle(surf, col, (int(rx), int(ry)), rad)

    # Muertes recientes
    y = 24
    for e in world.death_events[-5:]:
        age = world.time - e['t']
        a = max(0.0, 1 - age / 3.5)
        alpha = int(255 * a)
        if alpha <= 0:
            continue
        txt = f_small.render(e['msg'], True, (255, 255, 255))
        txt.set_alpha(alpha)
        rect = txt.get_rect(center=(cam.w // 2, y))
        surf.blit(txt, rect)
        y += 20

    # Barra boost
    if p.alive:
        bw = 180
        bh = 10
        bx = cam.w // 2 - bw // 2
        by = cam.h - 28
        pygame.draw.rect(surf, (42, 45, 61), (bx, by, bw, bh), border_radius=4)
        frac = clamp((p.length - MIN_LEN_FOR_BOOST) /
                     max(1, 60 - MIN_LEN_FOR_BOOST), 0, 1)
        if frac > 0:
            pygame.draw.rect(surf, YELLOW, (bx, by, int(bw * frac), bh),
                             border_radius=4)


# =============================================================================
# UI: MENÚ / PAUSA / GAME OVER
# =============================================================================
def draw_panel(surf, w, h, title, lines, fonts, title_color=YELLOW, hint=None):
    f_big, f_med, f_small, f_tiny = fonts
    # Fondo semi-transparente
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    surf.blit(overlay, (0, 0))

    pw, ph = 500, 360
    px = (w - pw) // 2
    py = (h - ph) // 2
    pygame.draw.rect(surf, (18, 20, 30), (px, py, pw, ph), border_radius=16)
    pygame.draw.rect(surf, (58, 64, 96), (px, py, pw, ph), 2, border_radius=16)

    title_surf = f_big.render(title, True, title_color)
    title_rect = title_surf.get_rect(center=(w // 2, py + 60))
    surf.blit(title_surf, title_rect)

    yy = py + 130
    for text, color in lines:
        txt = f_med.render(text, True, color)
        rect = txt.get_rect(center=(w // 2, yy))
        surf.blit(txt, rect)
        yy += 42

    if hint is not None:
        hint_surf = f_tiny.render(hint, True, (136, 136, 153))
        rect = hint_surf.get_rect(center=(w // 2, py + ph - 28))
        surf.blit(hint_surf, rect)


def menu_rects(w, h):
    """Calcula los rectángulos de UI del menú (input, botón 1P, botón 2P)."""
    pw, ph = 560, 520
    px = (w - pw) // 2
    py = (h - ph) // 2
    ix = px + 40
    iy = py + 150
    iw = pw - 80
    ih = 54
    bx = px + 40
    by1 = iy + ih + 20
    bw = pw - 80
    bh = 56
    by2 = by1 + bh + 12
    return {
        'panel': pygame.Rect(px, py, pw, ph),
        'input': pygame.Rect(ix, iy, iw, ih),
        'play_1p': pygame.Rect(bx, by1, bw, bh),
        'play_2p': pygame.Rect(bx, by2, bw, bh),
    }


def draw_menu(surf, w, h, name_buffer, name2_buffer, focus, fonts, time_s):
    f_big, f_med, f_small, f_tiny = fonts
    # Fondo con grilla
    surf.fill(BG_COLOR)
    for x in range(0, w, 60):
        pygame.draw.line(surf, GRID_COLOR, (x, 0), (x, h))
    for y in range(0, h, 60):
        pygame.draw.line(surf, GRID_COLOR, (0, y), (w, y))

    r = menu_rects(w, h)
    panel = r['panel']
    pygame.draw.rect(surf, (18, 20, 30), panel, border_radius=16)
    pygame.draw.rect(surf, (58, 64, 96), panel, 2, border_radius=16)

    title = f_big.render('GUSANITOS', True, YELLOW)
    surf.blit(title, title.get_rect(center=(w // 2, panel.top + 60)))

    sub = f_small.render('ARENA - juego tipo slither / snake.io', True, (170, 170, 187))
    surf.blit(sub, sub.get_rect(center=(w // 2, panel.top + 110)))

    # Input P1
    ibox = r['input']
    pygame.draw.rect(surf, (26, 29, 43), ibox, border_radius=10)
    border = YELLOW if focus == 'p1' else (85, 85, 102)
    pygame.draw.rect(surf, border, ibox, 2, border_radius=10)
    label1 = f_tiny.render('Nombre Jugador 1', True, (136, 136, 153))
    surf.blit(label1, (ibox.left + 6, ibox.top - 18))
    name_txt = f_med.render(name_buffer or 'Tu nombre', True,
                            (255, 255, 255) if name_buffer else (100, 100, 120))
    surf.blit(name_txt, name_txt.get_rect(center=ibox.center))
    if focus == 'p1' and name_buffer and int(time_s * 2) % 2 == 0:
        cx = ibox.centerx + name_txt.get_width() // 2 + 4
        pygame.draw.line(surf, (255, 255, 255), (cx, ibox.top + 12),
                         (cx, ibox.bottom - 12), 2)

    # Botón JUGAR 1P
    b1 = r['play_1p']
    pygame.draw.rect(surf, (67, 171, 94), b1, border_radius=10)
    btn = f_med.render('JUGAR  (1 jugador)', True, (255, 255, 255))
    surf.blit(btn, btn.get_rect(center=b1.center))

    # Botón MULTIJUGADOR (2P)
    b2 = r['play_2p']
    pygame.draw.rect(surf, (45, 109, 176), b2, border_radius=10)
    btn2 = f_med.render('MULTIJUGADOR  (pantalla partida)', True, (255, 255, 255))
    surf.blit(btn2, btn2.get_rect(center=b2.center))

    hint = f_tiny.render(
        'P1: Mouse / Clic / Espacio  |  P2 (split): WASD + Shift  |  F: fullscreen  |  Esc: pausa',
        True, (136, 136, 153))
    surf.blit(hint, hint.get_rect(center=(w // 2, panel.bottom - 28)))


# =============================================================================
# WASD -> target angle helper
# =============================================================================
def wasd_direction(keys):
    dx = 0
    dy = 0
    if keys[pygame.K_w]:
        dy -= 1
    if keys[pygame.K_s]:
        dy += 1
    if keys[pygame.K_a]:
        dx -= 1
    if keys[pygame.K_d]:
        dx += 1
    if dx == 0 and dy == 0:
        return None
    return math.atan2(dy, dx)


# =============================================================================
# GAME CONTROLLER
# =============================================================================
def main():
    pygame.init()
    pygame.display.set_caption('Gusanitos Arena')
    flags = pygame.RESIZABLE | pygame.DOUBLEBUF
    screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), flags)
    clock = pygame.time.Clock()

    f_big = pygame.font.SysFont('arial', 48, bold=True)
    f_med = pygame.font.SysFont('arial', 24, bold=True)
    f_small = pygame.font.SysFont('arial', 16, bold=True)
    f_tiny = pygame.font.SysFont('arial', 14)
    fonts = (f_big, f_med, f_small, f_tiny)

    # Estados posibles:
    #   'menu' | 'playing' | 'paused' | 'gameover'
    # Multiplayer usa los mismos pero con world.players = [p1, p2]
    state = 'menu'
    mp_mode = False          # True si es partida de 2 jugadores
    name_buffer = 'P1'
    name2_buffer = 'P2'
    focus = 'p1'             # 'p1' (siempre usado para input de texto)
    world: Optional[World] = None
    cam1: Optional[Camera] = None
    cam2: Optional[Camera] = None
    boost_p1 = False         # en 1P: boost del mouse player; en 2P: boost P1 (WASD + Shift)
    boost_p2 = False         # en 2P: boost P2 (mouse + clic/espacio)
    fullscreen = False
    time_s = 0.0

    def start_game(multiplayer=False):
        nonlocal world, cam1, cam2, state, mp_mode
        mp_mode = multiplayer
        w, h = screen.get_size()
        if multiplayer:
            n1 = (name_buffer.strip() or 'P1')[:14]
            n2 = (name2_buffer.strip() or 'P2')[:14]
            world = World([n1, n2])
            half_w = w // 2
            p1 = world.players[0]
            p2 = world.players[1]
            cam1 = Camera(p1.head[0], p1.head[1], half_w, h)
            cam2 = Camera(p2.head[0], p2.head[1], w - half_w, h)
        else:
            n1 = (name_buffer.strip() or 'Tu')[:14]
            world = World(n1)
            cam1 = Camera(world.player.head[0], world.player.head[1], w, h)
            cam2 = None
        state = 'playing'

    def toggle_fullscreen():
        nonlocal fullscreen, screen, cam1, cam2
        fullscreen = not fullscreen
        if fullscreen:
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF)
        else:
            screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT),
                                             pygame.RESIZABLE | pygame.DOUBLEBUF)
        w, h = screen.get_size()
        if cam1 is not None:
            if mp_mode and cam2 is not None:
                half = w // 2
                cam1.resize(half, h)
                cam2.resize(w - half, h)
            else:
                cam1.resize(w, h)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(0.05, dt)
        time_s += dt

        mouse_pos = pygame.mouse.get_pos()
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE and not fullscreen:
                screen = pygame.display.set_mode((event.w, event.h),
                                                 pygame.RESIZABLE | pygame.DOUBLEBUF)
                if cam1 is not None:
                    if mp_mode and cam2 is not None:
                        half = event.w // 2
                        cam1.resize(half, event.h)
                        cam2.resize(event.w - half, event.h)
                    else:
                        cam1.resize(event.w, event.h)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    toggle_fullscreen()
                    continue
                if event.key == pygame.K_ESCAPE:
                    if state == 'playing':
                        state = 'paused'
                    elif state == 'paused':
                        state = 'playing'
                    elif state == 'menu' and fullscreen:
                        toggle_fullscreen()
                    continue

                if state == 'menu':
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        start_game(multiplayer=False)
                    elif event.key == pygame.K_BACKSPACE:
                        name_buffer = name_buffer[:-1]
                    elif event.unicode and event.unicode.isprintable() and len(name_buffer) < 14:
                        name_buffer += event.unicode

                elif state == 'playing':
                    if event.key == pygame.K_SPACE:
                        # En 1P: boost del jugador. En 2P: Space es boost del P2 (mouse)
                        if mp_mode:
                            boost_p2 = True
                        else:
                            boost_p1 = True
                    elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                        if mp_mode:
                            boost_p1 = True
                    elif event.key == pygame.K_f:
                        toggle_fullscreen()

                elif state == 'gameover':
                    if event.key == pygame.K_RETURN:
                        start_game(multiplayer=mp_mode)
                    elif event.key == pygame.K_m:
                        state = 'menu'
                    elif event.key == pygame.K_f:
                        toggle_fullscreen()

            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    if mp_mode:
                        boost_p2 = False
                    else:
                        boost_p1 = False
                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    if mp_mode:
                        boost_p1 = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if state == 'playing':
                        # Clic izquierdo: boost del jugador del mouse
                        if mp_mode:
                            boost_p2 = True
                        else:
                            boost_p1 = True
                    elif state == 'menu':
                        w, h = screen.get_size()
                        rects = menu_rects(w, h)
                        if rects['play_1p'].collidepoint(event.pos):
                            start_game(multiplayer=False)
                        elif rects['play_2p'].collidepoint(event.pos):
                            start_game(multiplayer=True)
                    elif state == 'gameover':
                        w, h = screen.get_size()
                        pw, ph = 500, 360
                        px = (w - pw) // 2
                        py = (h - ph) // 2
                        retry_rect = pygame.Rect(px + 40, py + ph - 100, pw - 80, 44)
                        menu_rect = pygame.Rect(px + 40, py + ph - 50, pw - 80, 36)
                        if retry_rect.collidepoint(event.pos):
                            start_game(multiplayer=mp_mode)
                        elif menu_rect.collidepoint(event.pos):
                            state = 'menu'

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if mp_mode:
                        boost_p2 = False
                    else:
                        boost_p1 = False

        w, h = screen.get_size()

        # ======= LOGICA DE JUEGO =======
        if state == 'playing' and world is not None and cam1 is not None:
            if not mp_mode:
                # 1 jugador: mouse -> direccion
                p = world.player
                if p.alive:
                    mw = cam1.screen_to_world(mouse_pos[0], mouse_pos[1])
                    dx = mw[0] - p.head[0]
                    dy = mw[1] - p.head[1]
                    if dx * dx + dy * dy > 4:
                        p.target_angle = math.atan2(dy, dx)
                    p.boost = boost_p1
                world.update(dt)
                cam1.set_zoom_for_snake(p)
                cam1.follow(p.head[0], p.head[1], dt)
                if not p.alive:
                    state = 'gameover'
            else:
                # 2 jugadores: pantalla partida
                p1 = world.players[0]
                p2 = world.players[1]
                half_w = w // 2

                # P1: WASD (+ Shift boost)
                if p1.alive:
                    d1 = wasd_direction(keys)
                    if d1 is not None:
                        p1.target_angle = d1
                    p1.boost = boost_p1

                # P2: mouse relativo a la mitad derecha
                if p2.alive and cam2 is not None:
                    rel_x = mouse_pos[0] - half_w
                    rel_y = mouse_pos[1]
                    mw2 = cam2.screen_to_world(rel_x, rel_y)
                    dx = mw2[0] - p2.head[0]
                    dy = mw2[1] - p2.head[1]
                    if dx * dx + dy * dy > 4:
                        p2.target_angle = math.atan2(dy, dx)
                    p2.boost = boost_p2

                world.update(dt)

                cam1.set_zoom_for_snake(p1)
                cam1.follow(p1.head[0], p1.head[1], dt)
                if cam2 is not None:
                    cam2.set_zoom_for_snake(p2)
                    cam2.follow(p2.head[0], p2.head[1], dt)

                if not p1.alive and not p2.alive:
                    state = 'gameover'

        # ======= RENDER =======
        if state == 'menu' or world is None:
            draw_menu(screen, w, h, name_buffer, name2_buffer, focus, fonts, time_s)
        else:
            if not mp_mode:
                world.draw_background(screen, cam1)
                world.draw_entities(screen, cam1, f_small)
                draw_hud(screen, world, cam1, fonts, world.player)
            else:
                # Render en dos subsuperficies
                half_w = w // 2
                try:
                    left = screen.subsurface((0, 0, half_w, h))
                    right = screen.subsurface((half_w, 0, w - half_w, h))
                except ValueError:
                    left = screen
                    right = None

                world.draw_background(left, cam1)
                world.draw_entities(left, cam1, f_small)
                draw_hud(left, world, cam1, fonts, world.players[0])

                if right is not None and cam2 is not None:
                    world.draw_background(right, cam2)
                    world.draw_entities(right, cam2, f_small)
                    draw_hud(right, world, cam2, fonts, world.players[1])

                # Separador vertical
                pygame.draw.line(screen, (80, 90, 120),
                                 (half_w, 0), (half_w, h), 3)
                # Etiquetas de jugador
                p1 = world.players[0]
                p2 = world.players[1]
                tag1 = f_small.render(f'P1 · WASD · Shift boost · {p1.name}',
                                      True, p1.highlight)
                tag2 = f_small.render(f'P2 · Mouse · Clic/Espacio boost · {p2.name}',
                                      True, p2.highlight)
                draw_rounded_rect(screen, (0, 0, 0),
                                  (10, h - 28, tag1.get_width() + 20, 22),
                                  6, alpha=140)
                screen.blit(tag1, (20, h - 26))
                draw_rounded_rect(screen, (0, 0, 0),
                                  (half_w + 10, h - 28, tag2.get_width() + 20, 22),
                                  6, alpha=140)
                screen.blit(tag2, (half_w + 20, h - 26))

            if state == 'paused':
                draw_panel(screen, w, h, 'PAUSA', [], fonts,
                           title_color=(255, 255, 255),
                           hint='Presiona Esc para continuar')

            elif state == 'gameover':
                if mp_mode:
                    p1 = world.players[0]
                    p2 = world.players[1]
                    if p1.length > p2.length:
                        winner = p1.name
                    elif p2.length > p1.length:
                        winner = p2.name
                    else:
                        winner = 'Empate'
                    lines = [
                        (f'Ganador: {winner}', YELLOW),
                        (f'{p1.name}: {p1.length}  (kills {p1.kills})', (255, 255, 255)),
                        (f'{p2.name}: {p2.length}  (kills {p2.kills})', (255, 255, 255)),
                    ]
                else:
                    p = world.player
                    lines = [
                        (f'Score: {p.score}', (255, 255, 255)),
                        (f'Kills: {p.kills}', (255, 255, 255)),
                        (f'Tiempo vivo: {int(p.time_alive)}s', (255, 255, 255)),
                    ]
                draw_panel(screen, w, h, 'GAME OVER', lines, fonts,
                           title_color=(224, 80, 80),
                           hint='Enter: reintentar   |   M: menu')

                pw, ph = 500, 360
                px = (w - pw) // 2
                py = (h - ph) // 2
                retry_rect = pygame.Rect(px + 40, py + ph - 100, pw - 80, 44)
                menu_rect = pygame.Rect(px + 40, py + ph - 50, pw - 80, 36)
                pygame.draw.rect(screen, (67, 171, 94), retry_rect, border_radius=10)
                pygame.draw.rect(screen, (45, 109, 176), menu_rect, border_radius=10)
                r_txt = f_med.render('REINTENTAR', True, (255, 255, 255))
                m_txt = f_small.render('MENU', True, (255, 255, 255))
                screen.blit(r_txt, r_txt.get_rect(center=retry_rect.center))
                screen.blit(m_txt, m_txt.get_rect(center=menu_rect.center))

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == '__main__':
    main()

import math
import os
import random
import sys

import pygame
from pygame.math import Vector2

WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
FPS = 60
MAP_WIDTH = 4000
MAP_HEIGHT = 4000
INITIAL_ORBS = 660
BOT_COUNT = 24
ORB_SPAWN_CHANCE = 0.02
MAX_ORBS = 780
BOOST_DRAIN_RATE = 10.0

COLOR_BG = (16, 16, 24)
COLOR_GRID = (30, 30, 40)
COLOR_TEXT = (240, 240, 240)
COLOR_ORB = (130, 240, 160)
COLOR_DEAD = (120, 120, 120)

pygame.init()
pygame.display.set_caption("Slither.io estilo Python")
FONT = pygame.font.SysFont("consolas", 18)
TITLE_FONT = pygame.font.SysFont("consolas", 32, bold=True)
MENU_FONT = pygame.font.SysFont("consolas", 28)
MENU_BUTTON_FONT = pygame.font.SysFont("consolas", 32, bold=True)
SCREEN = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WINDOW_WIDTH, WINDOW_HEIGHT = SCREEN.get_size()
CLOCK = pygame.time.Clock()

BASE_DIR = os.path.dirname(__file__)
IMAGE_DIR = os.path.join(BASE_DIR, "imagenes", "fondo")
GAME_BACKGROUND = pygame.transform.smoothscale(
    pygame.image.load(os.path.join(IMAGE_DIR, "fondo.png")).convert(),
    (WINDOW_WIDTH, WINDOW_HEIGHT),
)
MENU_BACKGROUND = pygame.transform.smoothscale(
    pygame.image.load(os.path.join(IMAGE_DIR, "menu.png")).convert(),
    (WINDOW_WIDTH, WINDOW_HEIGHT),
)
MENU2_BACKGROUND = pygame.transform.smoothscale(
    pygame.image.load(os.path.join(IMAGE_DIR, "menu2.png")).convert(),
    (WINDOW_WIDTH, WINDOW_HEIGHT),
)

INPUT_MAX_LENGTH = 16
MENU_INPUT_RECT = pygame.Rect(WINDOW_WIDTH // 2 - 260, 300, 520, 70)
MENU_PLAY_RECT = pygame.Rect(WINDOW_WIDTH // 2 - 220, 430, 440, 100)
MENU_WORM_RECT = pygame.Rect(44, WINDOW_HEIGHT - 198, 120, 104)
COLOR_CIRCLE_RADIUS = 38
COLOR_CIRCLE_POSITIONS = [
    Vector2(WINDOW_WIDTH // 2 - 300 + i * 120, 285) for i in range(6)
]
COLOR_OPTIONS = [
    ((220, 50, 50), "Rojo"),
    ((240, 205, 40), "Amarillo"),
    ((40, 90, 230), "Azul"),
    ((40, 190, 70), "Verde"),
    ((180, 60, 240), "Violeta"),
    ((30, 30, 30), "Negro"),
]
MENU_EXIT_RECT = pygame.Rect(WINDOW_WIDTH // 2 - 180, 470, 360, 90)
MENU_MULTIPLAYER_RECT = pygame.Rect(WINDOW_WIDTH // 2 - 220, 550, 440, 100)
MENU_TUTORIAL_RECT = pygame.Rect(WINDOW_WIDTH - 200, WINDOW_HEIGHT - 80, 180, 60)
MINIMAP_SIZE = 224
MINIMAP_BORDER = 4
MINIMAP_RECT = pygame.Rect(16, WINDOW_HEIGHT - 26 - MINIMAP_SIZE, MINIMAP_SIZE, MINIMAP_SIZE)
MINIMAP_BG_COLOR = (18, 18, 28)
MINIMAP_BORDER_COLOR = (220, 220, 220)
MINIMAP_PLAYER_COLOR = (255, 255, 255)
MINIMAP_ORB_COLOR = (130, 240, 160)
MINIMAP_LIMIT_COLOR = (240, 120, 120)


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def lerp(a, b, t):
    return a + (b - a) * t


class Orb:
    def __init__(self, pos, mass):
        self.pos = Vector2(pos)
        self.mass = mass
        self.radius = max(4, int(math.sqrt(self.mass * 1.8) + 2))
        self.color = COLOR_ORB

    def draw(self, surface, camera_offset):
        screen_pos = self.pos - camera_offset
        if (
            -self.radius <= screen_pos.x <= WINDOW_WIDTH + self.radius
            and -self.radius <= screen_pos.y <= WINDOW_HEIGHT + self.radius
        ):
            pygame.draw.circle(surface, self.color, screen_pos, self.radius)


class Snake:
    def __init__(self, pos, color, name, is_player=False, player_id=None):
        self.head = Vector2(pos)
        self.direction = Vector2(1, 0)
        self.color = color
        self.name = name
        self.is_player = is_player
        self.player_id = player_id  # 1 o 2 para multijugador
        self.mass = 35.0
        self.alive = True
        self.path = [Vector2(self.head)]
        self.body_points = [Vector2(self.head)]
        self.boost_energy = 0.0
        self.boosting = False
        self.target = None
        self.respawn_timer = 0.0
        self.spawn_count = 0
        self.death_spawned = False
        self.boost_drop_accumulator = 0.0

    @property
    def radius(self):
        return max(10, int(6 + math.sqrt(self.mass)))

    @property
    def speed(self):
        base = 140.0 + self.mass * 0.08
        return base * (1.9 if self.boosting else 1.0)

    def update(self, dt, orbs, snakes):
        if not self.alive:
            self.respawn_timer -= dt
            return

        if self.is_player:
            self.update_player(dt)
        else:
            self.update_bot(dt, snakes)

        if self.boosting and self.mass > 12:
            lost = BOOST_DRAIN_RATE * dt
            self.mass -= lost
            self.boost_drop_accumulator += lost
            self.mass = max(self.mass, 10.0)
            self.spawn_boost_orbs(orbs)
            if self.mass <= 10:
                self.die(orbs)
                return

        move = self.direction.normalize() * self.speed * dt
        new_head = self.head + move
        if new_head.x <= 0 or new_head.x >= MAP_WIDTH or new_head.y <= 0 or new_head.y >= MAP_HEIGHT:
            self.head = new_head
            self.die(orbs)
            return

        self.head = new_head
        self.path.insert(0, Vector2(self.head))
        if len(self.path) > 2200:
            self.path.pop()

        self.eat_orbs(orbs)
        self.body_points = self.compute_body_points()

    def update_player(self, dt):
        if self.player_id == 1:
            # Jugador 1: Control con mouse
            mouse_screen = Vector2(pygame.mouse.get_pos())
            camera_offset = self.head - Vector2(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
            mouse_world = mouse_screen + camera_offset
            direction = mouse_world - self.head
            if direction.length_squared() > 0.01:
                self.direction = direction.normalize()
            self.boosting = pygame.mouse.get_pressed()[0]
        elif self.player_id == 2:
            # Jugador 2: Control con flechas
            keys = pygame.key.get_pressed()
            direction = Vector2(0, 0)
            if keys[pygame.K_UP]:
                direction.y = -1
            if keys[pygame.K_DOWN]:
                direction.y = 1
            if keys[pygame.K_LEFT]:
                direction.x = -1
            if keys[pygame.K_RIGHT]:
                direction.x = 1
            if direction.length_squared() > 0.01:
                self.direction = direction.normalize()
            self.boosting = keys[pygame.K_SPACE]
        else:
            # Modo single player original
            mouse_screen = Vector2(pygame.mouse.get_pos())
            camera_offset = self.head - Vector2(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
            mouse_world = mouse_screen + camera_offset
            direction = mouse_world - self.head
            if direction.length_squared() > 0.01:
                self.direction = direction.normalize()
            self.boosting = pygame.mouse.get_pressed()[0]

    def update_bot(self, dt, snakes):
        self.boosting = False
        near_edge = (
            self.head.x < 170
            or self.head.x > MAP_WIDTH - 170
            or self.head.y < 170
            or self.head.y > MAP_HEIGHT - 170
        )

        if self.target is None or self.head.distance_to(self.target) < 30 or random.random() < 0.018:
            self.choose_new_target(snakes)

        if self.target is not None:
            direction = self.target - self.head
            if direction.length_squared() > 0.01:
                desired = direction.normalize()
                self.direction = lerp(self.direction, desired, 0.05)

        if random.random() < 0.009:
            self.direction = self.direction.rotate(random.uniform(-14, 14))

        if self.mass > 30:
            target_distance = self.head.distance_to(self.target or self.head)
            boost_chance = 0.018 if target_distance > 100 else 0.008
            if random.random() < boost_chance:
                self.boosting = True

        if near_edge and random.random() < 0.45:
            self.target = Vector2(MAP_WIDTH / 2, MAP_HEIGHT / 2)

    def choose_new_target(self, snakes):
        visible_orbs = []
        for orb in world_orbs:
            if self.head.distance_to(orb.pos) < 420:
                visible_orbs.append(orb)
        if visible_orbs:
            best = max(
                visible_orbs,
                key=lambda o: o.mass * 1.6 - self.head.distance_to(o.pos) * 0.16,
            )
            self.target = best.pos
            return

        safe_x = clamp(random.uniform(self.head.x - 320, self.head.x + 320), 100, MAP_WIDTH - 100)
        safe_y = clamp(random.uniform(self.head.y - 320, self.head.y + 320), 100, MAP_HEIGHT - 100)
        self.target = Vector2(safe_x, safe_y)

    def eat_orbs(self, orbs):
        for orb in orbs[:]:
            if self.head.distance_to(orb.pos) < self.radius + orb.radius:
                self.mass += orb.mass * 0.65
                self.mass = min(self.mass, 1800)
                orbs.remove(orb)

    def spawn_boost_orbs(self, orbs):
        self.boost_drop_accumulator += 0.0
        while self.boost_drop_accumulator > 1.0:
            self.boost_drop_accumulator -= 1.0
            tail_pos = self.get_tail_position(45)
            if tail_pos is None:
                tail_pos = self.head - self.direction * 16
            offset = Vector2(random.uniform(-18, 18), random.uniform(-18, 18))
            orbs.append(Orb(tail_pos + offset, 1.0))

    def get_tail_position(self, distance_from_head: float):
        if len(self.path) < 2:
            return None
        traveled = 0.0
        prev = self.path[0]
        for point in self.path[1:]:
            segment = point - prev
            segment_length = segment.length()
            if traveled + segment_length >= distance_from_head:
                t = (distance_from_head - traveled) / segment_length
                return prev + segment * t
            traveled += segment_length
            prev = point
        return self.path[-1]

    def compute_body_points(self):
        points = []
        if len(self.path) < 2:
            return points
        spacing = max(12, self.radius * 0.92)
        needed = int(self.mass * 1.0) + 14
        accumulated = 0.0
        prev = self.path[0]
        idx = 1
        while idx < len(self.path) and len(points) < needed:
            point = self.path[idx]
            segment = point - prev
            seg_length = segment.length()
            if seg_length == 0:
                idx += 1
                continue
            if accumulated + seg_length >= spacing:
                t = (spacing - accumulated) / seg_length
                sample = prev + segment * t
                points.append(sample)
                prev = sample
                accumulated = 0.0
            else:
                accumulated += seg_length
                prev = point
                idx += 1
        return points

    def get_body_points(self):
        return self.body_points

    def draw(self, surface, camera_offset):
        if not self.alive:
            return
        body_points = self.get_body_points()
        if body_points:
            for i, point in enumerate(body_points):
                ratio = i / max(1, len(body_points) - 1)
                radius = int(self.radius * (0.95 - 0.45 * ratio))
                if radius < 2:
                    continue

                base_color = [
                    int(lerp(self.color[c], COLOR_DEAD[c], 0.18 + 0.6 * ratio))
                    for c in range(3)
                ]
                shadow = [max(0, c - 32) for c in base_color]
                highlight = [min(255, int(c * 1.25 + 12)) for c in base_color]
                glow = [min(255, int(c * 1.16 + 16)) for c in base_color]

                pos = point - camera_offset
                pygame.draw.circle(surface, shadow, pos + Vector2(2, 2), radius)
                pygame.draw.circle(surface, base_color, pos, radius)

                if radius > 6:
                    pygame.draw.circle(surface, highlight, pos, radius - 2, 2)
                    glow_radius = max(2, radius // 3)
                    pygame.draw.circle(surface, glow, pos - Vector2(1, 1), glow_radius)

                if radius > 8 and i % 3 == 0:
                    spark_pos = pos + Vector2(radius * 0.25, -radius * 0.22)
                    spark_color = [min(255, int(c * 1.3)) for c in base_color]
                    pygame.draw.circle(surface, spark_color, spark_pos, max(1, radius // 6))

        head_pos = self.head - camera_offset
        head_color = self.color
        dark_head = [max(0, c - 26) for c in head_color]
        glow_color = [min(255, c + 70) for c in head_color]
        highlight_head = [min(255, int(c * 1.18 + 18)) for c in head_color]
        glow = [min(255, int(c * 1.16 + 16)) for c in head_color]

        pygame.draw.circle(surface, dark_head, head_pos, self.radius + 2)
        pygame.draw.circle(surface, glow_color, head_pos, int(self.radius * 0.7), 3)
        pygame.draw.circle(surface, head_color, head_pos, self.radius)
        pygame.draw.circle(surface, highlight_head, head_pos - Vector2(0, self.radius * 0.15), max(3, self.radius // 5))

        eye_direction = self.direction.normalize() if self.direction.length_squared() > 0.01 else Vector2(1, 0)
        eye_offset = eye_direction * (self.radius * 0.38)
        left_eye = head_pos + eye_offset.rotate(24)
        right_eye = head_pos + eye_offset.rotate(-24)
        eye_radius = max(3, self.radius // 4)

        for eye_center in (left_eye, right_eye):
            pygame.draw.circle(surface, (255, 255, 255), eye_center, eye_radius)
            pygame.draw.circle(surface, (45, 45, 45), eye_center, max(2, eye_radius // 2))
            pygame.draw.circle(surface, (180, 220, 255), eye_center - Vector2(eye_radius * 0.2, -eye_radius * 0.2), max(1, eye_radius // 3))

        nose_center = head_pos + eye_direction * (self.radius * 0.55)
        pygame.draw.circle(surface, (235, 235, 235), nose_center, max(2, self.radius // 8))
        cheek_offset = eye_direction.rotate(90) * (self.radius * 0.33)
        pygame.draw.circle(surface, glow, head_pos + cheek_offset, max(2, self.radius // 6))
        pygame.draw.circle(surface, glow, head_pos - cheek_offset, max(2, self.radius // 6))

    def check_death_collision(self, snakes, orbs):
        if not self.alive:
            return
        for other in snakes:
            if other is self or not other.alive:
                continue
            body_points = other.body_points[5:]
            for point in body_points:
                if self.head.distance_to(point) < self.radius * 0.95:
                    self.die(orbs)
                    return

    def die(self, orbs):
        if not self.alive:
            return
        self.alive = False
        self.death_spawned = True
        total_mass = max(8.0, self.mass)
        path_points = self.path[:] if self.path else [Vector2(self.head)]
        self.mass = 0.0
        self.path.clear()
        self.target = None
        self.respawn_timer = 3.5 if not self.is_player else 9999
        pieces = min(48, int(total_mass // 2) + 8)
        body_points = self.get_body_points() or path_points
        if not body_points:
            body_points = [self.head]

        for idx in range(pieces):
            orb_mass = max(1.0, min(8.0, random.gauss(total_mass / pieces, 1.4)))
            base_point = body_points[idx % len(body_points)]
            offset = Vector2(random.uniform(-10, 10), random.uniform(-10, 10))
            drop_pos = base_point + offset
            drop_pos.x = clamp(drop_pos.x, 0, MAP_WIDTH)
            drop_pos.y = clamp(drop_pos.y, 0, MAP_HEIGHT)
            orbs.append(Orb(drop_pos, orb_mass))

    def respawn(self):
        self.alive = True
        self.mass = 28.0
        self.head = Vector2(random.uniform(200, MAP_WIDTH - 200), random.uniform(200, MAP_HEIGHT - 200))
        self.path = [Vector2(self.head)]
        self.body_points = [Vector2(self.head)]
        self.direction = Vector2(1, 0)
        self.death_spawned = False
        self.boost_drop_accumulator = 0.0
        self.respawn_timer = 0.0


world_orbs = []


def spawn_initial_orbs():
    for _ in range(INITIAL_ORBS):
        world_orbs.append(
            Orb(
                (
                    random.uniform(40, MAP_WIDTH - 40),
                    random.uniform(40, MAP_HEIGHT - 40),
                ),
                random.choice([1.0, 1.0, 1.0, 2.0, 2.0, 3.0]),
            )
        )


def spawn_random_orb():
    mass = random.choice([1.0, 1.0, 1.0, 2.0, 3.0])
    pos = Vector2(random.uniform(20, MAP_WIDTH - 20), random.uniform(20, MAP_HEIGHT - 20))
    world_orbs.append(Orb(pos, mass))


def draw_background(surface, camera_offset):
    surface.blit(GAME_BACKGROUND, (0, 0))

    center_world = Vector2(MAP_WIDTH / 2, MAP_HEIGHT / 2)
    center_screen = center_world - camera_offset
    if 0 <= center_screen.x <= WINDOW_WIDTH and 0 <= center_screen.y <= WINDOW_HEIGHT:
        pygame.draw.circle(surface, (60, 60, 90), center_screen, 16, 2)

    map_rect = pygame.Rect(-camera_offset.x, -camera_offset.y, MAP_WIDTH, MAP_HEIGHT)
    pygame.draw.rect(surface, (220, 50, 50), map_rect, 6)


def draw_ui(surface, player, snakes):
    texts = []
    texts.append(f"Jugador: {int(player.mass)} masa    Segundos: {pygame.time.get_ticks() // 1000}")
    texts.append("Controles: Mueve el mouse | Click para boost | R para respawn")
    for i, line in enumerate(texts):
        rendered = FONT.render(line, True, COLOR_TEXT)
        surface.blit(rendered, (16, 16 + 22 * i))

    ranking = sorted(snakes, key=lambda s: s.mass, reverse=True)[:6]
    title = TITLE_FONT.render("Ranking", True, COLOR_TEXT)
    surface.blit(title, (WINDOW_WIDTH - 220, 16))
    for idx, snake in enumerate(ranking, start=1):
        status = "VIVO" if snake.alive else "MUERTO"
        line = f"{idx}. {snake.name[:10]:10} {int(snake.mass):4} {status}"
        rendered = FONT.render(line, True, COLOR_TEXT)
        surface.blit(rendered, (WINDOW_WIDTH - 220, 24 + 28 * idx))

    draw_minimap(surface, player, world_orbs)

    if not player.alive:
        msg = "Has muerto. Presiona R para reaparecer." if player.respawn_timer >= 0 else ""
        rendered = TITLE_FONT.render(msg, True, (255, 120, 120))
        rect = rendered.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
        surface.blit(rendered, rect)


def draw_ui_multiplayer(surface, player, snakes, side="left"):
    """Dibuja la UI para un jugador en modo multijugador"""
    if side == "left":
        x_offset = 16
        rank_x = WINDOW_WIDTH // 2 - 220
    else:
        x_offset = WINDOW_WIDTH // 2 + 16
        rank_x = WINDOW_WIDTH - 220

    texts = []
    texts.append(f"{player.name}: {int(player.mass)} masa")
    texts.append(f"Segundos: {pygame.time.get_ticks() // 1000}")
    for i, line in enumerate(texts):
        rendered = FONT.render(line, True, COLOR_TEXT)
        surface.blit(rendered, (x_offset, 16 + 22 * i))

    ranking = sorted(snakes, key=lambda s: s.mass, reverse=True)[:5]
    title = FONT.render("Ranking", True, COLOR_TEXT)
    surface.blit(title, (rank_x, 16))
    for idx, snake in enumerate(ranking, start=1):
        status = "VIVO" if snake.alive else "MUERTO"
        line = f"{idx}. {snake.name[:8]:8} {int(snake.mass):4}"
        rendered = FONT.render(line, True, COLOR_TEXT)
        surface.blit(rendered, (rank_x, 24 + 22 * idx))

    if not player.alive:
        msg = "Presiona R para reaparecer"
        rendered = FONT.render(msg, True, (255, 120, 120))
        surface.blit(rendered, (x_offset, 16 + 100))


def draw_main_menu(surface, active_input, nickname, selected_color_name):
    surface.blit(MENU_BACKGROUND, (0, 0))

    pygame.draw.rect(surface, (80, 70, 120), MENU_INPUT_RECT, border_radius=36)
    pygame.draw.rect(
        surface,
        (220, 220, 220) if active_input else (180, 180, 200),
        MENU_INPUT_RECT,
        3,
        border_radius=36,
    )

    input_text = nickname if nickname else "Nickname"
    text_color = (240, 240, 240) if nickname else (180, 180, 205)
    rendered = MENU_FONT.render(input_text, True, text_color)
    text_rect = rendered.get_rect(center=MENU_INPUT_RECT.center)
    surface.blit(rendered, text_rect)

    pygame.draw.rect(surface, (90, 180, 130), MENU_PLAY_RECT, border_radius=48)
    rendered = MENU_BUTTON_FONT.render("Play Online", True, (255, 255, 255))
    text_rect = rendered.get_rect(center=MENU_PLAY_RECT.center)
    surface.blit(rendered, text_rect)

    pygame.draw.rect(surface, (130, 100, 200), MENU_MULTIPLAYER_RECT, border_radius=48)
    rendered = MENU_BUTTON_FONT.render("Multijugador", True, (255, 255, 255))
    text_rect = rendered.get_rect(center=MENU_MULTIPLAYER_RECT.center)
    surface.blit(rendered, text_rect)

    pygame.draw.rect(surface, (220, 220, 255), MENU_WORM_RECT, 3, border_radius=40)
    label = MENU_FONT.render("Click gusano", True, (245, 245, 245))
    label_rect = label.get_rect(midtop=(MENU_WORM_RECT.centerx, MENU_WORM_RECT.bottom + 8))
    surface.blit(label, label_rect)

    color_label = FONT.render(f"Color seleccionado: {selected_color_name}", True, (220, 220, 220))
    surface.blit(color_label, (20, 20))
    # Botón Tutorial
    pygame.draw.rect(surface, (120, 120, 180), MENU_TUTORIAL_RECT, border_radius=30)

    tutorial_text = FONT.render("Tutorial", True, (255,255,255))
    tutorial_rect = tutorial_text.get_rect(center=MENU_TUTORIAL_RECT.center)

    surface.blit(tutorial_text, tutorial_rect)

def draw_color_menu(surface, selected_color):
    surface.blit(MENU2_BACKGROUND, (0, 0))

    header = MENU_BUTTON_FONT.render("Selecciona tu color", True, (255, 255, 255))
    header_rect = header.get_rect(center=(WINDOW_WIDTH / 2, 180))
    surface.blit(header, header_rect)

    for index, (position) in enumerate(COLOR_CIRCLE_POSITIONS):
        color, _ = COLOR_OPTIONS[index]
        pygame.draw.circle(surface, color, position, COLOR_CIRCLE_RADIUS)
        if selected_color == color:
            pygame.draw.circle(surface, (255, 255, 255), position, COLOR_CIRCLE_RADIUS + 6, 4)

    pygame.draw.rect(surface, (90, 180, 130), MENU_EXIT_RECT, border_radius=44)
    rendered = MENU_BUTTON_FONT.render("Salir", True, (255, 255, 255))
    text_rect = rendered.get_rect(center=MENU_EXIT_RECT.center)
    surface.blit(rendered, text_rect)

    description = FONT.render("Elige rojo, amarillo, azul, verde, violeta o negro.", True, (225, 225, 225))
    desc_rect = description.get_rect(center=(WINDOW_WIDTH / 2, MENU_EXIT_RECT.top - 40))
    surface.blit(description, desc_rect)


def draw_multiplayer_menu(surface, player1_name, player1_color_name, player2_name, player2_color_name, active_input_p1):
    """Dibuja el menú para seleccionar configuración en modo multijugador"""
    surface.blit(MENU_BACKGROUND, (0, 0))
    
    # Título
    title = TITLE_FONT.render("MULTIJUGADOR", True, (255, 255, 255))
    title_rect = title.get_rect(center=(WINDOW_WIDTH / 2, 40))
    surface.blit(title, title_rect)
    
    # Sección Jugador 1 (izquierda)
    p1_x = WINDOW_WIDTH // 4
    p1_title = MENU_FONT.render("Jugador 1 (MOUSE + CLICK)", True, (255, 255, 255))
    p1_title_rect = p1_title.get_rect(center=(p1_x, 100))
    surface.blit(p1_title, p1_title_rect)
    
    p1_input_rect = pygame.Rect(p1_x - 130, 160, 260, 60)
    pygame.draw.rect(surface, (80, 70, 120), p1_input_rect, border_radius=36)
    pygame.draw.rect(
        surface,
        (220, 220, 220) if active_input_p1 else (180, 180, 200),
        p1_input_rect,
        3,
        border_radius=36,
    )
    p1_input_text = player1_name if player1_name else "Ingresa nombre..."
    p1_text_color = (240, 240, 240) if player1_name else (180, 180, 205)
    p1_rendered = MENU_FONT.render(p1_input_text, True, p1_text_color)
    p1_rect = p1_rendered.get_rect(center=p1_input_rect.center)
    surface.blit(p1_rendered, p1_rect)
    
    p1_color_label = FONT.render(f"Color: {player1_color_name}", True, (220, 220, 220))
    surface.blit(p1_color_label, (p1_x - 100, 240))
    
    # Sección Jugador 2 (derecha)
    p2_x = 3 * WINDOW_WIDTH // 4
    p2_title = MENU_FONT.render("Jugador 2 (FLECHAS + ESPACIO)", True, (255, 255, 255))
    p2_title_rect = p2_title.get_rect(center=(p2_x, 100))
    surface.blit(p2_title, p2_title_rect)
    
    p2_info = FONT.render(f"Nombre: {player2_name if player2_name else 'JUGADOR2'}", True, (220, 220, 220))
    p2_info_rect = p2_info.get_rect(center=(p2_x, 180))
    surface.blit(p2_info, p2_info_rect)
    
    p2_color_label = FONT.render(f"Color: {player2_color_name}", True, (220, 220, 220))
    surface.blit(p2_color_label, (p2_x - 100, 240))
    
    # Estado del formulario
    status_text = "Completa el nombre para Jugador 1" if not player1_name.strip() else "¡Listo para jugar!"
    status_color = (255, 150, 150) if not player1_name.strip() else (150, 255, 150)
    status = FONT.render(status_text, True, status_color)
    status_rect = status.get_rect(center=(WINDOW_WIDTH / 2, 300))
    surface.blit(status, status_rect)
    
    # Botón de juego
    play_rect = pygame.Rect(WINDOW_WIDTH // 2 - 150, WINDOW_HEIGHT - 120, 300, 80)
    play_color = (90, 180, 130) if player1_name.strip() else (80, 100, 100)
    pygame.draw.rect(surface, play_color, play_rect, border_radius=48)
    play_text = MENU_BUTTON_FONT.render("¡JUGAR!", True, (255, 255, 255))
    play_text_rect = play_text.get_rect(center=play_rect.center)
    surface.blit(play_text, play_text_rect)
    
    # Botón atrás
    back_rect = pygame.Rect(16, 16, 120, 50)
    pygame.draw.rect(surface, (200, 100, 100), back_rect, border_radius=30)
    back_text = MENU_FONT.render("Atrás", True, (255, 255, 255))
    back_text_rect = back_text.get_rect(center=back_rect.center)
    surface.blit(back_text, back_text_rect)
    
    return play_rect, back_rect, p1_input_rect


def draw_minimap(surface, player, orbs):
    pygame.draw.rect(surface, MINIMAP_BG_COLOR, MINIMAP_RECT, border_radius=18)
    pygame.draw.rect(surface, MINIMAP_BORDER_COLOR, MINIMAP_RECT, MINIMAP_BORDER, border_radius=18)

    def world_to_minimap(world_pos):
        x = MINIMAP_RECT.x + (world_pos.x / MAP_WIDTH) * MINIMAP_RECT.width
        y = MINIMAP_RECT.y + (world_pos.y / MAP_HEIGHT) * MINIMAP_RECT.height
        return Vector2(x, y)

    # Dibujar los límites del mapa dentro del minimapa
    inner_rect = MINIMAP_RECT.inflate(-MINIMAP_BORDER * 2, -MINIMAP_BORDER * 2)
    pygame.draw.rect(surface, MINIMAP_LIMIT_COLOR, inner_rect, 2, border_radius=14)

    # Orbes dentro del minimapa
    for orb in orbs:
        pos = world_to_minimap(orb.pos)
        if inner_rect.collidepoint(pos):
            surface.fill(MINIMAP_ORB_COLOR, (int(pos.x), int(pos.y), 2, 2))

    # Posición del jugador
    player_pos = world_to_minimap(player.head)
    pygame.draw.circle(surface, MINIMAP_PLAYER_COLOR, player_pos, 5)
    pygame.draw.circle(surface, (0, 0, 0), player_pos, 2)

    label = FONT.render("Mapa", True, (220, 220, 220))
    surface.blit(label, (MINIMAP_RECT.x + 8, MINIMAP_RECT.y + 8))

def draw_minimap_multiplayer(surface, player, orbs):

    minimap_size = 140

    minimap_rect = pygame.Rect(
        16,
        WINDOW_HEIGHT - minimap_size - 16,
        minimap_size,
        minimap_size
    )

    pygame.draw.rect(surface, MINIMAP_BG_COLOR, minimap_rect, border_radius=12)
    pygame.draw.rect(surface, MINIMAP_BORDER_COLOR, minimap_rect, 2, border_radius=12)

    def world_to_minimap(world_pos):
        x = minimap_rect.x + (world_pos.x / MAP_WIDTH) * minimap_rect.width
        y = minimap_rect.y + (world_pos.y / MAP_HEIGHT) * minimap_rect.height
        return Vector2(x, y)

    inner_rect = minimap_rect.inflate(-4, -4)
    pygame.draw.rect(surface, MINIMAP_LIMIT_COLOR, inner_rect, 1, border_radius=10)

    for orb in orbs:
        pos = world_to_minimap(orb.pos)
        if inner_rect.collidepoint(pos):
            surface.fill(MINIMAP_ORB_COLOR, (int(pos.x), int(pos.y), 1, 1))

    player_pos = world_to_minimap(player.head)
    pygame.draw.circle(surface, MINIMAP_PLAYER_COLOR, player_pos, 3)
    pygame.draw.circle(surface, (0, 0, 0), player_pos, 1)

def draw_ranking_multiplayer(surface, snakes, player, side):

    ranking = sorted(snakes, key=lambda s: s.mass, reverse=True)[:5]

    if side == "left":
        x = 16
    else:
        x = WINDOW_WIDTH // 2 - 200

    title = FONT.render("TOP", True, COLOR_TEXT)
    surface.blit(title, (x, 16))

    for i, snake in enumerate(ranking, start=1):

        status = "VIVO" if snake.alive else "X"

        if snake == player:
            color = (255,255,255)
        else:
            color = (200,200,200)

        line = f"{i}. {snake.name[:8]:8} {int(snake.mass):4} {status}"
        txt = FONT.render(line, True, color)

        surface.blit(txt, (x, 40 + i * 22))

def draw_split_screen(surface, player1, player2, snakes, orbs):
    """Dibuja el juego dividido en dos pantallas para multijugador"""
    # Pantalla izquierda - Jugador 1
    left_surface = pygame.Surface((WINDOW_WIDTH // 2, WINDOW_HEIGHT))
    
    # Cámara para jugador 1
    camera_offset_p1 = player1.head - Vector2(WINDOW_WIDTH // 4, WINDOW_HEIGHT / 2)
    
    # Dibujar fondo, orbes y serpientes en la pantalla izquierda
    left_surface.blit(GAME_BACKGROUND, (0, 0))
    
    # Dibujar mapa límite
    center_world = Vector2(MAP_WIDTH / 2, MAP_HEIGHT / 2)
    center_screen = center_world - camera_offset_p1
    if 0 <= center_screen.x <= WINDOW_WIDTH // 2 and 0 <= center_screen.y <= WINDOW_HEIGHT:
        pygame.draw.circle(left_surface, (60, 60, 90), center_screen, 16, 2)
    
    map_rect = pygame.Rect(-camera_offset_p1.x, -camera_offset_p1.y, MAP_WIDTH, MAP_HEIGHT)
    pygame.draw.rect(left_surface, (220, 50, 50), map_rect, 6)
    
    # Dibujar orbes
    for orb in orbs:
        orb.draw(left_surface, camera_offset_p1)
    
    # Dibujar serpientes
    for snake in snakes:
        snake.draw(left_surface, camera_offset_p1)
    
    # Dibujar UI para jugador 1
    draw_minimap_multiplayer(left_surface, player1, orbs)
    draw_ranking_multiplayer(left_surface, snakes, player1, "left")
    
    # Pantalla derecha - Jugador 2
    right_surface = pygame.Surface((WINDOW_WIDTH // 2, WINDOW_HEIGHT))
    
    # Cámara para jugador 2
    camera_offset_p2 = player2.head - Vector2(WINDOW_WIDTH // 4, WINDOW_HEIGHT / 2)
    
    # Dibujar fondo, orbes y serpientes en la pantalla derecha
    right_surface.blit(GAME_BACKGROUND, (0, 0))
    
    # Dibujar mapa límite
    center_screen = center_world - camera_offset_p2
    if 0 <= center_screen.x <= WINDOW_WIDTH // 2 and 0 <= center_screen.y <= WINDOW_HEIGHT:
        pygame.draw.circle(right_surface, (60, 60, 90), center_screen, 16, 2)
    
    map_rect = pygame.Rect(-camera_offset_p2.x, -camera_offset_p2.y, MAP_WIDTH, MAP_HEIGHT)
    pygame.draw.rect(right_surface, (220, 50, 50), map_rect, 6)
    
    # Dibujar orbes
    for orb in orbs:
        orb.draw(right_surface, camera_offset_p2)
    
    # Dibujar serpientes
    for snake in snakes:
        snake.draw(right_surface, camera_offset_p2)
    
    # Dibujar UI para jugador 2
    draw_minimap_multiplayer(right_surface, player2, orbs)
    draw_ranking_multiplayer(right_surface, snakes, player2, "right")
    
    # Combinar las dos pantallas en la pantalla principal
    surface.blit(left_surface, (0, 0))
    surface.blit(right_surface, (WINDOW_WIDTH // 2, 0))
    
    # Dibujar línea divisoria
    pygame.draw.line(surface, (150, 150, 150), (WINDOW_WIDTH // 2, 0), (WINDOW_WIDTH // 2, WINDOW_HEIGHT), 3)


def start_game(name, color):
    global world_orbs
    world_orbs = []
    spawn_initial_orbs()
    snakes = []
    name_value = name.strip() or "JUGADOR"
    player = Snake((MAP_WIDTH / 2, MAP_HEIGHT / 2), color, name_value, is_player=True)
    snakes.append(player)

    bot_colors = [
        (240, 120, 120),
        (120, 240, 140),
        (250, 210, 90),
        (180, 120, 250),
        (240, 90, 180),
        (120, 220, 230),
        (200, 190, 100),
        (140, 240, 170),
    ]
    for index in range(BOT_COUNT):
        pos = (
            random.uniform(120, MAP_WIDTH - 120),
            random.uniform(120, MAP_HEIGHT - 120),
        )
        snakes.append(Snake(pos, bot_colors[index % len(bot_colors)], f"BOT{index + 1}"))

    return snakes, player


def start_multiplayer_game(name1, color1, name2, color2):
    """Inicia un juego con dos jugadores"""
    global world_orbs
    world_orbs = []
    spawn_initial_orbs()
    snakes = []
    
    name1_value = name1.strip() or "JUGADOR1"
    name2_value = name2.strip() or "JUGADOR2"
    
    # Jugador 1
    player1 = Snake((MAP_WIDTH / 3, MAP_HEIGHT / 2), color1, name1_value, is_player=True, player_id=1)
    snakes.append(player1)
    
    # Jugador 2
    player2 = Snake((2 * MAP_WIDTH / 3, MAP_HEIGHT / 2), color2, name2_value, is_player=True, player_id=2)
    snakes.append(player2)

    # Agregar bots
    bot_colors = [
        (240, 120, 120),
        (120, 240, 140),
        (250, 210, 90),
        (180, 120, 250),
        (240, 90, 180),
        (120, 220, 230),
        (200, 190, 100),
        (140, 240, 170),
    ]
    for index in range(BOT_COUNT):
        pos = (
            random.uniform(120, MAP_WIDTH - 120),
            random.uniform(120, MAP_HEIGHT - 120),
        )
        snakes.append(Snake(pos, bot_colors[index % len(bot_colors)], f"BOT{index + 1}"))

    return snakes, player1, player2


def respawn_player(player):
    player.respawn()

def draw_tutorial(surface):

    surface.fill((20,20,30))

    title = TITLE_FONT.render("TUTORIAL", True, (255,255,255))
    surface.blit(title, (WINDOW_WIDTH//2 - 100, 80))

    lines = [
        "PlayOnline:",
        "Manejar jugador: Mouse",
        "Boost: Click",
        "",
        "Multiplayer:",
        "",
        "Jugador 1:",
        "Manejar jugador: Mouse",
        "Boost: Click",
        "",
        "Jugador 2:",
        "Manejar jugador: W A S D",
        "Boost: Espacio"
    ]

    y = 200
    for line in lines:
        text = FONT.render(line, True, (220,220,220))
        surface.blit(text, (WINDOW_WIDTH//2 - 200, y))
        y += 30

def main():
    menu_state = "main"
    nickname = ""
    selected_color = (180, 60, 240)
    selected_color_name = "Violeta"
    active_input = False
    snakes = []
    player = None
    running = True
    
    # Para multijugador
    player1_name = ""
    player1_color = (220, 50, 50)
    player1_color_name = "Rojo"
    player2_name = ""
    player2_color = (240, 205, 40)
    player2_color_name = "Amarillo"
    active_input_p1 = True
    player1 = None
    player2 = None
    
    # Para almacenar rectángulos del menú multijugador
    multiplayer_menu_rects = {"play": None, "back": None, "input": None}

    while running:
        dt = CLOCK.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if menu_state == "multiplayer_setup":
                        menu_state = "main"
                    else:
                        running = False
                elif menu_state == "main" and active_input:
                    if event.key == pygame.K_BACKSPACE:
                        nickname = nickname[:-1]
                    elif event.key == pygame.K_RETURN:
                        snakes, player = start_game(nickname, selected_color)
                        menu_state = "playing"
                        active_input = False
                    elif event.unicode.isprintable():
                        if len(nickname) < INPUT_MAX_LENGTH:
                            nickname += event.unicode
                elif menu_state == "multiplayer_setup":
                    if event.key == pygame.K_BACKSPACE and active_input_p1:
                        player1_name = player1_name[:-1]
                    elif event.key == pygame.K_RETURN:
                        pass  # Enter en el menú se maneja en click
                    elif active_input_p1 and event.unicode.isprintable():
                        if len(player1_name) < INPUT_MAX_LENGTH:
                            player1_name += event.unicode
                elif menu_state == "playing" and player is not None:
                    if event.key == pygame.K_r and not player.alive:
                        respawn_player(player)
                elif menu_state == "multiplayer":
                    if event.key == pygame.K_r:
                        if player1 is not None and not player1.alive:
                            player1.respawn()
                        if player2 is not None and not player2.alive:
                            player2.respawn()   

            elif event.type == pygame.MOUSEBUTTONDOWN:

                mouse_pos = event.pos

                if menu_state == "main":

                    if MENU_PLAY_RECT.collidepoint(mouse_pos):
                        snakes, player = start_game(nickname, selected_color)
                        menu_state = "playing"

                    elif MENU_MULTIPLAYER_RECT.collidepoint(mouse_pos):
                        menu_state = "multiplayer_setup"

                    elif MENU_TUTORIAL_RECT.collidepoint(mouse_pos):
                        menu_state = "tutorial"

                    elif MENU_WORM_RECT.collidepoint(mouse_pos):
                        menu_state = "color"


                elif menu_state == "color":

                    if MENU_EXIT_RECT.collidepoint(mouse_pos):
                        menu_state = "main"

                    else:
                        for index, position in enumerate(COLOR_CIRCLE_POSITIONS):
                            distance = Vector2(mouse_pos).distance_to(position)
                            if distance <= COLOR_CIRCLE_RADIUS:
                                selected_color, selected_color_name = COLOR_OPTIONS[index]
                                break


                elif menu_state == "tutorial":
                    menu_state = "main"


                elif menu_state == "multiplayer_setup":

                    if multiplayer_menu_rects["play"] and multiplayer_menu_rects["play"].collidepoint(mouse_pos):
                        if player1_name.strip():
                            if not player2_name.strip():
                                player2_name = "JUGADOR2"
                            snakes, player1, player2 = start_multiplayer_game(
                                player1_name, player1_color, player2_name, player2_color
                            )
                            menu_state = "multiplayer"

                    elif multiplayer_menu_rects["back"] and multiplayer_menu_rects["back"].collidepoint(mouse_pos):
                        menu_state = "main"

                    elif multiplayer_menu_rects["input"] and multiplayer_menu_rects["input"].collidepoint(mouse_pos):
                        active_input_p1 = True

                    else:
                        active_input_p1 = False
                    else:
                    for index, position in enumerate(COLOR_CIRCLE_POSITIONS):
                            distance = Vector2(mouse_pos).distance_to(position)
                            if distance <= COLOR_CIRCLE_RADIUS:
                                selected_color, selected_color_name = COLOR_OPTIONS[index]
                                break
                elif menu_state == "multiplayer_setup":
                    mouse_pos = event.pos
                    if multiplayer_menu_rects["play"] and multiplayer_menu_rects["play"].collidepoint(mouse_pos):
                        if player1_name.strip():
                            # Si player2_name está vacío, usar un nombre por defecto
                            if not player2_name.strip():
                                player2_name = "JUGADOR2"
                            snakes, player1, player2 = start_multiplayer_game(player1_name, player1_color, player2_name, player2_color)
                            menu_state = "multiplayer"
                    elif multiplayer_menu_rects["back"] and multiplayer_menu_rects["back"].collidepoint(mouse_pos):
                        menu_state = "main"
                    elif multiplayer_menu_rects["input"] and multiplayer_menu_rects["input"].collidepoint(mouse_pos):
                        active_input_p1 = True
                    else:
                        active_input_p1 = False
                elif menu_state == "tutorial":
                    draw_tutorial(SCREEN)

        if menu_state == "playing":
            if random.random() < ORB_SPAWN_CHANCE and len(world_orbs) < MAX_ORBS:
                spawn_random_orb()

            for snake in snakes:
                snake.update(dt, world_orbs, snakes)

            for snake in snakes:
                snake.check_death_collision(snakes, world_orbs)

            for snake in snakes:
                if not snake.alive and not snake.is_player and snake.respawn_timer <= 0:
                    snake.respawn()

            if player is not None and player.alive:
                camera_offset = player.head - Vector2(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
            else:
                camera_offset = Vector2(MAP_WIDTH / 2 - WINDOW_WIDTH / 2, MAP_HEIGHT / 2 - WINDOW_HEIGHT / 2)

            draw_background(SCREEN, camera_offset)

            for orb in world_orbs:
                orb.draw(SCREEN, camera_offset)

            for snake in snakes:
                snake.draw(SCREEN, camera_offset)

            if player is not None:
                draw_ui(SCREEN, player, snakes)
        elif menu_state == "multiplayer":
            if random.random() < ORB_SPAWN_CHANCE and len(world_orbs) < MAX_ORBS:
                spawn_random_orb()

            for snake in snakes:
                snake.update(dt, world_orbs, snakes)

            for snake in snakes:
                snake.check_death_collision(snakes, world_orbs)

            for snake in snakes:
                if not snake.alive and not snake.is_player and snake.respawn_timer <= 0:
                    snake.respawn()

            if player1 is not None and player2 is not None:
                draw_split_screen(SCREEN, player1, player2, snakes, world_orbs)
        elif menu_state == "main":
            draw_main_menu(SCREEN, active_input, nickname, selected_color_name)
        elif menu_state == "color":
            draw_color_menu(SCREEN, selected_color)
        elif menu_state == "multiplayer_setup":
            play_rect, back_rect, p1_input_rect = draw_multiplayer_menu(
                SCREEN, player1_name, player1_color_name, player2_name, player2_color_name, active_input_p1
            )
            multiplayer_menu_rects["play"] = play_rect
            multiplayer_menu_rects["back"] = back_rect
            multiplayer_menu_rects["input"] = p1_input_rect

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

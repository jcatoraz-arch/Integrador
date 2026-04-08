import math
import random
import sys

import pygame
from pygame.math import Vector2

WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
FPS = 60
MAP_WIDTH = 4000
MAP_HEIGHT = 4000
INITIAL_ORBS = 220
BOT_COUNT = 8
ORB_SPAWN_CHANCE = 0.02
MAX_ORBS = 260

COLOR_BG = (16, 16, 24)
COLOR_GRID = (30, 30, 40)
COLOR_TEXT = (240, 240, 240)
COLOR_ORB = (130, 240, 160)
COLOR_DEAD = (120, 120, 120)

pygame.init()
pygame.display.set_caption("Slither.io estilo Python")
FONT = pygame.font.SysFont("consolas", 18)
TITLE_FONT = pygame.font.SysFont("consolas", 32, bold=True)
SCREEN = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
CLOCK = pygame.time.Clock()


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
    def __init__(self, pos, color, name, is_player=False):
        self.head = Vector2(pos)
        self.direction = Vector2(1, 0)
        self.color = color
        self.name = name
        self.is_player = is_player
        self.mass = 35.0
        self.alive = True
        self.path = [Vector2(self.head)]
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
            lost = 18.0 * dt
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

    def update_player(self, dt):
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

        if self.mass > 38 and self.head.distance_to(self.target or self.head) > 120 and random.random() < 0.012:
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
                self.mass += orb.mass * 0.9
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

    def get_body_points(self):
        points = []
        if len(self.path) < 2:
            return points
        spacing = max(8, self.radius * 0.7)
        needed = int(self.mass * 1.4) + 18
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
                color = [
                    int(lerp(self.color[c], COLOR_DEAD[c], 0.18 + 0.6 * ratio))
                    for c in range(3)
                ]
                pygame.draw.circle(surface, color, point - camera_offset, radius)

        head_pos = self.head - camera_offset
        pygame.draw.circle(surface, self.color, head_pos, self.radius)
        eye_direction = self.direction.normalize() if self.direction.length_squared() > 0.01 else Vector2(1, 0)
        eye_offset = eye_direction * (self.radius * 0.4)
        eye_center = head_pos + eye_offset
        pygame.draw.circle(surface, (255, 255, 255), eye_center, max(3, self.radius // 5))
        pygame.draw.circle(surface, (30, 30, 40), eye_center, max(2, self.radius // 8))

    def check_death_collision(self, snakes, orbs):
        if not self.alive:
            return
        for other in snakes:
            if other is self or not other.alive:
                continue
            body_points = other.get_body_points()[5:]
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
        for _ in range(pieces):
            orb_mass = max(1.0, min(8.0, random.gauss(total_mass / pieces, 1.4)))
            if path_points:
                base_point = random.choice(path_points)
            else:
                base_point = self.head
            offset = Vector2(random.uniform(-28, 28), random.uniform(-28, 28))
            drop_pos = base_point + offset
            drop_pos.x = clamp(drop_pos.x, 0, MAP_WIDTH)
            drop_pos.y = clamp(drop_pos.y, 0, MAP_HEIGHT)
            orbs.append(Orb(drop_pos, orb_mass))

    def respawn(self):
        self.alive = True
        self.mass = 28.0
        self.head = Vector2(random.uniform(200, MAP_WIDTH - 200), random.uniform(200, MAP_HEIGHT - 200))
        self.path = [Vector2(self.head)]
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
    surface.fill(COLOR_BG)
    grid_size = 200
    start_x = int((camera_offset.x // grid_size) * grid_size - camera_offset.x)
    start_y = int((camera_offset.y // grid_size) * grid_size - camera_offset.y)
    for x in range(start_x, WINDOW_WIDTH + grid_size, grid_size):
        pygame.draw.line(surface, COLOR_GRID, (x, 0), (x, WINDOW_HEIGHT))
    for y in range(start_y, WINDOW_HEIGHT + grid_size, grid_size):
        pygame.draw.line(surface, COLOR_GRID, (0, y), (WINDOW_WIDTH, y))

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

    if not player.alive:
        msg = "Has muerto. Presiona R para reaparecer." if player.respawn_timer >= 0 else ""
        rendered = TITLE_FONT.render(msg, True, (255, 120, 120))
        rect = rendered.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
        surface.blit(rendered, rect)


def respawn_player(player):
    player.respawn()


def main():
    spawn_initial_orbs()
    snakes = []
    player = Snake((MAP_WIDTH / 2, MAP_HEIGHT / 2), (80, 190, 250), "JUGADOR", is_player=True)
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

    running = True
    while running:
        dt = CLOCK.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r and not player.alive:
                    respawn_player(player)

        if random.random() < ORB_SPAWN_CHANCE and len(world_orbs) < MAX_ORBS:
            spawn_random_orb()

        for snake in snakes:
            snake.update(dt, world_orbs, snakes)

        for snake in snakes:
            snake.check_death_collision(snakes, world_orbs)

        for snake in snakes:
            if not snake.alive and not snake.is_player and snake.respawn_timer <= 0:
                snake.respawn()

        if player.alive:
            camera_offset = player.head - Vector2(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
        else:
            camera_offset = Vector2(MAP_WIDTH / 2 - WINDOW_WIDTH / 2, MAP_HEIGHT / 2 - WINDOW_HEIGHT / 2)

        draw_background(SCREEN, camera_offset)

        for orb in world_orbs:
            orb.draw(SCREEN, camera_offset)

        for snake in snakes:
            snake.draw(SCREEN, camera_offset)

        draw_ui(SCREEN, player, snakes)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

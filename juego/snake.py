import random
import math
from collections import deque
from pygame.math import Vector2

import constants as c

class Snake:
    def __init__(self, identity, position, color, is_player=False):
        self.id = identity
        self.color = color
        self.is_player = is_player
        self.alive = True
        self.head = Vector2(position)
        self.direction = Vector2(1, 0)
        self.mass = c.SNAKE_INITIAL_MASS
        self.history = deque([Vector2(self.head)], maxlen=1600)
        self.body_positions = []
        self.boosting = False
        self.acceleration = 0.0
        self.target_mass = self.mass
        self.respawn_timer = 0.0
        self.navigation_timer = 0.0
        self.wander_target = Vector2(position)

    @property
    def radius(self):
        return max(8, int(self.mass * 0.35))

    @property
    def length(self):
        return int(max(10, self.mass))

    def get_speed(self):
        base = c.SNAKE_BASE_SPEED + self.mass * 0.12
        return base * (c.SNAKE_BOOST_MULTIPLIER if self.boosting else 1.0)

    def update(self, dt, world_size, target_point=None, orbs=None):
        if not self.alive:
            return []

        if self.is_player and target_point is not None:
            direction = target_point - self.head
            if direction.length_squared() > 1:
                self.direction = direction.normalize()
        else:
            self._update_ai(dt, orbs)

        self.boosting = self.boosting and self.mass > c.SNAKE_MIN_MASS
        self._move(dt, world_size)
        self._update_mass(dt)
        self._update_body()
        return self._maybe_boost_orb(dt)

    def _update_ai(self, dt, orbs):
        self.navigation_timer -= dt
        if not orbs or self.navigation_timer <= 0:
            self.navigation_timer = random.uniform(1.2, 2.6)
            if orbs:
                nearest = min(orbs, key=lambda orb: orb.position.distance_squared_to(self.head))
                self.wander_target = Vector2(nearest.position)
            else:
                self.wander_target = self.head + Vector2(random.uniform(-1, 1), random.uniform(-1, 1)) * 400.0

        desired = self.wander_target - self.head
        if desired.length_squared() > 1:
            desired = desired.normalize()
            self.direction = self.direction.lerp(desired, 0.04).normalize()

        self.boosting = random.random() < 0.008 and self.mass > 18.0

    def _move(self, dt, world_size):
        speed = self.get_speed()
        move_vector = self.direction * speed * dt
        self.head += move_vector
        self.head.x = max(0, min(world_size[0], self.head.x))
        self.head.y = max(0, min(world_size[1], self.head.y))
        self.history.appendleft(Vector2(self.head))

    def _update_mass(self, dt):
        if self.boosting:
            self.mass -= c.SNAKE_MASS_LOSS_BOOST * dt
        else:
            self.mass -= c.SNAKE_MASS_DECAY * dt * 0.08
        self.mass = min(max(self.mass, c.SNAKE_MIN_MASS), c.SNAKE_MAX_MASS)

    def _update_body(self):
        positions = []
        spacing = c.SNAKE_SEGMENT_DISTANCE
        index = 0
        last = self.history[0]
        traveled = 0.0
        while len(positions) < self.length and index + 1 < len(self.history):
            current = self.history[index + 1]
            traveled += last.distance_to(current)
            if traveled >= spacing:
                positions.append(Vector2(current))
                last = current
                traveled = 0.0
            index += 1
        self.body_positions = positions

    def _maybe_boost_orb(self, dt):
        if self.boosting and self.mass > c.SNAKE_MIN_MASS + 2.0:
            self.acceleration += dt * 24.0
            if self.acceleration >= 6.0:
                self.acceleration = 0.0
                return [Vector2(self.head - self.direction * (self.radius + 6))]
        return []

    def draw(self, surface, camera_offset):
        offset_head = self.head - camera_offset
        colors = self._segment_colors()
        for idx, pos in enumerate(self.body_positions):
            screen_pos = pos - camera_offset
            if idx >= len(colors):
                break
            radius = max(4, int(self.radius * (1.0 - idx / max(16.0, len(self.body_positions)))))
            pygame.draw.circle(surface, colors[idx], (int(screen_pos.x), int(screen_pos.y)), radius)

        head_color = self.color if self.alive else c.COLOR_DEAD
        pygame.draw.circle(surface, head_color, (int(offset_head.x), int(offset_head.y)), self.radius)
        eye_offset = self.direction.rotate(90) * (self.radius * 0.35)
        eye_dir = self.direction * (self.radius * 0.55)
        left_eye = offset_head + eye_dir + eye_offset
        right_eye = offset_head + eye_dir - eye_offset
        pygame.draw.circle(surface, (255, 255, 255), (int(left_eye.x), int(left_eye.y)), max(2, self.radius // 5))
        pygame.draw.circle(surface, (255, 255, 255), (int(right_eye.x), int(right_eye.y)), max(2, self.radius // 5))

    def _segment_colors(self):
        gradient = []
        base = self.color
        length = len(self.body_positions)
        for i in range(length):
            t = i / max(1, length - 1)
            r = int(base[0] * (1 - t) + 20 * t)
            g = int(base[1] * (1 - t) + 24 * t)
            b = int(base[2] * (1 - t) + 42 * t)
            gradient.append((r, g, b))
        return gradient

    def eat_orb(self, orb):
        self.mass += orb.mass * 1.3
        self.mass = min(self.mass, c.SNAKE_MAX_MASS)

    def die(self):
        self.alive = False
        return [Vector2(p) for p in self.body_positions] + [Vector2(self.head)]

    def reset(self, position):
        self.head = Vector2(position)
        self.history = deque([Vector2(self.head)], maxlen=1600)
        self.body_positions = []
        self.mass = c.SNAKE_INITIAL_MASS
        self.direction = Vector2(1, 0)
        self.alive = True
        self.boosting = False

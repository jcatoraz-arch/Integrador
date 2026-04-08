from pygame.math import Vector2
import random

from constants import ORB_MIN_MASS, ORB_MAX_MASS, COLOR_ORB

class Orb:
    def __init__(self, position, mass=None):
        self.position = Vector2(position)
        self.mass = mass if mass is not None else random.uniform(ORB_MIN_MASS, ORB_MAX_MASS)
        self.radius = max(3, int(self.mass * 1.4))
        self.color = COLOR_ORB

    def draw(self, surface, camera_offset):
        screen_pos = self.position - camera_offset
        pygame.draw.circle(surface, self.color, (int(screen_pos.x), int(screen_pos.y)), self.radius)

    def get_hitbox(self):
        return self.position, self.radius

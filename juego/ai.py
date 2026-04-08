import math
import random
from constants import *

class AISnakeController:
    def __init__(self, snake):
        self.snake = snake
        self.target_food = None
        self.avoid_target = None
        self.update_timer = 0

    def update(self, foods, snakes):
        self.update_timer += 1
        if self.update_timer < AI_UPDATE_RATE:
            return

        self.update_timer = 0

        # Find nearest food
        nearest_food = None
        nearest_dist = float('inf')

        for food in foods:
            dist = math.hypot(food.x - self.snake.x, food.y - self.snake.y)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_food = food

        self.target_food = nearest_food

        # Avoid larger snakes
        self.avoid_target = None
        for other_snake in snakes:
            if other_snake != self.snake and other_snake.alive:
                if other_snake.mass > self.snake.mass * 1.2:  # Avoid much larger snakes
                    dist = math.hypot(other_snake.x - self.snake.x, other_snake.y - self.snake.y)
                    if dist < 200:  # Within danger zone
                        self.avoid_target = other_snake
                        break

        # Set target angle
        if self.avoid_target:
            # Move away from threat
            dx = self.snake.x - self.avoid_target.x
            dy = self.snake.y - self.avoid_target.y
            self.snake.target_angle = math.atan2(dy, dx)
        elif self.target_food:
            # Move towards food
            dx = self.target_food.x - self.snake.x
            dy = self.target_food.y - self.snake.y
            self.snake.target_angle = math.atan2(dy, dx)
        else:
            # Random movement
            self.snake.target_angle += random.uniform(-0.5, 0.5)

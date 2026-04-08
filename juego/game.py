import pygame
import random
import sys
from constants import *
from snake import Snake
from food import Food
from ai import AISnakeController

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Slither.io Style Game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, FONT_SIZE)

        self.reset_game()

    def reset_game(self):
        # Create player snake
        self.player = Snake(WORLD_WIDTH // 2, WORLD_HEIGHT // 2, GREEN, is_player=True)

        # Create AI snakes
        self.ai_snakes = []
        self.ai_controllers = []
        colors = [RED, BLUE, YELLOW, PURPLE, ORANGE, PINK, CYAN, WHITE]
        for i in range(AI_COUNT):
            x = random.randint(100, WORLD_WIDTH - 100)
            y = random.randint(100, WORLD_HEIGHT - 100)
            color = random.choice(colors)
            snake = Snake(x, y, color)
            self.ai_snakes.append(snake)
            self.ai_controllers.append(AISnakeController(snake))

        # All snakes
        self.all_snakes = [self.player] + self.ai_snakes

        # Food
        self.foods = []
        for _ in range(FOOD_COUNT):
            self.foods.append(Food())

        # Camera
        self.camera_x = self.player.x - SCREEN_WIDTH // 2
        self.camera_y = self.player.y - SCREEN_HEIGHT // 2

        # Game state
        self.game_over = False
        self.score = 0

    def update(self):
        if self.game_over:
            return

        # Get mouse position for player control
        mouse_pos = pygame.mouse.get_pos()

        # Update player
        self.player.update(mouse_pos, self.camera_x, self.camera_y)

        # Update AI snakes
        for controller, snake in zip(self.ai_controllers, self.ai_snakes):
            if snake.alive:
                controller.update(self.foods, self.all_snakes)
                snake.update()

        # Check food collisions
        for snake in self.all_snakes:
            if snake.alive:
                eaten = snake.check_collision_with_food(self.foods)
                for food in eaten:
                    self.foods.remove(food)
                    snake.mass += MASS_PER_FOOD
                    if snake == self.player:
                        self.score += 1

        # Check snake collisions
        for snake in self.all_snakes:
            if snake.alive:
                head_rect = snake.get_head_rect()

                # Check collision with other snakes' bodies
                for other_snake in self.all_snakes:
                    if other_snake.alive and other_snake != snake:
                        body_rects = other_snake.get_body_rects()
                        for body_rect in body_rects:
                            if head_rect.colliderect(body_rect):
                                # Snake dies
                                food_positions = snake.die()
                                for pos in food_positions:
                                    self.foods.append(Food(pos[0], pos[1]))
                                break
                        if not snake.alive:
                            break

        # Respawn food
        while len(self.foods) < FOOD_COUNT:
            self.foods.append(Food())

        # Update camera to follow player
        target_x = self.player.x - SCREEN_WIDTH // 2
        target_y = self.player.y - SCREEN_HEIGHT // 2

        self.camera_x += (target_x - self.camera_x) * CAMERA_SMOOTHING
        self.camera_y += (target_y - self.camera_y) * CAMERA_SMOOTHING

        # Keep camera within world bounds
        self.camera_x = max(0, min(WORLD_WIDTH - SCREEN_WIDTH, self.camera_x))
        self.camera_y = max(0, min(WORLD_HEIGHT - SCREEN_HEIGHT, self.camera_y))

        # Check game over
        if not self.player.alive:
            self.game_over = True

    def draw(self):
        self.screen.fill(BLACK)

        # Draw world bounds (optional grid)
        for x in range(0, WORLD_WIDTH, 100):
            screen_x = x - self.camera_x
            if 0 <= screen_x <= SCREEN_WIDTH:
                pygame.draw.line(self.screen, (50, 50, 50),
                               (screen_x, 0), (screen_x, SCREEN_HEIGHT))

        for y in range(0, WORLD_HEIGHT, 100):
            screen_y = y - self.camera_y
            if 0 <= screen_y <= SCREEN_HEIGHT:
                pygame.draw.line(self.screen, (50, 50, 50),
                               (0, screen_y), (SCREEN_WIDTH, screen_y))

        # Draw food
        for food in self.foods:
            food.draw(self.screen, self.camera_x, self.camera_y)

        # Draw snakes
        for snake in self.all_snakes:
            snake.draw(self.screen, self.camera_x, self.camera_y)

        # Draw UI
        self.draw_ui()

        pygame.display.flip()

    def draw_ui(self):
        # Score
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))

        # Mass
        mass_text = self.font.render(f"Mass: {int(self.player.mass)}", True, WHITE)
        self.screen.blit(mass_text, (10, 40))

        # Length
        length_text = self.font.render(f"Length: {len(self.player.body)}", True, WHITE)
        self.screen.blit(length_text, (10, 70))

        # Leaderboard
        self.draw_leaderboard()

        # Game over screen
        if self.game_over:
            game_over_text = self.font.render("GAME OVER - Press R to restart", True, RED)
            text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(game_over_text, text_rect)

    def draw_leaderboard(self):
        # Sort snakes by mass
        sorted_snakes = sorted([s for s in self.all_snakes if s.alive],
                              key=lambda s: s.mass, reverse=True)

        leaderboard_text = self.font.render("Leaderboard:", True, WHITE)
        self.screen.blit(leaderboard_text, (SCREEN_WIDTH - 200, 10))

        for i, snake in enumerate(sorted_snakes[:LEADERBOARD_SIZE]):
            color_name = "YOU" if snake.is_player else f"AI {i+1}"
            text = self.font.render(f"{i+1}. {color_name}: {int(snake.mass)}", True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH - 200, 40 + i * 30))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and self.game_over:
                    self.reset_game()
                elif event.key == pygame.K_ESCAPE:
                    return False
        return True

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

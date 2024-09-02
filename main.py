import pygame
import sys
import math
import random
import asyncio

pygame.init()

# Constants
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 800
INITIAL_BALL_SPAWN_INTERVAL = 700  # Initial milliseconds between ball spawns, reduced by 30%
SOYBEAN_SPAWN_INTERVAL = 5000  # Milliseconds between soybean spawns
SOYBEAN_LIFETIME = 3000  # Milliseconds before a soybean disappears

# Define custom events for spawning balls and soybeans
SPAWN_BALL_EVENT = pygame.USEREVENT + 1
SPAWN_SOYBEAN_EVENT = pygame.USEREVENT + 2

# Set timers for ball and soybean spawns
pygame.time.set_timer(SPAWN_BALL_EVENT, INITIAL_BALL_SPAWN_INTERVAL)
pygame.time.set_timer(SPAWN_SOYBEAN_EVENT, SOYBEAN_SPAWN_INTERVAL)

# Initialize Pygame's mixer for MIDI music
pygame.mixer.init()

# Arrow class to handle shooting in a specified direction
class Arrow(pygame.sprite.Sprite):
    def __init__(self, x, y, angle):
        super().__init__()
        self.image = pygame.image.load("assets/arrow.png").convert_alpha()  # Load arrow PNG image
        self.image = pygame.transform.rotate(self.image, -angle)  # Rotate the image based on the angle
        self.image = pygame.transform.scale(self.image, (20, 20))  # Scale the image if necessary
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 10

        # Calculate the direction vector based on the angle
        rad_angle = math.radians(angle)
        self.dx = math.cos(rad_angle) * self.speed
        self.dy = -math.sin(rad_angle) * self.speed  # Negative because pygame's y-axis increases downwards

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy

        # Remove the arrow if it goes off the screen
        if (self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT or
            self.rect.left > SCREEN_WIDTH or self.rect.right < 0):
            self.kill()

# Player class to handle movement, shooting, and health
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, image):
        super().__init__()
        self.image = pygame.transform.scale(image, (100, 100))  # Scale the image if necessary
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 5
        self.arrows = pygame.sprite.Group()  # Group to hold arrows
        self.hp = 7  # Reduced player health to make the game harder

    def update(self, keys):
        # Move the player freely
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rect.x += self.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.rect.y += self.speed

        # Keep player within the screen bounds
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

    def shoot(self, angle):
        arrow = Arrow(self.rect.centerx, self.rect.centery, angle)
        self.arrows.add(arrow)

    def reduce_hp(self):
        self.hp -= 1

    def increase_hp(self):
        if self.hp < 10:  # Cap the health at 10
            self.hp += 1

# Ball class to create balls moving towards the center
class Ball(pygame.sprite.Sprite):
    def __init__(self, x, y, target_x, target_y, image):
        super().__init__()
        self.image = pygame.transform.scale(image, (40, 40))  # Scale the image if necessary
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = random.uniform(2.6, 7.8)  # 30% increase in initial speed range

        # Calculate direction vector towards the target (center of the screen)
        dx = target_x - x
        dy = target_y - y
        distance = math.hypot(dx, dy)  # Euclidean distance

        if distance == 0:
            self.dx = 0
            self.dy = 0
        else:
            self.dx = (dx / distance) * self.speed  # Normalize and apply speed
            self.dy = (dy / distance) * self.speed

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy

        # Remove the ball if it moves beyond the screen boundaries
        if (self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or
            self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT):
            self.kill()

# Soybean class to handle the healing items
class Soybean(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.image.load("assets/soybean.png").convert_alpha()  # Load the soybean image
        self.image = pygame.transform.scale(self.image, (50, 50))  # Resize if necessary
        self.rect = self.image.get_rect(center=(x, y))
        self.spawn_time = pygame.time.get_ticks()

    def draw_aura(self, surface):
        # Calculate aura transparency based on time (pulsing effect)
        time_elapsed = pygame.time.get_ticks() - self.spawn_time
        alpha = 128 + 127 * math.sin(time_elapsed * 0.005)  # Alpha oscillates between 1 and 255

        # Create an aura surface with varying transparency
        aura_radius = 40
        aura_color = (0, 255, 0, alpha)  # Green with varying transparency
        aura_surface = pygame.Surface((aura_radius * 2, aura_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(aura_surface, aura_color, (aura_radius, aura_radius), aura_radius)
        surface.blit(aura_surface, (self.rect.centerx - aura_radius, self.rect.centery - aura_radius))

    def update(self):
        # Disappear after 3 seconds
        if pygame.time.get_ticks() - self.spawn_time > SOYBEAN_LIFETIME:
            self.kill()

class Boss(pygame.sprite.Sprite):
    def __init__(self, x, y, image, health=100):
        super().__init__()
        self.image = pygame.transform.scale(image, (200, 200))  # Use the boss image
        self.rect = self.image.get_rect(center=(x, y))
        self.health = health
        self.shoot_cooldown = 2000  # Milliseconds between shots
        self.last_shot_time = pygame.time.get_ticks()

    def update(self, player, balls_group, ball_image):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_shot_time >= self.shoot_cooldown:
            self.shoot(player.rect.center, balls_group, ball_image)
            self.last_shot_time = current_time

    def shoot(self, target_pos, balls_group, ball_image):
        for _ in range(5):  # Boss shoots 5 balls at once
            ball = Ball(self.rect.centerx, self.rect.centery, target_pos[0], target_pos[1], ball_image)
            balls_group.add(ball)

    def reduce_health(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.kill()

# Game class to manage the game loop
class Game:
    def __init__(self, width=SCREEN_WIDTH, height=SCREEN_HEIGHT):
        self.screen_width = width
        self.screen_height = height
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("SoyBoyz Adventure")

        self.clock = pygame.time.Clock()
        self.running = True

        self.levels = [20, 35, 60, 100]  # Balls to destroy for each level
        self.current_level = 0
        self.balls_destroyed = 0
        self.total_balls_needed = self.levels[self.current_level]
        self.progress_bar_length = 200

        # Load player images for each level
        self.player_images = [
            pygame.image.load("assets/player_level1.png").convert_alpha(),
            pygame.image.load("assets/player_level2.png").convert_alpha(),
            pygame.image.load("assets/player_level3.png").convert_alpha(),
            pygame.image.load("assets/player_level4.png").convert_alpha()
        ]

        # Load the ball and boss images
        self.ball_image = pygame.image.load("assets/ball.png").convert_alpha()
        self.boss_image = pygame.image.load("assets/boss.png").convert_alpha()  # Load boss image

        # Load and scale the pointer images for each player
        self.pointer_images = [
            pygame.transform.scale(pygame.image.load("assets/pointer1.png").convert_alpha(), (50, 50)),
            pygame.transform.scale(pygame.image.load("assets/pointer2.png").convert_alpha(), (30, 70)),
            pygame.transform.scale(pygame.image.load("assets/pointer3.png").convert_alpha(), (70, 30)),
            pygame.transform.scale(pygame.image.load("assets/pointer4.png").convert_alpha(), (60, 60))
        ]

        # Load the sound for catching soybeans
        self.catch_sound = pygame.mixer.Sound("assets/catch_sound.mp3")  # Load sound effect
        self.catch_sound.set_volume(0.2)

        # Initialize player with the first image and corresponding pointer
        self.player = Player(self.screen_width // 2, self.screen_height // 2, self.player_images[0])
        self.all_sprites = pygame.sprite.Group()
        self.all_sprites.add(self.player)

        self.balls = pygame.sprite.Group()
        self.soybeans = pygame.sprite.Group()

        # Font for displaying text
        self.font = pygame.font.SysFont(None, 48)
        self.button_font = pygame.font.SysFont(None, 36)

        # Set the initial spawn interval and speed range
        self.spawn_interval = INITIAL_BALL_SPAWN_INTERVAL
        self.min_ball_speed = 2.6
        self.max_ball_speed = 7.8

    def main_menu(self):
        while True:
            self.screen.fill((0, 0, 0))

            # Display the title
            title_text = self.font.render("SoyBoyz Adventure", True, (255, 255, 255))
            self.screen.blit(title_text, (self.screen_width // 2 - title_text.get_width() // 2, 150))

            # Create Play and Exit buttons
            play_button = pygame.Rect(self.screen_width // 2 - 100, 300, 200, 50)
            exit_button = pygame.Rect(self.screen_width // 2 - 100, 400, 200, 50)

            pygame.draw.rect(self.screen, (0, 255, 0), play_button)
            pygame.draw.rect(self.screen, (255, 0, 0), exit_button)

            play_text = self.button_font.render("Play", True, (0, 0, 0))
            exit_text = self.button_font.render("Exit", True, (0, 0, 0))

            self.screen.blit(play_text, (play_button.centerx - play_text.get_width() // 2, play_button.centery - play_text.get_height() // 2))
            self.screen.blit(exit_text, (exit_button.centerx - exit_text.get_width() // 2, exit_button.centery - exit_text.get_height() // 2))

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if play_button.collidepoint(event.pos):
                        self.reset_game()  # Reset the game state
                        return  # Exit the menu and start the game
                    elif exit_button.collidepoint(event.pos):
                        pygame.quit()
                        sys.exit()

    def reset_game(self):
        # Reset player HP and position
        self.player.hp = 7  # Reset HP to the initial value
        self.player.rect.center = (self.screen_width // 2, self.screen_height // 2)

        # Reset player image to the first image
        self.player.image = pygame.transform.scale(self.player_images[0], (100, 100))
        self.player.rect = self.player.image.get_rect(center=self.player.rect.center)

        # Reset level and ball count
        self.current_level = 0
        self.balls_destroyed = 0
        self.total_balls_needed = self.levels[self.current_level]

        # Clear all sprites and restart with initial conditions
        self.all_sprites.empty()
        self.balls.empty()
        self.soybeans.empty()
        self.all_sprites.add(self.player)

        # Remove the boss if it existed
        if hasattr(self, 'boss'):
            del self.boss

        # Reset progress bar
        self.progress_bar_length = 0

        # Reset timers and difficulty settings
        self.spawn_interval = INITIAL_BALL_SPAWN_INTERVAL
        pygame.time.set_timer(SPAWN_BALL_EVENT, self.spawn_interval)
        self.min_ball_speed = 2.6  # Reset to initial speed
        self.max_ball_speed = 7.8

    def play_music(self):
        pygame.mixer.music.load("assets/quarta_passada.mid")  # Replace with your MIDI file's path
        pygame.mixer.music.play(-1)  # Loop the music

    def spawn_ball(self):
        edge_positions = [
            (random.randint(0, self.screen_width), 0),  # Top edge
            (random.randint(0, self.screen_width), self.screen_height),  # Bottom edge
            (0, random.randint(0, self.screen_height)),  # Left edge
            (self.screen_width, random.randint(0, self.screen_height))  # Right edge
        ]
        x, y = random.choice(edge_positions)

        ball = Ball(x, y, self.screen_width // 2, self.screen_height // 2, self.ball_image)  # Use the same image for all balls
        ball.speed = random.uniform(self.min_ball_speed, self.max_ball_speed)
        self.balls.add(ball)
        self.all_sprites.add(ball)

    def spawn_soybean(self):
        x = random.randint(20, self.screen_width - 20)
        y = random.randint(20, self.screen_height - 20)
        soybean = Soybean(x, y)
        self.soybeans.add(soybean)
        self.all_sprites.add(soybean)

    async def run(self):
        self.main_menu()  # Display the main menu before starting the game
        self.play_music()  # Start playing the MIDI music

        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)  # Maintain 60 FPS

        await asyncio.sleep(0)

        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == SPAWN_BALL_EVENT:
                self.spawn_ball()
            elif event.type == SPAWN_SOYBEAN_EVENT:
                self.spawn_soybean()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                angle = self.get_angle_to_mouse()
                self.player.shoot(angle)

    def display_lose_message(self):
        self.screen.fill((0, 0, 0))
        lose_text = self.font.render("You Lose", True, (255, 0, 0))
        self.screen.blit(lose_text, (self.screen_width // 2 - lose_text.get_width() // 2, self.screen_height // 2 - lose_text.get_height() // 2))
        pygame.display.flip()
        pygame.time.wait(5000)  # Wait for 5 seconds
        self.reset_game()  # Reset the game state
        self.main_menu()  # Go back to the main menu

    def update(self):
        keys = pygame.key.get_pressed()
        self.player.update(keys)
        self.player.arrows.update()
        self.balls.update()
        self.soybeans.update()

        # Boss attacks during the final level
        if hasattr(self, 'boss') and self.boss.alive():
            self.boss.update(self.player, self.balls, self.ball_image)

            # Check if player's arrows hit the boss
            boss_hit = pygame.sprite.spritecollide(self.boss, self.player.arrows, True)
            if boss_hit:
                self.boss.reduce_health(5)  # Reduce boss health when hit

            # Check if the boss is defeated
            if not self.boss.alive():
                self.display_win_message()

        # Handle other collisions and level progress as before
        # Check for collisions between arrows and balls
        collisions = pygame.sprite.groupcollide(self.balls, self.player.arrows, True, True)
        if collisions:
            destroyed = sum(len(v) for v in collisions.values())
            self.balls_destroyed += destroyed
            self.update_progress_bar()

        # Check for collisions between the player and balls
        if pygame.sprite.spritecollide(self.player, self.balls, True):
            self.player.reduce_hp()
            if self.player.hp <= 0:
                self.display_lose_message()  # Call the lose message display function
                return  # Exit the update method to stop further updates

        # Check for collisions between the player and soybeans
        if pygame.sprite.spritecollide(self.player, self.soybeans, True):
            self.catch_sound.play()  # Play the catch sound effect
            self.player.increase_hp()

        # Check if the level is complete
        if self.balls_destroyed >= self.total_balls_needed and not hasattr(self, 'boss'):
            self.next_level()

    def update_progress_bar(self):
        progress = self.balls_destroyed / self.total_balls_needed
        self.progress_bar_length = 200 * min(progress, 1)  # Ensure it doesn't exceed 200

    def start_boss_level(self):
        self.boss = Boss(self.screen_width // 2, self.screen_height // 4, self.boss_image, health=100)  # Correct image used here
        self.all_sprites.add(self.boss)
        print("Boss level started!")

    def next_level(self):
        self.current_level += 1
        if self.current_level < len(self.levels):
            # Normal levels
            self.total_balls_needed = self.levels[self.current_level]
            self.balls_destroyed = 0
            self.progress_bar_length = 0

            # Increase difficulty for the next level
            self.spawn_interval = max(140, int(self.spawn_interval * 0.7))  # 30% faster spawns
            pygame.time.set_timer(SPAWN_BALL_EVENT, self.spawn_interval)
            self.min_ball_speed *= 1.3  # Increase minimum ball speed by 30%
            self.max_ball_speed *= 1.3  # Increase maximum ball speed by 30%

            # Update player's image for the next level
            self.player.image = pygame.transform.scale(self.player_images[self.current_level], (100, 100))
            self.player.rect = self.player.image.get_rect(center=self.player.rect.center)

            print(f"Level {self.current_level + 1} started! Destroy {self.total_balls_needed} balls.")
        else:
            # Final level with the boss
            self.start_boss_level()

    def display_win_message(self):
        self.screen.fill((0, 0, 0))
        win_text = self.font.render("You Won!", True, (255, 255, 255))
        self.screen.blit(win_text, (self.screen_width // 2 - win_text.get_width() // 2, self.screen_height // 2 - win_text.get_height() // 2))
        pygame.display.flip()
        pygame.time.wait(5000)  # Wait for 5 seconds
        self.reset_game()  # Reset the game state
        self.main_menu()  # Go back to the main menu

    def get_angle_to_mouse(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        rel_x, rel_y = mouse_x - self.player.rect.centerx, mouse_y - self.player.rect.centery
        angle = math.degrees(math.atan2(-rel_y, rel_x))  # Negative because pygame's y-axis increases downwards
        return angle

    def draw(self):
        self.screen.fill((0, 0, 0))  # Clear screen with black

        # Draw auras for soybeans
        for sprite in self.all_sprites:
            if isinstance(sprite, Soybean):
                sprite.draw_aura(self.screen)

        # Draw all sprites (including soybeans, player, balls, etc.)
        self.all_sprites.draw(self.screen)
        self.player.arrows.draw(self.screen)

        # Calculate the position to draw the pointer
        angle = self.get_angle_to_mouse()
        line_length = 50
        end_x = self.player.rect.centerx + line_length * math.cos(math.radians(angle))
        end_y = self.player.rect.centery - line_length * math.sin(math.radians(angle))

        # Ensure we don't access a pointer image out of range
        if self.current_level < len(self.pointer_images):
            pointer_image = self.pointer_images[self.current_level]
            pointer_rect = pointer_image.get_rect(center=(end_x, end_y))
            self.screen.blit(pointer_image, pointer_rect)

        # Draw HP bar
        pygame.draw.rect(self.screen, (255, 0, 0), (10, 10, 200, 20))  # Red background
        pygame.draw.rect(self.screen, (0, 255, 0), (10, 10, 20 * self.player.hp, 20))  # Green HP

        # Draw Progress bar
        pygame.draw.rect(self.screen, (255, 255, 0), (10, 40, self.progress_bar_length, 20))  # Yellow progress

        # Display Level and Balls Destroyed
        level_text = self.font.render(f"Level: {self.current_level + 1}/{len(self.levels)}", True, (255, 255, 255))
        balls_text = self.font.render(f"Balls Destroyed: {self.balls_destroyed}/{self.total_balls_needed}", True, (255, 255, 255))
        hp_text = self.font.render(f"HP: {self.player.hp}", True, (255, 255, 255))
        self.screen.blit(level_text, (10, 70))
        self.screen.blit(balls_text, (10, 100))
        self.screen.blit(hp_text, (10, 130))

        # Draw Boss Health Bar if the boss exists
        if hasattr(self, 'boss') and self.boss.alive():
            boss_health_text = self.font.render("Boss Health", True, (255, 255, 255))
            self.screen.blit(boss_health_text, (self.screen_width // 2 - boss_health_text.get_width() // 2, 20))
            pygame.draw.rect(self.screen, (255, 0, 0), (self.screen_width // 2 - 100, 50, 200, 20))
            pygame.draw.rect(self.screen, (0, 255, 0), (self.screen_width // 2 - 100, 50, 2 * self.boss.health, 20))

        pygame.display.flip()

if __name__ == "__main__":
    game = Game()
    asyncio.run( game.run() )

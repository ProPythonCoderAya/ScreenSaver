import pygame
import random
pygame.init()

info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), flags=pygame.FULLSCREEN)
pygame.display.set_caption("Screen Saver")
pygame.mouse.set_visible(False)

BLACK = (0, 0, 0)
BRIGHT_GREEN = (0, 255, 0)

font_size = 20
font = pygame.font.SysFont('Courier', font_size)

chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*()"

cols = WIDTH // font_size

speed = 1
fps = 20

clock = pygame.time.Clock()
running = True
attempt = 0

# Each rain is a dict: {'y': float, 'trail': list of (char, alpha)}
rain_columns = [[] for _ in range(cols)]

def create_rain(y=None):
    if y is None:
        y = random.uniform(-20, 0)
    return {'y': y, 'trail': []}

def can_spawn_rain(y_new, rains, min_distance=10):
    for rain in rains:
        if abs(rain['y'] - y_new) < min_distance:
            return False
    return True

# Initialize columns with 1-3 rains each, spaced properly
for i in range(cols):
    rains = rain_columns[i]
    attempts = 0
    while len(rains) < random.randint(1, 3) and attempts < 10:
        y_try = random.uniform(-20, 0)
        if can_spawn_rain(y_try, rains):
            rains.append(create_rain(y_try))
        attempts += 1

while running:
    screen.fill(BLACK)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEMOTION or event.type == pygame.KEYDOWN:
            attempt += 1
            if attempt == 2:
                running = False

    for i in range(cols):
        rains = rain_columns[i]

        for rain in rains[:]:  # iterate over a copy to remove safely
            rain['y'] += speed

            # Occasionally add new chars to trail
            if len(rain['trail']) == 0 or random.random() < 0.5:
                rain['trail'].insert(0, (random.choice(chars), 255))

            # Limit trail length
            if len(rain['trail']) > 20:
                rain['trail'].pop()

            # Draw trail
            for j, (char, alpha) in enumerate(rain['trail']):
                x = i * font_size
                y = int((rain['y'] - j) * font_size)

                if 0 <= y < HEIGHT:
                    text_surface = font.render(char, True, BRIGHT_GREEN)
                    text_surface.set_alpha(alpha)
                    screen.blit(text_surface, (x, y))

                    # Fade alpha for trail
                    new_alpha = max(alpha - 15, 0)
                    rain['trail'][j] = (char, new_alpha)

            # Remove rain if off screen and faded
            if rain['y'] * font_size > HEIGHT + len(rain['trail']) * font_size:
                rains.remove(rain)

        # Try to spawn new rains if fewer than 5, avoiding overlap
        if len(rains) < 5 and random.random() < 0.02:
            for _ in range(5):
                y_try = random.uniform(-20, 0)
                if can_spawn_rain(y_try, rains):
                    rains.append(create_rain(y_try))
                    break

    pygame.display.flip()
    clock.tick(fps)

pygame.mouse.set_visible(True)
pygame.quit()

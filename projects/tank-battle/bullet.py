import pygame
from typing import Optional, Tuple

from map import Map, TILE_SIZE, BRICK, STEEL, BASE


class Bullet:
    """Projectile fired by tanks."""

    SIZE = 6
    SPEED = 6

    def __init__(self, x: float, y: float, direction: int, owner: str, can_penetrate: bool = False) -> None:
        self.x: float = x
        self.y: float = y
        self.direction: int = direction  # 0=UP, 1=RIGHT, 2=DOWN, 3=LEFT
        self.owner: str = owner  # 'player' or 'enemy'
        self.can_penetrate: bool = can_penetrate  # Heavy tank bullets penetrate bricks
        self.alive: bool = True

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.SIZE // 2), int(self.y - self.SIZE // 2), self.SIZE, self.SIZE)

    def update(self, game_map: Map) -> Optional[Tuple[int, int]]:
        """Move bullet. Returns (px, py) if a brick was destroyed, else None."""
        dx, dy = 0, 0
        if self.direction == 0:
            dy = -self.SPEED
        elif self.direction == 1:
            dx = self.SPEED
        elif self.direction == 2:
            dy = self.SPEED
        elif self.direction == 3:
            dx = -self.SPEED

        self.x += dx
        self.y += dy

        # Check bounds
        if self.x < 0 or self.x > 832 or self.y < 0 or self.y > 640:
            self.alive = False
            return None

        # Check map collision
        tile = game_map.get_tile_at_pixel(int(self.x), int(self.y))
        if tile == BRICK:
            grid_x = int(self.x) // TILE_SIZE
            grid_y = int(self.y) // TILE_SIZE
            if self.can_penetrate:
                # Penetrate but still destroy the brick
                game_map.set_tile(grid_x, grid_y, 0)
                self.alive = False  # Bullet stops after penetrating one brick
                return (grid_x * TILE_SIZE + TILE_SIZE // 2, grid_y * TILE_SIZE + TILE_SIZE // 2)
            else:
                game_map.set_tile(grid_x, grid_y, 0)
                self.alive = False
                return (grid_x * TILE_SIZE + TILE_SIZE // 2, grid_y * TILE_SIZE + TILE_SIZE // 2)
        elif tile == STEEL:
            self.alive = False
            return None
        elif tile == BASE:
            self.alive = False
            return (int(self.x), int(self.y))

        return None

    def render(self, screen: pygame.Surface) -> None:
        color = (255, 255, 0) if self.owner == 'player' else (255, 100, 100)
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.SIZE // 2)
        pygame.draw.circle(screen, (255, 255, 255), (int(self.x), int(self.y)), self.SIZE // 2 - 1)


class Explosion:
    """Brief explosion visual effect."""

    MAX_LIFE = 15
    MAX_RADIUS = 25

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
        self.life = self.MAX_LIFE
        self.alive = True

    def update(self) -> None:
        self.life -= 1
        if self.life <= 0:
            self.alive = False

    def render(self, screen: pygame.Surface) -> None:
        if not self.alive:
            return
        progress = 1.0 - (self.life / self.MAX_LIFE)
        radius = int(self.MAX_RADIUS * progress)
        alpha = int(255 * (1.0 - progress))
        # Draw expanding circles
        if radius > 0:
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 200, 0, alpha), (radius, radius), radius)
            screen.blit(s, (self.x - radius, self.y - radius))
            inner_r = max(1, radius - 5)
            s2 = pygame.Surface((inner_r * 2, inner_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s2, (255, 100, 0, alpha), (inner_r, inner_r), inner_r)
            screen.blit(s2, (self.x - inner_r, self.y - inner_r))

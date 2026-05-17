import pygame
import random
from typing import Tuple, Optional, List

from map import Map, TILE_SIZE
from bullet import Bullet

# Directions
UP = 0
RIGHT = 1
DOWN = 2
LEFT = 3

# Tank body size (slightly smaller than tile)
TANK_SIZE = 28
TANK_OFFSET = (TILE_SIZE - TANK_SIZE) // 2  # 2

# Type colors
COLOR_PLAYER = (34, 139, 34)      # Green
COLOR_ENEMY_NORMAL = (128, 128, 128)  # Gray
COLOR_ENEMY_FAST = (255, 215, 0)      # Yellow
COLOR_ENEMY_HEAVY = (220, 20, 60)     # Red

DIRECTION_VECTORS = {
    UP: (0, -1),
    RIGHT: (1, 0),
    DOWN: (0, 1),
    LEFT: (-1, 0),
}


class Tank:
    """Base tank class."""

    def __init__(self, x: int, y: int, direction: int, speed: int, color: Tuple[int, int, int],
                 health: int, max_cooldown: int) -> None:
        self.x: float = float(x)
        self.y: float = float(y)
        self.direction: int = direction
        self.speed: int = speed
        self.color: Tuple[int, int, int] = color
        self.health: int = health
        self.max_cooldown: int = max_cooldown
        self.cooldown_timer: int = 0
        self.invincible_timer: int = 0
        self.alive: bool = True

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) + TANK_OFFSET, int(self.y) + TANK_OFFSET, TANK_SIZE, TANK_SIZE)

    def get_cannon_tip(self) -> Tuple[float, float]:
        """Get the pixel position of the cannon tip for bullet spawning."""
        cx = self.x + TILE_SIZE // 2
        cy = self.y + TILE_SIZE // 2
        if self.direction == UP:
            return (cx, cy - TILE_SIZE // 2 - 4)
        elif self.direction == RIGHT:
            return (cx + TILE_SIZE // 2 + 4, cy)
        elif self.direction == DOWN:
            return (cx, cy + TILE_SIZE // 2 + 4)
        else:  # LEFT
            return (cx - TILE_SIZE // 2 - 4, cy)

    def try_move(self, dx: int, dy: int, game_map: Map, other_tanks: List['Tank']) -> bool:
        """Attempt to move by (dx, dy). Returns True if successful."""
        if dx == 0 and dy == 0:
            return False

        new_x = self.x + dx
        new_y = self.y + dy

        # Clamp to screen bounds
        new_x = max(0, min(new_x, 832 - TILE_SIZE))
        new_y = max(0, min(new_y, 640 - TILE_SIZE))

        new_rect = pygame.Rect(int(new_x) + TANK_OFFSET, int(new_y) + TANK_OFFSET, TANK_SIZE, TANK_SIZE)

        # Check map collision
        if not game_map.can_move(new_rect):
            return False

        # Check tank-tank collision
        for other in other_tanks:
            if other is self or not other.alive:
                continue
            if new_rect.colliderect(other.rect):
                return False

        self.x = new_x
        self.y = new_y
        return True

    def move_forward(self, game_map: Map, other_tanks: List['Tank']) -> bool:
        """Move in the current direction."""
        dx, dy = DIRECTION_VECTORS[self.direction]
        return self.try_move(dx * self.speed, dy * self.speed, game_map, other_tanks)

    def shoot(self) -> Optional[Bullet]:
        """Fire a bullet if cooldown allows."""
        if self.cooldown_timer > 0:
            return None
        self.cooldown_timer = self.max_cooldown
        bx, by = self.get_cannon_tip()
        return Bullet(bx, by, self.direction, 'player' if isinstance(self, PlayerTank) else 'enemy',
                      can_penetrate=(self.color == COLOR_ENEMY_HEAVY))

    def take_damage(self, damage: int = 1) -> bool:
        """Take damage. Returns True if tank died."""
        if self.invincible_timer > 0:
            return False
        self.health -= damage
        if self.health <= 0:
            self.alive = False
            return True
        return False

    def update(self) -> None:
        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1
        if self.invincible_timer > 0:
            self.invincible_timer -= 1

    def render(self, screen: pygame.Surface) -> None:
        if not self.alive:
            return
        # Invincible flash
        if self.invincible_timer > 0 and (self.invincible_timer // 3) % 2 == 0:
            return  # Skip drawing for flash effect

        body_rect = self.rect
        pygame.draw.rect(screen, self.color, body_rect)
        # Inner detail
        inner_color = tuple(min(c + 30, 255) for c in self.color)
        pygame.draw.rect(screen, inner_color,
                         (body_rect.x + 4, body_rect.y + 4, body_rect.width - 8, body_rect.height - 8))

        # Cannon barrel
        cx = int(self.x) + TILE_SIZE // 2
        cy = int(self.y) + TILE_SIZE // 2
        barrel_color = tuple(max(0, c - 40) for c in self.color)
        if self.direction == UP:
            pygame.draw.rect(screen, barrel_color, (cx - 3, cy - 18, 6, 14))
        elif self.direction == RIGHT:
            pygame.draw.rect(screen, barrel_color, (cx + 4, cy - 3, 14, 6))
        elif self.direction == DOWN:
            pygame.draw.rect(screen, barrel_color, (cx - 3, cy + 4, 6, 14))
        else:  # LEFT
            pygame.draw.rect(screen, barrel_color, (cx - 18, cy - 3, 14, 6))


class PlayerTank(Tank):
    """Player-controlled tank."""

    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y, UP, 2, COLOR_PLAYER, health=1, max_cooldown=20)
        self.lives: int = 3
        self.respawn_timer: int = 0

    def respawn(self, spawn_x: int, spawn_y: int) -> None:
        self.x = float(spawn_x)
        self.y = float(spawn_y)
        self.direction = UP
        self.health = 1
        self.alive = True
        self.invincible_timer = 90  # 1.5 seconds of invincibility
        self.cooldown_timer = 0
        self.respawn_timer = 0

    def update(self) -> None:
        super().update()
        if self.respawn_timer > 0:
            self.respawn_timer -= 1
            if self.respawn_timer == 0:
                self.alive = True

    def render(self, screen: pygame.Surface) -> None:
        if not self.alive:
            return
        super().render(screen)
        # Draw small life indicator
        font = pygame.font.SysFont(None, 20)
        text = font.render(f'x{self.lives}', True, (255, 255, 255))
        screen.blit(text, (int(self.x) + 8, int(self.y) - 14))


class EnemyTank(Tank):
    """AI-controlled enemy tank."""

    TYPE_NORMAL = 'normal'
    TYPE_FAST = 'fast'
    TYPE_HEAVY = 'heavy'

    def __init__(self, x: int, y: int, enemy_type: str = TYPE_NORMAL) -> None:
        if enemy_type == self.TYPE_FAST:
            color = COLOR_ENEMY_FAST
            speed = 2
            health = 1
            cooldown = 30
        elif enemy_type == self.TYPE_HEAVY:
            color = COLOR_ENEMY_HEAVY
            speed = 1
            health = 3
            cooldown = 40
        else:  # normal
            color = COLOR_ENEMY_NORMAL
            speed = 1
            health = 1
            cooldown = 35

        super().__init__(x, y, DOWN, speed, color, health=health, max_cooldown=cooldown)
        self.enemy_type: str = enemy_type
        self.change_dir_timer: int = random.randint(60, 120)
        self.shoot_timer: int = random.randint(30, 90)

    def update(self) -> None:
        super().update()
        if self.change_dir_timer > 0:
            self.change_dir_timer -= 1
        if self.shoot_timer > 0:
            self.shoot_timer -= 1

    def render(self, screen: pygame.Surface) -> None:
        if not self.alive:
            return
        super().render(screen)
        # Health indicator for heavy tanks
        if self.health > 1:
            font = pygame.font.SysFont(None, 16)
            text = font.render(str(self.health), True, (255, 255, 255))
            screen.blit(text, (int(self.x) + 12, int(self.y) + 10))

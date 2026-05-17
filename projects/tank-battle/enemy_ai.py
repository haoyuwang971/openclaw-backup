import random
from typing import List, Optional, Tuple

from map import Map, TILE_SIZE
from tank import EnemyTank, PlayerTank, UP, RIGHT, DOWN, LEFT, DIRECTION_VECTORS


class EnemyAI:
    """Controls enemy tank behavior."""

    SIGHT_RANGE = 5  # tiles

    def __init__(self, enemy: EnemyTank) -> None:
        self.enemy = enemy

    def update(self, game_map: Map, player: PlayerTank, all_enemies: List[EnemyTank]) -> Optional[int]:
        """
        Update AI state. Returns direction to shoot if firing, else None.
        """
        if not self.enemy.alive:
            return None

        # Random direction change timer
        if self.enemy.change_dir_timer <= 0:
            self.enemy.direction = random.choice([UP, RIGHT, DOWN, LEFT])
            self.enemy.change_dir_timer = random.randint(90, 180)

        # Check line of sight to player
        shoot_dir = self._check_line_of_sight(game_map, player)
        if shoot_dir is not None:
            self.enemy.direction = shoot_dir
            # Move toward player
            self.enemy.move_forward(game_map, all_enemies)
            if self.enemy.shoot_timer <= 0:
                self.enemy.shoot_timer = random.randint(20, 50)
                return shoot_dir
            return None

        # Normal wandering
        moved = self.enemy.move_forward(game_map, all_enemies)
        if not moved:
            # Hit a wall, pick new direction
            self.enemy.direction = self._pick_avoidance_direction(game_map, all_enemies)
            self.enemy.change_dir_timer = random.randint(60, 120)

        # Random shooting while wandering
        if self.enemy.shoot_timer <= 0:
            self.enemy.shoot_timer = random.randint(40, 100)
            return self.enemy.direction

        return None

    def _check_line_of_sight(self, game_map: Map, player: PlayerTank) -> Optional[int]:
        """Check if player is visible in any cardinal direction. Return direction if so."""
        if not player.alive:
            return None

        ex = int(self.enemy.x) // TILE_SIZE
        ey = int(self.enemy.y) // TILE_SIZE
        px = int(player.x) // TILE_SIZE
        py = int(player.y) // TILE_SIZE

        # Check UP
        if px == ex and py < ey:
            dist = ey - py
            if dist <= self.SIGHT_RANGE:
                clear = True
                for y in range(py + 1, ey):
                    if game_map.is_solid_for_tank(px, y):
                        clear = False
                        break
                if clear:
                    return UP

        # Check DOWN
        if px == ex and py > ey:
            dist = py - ey
            if dist <= self.SIGHT_RANGE:
                clear = True
                for y in range(ey + 1, py):
                    if game_map.is_solid_for_tank(px, y):
                        clear = False
                        break
                if clear:
                    return DOWN

        # Check LEFT
        if py == ey and px < ex:
            dist = ex - px
            if dist <= self.SIGHT_RANGE:
                clear = True
                for x in range(px + 1, ex):
                    if game_map.is_solid_for_tank(x, py):
                        clear = False
                        break
                if clear:
                    return LEFT

        # Check RIGHT
        if py == ey and px > ex:
            dist = px - ex
            if dist <= self.SIGHT_RANGE:
                clear = True
                for x in range(ex + 1, px):
                    if game_map.is_solid_for_tank(x, py):
                        clear = False
                        break
                if clear:
                    return RIGHT

        return None

    def _pick_avoidance_direction(self, game_map: Map, other_tanks: List[EnemyTank]) -> int:
        """Pick a direction that avoids walls and other tanks."""
        dirs = [UP, RIGHT, DOWN, LEFT]
        random.shuffle(dirs)
        for d in dirs:
            dx, dy = DIRECTION_VECTORS[d]
            test_rect = self.enemy.rect.copy()
            test_rect.x += dx * self.enemy.speed
            test_rect.y += dy * self.enemy.speed
            if not game_map.can_move(test_rect):
                continue
            # Check tank-tank collision
            overlap = False
            for other in other_tanks:
                if other is self.enemy or not other.alive:
                    continue
                if test_rect.colliderect(other.rect):
                    overlap = True
                    break
            if not overlap:
                return d
        return random.choice([UP, RIGHT, DOWN, LEFT])

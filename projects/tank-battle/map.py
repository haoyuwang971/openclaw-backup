import pygame
from typing import List, Tuple, Optional

TILE_SIZE = 32
SCREEN_WIDTH = 832   # 26 * 32
SCREEN_HEIGHT = 640  # 20 * 32

# Tile types
EMPTY = 0
BRICK = 1
STEEL = 2
WATER = 3
BASE = 4

# Character to tile mapping
CHAR_TO_TILE = {
    '.': EMPTY,
    '#': BRICK,
    '@': STEEL,
    '~': WATER,
    'P': EMPTY,
    'E': EMPTY,
    'B': BASE,
}


class Map:
    """Tile-based level map."""

    def __init__(self, filename: str) -> None:
        self.tiles: List[List[int]] = []
        self.player_spawn: Optional[Tuple[int, int]] = None
        self.enemy_spawns: List[Tuple[int, int]] = []
        self.base_positions: List[Tuple[int, int]] = []
        self.load(filename)

    def load(self, filename: str) -> None:
        with open(filename, 'r') as f:
            lines = [line.rstrip('\n') for line in f.readlines()]

        for row_idx, line in enumerate(lines):
            row: List[int] = []
            for col_idx, char in enumerate(line):
                if char == 'P':
                    self.player_spawn = (col_idx * TILE_SIZE, row_idx * TILE_SIZE)
                    row.append(EMPTY)
                elif char == 'E':
                    self.enemy_spawns.append((col_idx * TILE_SIZE, row_idx * TILE_SIZE))
                    row.append(EMPTY)
                elif char == 'B':
                    self.base_positions.append((col_idx * TILE_SIZE, row_idx * TILE_SIZE))
                    row.append(BASE)
                else:
                    row.append(CHAR_TO_TILE.get(char, EMPTY))
            self.tiles.append(row)

    def get_tile(self, grid_x: int, grid_y: int) -> int:
        if 0 <= grid_y < len(self.tiles) and 0 <= grid_x < len(self.tiles[0]):
            return self.tiles[grid_y][grid_x]
        return STEEL  # Out of bounds acts as steel wall

    def set_tile(self, grid_x: int, grid_y: int, tile: int) -> None:
        if 0 <= grid_y < len(self.tiles) and 0 <= grid_x < len(self.tiles[0]):
            self.tiles[grid_y][grid_x] = tile

    def is_solid_for_tank(self, grid_x: int, grid_y: int) -> bool:
        tile = self.get_tile(grid_x, grid_y)
        return tile in (BRICK, STEEL, WATER, BASE)

    def is_solid_for_bullet(self, grid_x: int, grid_y: int) -> bool:
        tile = self.get_tile(grid_x, grid_y)
        return tile in (BRICK, STEEL)

    def can_move(self, rect: pygame.Rect) -> bool:
        """Check if a rectangle can be placed without colliding with blocking tiles."""
        start_col = rect.left // TILE_SIZE
        end_col = (rect.right - 1) // TILE_SIZE
        start_row = rect.top // TILE_SIZE
        end_row = (rect.bottom - 1) // TILE_SIZE

        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                if self.is_solid_for_tank(col, row):
                    return False
        return True

    def get_tile_at_pixel(self, px: int, py: int) -> int:
        return self.get_tile(px // TILE_SIZE, py // TILE_SIZE)

    def set_tile_at_pixel(self, px: int, py: int, tile: int) -> None:
        self.set_tile(px // TILE_SIZE, py // TILE_SIZE, tile)

    def render(self, screen: pygame.Surface) -> None:
        for row_idx, row in enumerate(self.tiles):
            for col_idx, tile in enumerate(row):
                x = col_idx * TILE_SIZE
                y = row_idx * TILE_SIZE
                if tile == BRICK:
                    pygame.draw.rect(screen, (139, 69, 19), (x, y, TILE_SIZE, TILE_SIZE))
                    # Add a cross pattern
                    pygame.draw.line(screen, (100, 50, 10), (x, y), (x + TILE_SIZE, y + TILE_SIZE), 2)
                    pygame.draw.line(screen, (100, 50, 10), (x + TILE_SIZE, y), (x, y + TILE_SIZE), 2)
                elif tile == STEEL:
                    pygame.draw.rect(screen, (128, 128, 128), (x, y, TILE_SIZE, TILE_SIZE))
                    pygame.draw.rect(screen, (64, 64, 64), (x, y, TILE_SIZE, TILE_SIZE), 2)
                    pygame.draw.rect(screen, (90, 90, 90), (x + 6, y + 6, TILE_SIZE - 12, TILE_SIZE - 12), 1)
                elif tile == WATER:
                    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                    s.fill((0, 100, 255, 128))
                    screen.blit(s, (x, y))
                    # Small wave lines
                    pygame.draw.line(screen, (0, 80, 200), (x + 4, y + 16), (x + 28, y + 16), 2)
                    pygame.draw.line(screen, (0, 80, 200), (x + 8, y + 24), (x + 24, y + 24), 2)
                elif tile == BASE:
                    # Draw a white "eagle" shape
                    pygame.draw.rect(screen, (255, 255, 255), (x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4))
                    pygame.draw.polygon(screen, (0, 0, 0), [
                        (x + 16, y + 6),
                        (x + 22, y + 14),
                        (x + 16, y + 26),
                        (x + 10, y + 14),
                    ])
                    pygame.draw.rect(screen, (255, 255, 255), (x + 14, y + 12, 4, 8))

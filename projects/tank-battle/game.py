import pygame
import random
from typing import List, Optional

from map import Map, TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, BRICK, STEEL, BASE
from tank import PlayerTank, EnemyTank, UP, RIGHT, DOWN, LEFT, COLOR_ENEMY_NORMAL, COLOR_ENEMY_FAST, COLOR_ENEMY_HEAVY
from bullet import Bullet, Explosion
from enemy_ai import EnemyAI

# Game states
STATE_MENU = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2
STATE_VICTORY = 3

TOTAL_ENEMIES = 6


class Game:
    """Main game class - state machine and game loop."""

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tank Battle")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont(None, 72)
        self.font_medium = pygame.font.SysFont(None, 36)
        self.font_small = pygame.font.SysFont(None, 24)
        self.running = True
        self.state = STATE_MENU
        self.map: Optional[Map] = None
        self.player: Optional[PlayerTank] = None
        self.enemies: List[EnemyTank] = []
        self.enemy_ais: List[EnemyAI] = []
        self.bullets: List[Bullet] = []
        self.explosions: List[Explosion] = []
        self.enemies_killed = 0
        self.enemies_spawned = 0
        self.base_destroyed = False
        self._load_level()

    def _load_level(self) -> None:
        self.map = Map("levels/level01.txt")
        self.enemies.clear()
        self.enemy_ais.clear()
        self.bullets.clear()
        self.explosions.clear()
        self.enemies_killed = 0
        self.enemies_spawned = 0
        self.base_destroyed = False

        if self.map.player_spawn:
            self.player = PlayerTank(self.map.player_spawn[0], self.map.player_spawn[1])
        else:
            self.player = PlayerTank(SCREEN_WIDTH // 2 - TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 2)

        # Spawn initial enemies
        self._spawn_enemies(initial=True)

    def _spawn_enemies(self, initial: bool = False) -> None:
        if not self.map or not self.player:
            return
        spawns = self.map.enemy_spawns[:]
        if not spawns:
            spawns = [(TILE_SIZE * 5, TILE_SIZE), (TILE_SIZE * 13, TILE_SIZE), (TILE_SIZE * 21, TILE_SIZE)]

        count = 3 if initial else 1
        for _ in range(count):
            if self.enemies_spawned >= TOTAL_ENEMIES:
                break
            spawn = random.choice(spawns)
            # Don't spawn on top of existing tanks
            overlap = False
            test_rect = pygame.Rect(spawn[0] + 2, spawn[1] + 2, 28, 28)
            for e in self.enemies:
                if e.alive and e.rect.colliderect(test_rect):
                    overlap = True
                    break
            if self.player and self.player.alive and self.player.rect.colliderect(test_rect):
                overlap = True
            if overlap:
                continue

            enemy_type = self._pick_enemy_type()
            enemy = EnemyTank(spawn[0], spawn[1], enemy_type)
            self.enemies.append(enemy)
            self.enemy_ais.append(EnemyAI(enemy))
            self.enemies_spawned += 1

    def _pick_enemy_type(self) -> str:
        # Mix: 3 normal, 2 fast, 1 heavy
        weights = [EnemyTank.TYPE_NORMAL] * 3 + [EnemyTank.TYPE_FAST] * 2 + [EnemyTank.TYPE_HEAVY] * 1
        return random.choice(weights)

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(60)
            self._handle_events()

            if self.state == STATE_MENU:
                self._update_menu()
                self._render_menu()
            elif self.state == STATE_PLAYING:
                self._update_playing()
                self._render_playing()
            elif self.state == STATE_GAME_OVER:
                self._update_game_over()
                self._render_game_over()
            elif self.state == STATE_VICTORY:
                self._update_victory()
                self._render_victory()

            pygame.display.flip()

        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self._load_level()
                    self.state = STATE_PLAYING
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
                elif self.state == STATE_MENU:
                    if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        self.state = STATE_PLAYING

    def _update_menu(self) -> None:
        pass

    def _render_menu(self) -> None:
        self.screen.fill((20, 20, 20))
        title = self.font_large.render("TANK BATTLE", True, (34, 139, 34))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 180))

        instructions = [
            "WASD / Arrow Keys - Move",
            "SPACE - Shoot",
            "R - Restart",
            "ESC - Quit",
            "",
            "Protect the base! Destroy all enemies!",
            "",
            "Press SPACE or ENTER to start",
        ]
        y = 300
        for line in instructions:
            if line:
                text = self.font_small.render(line, True, (200, 200, 200))
                self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
            y += 28

    def _update_playing(self) -> None:
        if not self.player or not self.map:
            return

        # Player input
        keys = pygame.key.get_pressed()
        if self.player.alive:
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                self.player.direction = UP
                self.player.move_forward(self.map, [self.player] + self.enemies)
            elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
                self.player.direction = DOWN
                self.player.move_forward(self.map, [self.player] + self.enemies)
            elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
                self.player.direction = LEFT
                self.player.move_forward(self.map, [self.player] + self.enemies)
            elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                self.player.direction = RIGHT
                self.player.move_forward(self.map, [self.player] + self.enemies)
            if keys[pygame.K_SPACE]:
                bullet = self.player.shoot()
                if bullet:
                    self.bullets.append(bullet)

        self.player.update()

        # Enemy AI
        for ai in self.enemy_ais:
            shoot_dir = ai.update(self.map, self.player, self.enemies)
            if shoot_dir is not None:
                bullet = ai.enemy.shoot()
                if bullet:
                    self.bullets.append(bullet)

        for enemy in self.enemies:
            enemy.update()

        # Spawn more enemies if needed
        alive_enemies = sum(1 for e in self.enemies if e.alive)
        if alive_enemies < 3 and self.enemies_spawned < TOTAL_ENEMIES:
            self._spawn_enemies(initial=False)

        # Check victory
        if alive_enemies == 0 and self.enemies_spawned >= TOTAL_ENEMIES:
            self.state = STATE_VICTORY
            return

        # Update bullets
        for bullet in self.bullets:
            hit_pos = bullet.update(self.map)
            if hit_pos:
                self.explosions.append(Explosion(hit_pos[0], hit_pos[1]))
                # Check if base was hit
                tile = self.map.get_tile_at_pixel(int(bullet.x), int(bullet.y))
                if tile == BASE:
                    self.base_destroyed = True
                    self.state = STATE_GAME_OVER
                    return

        # Bullet-tank collisions
        for bullet in self.bullets:
            if not bullet.alive:
                continue
            if bullet.owner == 'player':
                for enemy in self.enemies:
                    if enemy.alive and bullet.rect.colliderect(enemy.rect):
                        died = enemy.take_damage(1)
                        bullet.alive = False
                        self.explosions.append(Explosion(int(enemy.x + TILE_SIZE // 2), int(enemy.y + TILE_SIZE // 2)))
                        if died:
                            self.enemies_killed += 1
                        break
            else:  # enemy bullet
                if self.player and self.player.alive and bullet.rect.colliderect(self.player.rect):
                    died = self.player.take_damage(1)
                    bullet.alive = False
                    self.explosions.append(Explosion(int(self.player.x + TILE_SIZE // 2), int(self.player.y + TILE_SIZE // 2)))
                    if died:
                        self.player.lives -= 1
                        if self.player.lives > 0:
                            # Respawn
                            if self.map and self.map.player_spawn:
                                self.player.respawn(self.map.player_spawn[0], self.map.player_spawn[1])
                            else:
                                self.player.respawn(SCREEN_WIDTH // 2 - TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 2)
                        else:
                            self.state = STATE_GAME_OVER
                            return

        # Bullet-bullet collisions (both destroyed)
        for i, b1 in enumerate(self.bullets):
            if not b1.alive:
                continue
            for j, b2 in enumerate(self.bullets):
                if i >= j or not b2.alive:
                    continue
                if b1.owner != b2.owner and b1.rect.colliderect(b2.rect):
                    b1.alive = False
                    b2.alive = False
                    mx = (b1.x + b2.x) / 2
                    my = (b1.y + b2.y) / 2
                    self.explosions.append(Explosion(int(mx), int(my)))

        # Clean up dead bullets
        self.bullets = [b for b in self.bullets if b.alive]

        # Update explosions
        for exp in self.explosions:
            exp.update()
        self.explosions = [e for e in self.explosions if e.alive]

    def _render_playing(self) -> None:
        self.screen.fill((0, 0, 0))
        if self.map:
            self.map.render(self.screen)

        for enemy in self.enemies:
            enemy.render(self.screen)

        if self.player:
            self.player.render(self.screen)

        for bullet in self.bullets:
            bullet.render(self.screen)

        for exp in self.explosions:
            exp.render(self.screen)

        # HUD
        if self.player:
            lives_text = self.font_small.render(f"Lives: {self.player.lives}", True, (255, 255, 255))
            self.screen.blit(lives_text, (10, 10))
        enemies_left = TOTAL_ENEMIES - self.enemies_killed
        enemy_text = self.font_small.render(f"Enemies: {enemies_left}", True, (255, 255, 255))
        self.screen.blit(enemy_text, (SCREEN_WIDTH - enemy_text.get_width() - 10, 10))

    def _update_game_over(self) -> None:
        pass

    def _render_game_over(self) -> None:
        self._render_playing()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        text = self.font_large.render("GAME OVER", True, (255, 0, 0))
        self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - 60))
        restart = self.font_medium.render("Press R to Restart", True, (255, 255, 255))
        self.screen.blit(restart, (SCREEN_WIDTH // 2 - restart.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

    def _update_victory(self) -> None:
        pass

    def _render_victory(self) -> None:
        self._render_playing()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        text = self.font_large.render("VICTORY!", True, (34, 139, 34))
        self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - 60))
        restart = self.font_medium.render("Press R to Restart", True, (255, 255, 255))
        self.screen.blit(restart, (SCREEN_WIDTH // 2 - restart.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

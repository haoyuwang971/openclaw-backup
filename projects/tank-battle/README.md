# Tank Battle

A classic tank battle game implemented in Python with Pygame.

## Controls

- **W / Up Arrow** - Move up
- **S / Down Arrow** - Move down
- **A / Left Arrow** - Move left
- **D / Right Arrow** - Move right
- **Space** - Shoot
- **R** - Restart (from GAME OVER or VICTORY screen)
- **ESC** - Quit

## Setup

```bash
cd projects/tank-battle
pip install -r requirements.txt
python main.py
```

## Game Rules

- Protect the **white base** (eagle) at the bottom of the map
- Destroy all **6 enemy tanks** to win
- You have **3 lives**
- **Green** = Player tank
- **Gray** = Normal enemy (1 HP, slow)
- **Yellow** = Fast enemy (1 HP, fast)
- **Red** = Heavy enemy (3 HP, slow, bullets penetrate bricks)

## Map Tiles

- **Brown** = Brick wall (destroyed by 1 bullet)
- **Gray with border** = Steel wall (indestructible)
- **Blue** = Water (tanks can't pass, bullets can)
- **White** = Base (must protect!)

## Window

Game window size is **832x640** (26 columns x 20 rows of 32x32 tiles).

## Dependencies

- Python 3.8+
- pygame >= 2.5.0

## License

MIT

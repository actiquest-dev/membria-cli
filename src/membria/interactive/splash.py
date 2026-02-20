"""
Splash Screen for Membria Interactive Shell
Left: Arkanoid — break MEMBRIA letters. Right: product info panel.
"""

import random
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static
from textual.screen import Screen
from rich.text import Text


# ── Pixel font, 5 rows. Each filled cell = CELL_W terminal columns. ──────────
FONT = {
    'M': [
        [1,0,0,0,1],
        [1,1,0,1,1],
        [1,0,1,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
    ],
    'E': [
        [1,1,1,1,1],
        [1,0,0,0,0],
        [1,1,1,1,0],
        [1,0,0,0,0],
        [1,1,1,1,1],
    ],
    'B': [
        [1,1,1,1,0],
        [1,0,0,0,1],
        [1,1,1,1,0],
        [1,0,0,0,1],
        [1,1,1,1,0],
    ],
    'R': [
        [1,1,1,1,0],
        [1,0,0,0,1],
        [1,1,1,1,0],
        [1,0,1,0,0],
        [1,0,0,1,0],
    ],
    'I': [
        [1,1,1],
        [0,1,0],
        [0,1,0],
        [0,1,0],
        [1,1,1],
    ],
    'A': [
        [0,1,1,1,0],
        [1,0,0,0,1],
        [1,1,1,1,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
    ],
}

WORD     = "MEMBRIA"
FONT_ROWS = 5
CELL_W   = 2      # each font pixel → 2 terminal cols
LETTER_GAP = 2    # cols between letters

# ── Powerups ──────────────────────────────────────────────────────────────────
POWERUPS = {
    '+': ('#21C93A', 'Wide paddle  '),
    '-': ('#FF5555', 'Narrow paddle'),
    '2': ('#FFE066', 'Extra ball   '),
    '♥': ('#FF88AA', 'Extra life   '),
    '☠': ('#CC44CC', 'Lose a life  '),
    'S': ('#88DDFF', 'Slow balls   '),
    'F': ('#FF8800', 'Fast balls   '),
}
POWERUP_KEYS = list(POWERUPS.keys())

# Speed constants — hard cap so game stays playable
_DX_MAX  = 1.3   # max horizontal speed (cells/tick)
_DY_BASE = 1.0   # vertical speed at normal pace
_DY_MAX  = 1.5   # absolute max vertical speed


def _build_letter_bricks(field_width: int, row_offset: int = 1) -> dict:
    total_cols = sum(len(FONT[ch][0]) * CELL_W for ch in WORD) + LETTER_GAP * (len(WORD) - 1)
    start_col  = max(0, (field_width - total_cols) // 2)
    bricks: dict = {}
    col = start_col
    for ch in WORD:
        glyph = FONT[ch]
        gw    = len(glyph[0]) * CELL_W
        for r, row in enumerate(glyph):
            for ci, filled in enumerate(row):
                if filled:
                    for cw in range(CELL_W):
                        bc = col + ci * CELL_W + cw
                        if bc < field_width:
                            bricks[(row_offset + r, bc)] = ch
        col += gw + LETTER_GAP
    return bricks


# ── Info panel content ────────────────────────────────────────────────────────
_INFO_LINES = [
    "[bold #5AA5FF]  MEMBRIA[/bold #5AA5FF]",
    "[#FFB84D]  Decision Intelligence[/#FFB84D]",
    "[#444466]  ─────────────────────────[/#444466]",
    "",
    "[bold #E8E8E8] What it is[/bold #E8E8E8]",
    "[#A0A0A0] Middleware that captures[/#A0A0A0]",
    "[#A0A0A0] dev decisions, tracks out-[/#A0A0A0]",
    "[#A0A0A0] comes & calibrates Claude.[/#A0A0A0]",
    "",
    "[bold #E8E8E8] The problem[/bold #E8E8E8]",
    "[#FF5555] ✗ LLMs repeat mistakes[/#FF5555]",
    "[#FF5555] ✗ No feedback loop[/#FF5555]",
    "[#FF5555] ✗ Context resets every run[/#FF5555]",
    "",
    "[bold #E8E8E8] The solution[/bold #E8E8E8]",
    "[#21C93A] ✓ Graph memory across runs[/#21C93A]",
    "[#21C93A] ✓ Bayesian calibration[/#21C93A]",
    "[#21C93A] ✓ +15% accuracy / 10× speed[/#21C93A]",
    "[#21C93A] ✓ Week 1→12: 55%→91%[/#21C93A]",
    "",
    "[bold #E8E8E8] Stack[/bold #E8E8E8]",
    "[#A0A0A0] Claude/MCP ↔ Membria[/#A0A0A0]",
    "[#A0A0A0]   ↓ FalkorDB graph[/#A0A0A0]",
    "[#A0A0A0] capture · track · inject[/#A0A0A0]",
    "",
    "[#444466]  ─────────────────────────[/#444466]",
    "[bold #E8E8E8] Powerups[/bold #E8E8E8]",
]
for _sym, (_color, _desc) in POWERUPS.items():
    _INFO_LINES.append(f" [{_color}]{_sym}[/{_color}] [#777777]{_desc.strip()}[/#777777]")

_INFO_LINES += [
    "",
    "[#444466]  ─────────────────────────[/#444466]",
    "[bold #E8E8E8] Controls[/bold #E8E8E8]",
    "[#5AA5FF] ←/→[/#5AA5FF][#C0C0C0]  move paddle[/#C0C0C0]",
    "[#5AA5FF] P  [/#5AA5FF][#C0C0C0]  pause/resume[/#C0C0C0]",
    "[#5AA5FF] Ent[/#5AA5FF][#C0C0C0]  skip & start[/#C0C0C0]",
]


class SplashScreen(Screen):
    """Membria splash — Arkanoid (left) + info panel (right)."""

    DEFAULT_CSS = """
    Screen {
        background: #0d1a0d;
        color: #E8E8E8;
    }

    #splash_container {
        width: 100%;
        height: 100%;
        layout: horizontal;
        background: #0d1a0d;
    }

    #left_pane {
        layout: vertical;
        width: 1fr;
        height: 100%;
        background: #0d1a0d;
    }

    #game_widget {
        width: 100%;
        height: 1fr;
        color: #E8E8E8;
        background: #0d1a0d;
        overflow: hidden;
    }

    #footer_widget {
        width: 100%;
        height: 2;
        background: #0a1a0a;
        color: #E8E8E8;
        overflow: hidden;
        padding: 0 1 0 1;
    }

    #info_pane {
        width: 32;
        height: 100%;
        background: #0a1a0a;
        padding: 0 1;
        overflow: hidden;
    }
    """

    def __init__(self):
        super().__init__()
        # Field dims — set properly in _resize_to_screen
        self.gw = 60
        self.gh = 24
        # Paddle
        self.paddle_base_w = 10
        self.paddle_w      = 10
        self.paddle_x      = 25
        # Physics
        self.balls: list = []   # [x, y, dx, dy]
        self.dy_speed = _DY_BASE
        # Bricks & powerups
        self.bricks: dict       = {}
        self.secret_bricks: set = set()
        self.powerups: list     = []   # [x, y, sym]
        # Drift
        self.brick_row_offset = 1
        self.drift_timer      = 0
        # Stats
        self.score  = 0
        self.lives  = 3
        self.frame  = 0
        self.paused = False
        self._interval = None
        # Paddle physics — press counter for acceleration
        self._paddle_vel: float = 0.0   # visual-only: used for glow colour
        self._press_count: int  = 0     # consecutive presses in same direction
        self._last_dir: str     = ""    # "left" or "right"
        # Hit flash effect
        self._paddle_hit_frame: int = -100  # frame when last ball hit paddle

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Horizontal(id="splash_container"):
            with Container(id="left_pane"):
                yield Static("", id="game_widget")
                yield Static("", id="footer_widget")
            yield Static(self._render_info(), id="info_pane")

    def _resize_to_screen(self) -> None:
        sw = self.size.width
        sh = self.size.height
        info_w     = 32                          # right panel fixed width
        game_cols  = max(36, sw - info_w)        # left_pane width
        self.gw    = game_cols - 2               # subtract │ border chars on each side
        # sh = game_widget rows + 2 footer rows
        # game_widget rows = gh + 2 (top ┌┐ and bottom └┘ borders)
        self.gh    = max(10, sh - 4)             # -2 footer -2 box borders
        self.paddle_base_w = max(6, self.gw // 7)
        self.paddle_w      = self.paddle_base_w
        self.paddle_x      = (self.gw - self.paddle_w) // 2

    def _init_game(self) -> None:
        self.dy_speed         = _DY_BASE
        self.balls            = [[float(self.gw // 2), float(self.gh - 4), 1.0, -_DY_BASE]]
        self.ball_trails      = [[]]   # trail per ball: list of (x, y) floats
        self.powerups         = []
        self.brick_row_offset = 1
        self.drift_timer      = 0
        self._init_bricks()

    def _init_bricks(self) -> None:
        self.bricks = _build_letter_bricks(self.gw, self.brick_row_offset)
        coords      = list(self.bricks.keys())
        n_secret    = max(1, len(coords) // 4)
        self.secret_bricks = set(random.sample(coords, min(n_secret, len(coords))))

    # ── Rendering ─────────────────────────────────────────────────────────────

    _ROW_COLORS = ["#FF5555", "#FFB84D", "#FFE066", "#5AA5FF", "#A8FF78"]

    # Each grid cell is a (char, color, bold) tuple or None for empty
    def _render_game(self) -> str:
        # Grid: None = empty, (ch, color, bold)
        grid: list[list] = [[None] * self.gw for _ in range(self.gh)]

        # Bricks
        for (r, c), _ in self.bricks.items():
            if 0 <= r < self.gh and 0 <= c < self.gw:
                ri    = (r - self.brick_row_offset) % FONT_ROWS
                color = self._ROW_COLORS[ri % len(self._ROW_COLORS)]
                char  = "▓" if (r, c) in self.secret_bricks else "█"
                grid[r][c] = (char, color, False)

        # Falling powerups
        for px, py, sym in self.powerups:
            ix, iy = int(px), int(py)
            if 0 <= iy < self.gh and 0 <= ix < self.gw:
                grid[iy][ix] = (sym, POWERUPS[sym][0], True)

        # Trails (before balls so ball overwrites)
        trail_chars  = ["·", "∘", "°"]
        trail_colors = ["#1a3a1a", "#1a4a2a", "#1e6e3e"]
        for trail in getattr(self, "ball_trails", []):
            for ti, (tx, ty) in enumerate(reversed(trail[-3:])):
                ix, iy = int(tx), int(ty)
                idx = min(ti, len(trail_chars) - 1)
                if 0 <= iy < self.gh and 0 <= ix < self.gw and grid[iy][ix] is None:
                    grid[iy][ix] = (trail_chars[idx], trail_colors[idx], False)

        # Paddle
        py_row  = self.gh - 2
        pw      = self.paddle_w
        hit_age = self.frame - self._paddle_hit_frame
        if hit_age < 3:
            glow = ["#FFEE00", "#FFFF55", "#FFFFFF", "#FFFF55", "#FFEE00"]
        elif hit_age < 5:
            glow = ["#FFB800", "#FFD700", "#FFEE00", "#FFD700", "#FFB800"]
        elif hit_age < 8:
            glow = ["#FF8800", "#FFAA00", "#FFCC00", "#FFAA00", "#FF8800"]
        else:
            speed_ratio = min(1.0, abs(self._paddle_vel) / 8.0)
            if speed_ratio > 0.6:
                glow = ["#00AAAA", "#00CCCC", "#00FFFF", "#88FFFF", "#FFFFFF"]
            elif speed_ratio > 0.2:
                glow = ["#1aaa3a", "#22dd55", "#33FF77", "#88ffaa", "#CCFFDD"]
            else:
                glow = ["#1a8a1a", "#21C93A", "#33FF55", "#66FF88", "#99FFAA"]
        for i, x in enumerate(range(self.paddle_x, self.paddle_x + pw)):
            if 0 <= x < self.gw:
                dist  = min(i, pw - 1 - i)
                color = glow[min(dist, len(glow) - 1)]
                if hit_age < 4 and (i == 0 or i == pw - 1):
                    ch = "✦"
                else:
                    ch = "▐" if i == 0 else ("▌" if i == pw - 1 else "▬")
                grid[py_row][x] = (ch, color, True)

        # Balls
        for bx, by, *_ in self.balls:
            fx = bx - int(bx)
            ch = "◐" if fx < 0.3 else ("◑" if fx > 0.7 else "●")
            ix, iy = int(bx), int(by)
            if 0 <= iy < self.gh and 0 <= ix < self.gw:
                grid[iy][ix] = (ch, "white", True)

        # Render to Rich markup string
        lines = [f"[#5AA5FF]┌{'─' * self.gw}┐[/#5AA5FF]"]
        for row in grid:
            cells = ""
            for cell in row:
                if cell is None:
                    cells += " "
                else:
                    ch, color, bold = cell
                    if bold:
                        cells += f"[bold {color}]{ch}[/bold {color}]"
                    else:
                        cells += f"[{color}]{ch}[/{color}]"
            lines.append(f"[#5AA5FF]│[/#5AA5FF]{cells}[#5AA5FF]│[/#5AA5FF]")
        lines.append(f"[#5AA5FF]└{'─' * self.gw}┘[/#5AA5FF]")
        return "\n".join(lines)

    def _render_footer(self) -> str:
        """HUD — two-row footer, text on second row for breathing room."""
        hearts     = "[#FF5555]" + "♥ " * self.lives + "[/#FF5555]"
        ball_count = f"[#FFE066]⊙×{len(self.balls)}[/#FFE066]"
        score      = f"[#FFB84D]{self.score} pts[/#FFB84D]"
        rows_left  = (self.gh - 4) - (self.brick_row_offset + FONT_ROWS)
        warn       = f"  [bold #FF5555]⚠ HURRY![/bold #FF5555]" if rows_left < 5 else ""
        if self.paused:
            status = "[bold #FFE066]⏸ PAUSED · P resume[/bold #FFE066]"
        else:
            status = "[#555555]←/→ move · P pause · Enter skip[/#555555]"
        return f"\n {hearts}  {ball_count}   {score}{warn}    {status}"

    def _render_info(self) -> str:
        lines = ["[bold #5AA5FF]─── about ───────────────────[/bold #5AA5FF]"]
        lines += list(_INFO_LINES)
        if self.paused:
            lines.append("")
            lines.append("[bold #FFE066]  ⏸ PAUSED[/bold #FFE066]")
            lines.append("[#FFE066]  P to resume[/#FFE066]")
        return "\n".join(lines)

    def _redraw(self) -> None:
        try:
            game_w   = self.query_one("#game_widget",   Static)
            footer_w = self.query_one("#footer_widget", Static)
            with self.app.batch_update():
                game_w.update(self._render_game())
                footer_w.update(self._render_footer())
                if self.frame % 20 == 0 or self.paused:
                    self.query_one("#info_pane", Static).update(self._render_info())
        except Exception:
            pass

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def on_mount(self) -> None:
        self._resize_to_screen()
        self._init_game()
        self._redraw()
        self._interval = self.set_interval(0.08, self._tick)

    def on_resize(self, _) -> None:
        self._resize_to_screen()
        self._init_game()
        self._redraw()

    def on_key(self, event) -> None:
        key = getattr(event, "key", "")
        if key in ("left", "h"):
            if self._last_dir == "left":
                self._press_count = min(self._press_count + 1, 10)
            else:
                self._press_count = 1
                self._last_dir = "left"
            step = 4 + self._press_count // 2
            self._paddle_vel = -float(step)
            self.paddle_x = max(0, self.paddle_x - step)
            # no _redraw() — tick handles it at 60ms
        elif key in ("right", "l"):
            if self._last_dir == "right":
                self._press_count = min(self._press_count + 1, 10)
            else:
                self._press_count = 1
                self._last_dir = "right"
            step = 4 + self._press_count // 2
            self._paddle_vel = float(step)
            self.paddle_x = min(self.gw - self.paddle_w, self.paddle_x + step)
            # no _redraw() — tick handles it at 60ms
        elif key == "p":
            self.paused = not self.paused
            self._redraw()  # immediate feedback for pause
        elif key in ("enter", "escape", "space"):
            self.dismiss()

    # ── Game tick ─────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        if self.paused:
            return
        self.frame += 1

        # Decay paddle glow velocity (visual only)
        self._paddle_vel *= 0.8
        if abs(self._paddle_vel) < 0.2:
            self._paddle_vel = 0.0

        # Drift every 120 ticks (~7 s)
        self.drift_timer += 1
        if self.drift_timer >= 120:
            self.drift_timer = 0
            self._drift_bricks()

        # Sync trails list length with balls
        while len(self.ball_trails) < len(self.balls):
            self.ball_trails.append([])
        while len(self.ball_trails) > len(self.balls):
            self.ball_trails.pop()

        # Move balls
        dead = []
        for i, ball in enumerate(self.balls):
            bx, by, dx, dy = ball

            # Record trail before moving
            self.ball_trails[i].append((bx, by))
            if len(self.ball_trails[i]) > 5:
                self.ball_trails[i].pop(0)

            bx += dx
            by += dy

            ix, iy = int(bx), int(by)

            # Side walls
            if bx <= 0:
                bx, dx = 0.0, abs(dx)
            elif bx >= self.gw - 1:
                bx, dx = float(self.gw - 1), -abs(dx)
            # Top wall
            if by <= 0:
                by, dy = 0.0, abs(dy)

            # Paddle — collision at gh-2 (where it's drawn)
            paddle_row = self.gh - 2
            if iy >= paddle_row and dy > 0:
                if self.paddle_x <= ix <= self.paddle_x + self.paddle_w:
                    by = float(paddle_row - 1)
                    dy = -self.dy_speed
                    rel = (ix - self.paddle_x) / max(1, self.paddle_w) - 0.5
                    dx  = max(-_DX_MAX, min(_DX_MAX, rel * 2.4))
                    if abs(dx) < 0.1:
                        dx = 0.3 if dx >= 0 else -0.3
                    self._paddle_hit_frame = self.frame  # trigger flash

            # Brick
            bx, by, dx, dy = self._check_brick(bx, by, dx, dy)

            if by >= self.gh - 1:
                dead.append(i)
            else:
                self.balls[i] = [bx, by, dx, dy]

        for i in sorted(dead, reverse=True):
            self.balls.pop(i)
            self.ball_trails.pop(i)

        if not self.balls:
            self.lives -= 1
            if self.lives <= 0:
                self.lives, self.score = 3, 0
                self._init_game()
            else:
                self._spawn_ball()

        # Move powerups
        paddle_row = self.gh - 2
        new_powerups = []
        for px, py, sym in self.powerups:
            py += 0.35
            if int(py) >= paddle_row:
                if self.paddle_x <= int(px) <= self.paddle_x + self.paddle_w:
                    self._apply_powerup(sym)
            elif py < self.gh:
                new_powerups.append([px, py, sym])
        self.powerups = new_powerups

        # All bricks gone
        if not self.bricks:
            self.score           += 200
            self.brick_row_offset = 1
            self._init_bricks()
            self._spawn_ball()

        self._redraw()

    def _drift_bricks(self) -> None:
        bottom_safe = self.gh - 3
        new_bricks, new_secret = {}, set()
        for (r, c), ch in self.bricks.items():
            nr = min(r + 1, bottom_safe)
            new_bricks[(nr, c)] = ch
            if (r, c) in self.secret_bricks:
                new_secret.add((nr, c))
        self.bricks        = new_bricks
        self.secret_bricks = new_secret
        self.brick_row_offset += 1

    def _check_brick(self, bx, by, dx, dy):
        ix, iy = int(bx), int(by)
        hit = None
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                k = (iy + dr, ix + dc)
                if k in self.bricks:
                    hit = k
                    break
            if hit:
                break
        if hit:
            hr, hc = hit
            is_secret = hit in self.secret_bricks
            del self.bricks[hit]
            self.secret_bricks.discard(hit)
            self.score += 10
            if is_secret:
                sym   = random.choice(POWERUP_KEYS)
                safe_x = float(max(0, min(self.gw - 1, hc)))
                self.powerups.append([safe_x, float(hr), sym])
            # Bounce
            if abs(hr - iy) >= abs(hc - ix):
                dy *= -1
            else:
                dx *= -1
        return bx, by, dx, dy

    def _spawn_ball(self) -> None:
        angle = random.choice([-0.9, -0.6, 0.6, 0.9])
        self.balls.append([
            float(self.gw // 2),
            float(self.gh - 4),
            angle,
            -self.dy_speed,
        ])
        self.ball_trails.append([])

    def _apply_powerup(self, sym: str) -> None:
        if sym == '+':
            self.paddle_w = min(self.gw - 4, self.paddle_w + 5)
        elif sym == '-':
            self.paddle_w = max(4, self.paddle_w - 4)
        elif sym == '2':
            self._spawn_ball()
        elif sym == '♥':
            self.lives = min(9, self.lives + 1)
        elif sym == '☠':
            self.lives -= 1
            if self.lives <= 0:
                self.lives, self.score = 3, 0
                self._init_game()
        elif sym == 'S':
            # Slow: reduce dy_speed, update all balls
            self.dy_speed = max(0.6, self.dy_speed - 0.15)
            for b in self.balls:
                b[3] = -self.dy_speed if b[3] < 0 else self.dy_speed
        elif sym == 'F':
            # Fast: increase dy_speed but hard-cap at _DY_MAX
            self.dy_speed = min(_DY_MAX, self.dy_speed + 0.15)
            for b in self.balls:
                b[3] = -self.dy_speed if b[3] < 0 else self.dy_speed


# ── Exit screen ───────────────────────────────────────────────────────────────

class ExitSplashScreen(Screen):
    """Exit splash screen with session summary"""

    DEFAULT_CSS = """
    Screen {
        background: #2e3440;
        color: #E8E8E8;
        align: center middle;
    }

    #exit_container {
        height: auto;
        width: 60;
        layout: vertical;
        align: center middle;
        background: #2e3440;
    }

    #exit_message {
        width: 60;
        height: auto;
        text-align: center;
        color: #E8E8E8;
    }
    """

    def __init__(self, session_stats: dict = None):
        super().__init__()
        self.session_stats = session_stats or {}

    def compose(self) -> ComposeResult:
        with Container(id="exit_container"):
            yield Static(self.render_exit_message(), id="exit_message")

    def render_exit_message(self):
        lines = [
            "[#5AA5FF][bold]Membria[/bold][/#5AA5FF]",
            "",
            "[#FFB84D]Session Summary[/#FFB84D]",
            f"[#21C93A]✓ Tasks completed: {self.session_stats.get('tasks_completed', 0)}[/#21C93A]",
            f"[#21C93A]✓ Decisions recorded: {self.session_stats.get('decisions_recorded', 0)}[/#21C93A]",
            f"[#FFB84D]📊 Tokens used: {self.session_stats.get('tokens_used', 0):,}[/#FFB84D]",
            f"[#E8E8E8]📈 Calibration updates: {self.session_stats.get('calibration_updates', 0)}[/#E8E8E8]",
            "",
            "[#999999]Graph is learning...[/#999999]",
        ]
        lines = ["[#5AA5FF]──────────────────────────────────────[/#5AA5FF]"] + lines + ["[#5AA5FF]──────────────────────────────────────[/#5AA5FF]"]
        return "\n".join(lines)

    def on_mount(self) -> None:
        self.set_timer(self._auto_dismiss, 3.0, count=1)

    def _auto_dismiss(self) -> None:
        self.dismiss()

    def on_key(self, _) -> None:
        self.dismiss()

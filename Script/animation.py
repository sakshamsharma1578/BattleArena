"""
animation.py
All visual effects: particles, floating text, hit flash, screen shake, transitions.
"""

import pygame
import random
import math


# ─────────────────────────────────────────────
#  FLOATING DAMAGE NUMBER
# ─────────────────────────────────────────────

class FloatingText:
    """A number or text that floats upward and fades out."""

    def __init__(self, text: str, x: int, y: int,
                 color=(255, 80, 80), font_size=28, duration=55):
        self.text = text
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.font_size = font_size
        self.duration = duration
        self.age = 0
        self.vy = -1.8          # upward drift speed
        self.vx = random.uniform(-0.5, 0.5)
        self.font = pygame.font.SysFont("Arial", font_size, bold=True)
        self.alive = True

    def update(self):
        self.age += 1
        self.y += self.vy
        self.x += self.vx
        self.vy *= 0.96         # decelerate
        if self.age >= self.duration:
            self.alive = False

    def draw(self, surface: pygame.Surface):
        alpha = max(0, 255 - int(255 * (self.age / self.duration)))
        r, g, b = self.color
        rendered = self.font.render(self.text, True, (r, g, b))
        rendered.set_alpha(alpha)
        surface.blit(rendered, (int(self.x) - rendered.get_width() // 2, int(self.y)))


# ─────────────────────────────────────────────
#  PARTICLE
# ─────────────────────────────────────────────

class Particle:
    """A single spark / ember particle."""

    def __init__(self, x, y, color, vx=None, vy=None, size=5, lifetime=40):
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.vx = vx if vx is not None else random.uniform(-3, 3)
        self.vy = vy if vy is not None else random.uniform(-4, -0.5)
        self.size = size
        self.lifetime = lifetime
        self.age = 0
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.18         # gravity
        self.vx *= 0.94
        self.age += 1
        self.size = max(1, self.size - 0.12)
        if self.age >= self.lifetime:
            self.alive = False

    def draw(self, surface: pygame.Surface):
        alpha_ratio = 1 - (self.age / self.lifetime)
        r = min(255, int(self.color[0]))
        g = min(255, int(self.color[1]))
        b = min(255, int(self.color[2]))
        pygame.draw.circle(surface, (r, g, b),
                           (int(self.x), int(self.y)), max(1, int(self.size)))


# ─────────────────────────────────────────────
#  HIT FLASH EFFECT
# ─────────────────────────────────────────────

class HitFlash:
    """Brief white/red flash over a character rect."""

    def __init__(self, rect: pygame.Rect, color=(255, 80, 80), duration=12):
        self.rect = rect
        self.color = color
        self.duration = duration
        self.age = 0
        self.alive = True

    def update(self):
        self.age += 1
        if self.age >= self.duration:
            self.alive = False

    def draw(self, surface: pygame.Surface):
        alpha = int(180 * (1 - self.age / self.duration))
        overlay = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        r, g, b = self.color
        overlay.fill((r, g, b, alpha))
        surface.blit(overlay, self.rect.topleft)


# ─────────────────────────────────────────────
#  SCREEN SHAKE
# ─────────────────────────────────────────────

class ScreenShake:
    """Camera shake effect."""

    def __init__(self, intensity=8, duration=20):
        self.intensity = intensity
        self.duration = duration
        self.age = 0
        self.alive = True
        self.offset = (0, 0)

    def update(self):
        self.age += 1
        if self.age >= self.duration:
            self.alive = False
            self.offset = (0, 0)
        else:
            decay = 1 - (self.age / self.duration)
            strength = int(self.intensity * decay)
            self.offset = (random.randint(-strength, strength),
                           random.randint(-strength, strength))

    @property
    def x(self):
        return self.offset[0]

    @property
    def y(self):
        return self.offset[1]


# ─────────────────────────────────────────────
#  SHAKE ANIMATION  (character wobble)
# ─────────────────────────────────────────────

class CharacterShake:
    """Horizontal wobble applied to a character sprite position."""

    def __init__(self, base_x: int, amplitude=12, duration=24):
        self.base_x = base_x
        self.amplitude = amplitude
        self.duration = duration
        self.age = 0
        self.alive = True

    def update(self):
        self.age += 1
        if self.age >= self.duration:
            self.alive = False

    @property
    def offset_x(self) -> int:
        if not self.alive:
            return 0
        t = self.age / self.duration
        decay = 1 - t
        return int(math.sin(self.age * 1.4) * self.amplitude * decay)


# ─────────────────────────────────────────────
#  FADE TRANSITION
# ─────────────────────────────────────────────

class FadeTransition:
    """Full-screen fade in/out."""

    def __init__(self, color=(0, 0, 0), mode="out", duration=30):
        self.color = color
        self.mode = mode            # "in" = fade from black, "out" = fade to black
        self.duration = duration
        self.age = 0
        self.alive = True

    def update(self):
        self.age += 1
        if self.age >= self.duration:
            self.alive = False

    @property
    def alpha(self) -> int:
        t = self.age / self.duration
        if self.mode == "out":
            return int(255 * t)
        else:
            return int(255 * (1 - t))

    def draw(self, surface: pygame.Surface):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        r, g, b = self.color
        overlay.fill((r, g, b, self.alpha))
        surface.blit(overlay, (0, 0))


# ─────────────────────────────────────────────
#  HEAL PULSE
# ─────────────────────────────────────────────

class HealPulse:
    """Expanding green ring around a character when healed."""

    def __init__(self, cx: int, cy: int, duration=35):
        self.cx = cx
        self.cy = cy
        self.duration = duration
        self.age = 0
        self.alive = True

    def update(self):
        self.age += 1
        if self.age >= self.duration:
            self.alive = False

    def draw(self, surface: pygame.Surface):
        t = self.age / self.duration
        radius = int(20 + 60 * t)
        alpha = int(200 * (1 - t))
        ring = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(ring, (80, 220, 100, alpha),
                           (radius + 2, radius + 2), radius, 3)
        surface.blit(ring, (self.cx - radius - 2, self.cy - radius - 2))


# ─────────────────────────────────────────────
#  ANIMATION MANAGER
# ─────────────────────────────────────────────

class AnimationManager:
    """Central manager — update and draw all active effects."""

    def __init__(self):
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.hit_flashes: list[HitFlash] = []
        self.shakes: list[CharacterShake] = []
        self.heal_pulses: list[HealPulse] = []
        self.screen_shake: ScreenShake | None = None
        self.fade: FadeTransition | None = None

    # ── Spawn helpers ──────────────────────────

    def spawn_particles(self, x, y, color, count=18, spread=30):
        for _ in range(count):
            px = x + random.randint(-spread, spread)
            py = y + random.randint(-spread // 2, spread // 2)
            self.particles.append(Particle(px, py, color))

    def spawn_damage(self, x, y, amount: int, is_crit=False):
        color = (255, 50, 50) if not is_crit else (255, 200, 50)
        size = 30 if not is_crit else 38
        text = f"-{amount}" if not is_crit else f"CRIT! -{amount}"
        self.floating_texts.append(FloatingText(text, x, y, color, size))

    def spawn_heal(self, x, y, amount: int):
        self.floating_texts.append(
            FloatingText(f"+{amount}", x, y, (80, 230, 100), 28))

    def spawn_status(self, x, y, text: str, color=(200, 200, 80)):
        self.floating_texts.append(FloatingText(text, x, y, color, 22, 70))

    def spawn_hit_flash(self, rect: pygame.Rect, color=(255, 80, 80)):
        self.hit_flashes.append(HitFlash(rect, color))

    def spawn_character_shake(self, base_x: int) -> CharacterShake:
        shake = CharacterShake(base_x)
        self.shakes.append(shake)
        return shake

    def spawn_screen_shake(self, intensity=8, duration=20):
        self.screen_shake = ScreenShake(intensity, duration)

    def spawn_heal_pulse(self, cx, cy):
        self.heal_pulses.append(HealPulse(cx, cy))

    def start_fade(self, mode="out", duration=30):
        self.fade = FadeTransition(mode=mode, duration=duration)

    @property
    def screen_offset(self) -> tuple[int, int]:
        if self.screen_shake and self.screen_shake.alive:
            return self.screen_shake.offset
        return (0, 0)

    def get_char_shake_offset(self, shake: CharacterShake | None) -> int:
        if shake and shake.alive:
            return shake.offset_x
        return 0

    # ── Update ─────────────────────────────────

    def update(self):
        for lst in (self.particles, self.floating_texts,
                    self.hit_flashes, self.shakes, self.heal_pulses):
            for item in lst:
                item.update()
            lst[:] = [item for item in lst if item.alive]

        if self.screen_shake:
            self.screen_shake.update()
        if self.fade:
            self.fade.update()
            if not self.fade.alive:
                self.fade = None

    # ── Draw ───────────────────────────────────

    def draw_behind_ui(self, surface: pygame.Surface):
        """Draw effects that should appear behind UI elements."""
        for p in self.particles:
            p.draw(surface)
        for hp in self.heal_pulses:
            hp.draw(surface)

    def draw_over_sprites(self, surface: pygame.Surface):
        """Draw hit flashes over sprites."""
        for hf in self.hit_flashes:
            hf.draw(surface)

    def draw_top(self, surface: pygame.Surface):
        """Draw floating numbers on top of everything."""
        for ft in self.floating_texts:
            ft.draw(surface)

    def draw_fade(self, surface: pygame.Surface):
        if self.fade:
            self.fade.draw(surface)

    def spawn_fire_particles(self, x, y, count=22):
        colors = [(255, 120, 20), (255, 60, 10), (220, 200, 40)]
        for _ in range(count):
            c = random.choice(colors)
            self.particles.append(
                Particle(x + random.randint(-20, 20),
                         y + random.randint(-10, 10), c,
                         vx=random.uniform(-1.5, 1.5),
                         vy=random.uniform(-3.5, -0.5),
                         size=random.randint(4, 8), lifetime=35))

    def spawn_ice_particles(self, x, y, count=20):
        colors = [(160, 220, 255), (200, 240, 255), (100, 180, 240)]
        for _ in range(count):
            c = random.choice(colors)
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.5, 4.0)
            self.particles.append(
                Particle(x, y, c,
                         vx=math.cos(angle) * speed,
                         vy=math.sin(angle) * speed - 2,
                         size=random.randint(3, 7), lifetime=30))

    def spawn_heal_particles(self, x, y, count=18):
        colors = [(60, 220, 100), (100, 255, 140), (180, 255, 180)]
        for _ in range(count):
            c = random.choice(colors)
            self.particles.append(
                Particle(x + random.randint(-25, 25),
                         y + random.randint(-15, 15), c,
                         vx=random.uniform(-1, 1),
                         vy=random.uniform(-3, -0.2),
                         size=random.randint(3, 6), lifetime=45))

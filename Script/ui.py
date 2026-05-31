"""
ui.py
All UI rendering: buttons, health/mp bars, combat log, character cards,
ability buttons, status badges, panels.
"""

import pygame
import math

# ─────────────────────────────────────────────
#  PALETTE
# ─────────────────────────────────────────────

C = {
    "bg":          (10,  10,  18),
    "panel":       (18,  18,  30),
    "panel2":      (24,  24,  40),
    "border":      (45,  45,  70),
    "border_gold": (180, 150, 60),
    "gold":        (210, 175, 80),
    "gold_light":  (240, 210, 120),
    "text":        (230, 225, 210),
    "text_muted":  (140, 135, 160),
    "text_dim":    (90,  88, 110),
    "hp_bg":       (60,  20,  20),
    "hp_fill":     (60, 200, 80),
    "hp_low":      (220, 70,  40),
    "hp_mid":      (220, 180, 40),
    "mp_bg":       (20,  20,  60),
    "mp_fill":     (70, 130, 220),
    "red":         (220, 70,  60),
    "green":       (60, 200, 80),
    "blue":        (70, 130, 220),
    "purple":      (160, 80, 220),
    "orange":      (220, 130, 40),
    "white":       (255, 255, 255),
    "black":       (0,   0,   0),
    "overlay":     (0,   0,   0, 160),
    "btn_idle":    (28,  28,  46),
    "btn_hover":   (38,  38,  62),
    "btn_press":   (50,  50,  80),
    "btn_border":  (60,  60,  95),
    "btn_border_h":(160, 140, 60),
    "log_bg":      (14,  14,  24),
    "log_border":  (38,  38,  60),
    "burn":        (220, 100, 40),
    "poison":      (100, 200, 60),
    "stun":        (210, 210, 60),
    "regen":       (60, 210, 100),
    "shield":      (80, 140, 220),
    "freeze":      (160, 220, 255),
    "weaken":      (210, 200, 60),
}

STATUS_COLORS = {
    "Burn":    C["burn"],
    "Poison":  C["poison"],
    "Stun":    C["stun"],
    "Freeze":  C["freeze"],
    "Regen":   C["regen"],
    "Shield":  C["shield"],
    "Weaken":  C["weaken"],
}

ABILITY_TYPE_COLORS = {
    "attack":  (200, 70,  60),
    "heal":    (60, 200, 90),
    "special": (160, 80, 220),
}


# ─────────────────────────────────────────────
#  FONT CACHE
# ─────────────────────────────────────────────

_font_cache: dict = {}

def get_font(size: int, bold=False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _font_cache:
        try:
            _font_cache[key] = pygame.font.Font(None, size)
        except Exception:
            _font_cache[key] = pygame.font.SysFont("Arial", size, bold=bold)
    return _font_cache[key]


# ─────────────────────────────────────────────
#  HELPER DRAWING FUNCTIONS
# ─────────────────────────────────────────────

def draw_rect_alpha(surface, color_with_alpha, rect, radius=0):
    """Draw a rectangle with optional per-surface alpha."""
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    if len(color_with_alpha) == 4:
        s.fill(color_with_alpha)
    else:
        s.fill((*color_with_alpha, 255))
    if radius > 0:
        mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255),
                         (0, 0, rect.width, rect.height), border_radius=radius)
        s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(s, rect.topleft)


def draw_rounded_rect(surface, color, rect, radius=8, border_color=None, border_width=1):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border_color:
        pygame.draw.rect(surface, border_color, rect, border_width, border_radius=radius)


def draw_text(surface, text, font, color, x, y, anchor="topleft"):
    rendered = font.render(str(text), True, color)
    rect = rendered.get_rect()
    setattr(rect, anchor, (x, y))
    surface.blit(rendered, rect)
    return rect


def draw_text_shadow(surface, text, font, color, x, y, anchor="topleft",
                     shadow_color=(0, 0, 0), shadow_offset=2):
    draw_text(surface, text, font, shadow_color,
              x + shadow_offset, y + shadow_offset, anchor)
    return draw_text(surface, text, font, color, x, y, anchor)


# ─────────────────────────────────────────────
#  BUTTON
# ─────────────────────────────────────────────

class Button:
    def __init__(self, rect: pygame.Rect, label: str,
                 font_size=22, icon="", color_override=None,
                 border_radius=8, tooltip=""):
        self.rect = rect
        self.label = label
        self.font_size = font_size
        self.icon = icon
        self.color_override = color_override
        self.border_radius = border_radius
        self.tooltip = tooltip
        self.hovered = False
        self.pressed = False
        self.enabled = True

    def handle_event(self, event) -> bool:
        """Returns True if button was clicked."""
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.rect.collidepoint(event.pos):
                self.pressed = False
                return True
            self.pressed = False
        return False

    def draw(self, surface: pygame.Surface):
        if not self.enabled:
            bg = tuple(max(0, c - 20) for c in C["panel"])
            border = C["border"]
            text_color = C["text_dim"]
        elif self.pressed:
            bg = C["btn_press"]
            border = C["gold"]
            text_color = C["gold_light"]
        elif self.hovered:
            bg = self.color_override or C["btn_hover"]
            border = C["btn_border_h"]
            text_color = C["gold_light"]
        else:
            bg = self.color_override or C["btn_idle"]
            border = C["btn_border"]
            text_color = C["text"]

        draw_rounded_rect(surface, bg, self.rect,
                          self.border_radius, border, 1)

        font = get_font(self.font_size, bold=True)
        full_label = f"{self.icon} {self.label}".strip() if self.icon else self.label
        draw_text_shadow(surface, full_label, font, text_color,
                         self.rect.centerx, self.rect.centery, "center")

        # Tooltip
        if self.hovered and self.tooltip:
            tip_font = get_font(16)
            tip = tip_font.render(self.tooltip, True, C["text"])
            tip_rect = tip.get_rect(midtop=(self.rect.centerx, self.rect.top - 28))
            tip_bg = tip_rect.inflate(12, 6)
            draw_rounded_rect(surface, C["panel2"], tip_bg, 5, C["border"])
            surface.blit(tip, tip_rect)


# ─────────────────────────────────────────────
#  ABILITY BUTTON
# ─────────────────────────────────────────────

class AbilityButton(Button):
    def __init__(self, rect, ability, index):
        super().__init__(rect, ability.name, font_size=17,
                         tooltip=ability.description)
        self.ability = ability
        self.index = index

    def draw(self, surface: pygame.Surface):
        ab = self.ability
        on_cd = ab.current_cd > 0
        no_mp = False  # Set externally

        if not self.enabled or on_cd:
            bg = (18, 18, 28)
            border = C["border"]
            text_col = C["text_dim"]
        elif self.pressed:
            bg = C["btn_press"]
            border = C["gold"]
            text_col = C["white"]
        elif self.hovered:
            bg = C["btn_hover"]
            border = C["btn_border_h"]
            text_col = C["gold_light"]
        else:
            bg = C["btn_idle"]
            border = ABILITY_TYPE_COLORS.get(ab.type, C["border"])
            text_col = C["text"]

        draw_rounded_rect(surface, bg, self.rect, 6, border, 1)

        # Icon
        icon_font = get_font(22)
        draw_text(surface, ab.icon, icon_font, text_col,
                  self.rect.x + 10, self.rect.centery, "midleft")

        # Name
        name_font = get_font(17, bold=True)
        draw_text(surface, ab.name, name_font, text_col,
                  self.rect.x + 36, self.rect.y + 6)

        # MP cost
        mp_font = get_font(14)
        mp_text = f"MP:{ab.mp_cost}" if ab.mp_cost > 0 else "Free"
        mp_col = C["blue"] if ab.mp_cost > 0 else C["green"]
        draw_text(surface, mp_text, mp_font, mp_col,
                  self.rect.x + 36, self.rect.bottom - 18)

        # Cooldown overlay
        if on_cd:
            draw_rect_alpha(surface, (0, 0, 0, 140), self.rect, 6)
            cd_font = get_font(20, bold=True)
            draw_text(surface, f"CD {ab.current_cd}", cd_font, C["red"],
                      self.rect.centerx, self.rect.centery, "center")

        # Tooltip
        if self.hovered and self.tooltip:
            tip_font = get_font(15)
            tip = tip_font.render(self.tooltip, True, C["text"])
            tip_rect = tip.get_rect(midbottom=(self.rect.centerx, self.rect.top - 4))
            tip_bg = tip_rect.inflate(12, 6)
            draw_rounded_rect(surface, C["panel2"], tip_bg, 5, C["border"])
            surface.blit(tip, tip_rect)


# ─────────────────────────────────────────────
#  HEALTH / MP BAR
# ─────────────────────────────────────────────

def draw_bar(surface, rect, value, max_value,
             fill_color, bg_color, border_color=None,
             show_text=True, font_size=15, label=""):
    """Draw a value/max bar with optional label."""
    pygame.draw.rect(surface, bg_color, rect, border_radius=4)
    if max_value > 0:
        ratio = max(0.0, min(1.0, value / max_value))
        fill_w = int(rect.width * ratio)
        if fill_w > 0:
            fill_rect = pygame.Rect(rect.x, rect.y, fill_w, rect.height)
            pygame.draw.rect(surface, fill_color, fill_rect, border_radius=4)
    if border_color:
        pygame.draw.rect(surface, border_color, rect, 1, border_radius=4)
    if show_text and label:
        f = get_font(font_size)
        draw_text(surface, label, f, C["text"],
                  rect.centerx, rect.centery, "center")


def draw_hp_bar(surface, x, y, w, h, hp, max_hp, label=True):
    ratio = hp / max_hp if max_hp > 0 else 0
    if ratio > 0.5:
        fill_col = C["hp_fill"]
    elif ratio > 0.25:
        fill_col = C["hp_mid"]
    else:
        fill_col = C["hp_low"]

    rect = pygame.Rect(x, y, w, h)
    draw_bar(surface, rect, hp, max_hp, fill_col, C["hp_bg"],
             C["border"], show_text=label,
             label=f"{int(hp)}/{max_hp}")


def draw_mp_bar(surface, x, y, w, h, mp, max_mp):
    rect = pygame.Rect(x, y, w, h)
    draw_bar(surface, rect, mp, max_mp, C["mp_fill"], C["mp_bg"],
             C["border"], show_text=True, font_size=13,
             label=f"MP {int(mp)}/{max_mp}")


# ─────────────────────────────────────────────
#  STATUS BADGES
# ─────────────────────────────────────────────

def draw_status_badges(surface, statuses, x, y):
    """Draw small colored status icons in a row."""
    bx = x
    for status in statuses:
        col = STATUS_COLORS.get(status.name, C["text_muted"])
        badge_rect = pygame.Rect(bx, y, 38, 20)
        draw_rounded_rect(surface, tuple(max(0, c // 3) for c in col),
                          badge_rect, 4, col, 1)
        f = get_font(13)
        label = f"{status.icon}{status.duration}"
        draw_text(surface, label, f, col,
                  badge_rect.centerx, badge_rect.centery, "center")
        bx += 42


# ─────────────────────────────────────────────
#  COMBAT LOG
# ─────────────────────────────────────────────

class CombatLog:
    def __init__(self, rect: pygame.Rect, max_lines=7):
        self.rect = rect
        self.max_lines = max_lines
        self.lines: list[tuple[str, tuple]] = []  # (text, color)
        self.font = get_font(16)

    def add(self, text: str, color=None):
        if color is None:
            color = C["text"]
        # Wrap long lines
        max_chars = self.rect.width // 8
        while len(text) > max_chars:
            self.lines.append((text[:max_chars], color))
            text = "  " + text[max_chars:]
        self.lines.append((text, color))
        if len(self.lines) > self.max_lines * 3:
            self.lines = self.lines[-(self.max_lines * 3):]

    def clear(self):
        self.lines.clear()

    def draw(self, surface: pygame.Surface):
        draw_rounded_rect(surface, C["log_bg"], self.rect, 8, C["log_border"])
        visible = self.lines[-self.max_lines:]
        for i, (text, color) in enumerate(visible):
            brightness = 1.0 if i == len(visible) - 1 else max(0.4, 1 - (len(visible) - 1 - i) * 0.15)
            faded_color = tuple(int(c * brightness) for c in color[:3])
            y = self.rect.y + 8 + i * 19
            if y + 18 < self.rect.bottom:
                draw_text(surface, text, self.font, faded_color, self.rect.x + 10, y)


# ─────────────────────────────────────────────
#  CHARACTER SELECTION CARD
# ─────────────────────────────────────────────

class CharSelectCard:
    CARD_W = 150
    CARD_H = 185

    def __init__(self, char_class, x, y, sprite_img=None):
        self.char_class = char_class
        self.sprite_img = sprite_img
        self.rect = pygame.Rect(x, y, self.CARD_W, self.CARD_H)
        self.selected = False
        self.hovered = False

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surface: pygame.Surface, anim_t=0):
        # Hover lift
        offset_y = -4 if self.hovered else 0
        rect = self.rect.move(0, offset_y)

        border_col = C["gold"] if self.selected else (C["btn_border_h"] if self.hovered else C["border"])
        bg_col = (32, 30, 52) if self.selected else (C["btn_hover"] if self.hovered else C["panel"])

        draw_rounded_rect(surface, bg_col, rect, 10, border_col, 2 if self.selected else 1)

        # Glow when selected
        if self.selected:
            glow_surf = pygame.Surface((rect.width + 16, rect.height + 16), pygame.SRCALPHA)
            pulse = int(30 + 20 * math.sin(anim_t * 3))
            pygame.draw.rect(glow_surf, (*C["gold"], pulse),
                             (0, 0, rect.width + 16, rect.height + 16), border_radius=14)
            surface.blit(glow_surf, (rect.x - 8, rect.y - 8))
            draw_rounded_rect(surface, bg_col, rect, 10, border_col, 2)

        # Sprite or placeholder
        img_rect = pygame.Rect(rect.x + 15, rect.y + 10, 120, 90)
        if self.sprite_img:
            scaled = pygame.transform.smoothscale(self.sprite_img, (120, 90))
            surface.blit(scaled, img_rect)
        else:
            # Colored placeholder with character initial
            draw_rounded_rect(surface, self.char_class.COLOR, img_rect, 6)
            big_font = get_font(44, bold=True)
            draw_text(surface, self.char_class.NAME[0], big_font,
                      (255, 255, 255), img_rect.centerx, img_rect.centery, "center")

        # Name
        name_font = get_font(18, bold=True)
        draw_text_shadow(surface, self.char_class.NAME, name_font, C["gold"],
                         rect.centerx, rect.y + 107, "midtop")

        # Class label
        cls_font = get_font(13)
        draw_text(surface, self.char_class.CLASS_LABEL, cls_font, C["text_muted"],
                  rect.centerx, rect.y + 127, "midtop")

        # Stats
        stat_font = get_font(13)
        hp_str = f"HP:{self.char_class.MAX_HP}"
        atk_str = f"ATK:{self.char_class.BASE_ATK}"
        def_str = f"DEF:{self.char_class.BASE_DEF}"
        y_stat = rect.y + 146
        draw_text(surface, hp_str, stat_font, C["red"], rect.x + 8, y_stat)
        draw_text(surface, atk_str, stat_font, C["orange"], rect.x + 58, y_stat)
        draw_text(surface, def_str, stat_font, C["blue"], rect.x + 108, y_stat)

        # Selected checkmark
        if self.selected:
            check_font = get_font(16, bold=True)
            draw_text(surface, "✓ SELECTED", check_font, C["gold"],
                      rect.centerx, rect.bottom - 16, "midbottom")


# ─────────────────────────────────────────────
#  PANEL DRAWING HELPERS
# ─────────────────────────────────────────────

def draw_panel(surface, rect, title="", color=None):
    bg = color or C["panel"]
    draw_rounded_rect(surface, bg, rect, 10, C["border"])
    if title:
        f = get_font(18, bold=True)
        draw_text_shadow(surface, title, f, C["gold"],
                         rect.x + 12, rect.y + 8)


def draw_divider(surface, x1, y, x2, color=None):
    col = color or C["border"]
    pygame.draw.line(surface, col, (x1, y), (x2, y), 1)


def draw_round_indicator(surface, rect, round_num, player_turn):
    draw_rounded_rect(surface, C["panel2"], rect, 8, C["border"])
    f_round = get_font(15)
    f_turn = get_font(17, bold=True)
    draw_text(surface, f"Round {round_num}", f_round, C["text_muted"],
              rect.centerx, rect.y + 6, "midtop")
    turn_text = "YOUR TURN" if player_turn else "ENEMY TURN"
    turn_col = C["green"] if player_turn else C["red"]
    draw_text(surface, turn_text, f_turn, turn_col,
              rect.centerx, rect.centery + 4, "center")


def draw_character_panel(surface, rect, character, is_player, shake_offset=0):
    """Draw the full character combat panel (stats, bars, statuses)."""
    draw_rounded_rect(surface, C["panel"], rect, 10, C["border"])

    lx = rect.x + shake_offset

    # Name + class
    name_font = get_font(20, bold=True)
    draw_text_shadow(surface, character.name, name_font,
                     character.color, lx + 10, rect.y + 8)
    cls_font = get_font(14)
    draw_text(surface, character.class_label, cls_font, C["text_muted"],
              lx + 10, rect.y + 31)

    # HP bar
    bar_w = rect.width - 20
    draw_hp_bar(surface, lx + 10, rect.y + 52, bar_w, 16,
                character.hp, character.max_hp)

    # MP bar
    draw_mp_bar(surface, lx + 10, rect.y + 72, bar_w, 10,
                character.mp, character.max_mp)

    # Status badges
    if character.statuses:
        draw_status_badges(surface, character.statuses, lx + 10, rect.y + 88)

"""
main.py
Battle Arena — Turn-Based Combat Game
Entry point. Manages the game loop and all state transitions.

States:
  MENU           -> character/enemy/difficulty selection
  BATTLE         -> active combat
  END            -> win/loss summary
"""

import pygame
import sys
import os
import math
import random

from character import ALL_CHARACTERS, Character
from animation import AnimationManager
from ui import (
    C, Button, AbilityButton, CombatLog, CharSelectCard,
    draw_panel, draw_round_indicator, draw_hp_bar, draw_mp_bar,
    draw_character_panel, draw_text, draw_text_shadow,
    draw_rounded_rect, draw_divider, get_font
)

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────

WINDOW_W, WINDOW_H = 900, 580
FPS = 60
TITLE = "Battle Arena"

# Layout regions (battle screen)
TOP_PANEL_H   = 115     # character stat panels
ARENA_Y       = TOP_PANEL_H + 10
ARENA_H       = 220     # sprite display area
BOTTOM_Y      = ARENA_Y + ARENA_H + 10
BOTTOM_H      = WINDOW_H - BOTTOM_Y - 8

# Character panel widths
CHAR_PANEL_W  = 310
LOG_X         = CHAR_PANEL_W + 10
LOG_W         = WINDOW_W - CHAR_PANEL_W * 2 - 20
ABILITY_BTN_H = 52
ABILITY_BTN_W = 200


# ─────────────────────────────────────────────
#  ASSET LOADER
# ─────────────────────────────────────────────

class AssetManager:
    def __init__(self, base_dir: str):
        self.img_dir = os.path.join(base_dir, "assets", "images")
        self.snd_dir = os.path.join(base_dir, "assets", "sounds")
        self._images: dict[str, pygame.Surface | None] = {}
        self._sounds: dict[str, pygame.mixer.Sound | None] = {}
        self._music_loaded = False

    def load_sprite(self, filename: str, size=(160, 180)) -> pygame.Surface | None:
        if filename in self._images:
            return self._images[filename]
        path = os.path.join(self.img_dir, filename)
        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, size)
            self._images[filename] = img
            return img
        except Exception:
            self._images[filename] = None
            return None

    def load_sound(self, key: str, filename: str) -> pygame.mixer.Sound | None:
        if key in self._sounds:
            return self._sounds[key]
        path = os.path.join(self.snd_dir, filename)
        try:
            snd = pygame.mixer.Sound(path)
            snd.set_volume(0.5)
            self._sounds[key] = snd
            return snd
        except Exception:
            self._sounds[key] = None
            return None

    def play_sound(self, key: str):
        snd = self._sounds.get(key)
        if snd:
            snd.play()

    def play_music(self, filename: str, loops=-1):
        path = os.path.join(self.snd_dir, filename)
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(loops)
            self._music_loaded = True
        except Exception:
            pass

    def stop_music(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass


# ─────────────────────────────────────────────
#  GAME CLASS
# ─────────────────────────────────────────────

class Game:
    # ── Init ──────────────────────────────────

    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        base = os.path.dirname(os.path.abspath(__file__))
        self.assets = AssetManager(base)
        self.anim = AnimationManager()

        # Load sounds
        self._load_sounds()

        # State machine
        self.state = "MENU"          # MENU | BATTLE | END

        # Game data
        self.player: Character | None = None
        self.enemy: Character | None = None
        self.difficulty = "Normal"
        self.player_turn = True
        self.round_num = 1
        self.battle_log = CombatLog(pygame.Rect(0, 0, 10, 10))  # resized later
        self.enemy_turn_timer = 0
        self.pending_result: str | None = None   # "win" | "lose"

        # Stats
        self.stat_dmg_dealt = 0
        self.stat_healed = 0

        # Ability buttons (rebuilt each battle)
        self.ability_buttons: list[AbilityButton] = []

        # Character selection
        self.player_cards: list[CharSelectCard] = []
        self.enemy_cards: list[CharSelectCard] = []
        self.selected_player_cls = None
        self.selected_enemy_cls = None
        self.sel_page = 0                # 0 = choose player, 1 = choose enemy
        self.difficulty_buttons: list[Button] = []

        # Shake references
        self.player_shake = None
        self.enemy_shake = None

        # UI clock for animations
        self.anim_t = 0.0

        # Background star field
        self.stars = [(random.randint(0, WINDOW_W), random.randint(0, WINDOW_H),
                       random.uniform(0.3, 1.5)) for _ in range(120)]

        self._build_menu_ui()

    def _load_sounds(self):
        sfx = [
            ("attack",  "attack.wav"),
            ("heal",    "heal.wav"),
            ("special", "special.wav"),
            ("click",   "click.wav"),
            ("win",     "win.wav"),
            ("lose",    "lose.wav"),
        ]
        for key, fname in sfx:
            self.assets.load_sound(key, fname)
        self.assets.play_music("battle_music.ogg")

    # ── Menu / Selection UI ───────────────────

    def _build_menu_ui(self):
        # Two rows of 5 character cards
        all_chars = ALL_CHARACTERS
        self.player_cards = []
        self.enemy_cards = []

        cols = 5
        card_w = CharSelectCard.CARD_W
        card_h = CharSelectCard.CARD_H
        gap = 12
        row_w = cols * card_w + (cols - 1) * gap
        start_x = (WINDOW_W - row_w) // 2
        row1_y = 200
        row2_y = row1_y + card_h + 16

        for i, cls in enumerate(all_chars):
            cx = start_x + i * (card_w + gap)
            sprite = self.assets.load_sprite(cls.SPRITE_FILE, (120, 90))
            pc = CharSelectCard(cls, cx, row1_y, sprite)
            ec = CharSelectCard(cls, cx, row2_y, sprite)
            self.player_cards.append(pc)
            self.enemy_cards.append(ec)

        # Difficulty buttons
        diffs = ["Easy", "Normal", "Hard"]
        dbw, dbh = 90, 34
        dy = WINDOW_H - 80
        total_w = len(diffs) * dbw + (len(diffs) - 1) * 12
        dx = (WINDOW_W - total_w) // 2
        self.difficulty_buttons = []
        for d in diffs:
            r = pygame.Rect(dx, dy, dbw, dbh)
            btn = Button(r, d, font_size=17)
            if d == self.difficulty:
                btn.hovered = False
            self.difficulty_buttons.append(btn)
            dx += dbw + 12

        # Start button
        self.btn_start = Button(
            pygame.Rect(WINDOW_W // 2 - 100, WINDOW_H - 38, 200, 32),
            "ENTER THE ARENA", font_size=19, icon="⚔")

    def _build_battle_ui(self):
        """Create ability buttons for the current player character."""
        self.ability_buttons = []
        if not self.player:
            return
        btn_y = BOTTOM_Y + 4
        for i, ab in enumerate(self.player.abilities):
            bx = 6 + i * (ABILITY_BTN_W + 6)
            r = pygame.Rect(bx, btn_y, ABILITY_BTN_W, ABILITY_BTN_H)
            self.ability_buttons.append(AbilityButton(r, ab, i))

        # Combat log
        log_y = BOTTOM_Y
        log_x = 6 + len(self.player.abilities) * (ABILITY_BTN_W + 6) + 8
        log_w = WINDOW_W - log_x - 6
        log_h = BOTTOM_H
        self.battle_log = CombatLog(
            pygame.Rect(log_x, log_y, log_w, log_h), max_lines=7)

    # ── Main Loop ─────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.anim_t += dt
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self._handle_event(event)

            self._update(dt)
            self._draw()

    # ── Event Handling ────────────────────────

    def _handle_event(self, event):
        if self.state == "MENU":
            self._menu_events(event)
        elif self.state == "BATTLE":
            self._battle_events(event)
        elif self.state == "END":
            self._end_events(event)

    def _menu_events(self, event):
        for i, card in enumerate(self.player_cards):
            if card.handle_event(event):
                for c in self.player_cards:
                    c.selected = False
                card.selected = True
                self.selected_player_cls = card.char_class
                self.assets.play_sound("click")

        for i, card in enumerate(self.enemy_cards):
            if card.handle_event(event):
                for c in self.enemy_cards:
                    c.selected = False
                card.selected = True
                self.selected_enemy_cls = card.char_class
                self.assets.play_sound("click")

        for i, btn in enumerate(self.difficulty_buttons):
            if btn.handle_event(event):
                self.difficulty = ["Easy", "Normal", "Hard"][i]
                for b in self.difficulty_buttons:
                    b.color_override = None
                btn.color_override = (40, 40, 65)
                self.assets.play_sound("click")

        if self.btn_start.handle_event(event):
            if self.selected_player_cls and self.selected_enemy_cls:
                self._start_battle()

    def _battle_events(self, event):
        if not self.player_turn:
            return
        if self.player and self.player.is_stunned:
            return

        for btn in self.ability_buttons:
            if not btn.enabled:
                continue
            if btn.handle_event(event):
                self._player_use_ability(btn.ability)
                break
        # Update hover state
        for btn in self.ability_buttons:
            btn.handle_event(event)

    def _end_events(self, event):
        if hasattr(self, "btn_play_again") and self.btn_play_again.handle_event(event):
            self.assets.play_sound("click")
            self._go_menu()
        if hasattr(self, "btn_rematch") and self.btn_rematch.handle_event(event):
            self.assets.play_sound("click")
            self._start_battle()

    # ── Battle Logic ──────────────────────────

    def _start_battle(self):
        self.player = self.selected_player_cls()
        self.enemy = self.selected_enemy_cls()
        self.player_turn = True
        self.round_num = 1
        self.stat_dmg_dealt = 0
        self.stat_healed = 0
        self.enemy_turn_timer = 0
        self.pending_result = None
        self.player_shake = None
        self.enemy_shake = None

        self._build_battle_ui()
        self._update_ability_buttons()
        self.battle_log.clear()
        self.battle_log.add(
            f"⚔  {self.player.name} vs {self.enemy.name}!  Battle begins!", C["gold"])
        self.battle_log.add(f"  Difficulty: {self.difficulty}", C["text_muted"])

        self.anim.start_fade("in", 25)
        self.state = "BATTLE"

    def _player_use_ability(self, ability):
        if not self.player_turn:
            return
        if ability.current_cd > 0 or self.player.mp < ability.mp_cost:
            return

        self.assets.play_sound(ability.sound_key)
        result = self.player.use_ability(ability, self.enemy)

        # Log messages
        for msg in result["messages"]:
            color = self._msg_color(result)
            self.battle_log.add(msg, color)

        # Spawn effects
        enemy_cx = WINDOW_W - 160
        enemy_cy = ARENA_Y + 100
        self._spawn_ability_effects(result, enemy_cx, enemy_cy, is_player_hitting=True)

        if result["damage"] > 0:
            self.stat_dmg_dealt += result["damage"]
            self.anim.spawn_damage(enemy_cx, enemy_cy - 40,
                                   result["damage"], result.get("crit", False))
            self.anim.spawn_screen_shake(6, 15)
            self.enemy_shake = self.anim.spawn_character_shake(enemy_cx)

        if result["heal"] > 0:
            self.stat_healed += result["heal"]
            player_cx = 160
            player_cy = ARENA_Y + 100
            self.anim.spawn_heal(player_cx, player_cy - 40, result["heal"])
            self.anim.spawn_heal_pulse(player_cx, player_cy)
            self.anim.spawn_heal_particles(player_cx, player_cy)

        self._check_end()
        if self.state != "BATTLE":
            return

        self._update_ability_buttons()
        self.player_turn = False
        self.enemy_turn_timer = FPS // 2      # delay before enemy acts

    def _enemy_turn(self):
        if not self.enemy or not self.player:
            return

        # Tick statuses for both at round start
        p_msgs = self.player.tick_statuses()
        e_msgs = self.enemy.tick_statuses()
        for m in p_msgs + e_msgs:
            self.battle_log.add(m, C["text_muted"])

        self._check_end()
        if self.state != "BATTLE":
            return

        # Check stun
        if self.enemy.is_stunned:
            self.battle_log.add(f"⚡ {self.enemy.name} is stunned! Loses turn.", C["stun"])
            self._end_enemy_turn()
            return

        ability = self.enemy.ai_choose_ability(self.player, self.difficulty)
        self.assets.play_sound(ability.sound_key)
        result = self.enemy.use_ability(ability, self.player)

        for msg in result["messages"]:
            self.battle_log.add(msg, self._msg_color(result))

        player_cx = 160
        player_cy = ARENA_Y + 100
        self._spawn_ability_effects(result, player_cx, player_cy, is_player_hitting=False)

        if result["damage"] > 0:
            self.anim.spawn_damage(player_cx, player_cy - 40, result["damage"])
            self.anim.spawn_screen_shake(5, 12)
            self.player_shake = self.anim.spawn_character_shake(player_cx)

        if result["heal"] > 0:
            enemy_cx = WINDOW_W - 160
            enemy_cy = ARENA_Y + 100
            self.anim.spawn_heal(enemy_cx, enemy_cy - 40, result["heal"])
            self.anim.spawn_heal_pulse(enemy_cx, enemy_cy)

        self._check_end()
        if self.state != "BATTLE":
            return

        self._end_enemy_turn()

    def _end_enemy_turn(self):
        # Tick cooldowns
        self.player.tick_cooldowns()
        self.enemy.tick_cooldowns()
        self.player.regen_mp(8)
        self.enemy.regen_mp(8)
        self.round_num += 1
        self.player_turn = True

        # Handle player stun
        if self.player.is_stunned:
            msgs = self.player.tick_statuses()
            for m in msgs:
                self.battle_log.add(m, C["stun"])
            self.player.tick_cooldowns()
            self.player.regen_mp(4)
            self.player_turn = True

        self._update_ability_buttons()

    def _update_ability_buttons(self):
        if not self.player:
            return
        for btn in self.ability_buttons:
            ab = btn.ability
            on_cd = ab.current_cd > 0
            no_mp = self.player.mp < ab.mp_cost
            btn.enabled = self.player_turn and not on_cd and not no_mp and not self.player.is_stunned

    def _check_end(self):
        if self.enemy and self.enemy.hp <= 0:
            self._trigger_end("win")
        elif self.player and self.player.hp <= 0:
            self._trigger_end("lose")

    def _trigger_end(self, result: str):
        self.pending_result = result
        self.assets.play_sound("win" if result == "win" else "lose")
        self.anim.start_fade("out", 35)
        # Transition after fade
        pygame.time.set_timer(pygame.USEREVENT + 1, 800, 1)
        self.state = "END_FADE"

    def _msg_color(self, result: dict) -> tuple:
        if result.get("damage", 0) > 0:
            return C["red"] if result.get("crit") else (210, 130, 130)
        if result.get("heal", 0) > 0:
            return C["green"]
        return C["text"]

    def _spawn_ability_effects(self, result, cx, cy, is_player_hitting):
        dmg = result.get("damage", 0)
        animation = result.get("animation", "attack")

        if dmg > 0:
            if animation == "attack":
                col = self.player.color if is_player_hitting else self.enemy.color
                self.anim.spawn_particles(cx, cy, col, count=20)
                hit_rect = pygame.Rect(cx - 80, cy - 90, 160, 180)
                self.anim.spawn_hit_flash(hit_rect)
            elif animation == "special":
                # Check what kind
                pass

        # Specific effects by result type
        msgs = " ".join(result.get("messages", []))
        if "burn" in msgs.lower() or "igni" in msgs.lower() or "fire" in msgs.lower():
            self.anim.spawn_fire_particles(cx, cy - 20, 25)
        if "freeze" in msgs.lower() or "frost" in msgs.lower() or "frozen" in msgs.lower():
            self.anim.spawn_ice_particles(cx, cy, 22)
        if "heal" in msgs.lower() or "regen" in msgs.lower() or "recover" in msgs.lower():
            self.anim.spawn_heal_particles(cx if not is_player_hitting else 160, cy)

    # ── Update ────────────────────────────────

    def _update(self, dt):
        self.anim.update()

        if self.state == "BATTLE":
            if not self.player_turn:
                self.enemy_turn_timer -= 1
                if self.enemy_turn_timer <= 0:
                    self._enemy_turn()

        elif self.state == "END_FADE":
            if not self.anim.fade:
                self.state = "END"
                self._build_end_ui()

    # ── Drawing ───────────────────────────────

    def _draw(self):
        ox, oy = self.anim.screen_offset
        # Offset surface for screen shake
        draw_surface = pygame.Surface((WINDOW_W, WINDOW_H))
        draw_surface.fill(C["bg"])

        # Stars background
        self._draw_stars(draw_surface)

        if self.state == "MENU":
            self._draw_menu(draw_surface)
        elif self.state in ("BATTLE", "END_FADE"):
            self._draw_battle(draw_surface)
        elif self.state == "END":
            self._draw_end(draw_surface)

        # Fade overlay
        self.anim.draw_fade(draw_surface)

        # Blit with shake offset
        self.screen.fill(C["bg"])
        self.screen.blit(draw_surface, (ox, oy))
        pygame.display.flip()

    def _draw_stars(self, surf):
        for sx, sy, brightness in self.stars:
            b = int(brightness * 60)
            pygame.draw.circle(surf, (b, b, b + 20), (int(sx), int(sy)), 1)

    # ── MENU DRAW ─────────────────────────────

    def _draw_menu(self, surf):
        # Title
        title_font = get_font(52, bold=True)
        draw_text_shadow(surf, "⚔  BATTLE ARENA  ⚔", title_font, C["gold"],
                         WINDOW_W // 2, 20, "midtop", shadow_offset=3)

        sub_font = get_font(16)
        draw_text(surf, "TURN-BASED COMBAT  ·  SELECT YOUR CHAMPION",
                  sub_font, C["text_muted"], WINDOW_W // 2, 78, "midtop")

        # Player row header
        h_font = get_font(17, bold=True)
        draw_text(surf, "── YOUR CHAMPION ──", h_font, C["gold"],
                  WINDOW_W // 2, 172, "midtop")

        for card in self.player_cards:
            card.draw(surf, self.anim_t)

        # Enemy row header
        enemy_y = 200 + CharSelectCard.CARD_H + 8
        draw_text(surf, "── CHOOSE YOUR ENEMY ──", h_font, C["red"],
                  WINDOW_W // 2, enemy_y - 24, "midtop")

        for card in self.enemy_cards:
            card.draw(surf, self.anim_t)

        # Difficulty
        diff_font = get_font(15)
        draw_text(surf, "DIFFICULTY", diff_font, C["text_muted"],
                  WINDOW_W // 2, WINDOW_H - 84, "midtop")
        for i, btn in enumerate(self.difficulty_buttons):
            is_sel = ["Easy", "Normal", "Hard"][i] == self.difficulty
            if is_sel:
                btn.color_override = (40, 42, 70)
            else:
                btn.color_override = None
            btn.draw(surf)

        # Start button — only enabled if both selected
        self.btn_start.enabled = bool(self.selected_player_cls and self.selected_enemy_cls)
        self.btn_start.draw(surf)

        if not (self.selected_player_cls and self.selected_enemy_cls):
            hint_font = get_font(14)
            draw_text(surf, "Select a champion and an enemy to begin",
                      hint_font, C["text_dim"], WINDOW_W // 2, WINDOW_H - 14, "midbottom")

    # ── BATTLE DRAW ───────────────────────────

    def _draw_battle(self, surf):
        p = self.player
        e = self.enemy
        if not p or not e:
            return

        # ── Top stat panels
        p_rect = pygame.Rect(6, 6, CHAR_PANEL_W, TOP_PANEL_H - 4)
        e_rect = pygame.Rect(WINDOW_W - CHAR_PANEL_W - 6, 6,
                             CHAR_PANEL_W, TOP_PANEL_H - 4)
        mid_rect = pygame.Rect(CHAR_PANEL_W + 12, 6,
                               WINDOW_W - CHAR_PANEL_W * 2 - 24, TOP_PANEL_H - 4)

        p_shake = self.anim.get_char_shake_offset(self.player_shake)
        e_shake = self.anim.get_char_shake_offset(self.enemy_shake)

        draw_character_panel(surf, p_rect, p, True, p_shake)
        draw_character_panel(surf, e_rect, e, False, e_shake)
        draw_round_indicator(surf, mid_rect, self.round_num, self.player_turn)

        # ── Arena background
        arena_rect = pygame.Rect(0, ARENA_Y, WINDOW_W, ARENA_H)
        draw_panel(surf, arena_rect)

        # Floor line
        floor_y = ARENA_Y + ARENA_H - 30
        pygame.draw.line(surf, C["border"],
                         (40, floor_y), (WINDOW_W - 40, floor_y), 1)

        # ── Particle effects (behind sprites)
        self.anim.draw_behind_ui(surf)

        # ── Player sprite
        p_sprite_x = 80 + p_shake
        p_sprite_y = ARENA_Y + 20
        p_img = self.assets.load_sprite(p.sprite_file, (160, 180))
        if p_img:
            surf.blit(p_img, (p_sprite_x, p_sprite_y))
        else:
            self._draw_placeholder_sprite(surf, p_sprite_x + 20, p_sprite_y, p.color, p.name[0])

        # Player dead overlay
        if not p.is_alive:
            overlay = pygame.Surface((160, 180), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            surf.blit(overlay, (p_sprite_x, p_sprite_y))

        # ── Enemy sprite (mirrored)
        e_sprite_x = WINDOW_W - 240 + e_shake
        e_sprite_y = ARENA_Y + 20
        e_img = self.assets.load_sprite(e.sprite_file, (160, 180))
        if e_img:
            flipped = pygame.transform.flip(e_img, True, False)
            surf.blit(flipped, (e_sprite_x, e_sprite_y))
        else:
            self._draw_placeholder_sprite(surf, e_sprite_x + 20, e_sprite_y, e.color, e.name[0])

        if not e.is_alive:
            overlay = pygame.Surface((160, 180), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            surf.blit(overlay, (e_sprite_x, e_sprite_y))

        # Hit flashes over sprites
        self.anim.draw_over_sprites(surf)

        # Active turn indicator arrow
        if self.player_turn and p.is_alive:
            self._draw_turn_arrow(surf, p_sprite_x + 80, ARENA_Y + 10, (60, 220, 100))
        elif not self.player_turn and e.is_alive:
            self._draw_turn_arrow(surf, e_sprite_x + 80, ARENA_Y + 10, (220, 70, 60))

        # VS text
        vs_font = get_font(28, bold=True)
        draw_text_shadow(surf, "VS", vs_font, C["gold"],
                         WINDOW_W // 2, ARENA_Y + ARENA_H // 2, "center")

        # ── Bottom: abilities + log
        bottom_bg = pygame.Rect(0, BOTTOM_Y - 4, WINDOW_W, BOTTOM_H + 8)
        draw_panel(surf, bottom_bg)

        # Ability buttons
        for btn in self.ability_buttons:
            btn.draw(surf)

        # Combat log
        self.battle_log.draw(surf)

        # Floating damage numbers (topmost)
        self.anim.draw_top(surf)

    def _draw_placeholder_sprite(self, surf, x, y, color, letter):
        """Draw a colored rectangle as a fallback sprite."""
        rect = pygame.Rect(x, y, 120, 160)
        draw_rounded_rect(surf, color, rect, 10)
        # Darken edges
        edge = pygame.Surface((120, 160), pygame.SRCALPHA)
        pygame.draw.rect(edge, (0, 0, 0, 80), (0, 0, 120, 160), border_radius=10)
        surf.blit(edge, (x, y))
        big_font = get_font(80, bold=True)
        draw_text(surf, letter, big_font, (255, 255, 255),
                  x + 60, y + 80, "center")

    def _draw_turn_arrow(self, surf, cx, y, color):
        pulse = int(math.sin(self.anim_t * 5) * 4)
        points = [
            (cx, y - 6 + pulse),
            (cx - 10, y - 18 + pulse),
            (cx + 10, y - 18 + pulse),
        ]
        pygame.draw.polygon(surf, color, points)

    # ── END DRAW ──────────────────────────────

    def _build_end_ui(self):
        cx = WINDOW_W // 2
        self.btn_play_again = Button(
            pygame.Rect(cx - 110, WINDOW_H - 70, 100, 36),
            "MENU", font_size=18, icon="🏠")
        self.btn_rematch = Button(
            pygame.Rect(cx + 10, WINDOW_H - 70, 100, 36),
            "REMATCH", font_size=18, icon="⚔")

    def _draw_end(self, surf):
        result = self.pending_result
        p = self.player
        e = self.enemy

        # Central panel
        panel_rect = pygame.Rect(150, 60, WINDOW_W - 300, WINDOW_H - 130)
        draw_rounded_rect(surf, C["panel"], panel_rect, 14, C["border"], 2)

        # Result title
        if result == "win":
            title_col = C["gold"]
            title_text = "⚔  VICTORY  ⚔"
        else:
            title_col = C["red"]
            title_text = "💀  DEFEAT  💀"

        tf = get_font(44, bold=True)
        draw_text_shadow(surf, title_text, tf, title_col,
                         WINDOW_W // 2, 90, "midtop", shadow_offset=3)

        if result == "win":
            sub = f"{p.name} defeated {e.name} in {self.round_num} rounds!"
        else:
            sub = f"{e.name} proved too powerful after {self.round_num} rounds."
        sub_f = get_font(20)
        draw_text(surf, sub, sub_f, C["text_muted"],
                  WINDOW_W // 2, 148, "midtop")

        # Stat cards
        stats = [
            ("ROUNDS", str(self.round_num), C["blue"]),
            ("DAMAGE DEALT", str(self.stat_dmg_dealt), C["red"]),
            ("HP HEALED", str(self.stat_healed), C["green"]),
        ]
        card_w, card_h = 140, 80
        total_w = 3 * card_w + 2 * 16
        sx = (WINDOW_W - total_w) // 2
        sy = 190
        for label, value, col in stats:
            cr = pygame.Rect(sx, sy, card_w, card_h)
            draw_rounded_rect(surf, C["panel2"], cr, 8, C["border"])
            lf = get_font(14)
            vf = get_font(32, bold=True)
            draw_text(surf, label, lf, C["text_muted"], cr.centerx, cr.y + 8, "midtop")
            draw_text(surf, value, vf, col, cr.centerx, cr.centery + 8, "center")
            sx += card_w + 16

        # Character summary
        if p and e:
            cf = get_font(16)
            p_hp = f"{p.name}  HP: {max(0, p.hp)}/{p.max_hp}"
            e_hp = f"{e.name}  HP: {max(0, e.hp)}/{e.max_hp}"
            draw_text(surf, p_hp, cf, C["green"] if p.is_alive else C["text_dim"],
                      WINDOW_W // 2 - 20, 300, "midright")
            draw_text(surf, "vs", cf, C["text_muted"], WINDOW_W // 2, 300, "midtop")
            draw_text(surf, e_hp, cf, C["red"] if not e.is_alive else C["text_dim"],
                      WINDOW_W // 2 + 20, 300, "midleft")

        self.btn_play_again.draw(surf)
        self.btn_rematch.draw(surf)

    def _go_menu(self):
        self.state = "MENU"
        self._build_menu_ui()
        self.anim.start_fade("in", 20)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    game = Game()
    game.run()

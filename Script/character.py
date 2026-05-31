"""
character.py
Defines all characters, abilities, status effects, and AI logic for Battle Arena.
"""

import random
import math


# ─────────────────────────────────────────────
#  STATUS EFFECTS
# ─────────────────────────────────────────────

class StatusEffect:
    """Base class for status effects applied to characters."""

    def __init__(self, name: str, duration: int, icon: str, color: tuple):
        self.name = name
        self.duration = duration        # turns remaining
        self.icon = icon
        self.color = color

    def on_turn_start(self, target) -> str:
        """Called at the start of the affected character's turn. Returns log message."""
        return ""

    def on_expire(self, target) -> str:
        return f"{target.name}'s {self.name} wore off."

    def __repr__(self):
        return f"{self.icon}{self.name}({self.duration})"


class BurnEffect(StatusEffect):
    def __init__(self, duration=3, damage_pct=0.06):
        super().__init__("Burn", duration, "🔥", (220, 90, 40))
        self.damage_pct = damage_pct

    def on_turn_start(self, target) -> str:
        dmg = max(1, int(target.max_hp * self.damage_pct))
        target.hp = max(0, target.hp - dmg)
        return f"🔥 {target.name} burns for {dmg} damage!"


class PoisonEffect(StatusEffect):
    def __init__(self, duration=4, damage_pct=0.04):
        super().__init__("Poison", duration, "☠", (100, 200, 80))
        self.damage_pct = damage_pct

    def on_turn_start(self, target) -> str:
        dmg = max(1, int(target.max_hp * self.damage_pct))
        target.hp = max(0, target.hp - dmg)
        return f"☠ {target.name} takes {dmg} poison damage!"


class RegenEffect(StatusEffect):
    def __init__(self, duration=3, heal_pct=0.07):
        super().__init__("Regen", duration, "💚", (60, 220, 100))
        self.heal_pct = heal_pct

    def on_turn_start(self, target) -> str:
        amount = max(1, int(target.max_hp * self.heal_pct))
        target.hp = min(target.max_hp, target.hp + amount)
        return f"💚 {target.name} regenerates {amount} HP!"


class StunEffect(StatusEffect):
    def __init__(self, duration=1):
        super().__init__("Stun", duration, "⚡", (200, 200, 60))

    def on_turn_start(self, target) -> str:
        return f"⚡ {target.name} is stunned and loses their turn!"


class ShieldEffect(StatusEffect):
    def __init__(self, duration=2, reduction=0.5):
        super().__init__("Shield", duration, "🛡", (100, 150, 220))
        self.reduction = reduction          # damage multiplier (0.5 = 50% less)

    def on_turn_start(self, target) -> str:
        return ""


class WeakenEffect(StatusEffect):
    def __init__(self, duration=2, multiplier=0.7):
        super().__init__("Weaken", duration, "💛", (200, 200, 60))
        self.multiplier = multiplier

    def on_turn_start(self, target) -> str:
        return f"💛 {target.name} is weakened!"


class FreezeEffect(StatusEffect):
    def __init__(self, duration=1):
        super().__init__("Freeze", duration, "❄", (150, 220, 255))

    def on_turn_start(self, target) -> str:
        return f"❄ {target.name} is frozen solid!"


# ─────────────────────────────────────────────
#  ABILITIES
# ─────────────────────────────────────────────

class Ability:
    """Represents a character ability with optional cooldown and MP cost."""

    def __init__(self, ability_id: str, name: str, icon: str,
                 ability_type: str, mp_cost: int, cooldown: int,
                 description: str, sound_key: str = "attack"):
        self.id = ability_id
        self.name = name
        self.icon = icon
        self.type = ability_type        # "attack" | "heal" | "special"
        self.mp_cost = mp_cost
        self.cooldown = cooldown        # max cooldown turns
        self.current_cd = 0             # remaining cooldown
        self.description = description
        self.sound_key = sound_key

    @property
    def is_ready(self) -> bool:
        return self.current_cd == 0

    def start_cooldown(self):
        self.current_cd = self.cooldown

    def tick_cooldown(self):
        if self.current_cd > 0:
            self.current_cd -= 1

    def __repr__(self):
        return f"<Ability {self.name} cd={self.current_cd}>"


# ─────────────────────────────────────────────
#  BASE CHARACTER
# ─────────────────────────────────────────────

class Character:
    """Base character class. All heroes/enemies inherit from this."""

    # Override these in subclasses
    NAME = "Character"
    CLASS_LABEL = "Fighter"
    SPRITE_FILE = "default.png"
    MAX_HP = 100
    MAX_MP = 60
    BASE_ATK = 20
    BASE_DEF = 8
    COLOR = (180, 180, 180)

    def __init__(self):
        self.name = self.NAME
        self.class_label = self.CLASS_LABEL
        self.sprite_file = self.SPRITE_FILE
        self.max_hp = self.MAX_HP
        self.max_mp = self.MAX_MP
        self.hp = self.MAX_HP
        self.mp = self.MAX_MP
        self.base_atk = self.BASE_ATK
        self.base_def = self.BASE_DEF
        self.color = self.COLOR

        self.statuses: list[StatusEffect] = []
        self.abilities: list[Ability] = []
        self._define_abilities()

    def _define_abilities(self):
        """Override in subclasses to populate self.abilities."""
        pass

    # ── Stats ──────────────────────────────────

    @property
    def atk(self) -> int:
        val = self.base_atk
        if self.has_status("Weaken"):
            val = int(val * 0.7)
        return val

    @property
    def defence(self) -> int:
        val = self.base_def
        if self.has_status("Shield"):
            val = int(val * 1.8)
        return val

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    @property
    def is_stunned(self) -> bool:
        return self.has_status("Stun") or self.has_status("Freeze")

    # ── Status helpers ─────────────────────────

    def has_status(self, name: str) -> bool:
        return any(s.name == name for s in self.statuses)

    def apply_status(self, effect: StatusEffect):
        # Replace existing status of same type
        self.statuses = [s for s in self.statuses if s.name != effect.name]
        self.statuses.append(effect)

    def remove_status(self, name: str):
        self.statuses = [s for s in self.statuses if s.name != name]

    def tick_statuses(self) -> list[str]:
        """Process all active status effects. Returns list of log messages."""
        messages = []
        expired = []
        for s in self.statuses:
            msg = s.on_turn_start(self)
            if msg:
                messages.append(msg)
            s.duration -= 1
            if s.duration <= 0:
                messages.append(s.on_expire(self))
                expired.append(s)
        for s in expired:
            self.statuses.remove(s)
        return messages

    # ── MP regen ───────────────────────────────

    def regen_mp(self, amount: int = 8):
        self.mp = min(self.max_mp, self.mp + amount)

    # ── Cooldown tick ──────────────────────────

    def tick_cooldowns(self):
        for ab in self.abilities:
            ab.tick_cooldown()

    # ── Combat ─────────────────────────────────

    def calculate_damage(self, raw: int, defender: "Character") -> int:
        """Apply defense and random variance to raw damage."""
        reduction = max(0, defender.defence - random.randint(0, 4))
        dmg = max(1, raw - reduction)
        return dmg

    def use_ability(self, ability: Ability, target: "Character") -> dict:
        """
        Execute an ability against target (or self for heals).
        Returns a result dict with keys: damage, heal, messages, animation, sound.
        """
        result = {
            "damage": 0,
            "heal": 0,
            "messages": [],
            "animation": ability.type,
            "sound": ability.sound_key,
            "crit": False,
        }

        # Spend MP and start cooldown
        self.mp = max(0, self.mp - ability.mp_cost)
        ability.start_cooldown()

        return result   # Subclasses build on this

    # ── AI decision ────────────────────────────

    def ai_choose_ability(self, enemy: "Character", difficulty: str) -> Ability:
        """Smart AI: choose the best ability based on state and difficulty."""
        hp_ratio = self.hp / self.max_hp
        enemy_hp_ratio = enemy.hp / enemy.max_hp

        available = [
            ab for ab in self.abilities
            if ab.is_ready and self.mp >= ab.mp_cost
        ]
        if not available:
            available = [self.abilities[0]]  # fallback: basic attack

        # Easy: mostly random
        if difficulty == "Easy":
            if hp_ratio < 0.25 and any(a.type == "heal" for a in available):
                heals = [a for a in available if a.type == "heal"]
                return random.choice(heals)
            return random.choice(available)

        # Normal: use heals when low, specials sometimes
        if difficulty == "Normal":
            if hp_ratio < 0.35 and any(a.type == "heal" for a in available):
                heals = [a for a in available if a.type == "heal"]
                return random.choice(heals)
            if enemy_hp_ratio < 0.4 and any(a.id in ("burst","slam","multishot","arrow_rain","divine","rage") for a in available):
                finishers = [a for a in available if a.id in ("burst","slam","multishot","arrow_rain","divine","rage")]
                if finishers:
                    return random.choice(finishers)
            return random.choice(available)

        # Hard: optimal play
        if hp_ratio < 0.3 and any(a.type == "heal" for a in available):
            heals = [a for a in available if a.type == "heal"]
            return random.choice(heals)
        if enemy_hp_ratio < 0.35 and any(a.type in ("attack","special") for a in available):
            attacks = [a for a in available if a.type in ("attack","special")]
            # Prefer highest-damage specials
            attacks.sort(key=lambda a: a.mp_cost, reverse=True)
            return attacks[0]
        specials = [a for a in available if a.type == "special"]
        if specials and random.random() < 0.55:
            return random.choice(specials)
        attacks = [a for a in available if a.type == "attack"]
        return random.choice(attacks) if attacks else random.choice(available)

    def __repr__(self):
        return f"<{self.name} HP={self.hp}/{self.max_hp}>"


# ─────────────────────────────────────────────
#  ❶  KRATOS  (God of War)
# ─────────────────────────────────────────────

class Kratos(Character):
    NAME = "Kratos"
    CLASS_LABEL = "Spartan Warrior"
    SPRITE_FILE = "kratos.png"
    MAX_HP = 160
    MAX_MP = 60
    BASE_ATK = 28
    BASE_DEF = 14
    COLOR = (180, 80, 60)

    def _define_abilities(self):
        self.abilities = [
            Ability("attack",  "Leviathan Strike", "⚔",  "attack",  0, 0, "Icy axe strike"),
            Ability("slam",    "Spartan Rage",      "💢", "attack", 20, 3, "Massive dmg + stun"),
            Ability("block",   "Guardian Shield",   "🛡", "special",15, 3, "Halves damage taken for 2 turns"),
            Ability("heal",    "Spartan Will",      "💚", "heal",   25, 4, "Recover 35% max HP"),
        ]

    def use_ability(self, ability: Ability, target: "Character") -> dict:
        result = super().use_ability(ability, target)

        if ability.id == "attack":
            raw = self.atk + random.randint(0, 10)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            result["damage"] = dmg
            result["messages"] = [f"⚔ {self.name} hurls the Leviathan Axe! {dmg} damage!"]

        elif ability.id == "slam":
            raw = int(self.atk * 1.6) + random.randint(5, 15)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            result["damage"] = dmg
            msgs = [f"💢 SPARTAN RAGE! {self.name} deals {dmg} damage!"]
            if random.random() < 0.45:
                target.apply_status(StunEffect(1))
                msgs.append(f"⚡ {target.name} is stunned!")
            result["messages"] = msgs

        elif ability.id == "block":
            self.apply_status(ShieldEffect(2))
            result["messages"] = [f"🛡 {self.name} raises the Guardian Shield!"]

        elif ability.id == "heal":
            amount = int(self.max_hp * 0.35)
            self.hp = min(self.max_hp, self.hp + amount)
            result["heal"] = amount
            result["messages"] = [f"💚 {self.name} draws on Spartan Will! +{amount} HP!"]

        return result


# ─────────────────────────────────────────────
#  ❷  HERMES  (Greek Messenger God)
# ─────────────────────────────────────────────

class Hermes(Character):
    NAME = "Hermes"
    CLASS_LABEL = "Divine Trickster"
    SPRITE_FILE = "hermes.png"
    MAX_HP = 110
    MAX_MP = 100
    BASE_ATK = 26
    BASE_DEF = 7
    COLOR = (120, 180, 220)

    def _define_abilities(self):
        self.abilities = [
            Ability("attack",    "Quickstep Slash",  "💨", "attack",  0, 0, "Swift blur attack"),
            Ability("multishot", "Hermes Rush",      "⚡", "attack", 25, 2, "3 rapid hits"),
            Ability("weaken",    "Crippling Curse",  "💛", "special",20, 3, "Weaken enemy ATK"),
            Ability("heal",      "Divine Speed",     "🌀", "heal",   30, 4, "Dodge + regen 3 turns"),
        ]

    def use_ability(self, ability: Ability, target: "Character") -> dict:
        result = super().use_ability(ability, target)

        if ability.id == "attack":
            raw = self.atk + random.randint(0, 12)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            result["damage"] = dmg
            result["messages"] = [f"💨 {self.name} blurs past! {dmg} damage!"]

        elif ability.id == "multishot":
            total = 0
            msgs = [f"⚡ {self.name} rushes with blinding speed!"]
            for i in range(3):
                raw = int(self.atk * 0.5) + random.randint(0, 6)
                dmg = self.calculate_damage(raw, target)
                target.hp = max(0, target.hp - dmg)
                total += dmg
            msgs.append(f"3 hits land for {total} total damage!")
            result["damage"] = total
            result["messages"] = msgs

        elif ability.id == "weaken":
            target.apply_status(WeakenEffect(2))
            result["messages"] = [f"💛 {self.name} curses {target.name}! ATK reduced!"]

        elif ability.id == "heal":
            self.apply_status(RegenEffect(3))
            result["messages"] = [f"🌀 {self.name} enters a divine sprint! Regen active!"]

        return result


# ─────────────────────────────────────────────
#  ❸  GERALT  (The Witcher)
# ─────────────────────────────────────────────

class Geralt(Character):
    NAME = "Geralt"
    CLASS_LABEL = "White Wolf Witcher"
    SPRITE_FILE = "geralt.png"
    MAX_HP = 140
    MAX_MP = 80
    BASE_ATK = 25
    BASE_DEF = 11
    COLOR = (200, 200, 200)

    def _define_abilities(self):
        self.abilities = [
            Ability("attack",  "Silver Sword",    "🗡",  "attack",  0, 0, "Fast silver strike"),
            Ability("igni",    "Igni Sign",        "🔥", "special", 25, 3, "Burn + damage"),
            Ability("aard",    "Aard Sign",        "💨", "special", 20, 3, "Stun + knockback dmg"),
            Ability("heal",    "Swallow Potion",   "🧪", "heal",    30, 4, "Strong regen 4 turns"),
        ]

    def use_ability(self, ability: Ability, target: "Character") -> dict:
        result = super().use_ability(ability, target)

        if ability.id == "attack":
            raw = self.atk + random.randint(0, 10)
            # Crit chance 20%
            crit = random.random() < 0.20
            if crit:
                raw = int(raw * 1.5)
                result["crit"] = True
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            result["damage"] = dmg
            msg = f"🗡 {self.name} strikes with the silver sword! {dmg} damage!"
            if crit:
                msg += " CRITICAL HIT!"
            result["messages"] = [msg]

        elif ability.id == "igni":
            raw = int(self.atk * 1.2) + random.randint(5, 12)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            target.apply_status(BurnEffect(3))
            result["damage"] = dmg
            result["messages"] = [f"🔥 IGNI! {self.name} blasts {target.name} for {dmg}! Now burning!"]

        elif ability.id == "aard":
            raw = int(self.atk * 1.1) + random.randint(3, 10)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            target.apply_status(StunEffect(1))
            result["damage"] = dmg
            result["messages"] = [f"💨 AARD! {target.name} is blasted back for {dmg}! Stunned!"]

        elif ability.id == "heal":
            self.apply_status(RegenEffect(4, heal_pct=0.08))
            result["messages"] = [f"🧪 {self.name} drinks Swallow Potion! Regenerating!"]

        return result


# ─────────────────────────────────────────────
#  ❹  EZIO  (Assassin's Creed)
# ─────────────────────────────────────────────

class Ezio(Character):
    NAME = "Ezio"
    CLASS_LABEL = "Master Assassin"
    SPRITE_FILE = "ezio.png"
    MAX_HP = 115
    MAX_MP = 90
    BASE_ATK = 27
    BASE_DEF = 9
    COLOR = (200, 60, 60)

    def _define_abilities(self):
        self.abilities = [
            Ability("attack",   "Hidden Blade",     "🗡",  "attack",  0, 0, "Lightning quick stab"),
            Ability("multishot","Eagle Strike",     "🦅",  "attack", 25, 2, "4 rapid dagger throws"),
            Ability("poison",   "Poison Blade",     "☠",  "special", 20, 3, "Coat blade with venom"),
            Ability("heal",     "Eagle Vision",     "👁",  "heal",    28, 4, "Predict + dodge + regen"),
        ]

    def use_ability(self, ability: Ability, target: "Character") -> dict:
        result = super().use_ability(ability, target)

        if ability.id == "attack":
            raw = self.atk + random.randint(0, 14)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            result["damage"] = dmg
            result["messages"] = [f"🗡 {self.name} strikes from the shadows! {dmg} damage!"]

        elif ability.id == "multishot":
            total = 0
            for _ in range(4):
                raw = int(self.atk * 0.45) + random.randint(0, 5)
                dmg = self.calculate_damage(raw, target)
                target.hp = max(0, target.hp - dmg)
                total += dmg
            result["damage"] = total
            result["messages"] = [f"🦅 Eagle Strike! 4 throws deal {total} total damage!"]

        elif ability.id == "poison":
            target.apply_status(PoisonEffect(4))
            result["messages"] = [f"☠ {self.name} poisons {target.name}! Venom spreading..."]

        elif ability.id == "heal":
            amount = int(self.max_hp * 0.25)
            self.hp = min(self.max_hp, self.hp + amount)
            self.apply_status(RegenEffect(2))
            result["heal"] = amount
            result["messages"] = [f"👁 Eagle Vision! {self.name} heals {amount} HP + regen!"]

        return result


# ─────────────────────────────────────────────
#  ❺  LINK  (Legend of Zelda)
# ─────────────────────────────────────────────

class Link(Character):
    NAME = "Link"
    CLASS_LABEL = "Hero of Time"
    SPRITE_FILE = "link.png"
    MAX_HP = 130
    MAX_MP = 85
    BASE_ATK = 23
    BASE_DEF = 13
    COLOR = (80, 200, 100)

    def _define_abilities(self):
        self.abilities = [
            Ability("attack",   "Master Sword",     "🗡",  "attack",  0, 0, "Sacred blade strike"),
            Ability("arrow_rain","Bow of Light",    "🏹",  "attack", 25, 3, "3 light arrows"),
            Ability("block",    "Hylian Shield",    "🛡",  "special", 18, 3, "Block + reflect chance"),
            Ability("heal",     "Fairy Bottle",     "🧚", "heal",    30, 4, "Full heal + shield"),
        ]

    def use_ability(self, ability: Ability, target: "Character") -> dict:
        result = super().use_ability(ability, target)

        if ability.id == "attack":
            raw = self.atk + random.randint(0, 10)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            result["damage"] = dmg
            result["messages"] = [f"🗡 {self.name} slashes with the Master Sword! {dmg} damage!"]

        elif ability.id == "arrow_rain":
            total = 0
            for _ in range(3):
                raw = int(self.atk * 0.6) + random.randint(2, 8)
                dmg = self.calculate_damage(raw, target)
                target.hp = max(0, target.hp - dmg)
                total += dmg
            result["damage"] = total
            result["messages"] = [f"🏹 Bow of Light fires 3 arrows for {total} damage!"]

        elif ability.id == "block":
            self.apply_status(ShieldEffect(2))
            result["messages"] = [f"🛡 {self.name} raises the Hylian Shield!"]

        elif ability.id == "heal":
            amount = int(self.max_hp * 0.40)
            self.hp = min(self.max_hp, self.hp + amount)
            self.apply_status(ShieldEffect(1))
            result["heal"] = amount
            result["messages"] = [f"🧚 Fairy revives {self.name}! +{amount} HP + temporary shield!"]

        return result


# ─────────────────────────────────────────────
#  ❻  DANTE  (Devil May Cry)
# ─────────────────────────────────────────────

class Dante(Character):
    NAME = "Dante"
    CLASS_LABEL = "Devil Hunter"
    SPRITE_FILE = "dante.png"
    MAX_HP = 125
    MAX_MP = 95
    BASE_ATK = 30
    BASE_DEF = 8
    COLOR = (220, 60, 60)

    def _define_abilities(self):
        self.abilities = [
            Ability("attack",  "Rebellion Slash",  "🗡",  "attack",  0, 0, "Stylish sword combo"),
            Ability("burst",   "Devil Trigger",    "👿",  "special", 35, 4, "Unleash demon power"),
            Ability("shoot",   "Ebony & Ivory",    "🔫", "attack",  20, 2, "Dual pistol barrage"),
            Ability("heal",    "Trickster Dodge",  "💨", "heal",    25, 4, "Evade + vitality restore"),
        ]

    def use_ability(self, ability: Ability, target: "Character") -> dict:
        result = super().use_ability(ability, target)

        if ability.id == "attack":
            raw = self.atk + random.randint(0, 15)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            result["damage"] = dmg
            result["messages"] = [f"🗡 {self.name} lands a stylish combo! {dmg} damage! SSS!"]

        elif ability.id == "burst":
            raw = int(self.atk * 2.0) + random.randint(10, 20)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            result["damage"] = dmg
            result["messages"] = [f"👿 DEVIL TRIGGER! {self.name} erupts for {dmg} MASSIVE DAMAGE!"]

        elif ability.id == "shoot":
            total = 0
            for _ in range(5):
                raw = int(self.atk * 0.35) + random.randint(0, 6)
                dmg = self.calculate_damage(raw, target)
                target.hp = max(0, target.hp - dmg)
                total += dmg
            result["damage"] = total
            result["messages"] = [f"🔫 Ebony & Ivory! 5 bullets for {total} total damage!"]

        elif ability.id == "heal":
            amount = int(self.max_hp * 0.30)
            self.hp = min(self.max_hp, self.hp + amount)
            result["heal"] = amount
            result["messages"] = [f"💨 {self.name} dodges and recovers! +{amount} HP!"]

        return result


# ─────────────────────────────────────────────
#  ❼  MASTER CHIEF  (Halo)
# ─────────────────────────────────────────────

class MasterChief(Character):
    NAME = "Master Chief"
    CLASS_LABEL = "SPARTAN-II"
    SPRITE_FILE = "masterchief.png"
    MAX_HP = 150
    MAX_MP = 70
    BASE_ATK = 26
    BASE_DEF = 16
    COLOR = (80, 140, 80)

    def _define_abilities(self):
        self.abilities = [
            Ability("attack",  "Assault Rifle",    "🔫", "attack",  0, 0, "Full-auto burst"),
            Ability("grenade", "Frag Grenade",     "💥", "attack", 25, 3, "Explosive + burn"),
            Ability("shield",  "Energy Shield",    "🛡",  "special", 20, 3, "Full shield recharge"),
            Ability("heal",    "Overshield",       "⚡",  "heal",    30, 4, "Overshield repair"),
        ]

    def use_ability(self, ability: Ability, target: "Character") -> dict:
        result = super().use_ability(ability, target)

        if ability.id == "attack":
            raw = self.atk + random.randint(0, 10)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            result["damage"] = dmg
            result["messages"] = [f"🔫 {self.name} unloads a burst! {dmg} damage!"]

        elif ability.id == "grenade":
            raw = int(self.atk * 1.4) + random.randint(8, 18)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            target.apply_status(BurnEffect(2))
            result["damage"] = dmg
            result["messages"] = [f"💥 Frag grenade explodes! {dmg} damage! {target.name} is burning!"]

        elif ability.id == "shield":
            self.apply_status(ShieldEffect(3))
            result["messages"] = [f"🛡 {self.name}'s Energy Shield is fully charged!"]

        elif ability.id == "heal":
            amount = int(self.max_hp * 0.32)
            self.hp = min(self.max_hp, self.hp + amount)
            result["heal"] = amount
            result["messages"] = [f"⚡ {self.name}'s Overshield repairs! +{amount} HP!"]

        return result


# ─────────────────────────────────────────────
#  ❽  ALOY  (Horizon Zero Dawn)
# ─────────────────────────────────────────────

class Aloy(Character):
    NAME = "Aloy"
    CLASS_LABEL = "Nora Huntress"
    SPRITE_FILE = "aloy.png"
    MAX_HP = 120
    MAX_MP = 90
    BASE_ATK = 24
    BASE_DEF = 10
    COLOR = (200, 160, 80)

    def _define_abilities(self):
        self.abilities = [
            Ability("attack",   "Sharpshot Bow",    "🏹",  "attack",  0, 0, "Precise arrow shot"),
            Ability("trap",     "Shock Trap",       "⚡",  "special", 22, 3, "Stun + shock damage"),
            Ability("fire_arrow","Fire Arrow",      "🔥",  "attack", 20, 2, "Burning arrow"),
            Ability("heal",     "Medicinal Herbs",  "🌿",  "heal",   25, 3, "Heal + cleanse status"),
        ]

    def use_ability(self, ability: Ability, target: "Character") -> dict:
        result = super().use_ability(ability, target)

        if ability.id == "attack":
            raw = self.atk + random.randint(0, 12)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            result["damage"] = dmg
            result["messages"] = [f"🏹 {self.name} fires a precise arrow! {dmg} damage!"]

        elif ability.id == "trap":
            raw = int(self.atk * 1.1) + random.randint(4, 12)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            target.apply_status(StunEffect(1))
            result["damage"] = dmg
            result["messages"] = [f"⚡ Shock Trap activates! {dmg} damage! {target.name} is stunned!"]

        elif ability.id == "fire_arrow":
            raw = int(self.atk * 1.2) + random.randint(3, 10)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            target.apply_status(BurnEffect(3))
            result["damage"] = dmg
            result["messages"] = [f"🔥 Fire Arrow! {dmg} damage! {target.name} is ignited!"]

        elif ability.id == "heal":
            amount = int(self.max_hp * 0.28)
            self.hp = min(self.max_hp, self.hp + amount)
            self.statuses.clear()
            result["heal"] = amount
            result["messages"] = [f"🌿 {self.name} uses Medicinal Herbs! +{amount} HP! All status effects cleared!"]

        return result


# ─────────────────────────────────────────────
#  ❾  ARTHAS  (WoW – Lich King)
# ─────────────────────────────────────────────

class Arthas(Character):
    NAME = "Arthas"
    CLASS_LABEL = "Lich King"
    SPRITE_FILE = "arthas.png"
    MAX_HP = 155
    MAX_MP = 85
    BASE_ATK = 29
    BASE_DEF = 13
    COLOR = (160, 200, 255)

    def _define_abilities(self):
        self.abilities = [
            Ability("attack",  "Frostmourne",      "❄",  "attack",  0, 0, "Soul-stealing sword"),
            Ability("freeze",  "Frost Nova",       "❄",  "special", 25, 3, "Freeze + AOE damage"),
            Ability("drain",   "Soul Drain",       "💜",  "special", 22, 3, "Drain HP from enemy"),
            Ability("heal",    "Undead Resilience","🦴",  "heal",    30, 4, "Dark regen 3 turns"),
        ]

    def use_ability(self, ability: Ability, target: "Character") -> dict:
        result = super().use_ability(ability, target)

        if ability.id == "attack":
            raw = self.atk + random.randint(0, 12)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            result["damage"] = dmg
            result["messages"] = [f"❄ {self.name} swings Frostmourne! {dmg} damage!"]

        elif ability.id == "freeze":
            raw = int(self.atk * 1.3) + random.randint(5, 15)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            target.apply_status(FreezeEffect(1))
            result["damage"] = dmg
            result["messages"] = [f"❄ Frost Nova! {dmg} damage! {target.name} is FROZEN!"]

        elif ability.id == "drain":
            raw = int(self.atk * 1.2) + random.randint(4, 10)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            self.hp = min(self.max_hp, self.hp + dmg // 2)
            result["damage"] = dmg
            result["heal"] = dmg // 2
            result["messages"] = [f"💜 Soul Drain! {dmg} stolen from {target.name}! {self.name} gains {dmg//2} HP!"]

        elif ability.id == "heal":
            self.apply_status(RegenEffect(3, heal_pct=0.09))
            result["messages"] = [f"🦴 {self.name} channels dark power! Undead regeneration active!"]

        return result


# ─────────────────────────────────────────────
#  ❿  LARA CROFT  (Tomb Raider)
# ─────────────────────────────────────────────

class LaraCroft(Character):
    NAME = "Lara Croft"
    CLASS_LABEL = "Tomb Raider"
    SPRITE_FILE = "lara.png"
    MAX_HP = 118
    MAX_MP = 88
    BASE_ATK = 25
    BASE_DEF = 9
    COLOR = (200, 160, 100)

    def _define_abilities(self):
        self.abilities = [
            Ability("attack",    "Dual Pistols",     "🔫", "attack",  0, 0, "Rapid pistol shots"),
            Ability("arrow_rain","Rope Arrow",       "🏹",  "attack", 22, 2, "Pin + multi-shot"),
            Ability("bomb",      "Molotov Cocktail", "🔥",  "special", 25, 3, "Fire bomb + burn"),
            Ability("heal",      "Survival Instinct","🧪",  "heal",    28, 4, "Field medkit + focus"),
        ]

    def use_ability(self, ability: Ability, target: "Character") -> dict:
        result = super().use_ability(ability, target)

        if ability.id == "attack":
            total = 0
            for _ in range(2):
                raw = int(self.atk * 0.6) + random.randint(0, 8)
                dmg = self.calculate_damage(raw, target)
                target.hp = max(0, target.hp - dmg)
                total += dmg
            result["damage"] = total
            result["messages"] = [f"🔫 {self.name} fires both pistols! {total} total damage!"]

        elif ability.id == "arrow_rain":
            raw = int(self.atk * 1.3) + random.randint(5, 14)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            target.apply_status(WeakenEffect(2))
            result["damage"] = dmg
            result["messages"] = [f"🏹 Rope Arrow pins {target.name}! {dmg} damage + weakened!"]

        elif ability.id == "bomb":
            raw = int(self.atk * 1.5) + random.randint(8, 16)
            dmg = self.calculate_damage(raw, target)
            target.hp = max(0, target.hp - dmg)
            target.apply_status(BurnEffect(3))
            result["damage"] = dmg
            result["messages"] = [f"🔥 Molotov Cocktail! {dmg} damage! {target.name} is burning!"]

        elif ability.id == "heal":
            amount = int(self.max_hp * 0.30)
            self.hp = min(self.max_hp, self.hp + amount)
            self.apply_status(RegenEffect(2))
            result["heal"] = amount
            result["messages"] = [f"🧪 {self.name} patches up! +{amount} HP + regen!"]

        return result


# ─────────────────────────────────────────────
#  CHARACTER REGISTRY
# ─────────────────────────────────────────────

ALL_CHARACTERS = [
    Kratos, Geralt, Ezio, Link, Dante,
    MasterChief, Aloy, Arthas, LaraCroft, Hermes,
]

from typing import Optional

def get_character_by_name(name: str) -> Optional[Character]:
    for cls in ALL_CHARACTERS:
        if cls.NAME == name:
            return cls()
    return None

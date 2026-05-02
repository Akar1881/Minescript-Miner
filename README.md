# miner.py — Full Configuration Guide

Universal block miner for Hypixel SkyBlock using Minescript.
Warps between routes, mines every target block it can reach, then loops forever.

---

## Controls

| Key | Action |
|-----|--------|
| **K** | Start / Pause mining |
| **ESC** | Stop the script completely |

Press K once to start. Press K again to pause mid-run. ESC kills the script and releases all held keys safely.

---

## Quick Start

1. Open `miner.py` in a text editor.
2. Edit only the section between the two `══` lines — everything above `# Internal state` is your config.
3. Run the script with Minescript, stand anywhere, press **K**.

---

## Configuration Reference

### TARGET_BLOCKS — What to mine

```python
TARGET_BLOCKS = [
    "minecraft:coal_block",
]
```

A list of Minecraft block IDs. The script will mine every block in this list.
You can put as many as you want — the script treats them all equally.

**How to find a block's ID:**

Stand next to the block in-game and run the Minescript command:
```
\getblock ~ ~ ~
```
It prints the full ID (e.g. `minecraft:coal_block`, `minecraft:mithril_ore`).

**Common examples:**

```python
# Coal blocks only
TARGET_BLOCKS = ["minecraft:coal_block"]

# Diamond ore (both variants)
TARGET_BLOCKS = [
    "minecraft:diamond_ore",
    "minecraft:deepslate_diamond_ore",
]

# SkyBlock custom ores (use exact IDs from getblock)
TARGET_BLOCKS = [
    "minecraft:mithril_ore",
    "minecraft:titanium_ore",
]

# Multiple completely different blocks at once
TARGET_BLOCKS = [
    "minecraft:coal_block",
    "minecraft:iron_ore",
    "minecraft:gold_ore",
]
```

---

### ROUTES — Where to warp

```python
ROUTES = {
    "Route 1": (162.0, 130.0, 35.5),
    "Route 2": (166.5, 132.0, 38.5),
    "Route 3": (168.5, 133.0, 42.5),
}
```

A list of named warp destinations. The script warps to Route 1, mines until nothing is left, warps to Route 2, mines, and so on. After the last route it loops back to Route 1 forever.

**Format:**
```
"Any Name You Want": (x, y, z),
```

**How to get coordinates for a route:**

1. Stand exactly where you want the script to land after warping.
2. Press F3 (debug screen) — read the **XYZ** line. Those are your x, y, z.
3. Paste them in as a new route.

The y value must be your **feet position** (the number shown in F3), not the block below you.

**Adding a route:**
```python
ROUTES = {
    "Route 1": (162.0, 130.0, 35.5),
    "Route 2": (166.5, 132.0, 38.5),
    "My New Spot": (200.0, 128.0, 50.0),   # ← add a line like this
}
```

**Removing a route:** delete its line entirely.

**Single route (no warping):**
```python
ROUTES = {
    "Only Spot": (162.0, 130.0, 35.5),
}
```
The script will still warp to it once on startup, then mine in a loop at that spot.

**Order matters** — routes run top to bottom, then repeat.

---

### MINING_SLOT and WARP_SLOT — Hotbar slots

```python
MINING_SLOT = 1   # slot of your pickaxe / mining tool
WARP_SLOT   = 2   # slot of your warp item
```

Slot numbers match what you see in-game: **1 = leftmost slot, 9 = rightmost slot**.

Put your pickaxe in slot 1 and your Etherwarp item in slot 2 (or change these numbers to match wherever you actually put them).

---

### REACH — Block scan radius

```python
REACH = 5.0
```

How far (in blocks) the script looks for target blocks around you after warping.
The default of `5.0` covers everything a player can normally mine.

| Value | Effect |
|-------|--------|
| `3.0` | Only nearby blocks, faster scan |
| `5.0` | Default — good balance |
| `6.0` | Slightly wider, may catch blocks you can't actually reach |

Do not go above `6.0` — the scanner will include blocks too far to mine and waste time.

---

### MINING_LOOK_SPEED — Camera rotation speed while mining

```python
MINING_LOOK_SPEED = 0.9
```

Controls how fast the camera rotates from block to block while mining.
Uses a smooth arc animation — it actually moves, not snaps.

| Value | Feel |
|-------|------|
| `0.0` | Very slow, very human-looking |
| `0.3` | Slow and deliberate |
| `0.6` | Medium — natural feeling |
| `0.9` | Fast arc, still visibly smooth (default) |
| `1.0` | Maximum speed smooth rotation |
| `None` | Instant snap — no animation at all |

```python
MINING_LOOK_SPEED = 0.9   # fast smooth rotation
MINING_LOOK_SPEED = 0.4   # slower, more human
MINING_LOOK_SPEED = None  # instant, fastest possible
```

---

### FOV_YAW_LIMIT and FOV_PITCH_LIMIT — Block priority cone

```python
FOV_YAW_LIMIT   = 80.0
FOV_PITCH_LIMIT = 65.0
```

Blocks inside this cone (in degrees) relative to where you are looking are mined first, nearest first. Blocks outside this cone are mined after, also nearest first.

This means the script prefers blocks already in your view before turning to look elsewhere — more natural and efficient.

You rarely need to change these. Wider values = more blocks treated as "in front". Narrower values = tighter priority zone.

---

### WARP_JITTER — Warp aim randomness

```python
WARP_JITTER = 0.0
```

Adds a random angle offset (in degrees) to the warp aim before firing.

**Keep this at `0.0`.** Etherwarp uses ray-tracing — even 1 degree of error at 15 blocks distance causes ~0.26 blocks of sideways drift, which is enough to land on the wrong block entirely. The aiming math is already precise without jitter.

Only increase this if you deliberately want imprecise warps (you don't).

---

### TOGGLE_KEY and KILL_KEY — Keybinds

```python
TOGGLE_KEY = 75   # K  — start / pause mining
KILL_KEY   = 256  # ESC — stop the script completely
```

Change these numbers to remap the keys. Use GLFW key codes:

| Key | Code |
|-----|------|
| A–Z | 65–90 (e.g. K = 75, O = 79, G = 71) |
| ESC | 256 |
| F1–F12 | 290–301 |
| Space | 32 |
| Enter | 257 |

Example — remap toggle from K to O:
```python
TOGGLE_KEY = 79   # O
```

---

## Full Example Config

```python
TARGET_BLOCKS = [
    "minecraft:mithril_ore",
    "minecraft:titanium_ore",
]

ROUTES = {
    "Spot A": (310.0, 170.0, -45.5),
    "Spot B": (318.5, 172.0, -40.0),
    "Spot C": (325.0, 168.0, -50.5),
}

MINING_SLOT = 3   # pickaxe in slot 3
WARP_SLOT   = 1   # warp item in slot 1

REACH             = 5.0
MINING_LOOK_SPEED = 0.9
FOV_YAW_LIMIT     = 80.0
FOV_PITCH_LIMIT   = 65.0
WARP_JITTER       = 0.0

TOGGLE_KEY = 75   # K
KILL_KEY   = 256  # ESC
```

---

## How It Works (overview)

1. Press **K** — script activates.
2. Equips your warp item, rotates camera to Route 1, sneaks and right-clicks (Etherwarp).
3. Waits for teleport to land, equips your pickaxe.
4. Scans all blocks within `REACH` radius, filters to `TARGET_BLOCKS`.
5. Sorts them: in-FOV blocks nearest-first, then out-of-FOV nearest-first.
6. Rotates to each block in order and holds left-click until it breaks.
7. When no more blocks are reachable, warps to Route 2 and repeats.
8. After the last route, loops back to Route 1 indefinitely.
9. Press **K** to pause (releases all held keys), **ESC** to stop completely.

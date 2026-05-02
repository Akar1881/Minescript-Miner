"""
miner.py  -  Universal block miner using Minescript-Miner visibility library
Controls : K = toggle mining on/off  |  ESC = kill script completely

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HOW TO CONFIGURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. TARGET_BLOCKS  — the block IDs you want to mine.
     Use the Minecraft internal ID (always "minecraft:something").
     You can list multiple blocks and it will mine all of them.

     Examples:
       ["minecraft:coal_block"]
       ["minecraft:diamond_ore", "minecraft:deepslate_diamond_ore"]
       ["minecraft:mithril_ore", "minecraft:titanium_ore"]

  2. ROUTES  — the warp locations the script cycles through.
     Format:  "Route Name": (x, y, z)
     The script warps to each route in order, mines until nothing is
     reachable, then moves to the next route. After the last route it
     loops back to the first one automatically.

     To add a route: paste a new line  "My Route": (x, y, z),
     To remove a route: delete its line.
     Order matters — routes run top to bottom then repeat.

  3. MINING_SLOT  — hotbar slot number of your mining tool  (1 = first slot)
     WARP_SLOT    — hotbar slot number of your warp tool    (2 = second slot)

  4. REACH  — how far (in blocks) the script scans for target blocks.
     Default 5.0. Going higher than 6 is not recommended.
"""

from system.lib import minescript
import sys, os, time, math, random, threading

# ── Miner library path (do not change) ────────────────────────────────────────
ROOT  = os.path.dirname(os.path.abspath(__file__))
MINER = os.path.join(ROOT, "Minescript-Miner-master")
if MINER not in sys.path:
    sys.path.insert(0, MINER)

from visibility_scanner.scanner import scan_target
from visibility_scanner.world_scanners import get_area
from rotation import look

# ══════════════════════════════════════════════════════════════════════════════
#  TARGET BLOCKS  —  blocks the script will mine
#  Use Minecraft block IDs. Add as many as you need.
# ══════════════════════════════════════════════════════════════════════════════
TARGET_BLOCKS = [
    "minecraft:coal_block",
    "minecraft:diamond_block",           # uncomment to also mine diamond ore
    # "minecraft:deepslate_diamond_ore", # deepslate variant
]

# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES  —  "Route Name": (x, y, z)
#  Script warps to each route, mines it dry, then moves to the next.
#  Loops forever. Add or remove lines freely.
# ══════════════════════════════════════════════════════════════════════════════
"""
# Coal Blocks
ROUTES = {
    "Route 1": (162.0, 130.0, 35.5),
    "Route 2": (166.5, 132.0, 38.5),
    "Route 3": (168.5, 133.0, 42.5),
}
"""

# Diamond Blocks
ROUTES = {
    "Route 1": (152, 130, 38),
    "Route 2": (149, 130, 44),
    "Route 3": (143, 130, 43),
    "Route 4": (141, 130, 47),
}

# ══════════════════════════════════════════════════════════════════════════════
#  SETTINGS  —  adjust to your setup
# ══════════════════════════════════════════════════════════════════════════════

# Hotbar slot numbers (1 = leftmost slot)
MINING_SLOT = 1   # slot of your pickaxe / mining tool
WARP_SLOT   = 2   # slot of your warp item

# How far to scan for blocks (in blocks). 5 is a good balance of speed/coverage.
REACH = 5.0

# How fast the camera rotates to each new block while mining.
# 0.0 = slowest smooth arc, 1.0 = fastest smooth arc (still actually rotates).
# Use player_set_orientation (instant snap) only if you set this to None.
MINING_LOOK_SPEED = 0.9

# Prefer blocks the player is already looking toward before going for others.
# These are the angle limits (in degrees) that count as "in view".
FOV_YAW_LIMIT   = 80.0
FOV_PITCH_LIMIT = 65.0

# Random angle jitter on warp aim (degrees). Keep at 0.
# Etherwarp hits the FIRST block the ray enters — any jitter risks hitting
# the wrong block (1° at 15 blocks = ~0.26 blocks of horizontal error).
WARP_JITTER = 0.0

# Toggle key (K) and kill key (ESC) — change the numbers to remap.
# Key codes: K=75, O=79, ESC=256, F=33, G=34
TOGGLE_KEY = 75   # K  — start / pause mining
KILL_KEY   = 256  # ESC — stop the script completely

# ── Internal state (do not touch) ─────────────────────────────────────────────
_running     = False
_stop_script = False
_lock        = threading.Lock()

# ── Internal helpers ──────────────────────────────────────────────────────────

def _equip(slot):
    # Switch hotbar to the given slot (converts 1-indexed to 0-indexed)
    try:
        minescript.player_inventory_select_slot(slot - 1)
    except Exception:
        pass

def _stopped():
    # Returns True if the script should pause or quit
    with _lock:
        return _stop_script or not _running

def _in_fov(eye, yaw, pitch, bx, by, bz):
    # Returns True if the block centre is within the player's view cone
    dx  = bx + 0.5 - eye[0]
    dy  = by + 0.5 - eye[1]
    dz  = bz + 0.5 - eye[2]
    dxz = math.sqrt(dx*dx + dz*dz)
    block_yaw   = math.degrees(math.atan2(-dx, dz))
    block_pitch = math.degrees(-math.atan2(dy, max(dxz, 1e-6)))
    dyaw   = abs(((block_yaw - yaw + 180) % 360) - 180)
    dpitch = abs(block_pitch - pitch)
    return dyaw <= FOV_YAW_LIMIT and dpitch <= FOV_PITCH_LIMIT

def _dsq(eye, bx, by, bz):
    # Squared distance from eye to block centre
    return (bx+0.5-eye[0])**2 + (by+0.5-eye[1])**2 + (bz+0.5-eye[2])**2

def _warp_angles(tx, ty, tz):
    # Etherwarp uses DDA ray traversal from the player's eye and lands you ON TOP
    # of the first non-air block the ray hits.
    #
    # How to aim correctly:
    #   - Route coords (tx, ty, tz) are the player's FEET landing position.
    #   - The floor block (the block you land on) occupies y = floor(ty)-1 in
    #     integer block coords. Its TOP FACE is at world-y = floor(ty).
    #   - Aim at the CENTER of that top face:
    #       aim_x = floor(tx) + 0.5
    #       aim_y = floor(ty)          ← top surface of the floor block
    #       aim_z = floor(tz) + 0.5
    #   - Zero jitter: any angular jitter at range risks the ray crossing into
    #     an adjacent block (e.g., 1° at 15 blocks ≈ 0.26 blocks of miss).
    #
    px, py, pz = minescript.player_position()
    ex, ey, ez = px, py + 1.62, pz          # ray originates at player's eye

    aim_x = math.floor(tx) + 0.5            # horizontal center of floor block
    aim_y = float(math.floor(ty))           # TOP FACE of the floor block
    aim_z = math.floor(tz) + 0.5

    dx  = aim_x - ex
    dy  = aim_y - ey
    dz  = aim_z - ez
    dxz = math.sqrt(dx * dx + dz * dz)

    yaw   = math.degrees(math.atan2(-dx, dz))
    pitch = math.degrees(-math.atan2(dy, max(dxz, 1e-6)))

    if WARP_JITTER > 0:
        yaw   += random.uniform(-WARP_JITTER, WARP_JITTER)
        pitch += random.uniform(-WARP_JITTER, WARP_JITTER)

    return yaw, pitch

# ── Warp ──────────────────────────────────────────────────────────────────────

def _warp(coords):
    # Equip warp item, aim at the floor block's top face, hold shift and right-click
    tx, ty, tz = coords
    _equip(WARP_SLOT)
    yaw, pitch = _warp_angles(tx, ty, tz)
    look(yaw, pitch, urgent=0.85)          # fast rotation — still smooth, not instant
    minescript.player_press_sneak(True)    # hold shift
    time.sleep(0.15)                       # wait for shift to register
    minescript.player_press_use(True)      # right-click — tap only, do NOT hold
    time.sleep(0.05)                       # just long enough to register one click
    minescript.player_press_use(False)     # release immediately (holding causes double-warp)
    time.sleep(0.05)                       # brief pause before releasing shift
    minescript.player_press_sneak(False)   # release shift
    time.sleep(0.35)                       # wait for teleport to land
    _equip(MINING_SLOT)

# ── Mine ──────────────────────────────────────────────────────────────────────

def _mine():
    # Mine all reachable target blocks at the current position then return.
    # Blocks in the player's FOV are prioritised; furthest/behind tried last.
    while True:
        if _stopped():
            minescript.player_press_attack(False)
            return

        px, py, pz = minescript.player_position()
        eye = (px, py + 1.62, pz)

        try:
            cur_yaw, cur_pitch = minescript.player_orientation()
        except Exception:
            cur_yaw, cur_pitch = 0.0, 0.0

        # Scan all blocks within reach
        try:
            occluders = get_area(position=eye, reach=REACH)
        except Exception:
            time.sleep(0.02)
            continue

        # Filter to target blocks only
        targets = [e for e in occluders if any(t in e[1] for t in TARGET_BLOCKS)]
        if not targets:
            return  # nothing left in this route → move on

        # Sort: in-FOV blocks first (nearest first), then out-of-FOV (nearest first)
        targets.sort(key=lambda e: (
            0 if _in_fov(eye, cur_yaw, cur_pitch, *e[0]) else 1,
            _dsq(eye, *e[0])
        ))

        # Find the first block that is actually reachable (not occluded)
        result = None
        for entry in targets:
            try:
                r = scan_target(position=eye, target=entry[0], occluders=occluders)
            except Exception:
                continue
            if r is not None:
                result = r
                break

        if result is None:
            return  # all candidates occluded → route done

        # Rotate camera to the block face.
        # look() plays a smooth arc animation; urgency controls the speed.
        # MINING_LOOK_SPEED=0.0 is slowest, 1.0 is fastest smooth rotation.
        if MINING_LOOK_SPEED is None:
            minescript.player_set_orientation(result.target_angle[0], result.target_angle[1])
        else:
            look(result.target_angle[0], result.target_angle[1], urgent=MINING_LOOK_SPEED)

        bx, by, bz = result.world_pos
        live = minescript.getblock(bx, by, bz)

        # Confirm block is still there before swinging
        if not any(t in live for t in TARGET_BLOCKS):
            continue

        # Hold left-click until the block breaks, then immediately find the next one
        minescript.player_press_attack(True)
        while minescript.getblock(bx, by, bz) == live:
            if _stopped():
                minescript.player_press_attack(False)
                return
            time.sleep(0.008)   # poll at ~125 Hz
        minescript.player_press_attack(False)

# ── Key listener ──────────────────────────────────────────────────────────────

def _keys():
    global _running, _stop_script
    try:
        with minescript.EventQueue() as q:
            q.register_key_listener()
            while True:
                ev = q.get()
                if ev.type == minescript.EventType.KEY and ev.action == 1:
                    if ev.key == TOGGLE_KEY:
                        with _lock:
                            _running = not _running
                        minescript.echo("[miner] " + ("STARTED" if _running else "PAUSED"))
                    elif ev.key == KILL_KEY:
                        with _lock:
                            _stop_script = True
                        minescript.echo("[miner] Stopped.")
                        break
                with _lock:
                    if _stop_script:
                        break
    except Exception:
        with _lock:
            _stop_script = True

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    minescript.echo("[miner] Ready.  K = start/stop  |  ESC = kill")
    threading.Thread(target=_keys, daemon=True).start()

    while True:
        with _lock:
            if _stop_script:
                break
            active = _running
        if not active:
            time.sleep(0.05)
            continue

        _equip(MINING_SLOT)

        # Loop through every route in order, then repeat from the top
        for name, coords in ROUTES.items():
            if _stopped():
                break
            minescript.echo(f"[miner] {name} — warping...")
            _warp(coords)
            _mine()

    try:
        minescript.player_press_attack(False)
        minescript.player_press_sneak(False)
    except Exception:
        pass
    minescript.echo("[miner] Done.")

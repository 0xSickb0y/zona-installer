# Startup banner: a random ASCII art from zona/assets/ascii/, colored, with the ZONA version below it.

## The braille art draws wider in the editor than in a terminal, so the right edge can't line up in both.
## Since zona's banner only ever appears in a terminal, the terminal is the one that matters.

import random
from pathlib import Path

ASCII_DIR = Path(__file__).parent.parent / "assets" / "ascii"
TIPS_FILE = Path(__file__).parent.parent / "assets" / "tips.txt"  # one tip per line, shown under the banner
YELLOW = "\033[33m"
DIM = "\033[2m"
RESET = "\033[0m"


def show_banner(version):
    """Print one of the ASCII arts at random, followed by 'ZONA v<version>' aligned to its right edge."""
    arts = sorted(ASCII_DIR.glob("*.txt"))
    if not arts:
        return  # no art shipped: the banner is cosmetic, never fail over it
    art = random.choice(arts).read_text(encoding="utf-8").rstrip("\n")
    width = max(len(line) for line in art.splitlines())
    print(f"\n{YELLOW}{art}\n{f'ZONA v{version}'.rjust(width)}{RESET}")
    tips = TIPS_FILE.read_text(encoding="utf-8").splitlines() if TIPS_FILE.is_file() else []
    tips = [tip.strip() for tip in tips if tip.strip()]
    if tips:
        print(f"{DIM}  » {random.choice(tips)}{RESET}")
    print()

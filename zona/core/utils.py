from zona.core.log import logger

def yes_or_no(question, default=None):
    while True:
        answer = input(f"{question}").strip().lower()
        if answer == "" and default is not None:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False

        logger.warning("- [Please answer [Y, yes] or [N, no].]\n")


def choose(title, options, default=0):
    """Pacman-style numbered menu. Returns the index of the chosen option.

    :: There are 3 runners available:
       [1] GE-Proton11-12-x86_64 (Default)
       [2] Proton - Experimental
       [3] Proton 11.0

    Enter a number (default=1) >>>
    """
    print(f"\n:: There are {len(options)} {title} available:")
    for number, option in enumerate(options, start=1):
        suffix = " (Default)" if number - 1 == default else ""
        print(f"   [{number}] {option}{suffix}")
    print()
    while True:
        try:
            answer = input(f"Enter a number (default={default + 1}) >>> ").strip()
        except EOFError:  # no terminal attached (piped input): take the default
            print()
            return default
        if answer == "":
            return default
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        logger.warning(f"- [Please enter a number between 1 and {len(options)}.]\n")
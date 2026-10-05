def yes_or_no(question, default=None):
    while True:
        answer = input(f"{question}").strip().lower()
        if answer == "" and default is not None:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False

        print("Please answer [Y, yes] or [N, no].")
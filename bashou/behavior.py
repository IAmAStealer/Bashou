"""What the pet does. Evolving doesn't change the art: each stage unlocks new actions.

Actions use the pet's poses when it has them (wash1, tail_up…) and small text
particles (z, ♪, ✦) in the spot at the top of the sprite, so every pet can do them.
"""

import random

# stage -> (mood, weight, (min s, max s)) available from that stage on.
# Sleep is not in here: the pet only sleeps when the terminal is idle.
MOODS = {
    1: [("look", 2, (4, 7))],
    2: [("wash", 3, (5, 10)), ("hum", 2, (6, 12))],
    3: [("dance", 2, (5, 9)), ("sparkle", 2, (6, 12))],
}
ACTIONS = {
    1: "breathe, blink, sleep, look around",
    2: "wash, hum, flick its tail",
    3: "dance, sparkle",
}
SLEEP_AFTER = (5 * 60, 15 * 60)    # idle seconds before falling asleep, drawn at random


class Behavior:
    def __init__(self, rng=random, now=0):
        self.rng = rng
        self.stage = 1
        self.mood, self.end = "awake", now + 20000
        self.tail_end = 0
        self.sleep_after = self.rng.randint(*SLEEP_AFTER) * 1000

    def moods(self):
        return [m for stage in range(1, self.stage + 1) for m in MOODS[stage]]

    def next_mood(self, ms):
        if self.mood != "awake":
            self.mood, length = "awake", self.rng.randint(30, 90)
        else:
            choices = [(m, span) for m, w, span in self.moods() for _ in range(w)]
            self.mood, span = self.rng.choice(choices)
            length = self.rng.randint(*span)
        self.end = ms + length * 1000

    def frame(self, ms, pet, threat=False, idle=0):
        """Poses and particle text for this instant. `idle`: ms since the last keypress or command."""
        if idle >= self.sleep_after:
            self.mood, self.end = "sleep", ms + 1000
        elif self.mood == "sleep":
            # Woken up: pick how long the next idle stretch must be before sleeping again.
            self.sleep_after = self.rng.randint(*SLEEP_AFTER) * 1000
            self.mood, self.end = "awake", ms + self.rng.randint(30, 90) * 1000
        elif ms >= self.end:
            self.next_mood(ms)
        has = pet.poses.__contains__
        poses, text = [], ""
        mood = self.mood

        if mood == "sleep":
            if ms % 16000 < 7000:
                poses.append("inhale")
            poses.append("closed")
            text = ["", "z", "z Z"][ms // 2500 % 3]
        else:
            if ms % 10000 < 4000:
                poses.append("inhale")
            if mood == "awake":
                if self.rng.randrange(40) == 0:
                    poses.append("closed")
                if self.stage >= 2 and ms >= self.tail_end and self.rng.randrange(80) == 0:
                    self.tail_end = ms + 1500
            elif mood == "look":
                poses.append("right" if ms // 1500 % 2 else "left")
            elif mood == "wash":
                if has("wash1"):
                    poses += ["closed", "wash1" if ms // 500 % 2 else "wash2"]
                else:
                    poses.append("closed")
                    text = "♥" if ms // 700 % 2 else ""
            elif mood == "hum":
                poses.append("closed")
                text = ["♪", "♪ ♫", " ♫", ""][ms // 600 % 4]
            elif mood == "dance":
                poses.append(["left", "right"][ms // 400 % 2])
                text = "♪" if ms // 400 % 2 else "♫"
            elif mood == "sparkle":
                text = ["✦", " ✧", "✦ ✧", "  ✦"][ms // 500 % 4]
        if ms < self.tail_end:
            poses.append("tail_up")
        if threat and mood != "sleep":
            text = "⚠" if ms // 1000 % 2 else ""
        return poses, text

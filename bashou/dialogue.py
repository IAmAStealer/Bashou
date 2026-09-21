"""What pets say: hints toward the next achievement, tips for their tool, and personality.

Personality = the pet's own voice + traits from the achievements you earned
(win a fight and your pets get bolder, run commands at 3 am and they get nocturnal…).
"""

import random

from . import achievements

VOICE = {
    "cat": "Mrrp.", "frog": "Ribbit.", "turtle": "…", "mushroom": "*puff*", "slime": "Blub.",
    "sofa": "*creak*", "octopus": "Glub!", "dragon": "Rawr!", "fox": "*sniff*", "owl": "Hoo.",
    "mole": "*dig dig*", "snake": "Sss…", "ghost": "Boo~", "spider": "*tik-tik*", "ant": "*click*",
    "axolotl": "*wiggle*",
}

TIPS = {
    "cat": ["Ctrl+R searches your history as you type.", "`cd -` jumps back to the previous folder.",
            "`sudo !!` reruns the last command with sudo.", "Ctrl+A / Ctrl+E: start / end of the line.",
            "Ctrl+W deletes the word before the cursor."],
    "frog": ["`!$` is the last argument of the previous command.", "`fc` opens the last command in your editor.",
             "`history | grep ssh` finds that command from last week.", "Press Ctrl+R again for older matches."],
    "turtle": ["`watch -n 5 df -h` reruns a command every 5 s.", "`time make` tells how long it took.",
               "`sleep 600 && echo done` waits 10 minutes.", "`crontab -e` runs things on a schedule."],
    "mushroom": ['for f in *.log; do gzip "$f"; done', 'while read -r l; do echo "$l"; done < file',
                 "for i in {1..5}; do echo $i; done", "until ping -c1 host; do sleep 1; done",
                 "`seq 0 5 20` counts by fives: 0 5 10 15 20."],
    "slime": ["today=$(date +%F) stores a command's output.", "diff <(ls a) <(ls b) compares two outputs.",
              "cat <<EOF > file writes several lines at once.", "echo $(( 6 * 7 )) does math in bash."],
    "sofa": ["sort | uniq -c | sort -rn makes a top list.", "`sort -u` sorts and dedupes in one go.",
             "sort -t, -k3 -n sorts a CSV by its 3rd column.", "`uniq -d` shows only the duplicates."],
    "octopus": ["cmd 2>&1 | less pages the errors too.", "cmd | tee out.txt shows AND saves.",
                "`set -o pipefail`: a pipe fails if any part fails.", "cmd |& grep x also pipes stderr."],
    "dragon": ["`bashou fight`: the arena is always open.", "Stuck in the arena? Type `hint`.",
               "A threat you ignore comes back later."],
    "fox": ["find . -name '*.log' -mtime +7 : week-old logs.", "find . -type f -size +100M : big files.",
            "find . -name '*.tmp' -delete cleans up.", "find . -newer ref.txt : changed since ref.txt."],
    "owl": ["awk '{print $1}' prints the first column.", "awk -F: '{print $1}' /etc/passwd lists users.",
            "awk 'NR==5' prints line 5.", "awk 'length > 80' finds long lines."],
    "mole": ["grep -rn TODO . shows file and line number.", "grep -v '^#' drops comment lines.",
             "grep -l pattern *.txt lists matching files.", "grep -i ignores case."],
    "snake": ["sed -n '10,20p' prints lines 10 to 20.", "sed -i.bak 's/a/b/g' f keeps a backup.",
              "sed '/^$/d' removes empty lines.", "sed 's/[[:space:]]*$//' trims trailing spaces."],
    "ghost": ["ps aux --sort=-%mem | head : memory hogs.", "pgrep -a python lists python processes.",
              "kill -TERM first; -KILL only as a last resort.", "Ctrl+Z then `bg`: resume a job in background."],
    "spider": ["strace -e trace=openat ls : files it opens.", "strace -c cmd : a syscall summary.",
               "strace -p PID attaches to a running process.", "strace -f follows child processes."],
    "ant": ["find . -name '*.bak' | xargs rm", "find . -print0 | xargs -0 : safe with spaces.",
            "xargs -P4 runs 4 jobs in parallel.", "ls *.txt | xargs -I{} cp {} {}.bak"],
    "axolotl": ["`jq .` pretty-prints JSON.", "jq -r '.[].name' : raw names, no quotes.",
                "jq 'map(select(.age > 30))' filters a list.", "curl -s url | jq '.items[0]'"],
}

# Achievement -> an example that earns it.
EXAMPLES = {
    "historian": "history | tail", "loop": "for f in *; do echo $f; done",
    "reader": "while read -r l; do echo $l; done < file", "ranges": "for i in {1..3}; do echo $i; done",
    "capture": "echo \"today: $(date +%A)\"", "nested": "echo $(basename $(pwd))",
    "substitute": "diff <(ls /bin) <(ls /usr/bin)", "here": "cat <<EOF\nhi\nEOF",
    "tally": "sort file | uniq -c", "ranking": "du -s * | sort -rn", "unique": "sort -u file",
    "plumber": "ps aux | grep bash | wc -l", "pipeline": "cat f | tr A-Z a-z | sort | uniq -c | sort -rn",
    "tee_time": "ls | tee list.txt", "merge": "make 2>&1 | less",
    "time_traveller": "find . -mtime -1", "executor": "find . -name '*.tmp' -exec rm {} +",
    "pruner": "find . -name .git -prune -o -type f -print",
    "field_reader": "awk -F: '{print $1}' /etc/passwd", "accountant": "awk '{s+=$1} END {print s}' f",
    "scribe": "awk '{printf \"%-10s %s\\n\", $1, $2}' f",
    "digger": "grep -rn TODO .", "regex": "grep -E 'cat|dog' f", "context": "grep -C2 error log",
    "in_place": "sed -i 's/old/new/' f", "global": "sed 's/a/b/g' f", "printer": "sed -n '1,5p' f",
    "census": "ps aux", "seeker": "pgrep -a bash", "signal": "kill -TERM <pid>",
    "filter": "strace -e trace=openat ls", "follow": "strace -f bash -c ls", "summary": "strace -c ls",
    "placeholder": "ls | xargs -I{} echo {}", "parallel": "ls | xargs -P4 -n1 echo",
    "null": "find . -print0 | xargs -0 ls", "raw": "jq -r '.name' f.json",
    "selector": "jq '.[] | select(.ok)' f.json", "mapper": "jq 'map(.id)' f.json",
    "warrior": "bashou fight",
}

# Trait (an achievement you earned) -> lines any pet may say.
TRAITS = {
    "warrior": ["Any threats around? I'm ready.", "I sharpened my claws. `bashou fight`?"],
    "veteran": ["Ten fights won. The threats fear us now."],
    "legend": ["Legends don't wait for threats. They hunt them."],
    "night_owl": ["Late again? I like the quiet.", "The prompt glows nicer at night."],
    "explorer": ["So many tools already. What's next, `man -k`?"],
    "streak7": ["Another day together. Keep the streak!"],
    "sprinter": ["So many commands today. Coffee break?"],
    "plumber": ["Pipes are the best toys."],
    "tally": ["I like things counted and sorted."],
}

PERSONAL = {
    "cat": ["I'll just sit on your keyboard… no? Fine."], "frog": ["Hop hop. What's next?"],
    "turtle": ["Slow and steady. No rush."], "mushroom": ["Loops make me grow."],
    "slime": ["I can take the shape of any output."], "sofa": ["Sit down. Relax. Run a command."],
    "octopus": ["Eight arms, eight pipes."], "dragon": ["I guard your shell."],
    "fox": ["I can find anything. Anything."], "owl": ["Every line has fields, if you look closely."],
    "mole": ["I dig through text all day."], "snake": ["I rewrite what I touch."],
    "ghost": ["I see every process…"], "spider": ["I hear every syscall on my web."],
    "ant": ["Many small jobs make one big job."], "axolotl": ["JSON is my favourite pond."],
}


def hint(state, pet, rng):
    """Next achievement of this pet's family, or any one left, with an example."""
    earned = set(state["achievements"])
    todo = [a for a in achievements.family(pet) if a.id not in earned and not a.state]
    todo = todo or [a for a in achievements.ALL if a.id not in earned and not a.state]
    if not todo:
        return None
    a = rng.choice(todo)
    example = EXAMPLES.get(a.id)
    if example and "\n" not in example:
        return f"Try `{example}` ({a.name})"
    return f"Next: {a.how} ({a.name})"


def line(state, pet, rng=random):
    """One thing for `pet` to say, with its voice."""
    earned = set(state["achievements"])
    traits = [t for trait, lines in TRAITS.items() if trait in earned for t in lines]
    pools = [(hint(state, pet, rng), 4), (rng.choice(TIPS[pet]), 4),
             (rng.choice(traits + PERSONAL[pet]), 2)]
    pools = [(text, w) for text, w in pools if text]
    text = rng.choices([t for t, _ in pools], [w for _, w in pools])[0]
    return f"{VOICE[pet]} {text}"

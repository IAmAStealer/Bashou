"""Lessons: the Sage Owl teaches a tool on the road, before any fight or chest asks for it."""

# Each page: (text, example). A lesson counts as "met" for the tool (see fight.learned).
LESSONS = [
    {"id": "pipes", "tool": "|", "topics": ("bash", "linux"), "title": "Pipes", "pages": [
        ("A pipe | sends what one command prints into the next command, as if it were a file.",
         "ls | wc -l     # how many files here?"),
        ("Chain small tools, one step each: grep keeps the lines with error, sort puts identical lines "
         "side by side, uniq -c counts each group.", "grep error app.log | sort | uniq -c"),
        ("uniq only merges identical lines that follow each other. Without sort, a city that appears on "
         "lines 1 and 3 is counted twice. So sort always comes before uniq.",
         "cut -d' ' -f3 people.txt | sort | uniq -c"),
        ("Read a pipe left to right: take a column, keep each value once (sort -u = sort then uniq), "
         "then count the lines.", "cut -d' ' -f1 access.log | sort -u | wc -l"),
    ]},
    {"id": "awk", "tool": "awk", "topics": ("bash", "linux"), "title": "awk, the column reader", "pages": [
        ("awk reads a file line by line and cuts each line into fields: $1 is the first word, "
         "$2 the second, $NF the last.", "awk '{print $1}' people.txt"),
        ("-F sets the separator, for CSV and friends.", "awk -F, '{print $2}' sales.csv"),
        ("A condition before the braces picks lines; END runs after the last one.",
         "awk '$2 > 30 {n++} END {print n}' people.txt"),
    ]},
]
BY_ID = {lesson["id"]: lesson for lesson in LESSONS}


def next_for(topic, seen):
    """The first lesson of this topic you haven't had yet, or None."""
    return next((le for le in LESSONS if topic in le["topics"] and le["id"] not in seen), None)

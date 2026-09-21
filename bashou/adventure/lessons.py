"""Lessons: the Sage Owl teaches a tool on the road, before any fight or chest asks for it."""

# Each page: (text, example). A lesson counts as "met" for the tool (see fight.learned).
LESSONS = [
    {"id": "pipes", "tool": "|", "topics": ("bash", "linux"), "title": "Pipes", "pages": [
        ("A pipe | sends the output of one command into the next one.", "ls | wc -l     # how many files here?"),
        ("Chain small tools, one step each.", "grep error app.log | sort | uniq -c"),
        ("Read it left to right: filter, keep what you need, then count.",
         "cut -d' ' -f1 access.log | sort -u | wc -l"),
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

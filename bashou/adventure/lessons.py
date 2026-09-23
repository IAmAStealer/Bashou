"""Lessons: the Sage Owl teaches a tool on the road, before any fight or chest asks for it."""

# Each page: (text, example). A lesson counts as "met" for the tool (see fight.learned).
LESSONS = [
    {"id": "sort", "tool": "sort", "topics": ("bash", "linux"), "title": "sort, the organizer", "pages": [
        ("sort prints the lines of a file in alphabetical order. The file itself doesn't change.",
         "sort names.txt"),
        ("Numbers sorted as text go wrong: 10 comes before 9, because the character 1 comes before 9. "
         "-n compares them as numbers.", "sort -n scores.txt"),
        ("-r reverses the order, biggest first. Together, -rn and then head keep the top of the list.",
         "sort -rn scores.txt | head -3"),
        ("sort puts identical lines side by side. That's what uniq needs, since it only merges lines that "
         "follow each other: uniq -c then counts each group. sort -u keeps one of each.",
         "sort visitors.txt | uniq -c"),
    ]},
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
    {"id": "pipelines", "tool": "yaml", "topics": ("cicd",), "title": "Pipeline files", "pages": [
        ("GitHub Actions reads .github/workflows/*.yml, GitLab reads .gitlab-ci.yml. Names that start with "
         "a dot are hidden: ls -a shows them.", "ls -a; cat .gitlab-ci.yml"),
        ("These files are YAML: the spaces at the start of a line say what belongs to what, 2 more per "
         "level. A line one space off lands in the wrong place, or breaks the file. Never use tabs.",
         "cat -A .github/workflows/ci.yml   # shows every space, and tabs as ^I"),
        ("Jobs run side by side unless you set an order: needs: on GitHub, stages: on GitLab. A deploy "
         "should wait for the tests, and be skipped when they fail.", "grep -n 'needs:\\|stage' .gitlab-ci.yml"),
        ("Conditions decide when a job runs: if: on GitHub, rules: on GitLab. when: manual makes GitLab "
         "wait for someone to click, handy for a production deploy.", "grep -n 'if:\\|rules:\\|when:' .gitlab-ci.yml"),
        ("Never write a password or a token in the file: everyone who reads the repository gets it. The "
         "CI keeps secrets for you: ${{ secrets.NAME }} on GitHub, a CI/CD variable on GitLab.",
         "grep -rni 'token\\|password' .github .gitlab-ci.yml"),
    ]},
]
BY_ID = {lesson["id"]: lesson for lesson in LESSONS}


def next_for(topic, seen):
    """The first lesson of this topic you haven't had yet, or None."""
    return next((le for le in LESSONS if topic in le["topics"] and le["id"] not in seen), None)

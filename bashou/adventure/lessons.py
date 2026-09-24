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
        ("These files are YAML, written like an outline: a line pushed further right belongs to the line "
         "above it. Each level is 2 spaces further right. Only spaces, never tabs.",
         "cat .github/workflows/ci.yml"),
        ("Jobs run side by side unless you set an order: needs: on GitHub, stages: on GitLab. A deploy "
         "should wait for the tests, and be skipped when they fail.", "grep -n 'needs:\\|stage' .gitlab-ci.yml"),
        ("Conditions decide when a job runs: if: on GitHub, rules: on GitLab. when: manual makes GitLab "
         "wait for someone to click, handy for a production deploy.", "grep -n 'if:\\|rules:\\|when:' .gitlab-ci.yml"),
        ("Never write a password or a token in the file: everyone who reads the repository gets it. The "
         "CI keeps secrets for you: ${{ secrets.NAME }} on GitHub, a CI/CD variable on GitLab.",
         "grep -rni 'token\\|password' .github .gitlab-ci.yml"),
    ]},
    {"id": "sql", "tool": "sqlite3", "topics": ("sql",), "title": "SQL with SQLite", "pages": [
        ("A database keeps data in tables: rows and columns, like a spreadsheet the computer can search fast. "
         "SQLite keeps a whole database in one file: sqlite3 opens it, and creates it if it doesn't exist yet. "
         "Delete the file and the database is gone, nothing else to clean up.", "sqlite3 shop.db"),
        ("Words that start with a dot are sqlite3's own commands: .tables lists the tables, .schema shows how "
         "one is built (its columns and their types), .quit leaves. You can also give them right after the file.",
         "sqlite3 shop.db .schema products"),
        ("SQL itself reads almost like English. SELECT picks columns, FROM names the table, WHERE keeps only the "
         "rows that match. A statement ends with a ;, and text goes between single quotes.",
         "sqlite3 shop.db \"SELECT name, price FROM products WHERE price > 20;\""),
        ("COUNT(*) counts the rows, SUM(col) adds up a column, ORDER BY sorts. They answer questions like "
         "\"how many\" and \"how much\" without reading every row yourself.",
         "SELECT COUNT(*) FROM products WHERE stock = 0;"),
        ("Tables point at each other with numbers: an order keeps the id of its customer, not the name, so a "
         "name is written only once. JOIN … ON puts the matching rows side by side again.",
         "SELECT customers.name, orders.total FROM orders JOIN customers ON orders.customer_id = customers.id;"),
        ("CREATE TABLE makes a table and gives each column a type: TEXT for words, INTEGER for whole numbers. "
         "INSERT INTO adds a row: the columns, then the values in the same order.",
         "INSERT INTO products (name, price, stock) VALUES ('lamp', 25, 12);"),
        ("UPDATE changes rows, and WHERE picks which ones. Forget the WHERE and every row changes! Run a SELECT "
         "with the same WHERE first: it shows exactly what the UPDATE (or a DELETE) will touch.",
         "UPDATE products SET price = 30 WHERE name = 'lamp';"),
        ("Add a row, or change it if it's already there? INSERT … ON CONFLICT DO UPDATE (an \"upsert\") does both "
         "in one statement. INSERT OR REPLACE looks similar but deletes the old row first: its other columns are lost.",
         "INSERT INTO stock (item, qty) VALUES ('mug', 5) ON CONFLICT(item) DO UPDATE SET qty = qty + excluded.qty;"),
    ]},
    {"id": "secrets", "tool": "gpg", "topics": ("linux",), "title": "gpg and pass, for secrets", "pages": [
        ("A file in clear can be read by anyone who gets the disk, a backup or your repository. gpg (GnuPG) locks "
         "files. -c locks one with a passphrase, and the same passphrase opens it.", "gpg -c notes.txt   # writes notes.txt.gpg"),
        ("gpg -d opens a locked file and prints it; -o writes it to a file instead. gpg keeps the clear original "
         "when it locks one: delete it yourself once the .gpg is made.", "gpg -d notes.txt.gpg"),
        ("A key pair has two halves: the public key you give to anyone, and the private key only you keep. What "
         "is encrypted for your public key opens only with your private key.", "gpg --full-generate-key"),
        ("It works the other way for signatures: a project signs its downloads with its private key, and you "
         "check them with its public key. \"Good signature\": it's from them, and nothing changed since.",
         "gpgv --keyring ./vendor.gpg tool.tar.gz.sig tool.tar.gz"),
        ("pass is the Unix password store: each password in its own file under ~/.password-store, encrypted with "
         "your gpg key. pass init <your key> starts it; pass generate makes a strong password; pass show prints one.",
         "pass generate web/forum 24"),
        ("A script should never hold a password: it ends up in backups, screenshots and git history. $( ) lets it "
         "fetch the password when it runs, so the file stays safe to share.", "DB_PASSWORD=\"$(pass show db/prod)\""),
        ("Not installed yet? On Debian and Ubuntu: sudo apt install gnupg pass. On Rocky, Alma and RHEL: sudo dnf "
         "install gnupg2, then pass from EPEL (sudo dnf install epel-release first).", "sudo apt install gnupg pass"),
    ]},
]
BY_ID = {lesson["id"]: lesson for lesson in LESSONS}


def next_for(topic, seen):
    """The first lesson of this topic you haven't had yet, or None."""
    return next((le for le in LESSONS if topic in le["topics"] and le["id"] not in seen), None)

"""SQL fights (owner, 2026-09-24): SQLite, because the whole database is one file you can delete, and
sqlite3 is one small package. Read with SELECT and JOIN, build a table, INSERT, UPDATE one row, and
INSERT … ON CONFLICT DO UPDATE (an "upsert").

The databases are made at setup with Python's own sqlite3 module and read back the same way, read-only:
Bashou never runs the player's SQL except the upsert file, on throwaway copies, with ATTACH refused.
"""

import shutil
import sqlite3
import tempfile
from pathlib import Path

from . import Challenge

PRODUCTS = [("lamp", 25, 12), ("chair", 45, 7), ("desk", 120, 3), ("mug", 8, 40), ("pen", 2, 300),
            ("notebook", 5, 150), ("backpack", 60, 9), ("headphones", 80, 14), ("kettle", 30, 6),
            ("clock", 22, 11), ("scarf", 18, 25), ("umbrella", 15, 30), ("keyboard", 70, 8), ("plant", 12, 20)]
MISSING = [("teapot", 28, 5), ("candle", 6, 60), ("mirror", 40, 4), ("blanket", 35, 10), ("stool", 20, 15)]
PEOPLE = ["Ada", "Linus", "Grace", "Ken", "Margaret", "Dennis", "Barbara", "Alan", "Radia", "Guido"]
CITIES = ["Lyon", "Oslo", "Porto", "Kyoto", "Quito", "Dakar"]


# What the player's SQL may do on the throwaway copy: read and change rows, nothing else. No ATTACH or
# VACUUM INTO (they write other files), no CREATE/DROP, no PRAGMA.
ALLOWED = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE,
           sqlite3.SQLITE_DELETE, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT,
           sqlite3.SQLITE_RECURSIVE}


def connect(path, readonly=True):
    """Read-only for Bashou's own queries; for the player's SQL, only row changes (see ALLOWED)."""
    uri = f"file:{Path(path).resolve()}?mode=ro" if readonly else f"file:{Path(path).resolve()}"
    db = sqlite3.connect(uri, uri=True, timeout=2)
    if not readonly:
        db.set_authorizer(lambda action, *args: sqlite3.SQLITE_OK if action in ALLOWED else sqlite3.SQLITE_DENY)
    return db


def rows(path, query, *params):
    """The rows of a query on a player's database, or None if it can't be read (no file, no table…)."""
    if not Path(path).is_file():
        return None
    try:
        db = connect(path)
        try:
            return db.execute(query, params).fetchall()
        finally:
            db.close()
    except sqlite3.Error:
        return None


def make_shop(work, rng, products=None):
    """shop.db: products, and customers with their orders (a customer's id in each order)."""
    db = sqlite3.connect(work / "shop.db")
    db.executescript("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, price INTEGER, stock INTEGER);"
                     "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, city TEXT);"
                     "CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id), "
                     "product TEXT, total INTEGER);")
    products = products or rng.sample(PRODUCTS, 10)
    db.executemany("INSERT INTO products (name, price, stock) VALUES (?, ?, ?)", products)
    people = rng.sample(PEOPLE, 6)
    db.executemany("INSERT INTO customers (name, city) VALUES (?, ?)", [(p, rng.choice(CITIES)) for p in people])
    for _ in range(18):
        name, price, _stock = rng.choice(products)
        qty = rng.randint(1, 3)
        db.execute("INSERT INTO orders (customer_id, product, total) VALUES (?, ?, ?)",
                   (rng.randint(1, len(people)), name, price * qty))
    db.commit()
    db.close()
    return products, people


def all_products(work):
    return rows(work / "shop.db", "SELECT name, price, stock FROM products ORDER BY name")


# --- SELECT: how many products cost more than … -------------------------------------------------

def count_setup(work, rng):
    products, _ = make_shop(work, rng)
    limit = rng.choice([10, 20, 25, 30, 50])
    return {"args": {"limit": limit}, "answer": str(sum(price > limit for _, price, _ in products))}


# --- JOIN: how much did … spend ------------------------------------------------------------------

def join_setup(work, rng):
    make_shop(work, rng)
    spent = rows(work / "shop.db", "SELECT customers.name, SUM(orders.total) FROM orders "
                 "JOIN customers ON orders.customer_id = customers.id GROUP BY customers.id")
    name, total = rng.choice(spent)
    return {"args": {"name": name}, "answer": str(total)}


# --- CREATE TABLE ----------------------------------------------------------------------------------

def create_setup(work, rng):
    table, first, second = rng.choice([("books", "title", "year"), ("movies", "title", "year"),
                                       ("songs", "title", "plays"), ("planets", "name", "moons")])
    return {"args": {"db": f"{table}.db", "table": table, "text": first, "number": second}}


def create_verify(work, meta, value):
    a = meta["args"]
    cols = rows(work / a["db"], "SELECT name, upper(type) FROM pragma_table_info(?)", a["table"])
    types = dict(cols or [])
    return (a["text"] in types and any(t in types[a["text"]] for t in ("TEXT", "CHAR", "CLOB"))
            and a["number"] in types and "INT" in types[a["number"]])


# --- INSERT --------------------------------------------------------------------------------------

def insert_setup(work, rng):
    products = rng.sample(PRODUCTS, 8)
    make_shop(work, rng, products)
    name, price, stock = rng.choice(MISSING)
    return {"args": {"item": name, "price": price, "stock": stock}, "before": sorted(map(list, products))}


def insert_verify(work, meta, value):
    a = meta["args"]
    now = all_products(work)
    return now is not None and sorted(map(list, now)) == sorted(meta["before"] + [[a["item"], a["price"], a["stock"]]])


# --- UPDATE, one row only ------------------------------------------------------------------------

def update_setup(work, rng):
    products = rng.sample(PRODUCTS, 8)
    make_shop(work, rng, products)
    name, price, stock = rng.choice(products)
    new = price + rng.choice([-3, -1, 2, 5, 10])
    after = sorted([n, new if n == name else p, s] for n, p, s in products)
    return {"args": {"item": name, "price": new}, "after": after}


def update_verify(work, meta, value):
    now = all_products(work)
    return now is not None and sorted(map(list, now)) == meta["after"]


# --- INSERT … ON CONFLICT DO UPDATE ----------------------------------------------------------------

UPSERT_FILE = "restock.sql"


def make_stock(path, items):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE stock (item TEXT PRIMARY KEY, qty INTEGER NOT NULL, shelf TEXT)")
    db.executemany("INSERT INTO stock VALUES (?, ?, ?)", items)
    db.commit()
    db.close()


def upsert_setup(work, rng):
    names = rng.sample([n for n, _, _ in PRODUCTS], 6)
    items = [(n, rng.randint(2, 30), f"{rng.choice('ABCD')}{rng.randint(1, 9)}") for n in names]
    item, n = rng.choice(names), rng.randint(3, 12)
    make_stock(work / "stock.db", items)
    (work / UPSERT_FILE).write_text("-- One statement: add the delivery to stock.db (see the task).\n")
    return {"args": {"item": item, "n": n, "file": UPSERT_FILE}, "items": items}


def run_on_copy(sql, items, drop=None):
    """Run the player's file on a fresh throwaway stock (without the row `drop`); its rows, or None."""
    tmp = Path(tempfile.mkdtemp(prefix="bashou-sql-"))
    try:
        make_stock(tmp / "stock.db", [i for i in items if i[0] != drop])
        db = connect(tmp / "stock.db", readonly=False)
        try:
            db.executescript(sql)
            db.commit()
            return {item: (qty, shelf) for item, qty, shelf in db.execute("SELECT item, qty, shelf FROM stock")}
        finally:
            db.close()
    except sqlite3.Error:
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def upsert_verify(work, meta, value):
    """The file must add to an item already there (keeping its shelf), and create it when it's missing."""
    try:
        sql = (work / UPSERT_FILE).read_text()
    except OSError:
        return False
    a, items = meta["args"], [tuple(i) for i in meta["items"]]
    item, n = a["item"], a["n"]
    here = run_on_copy(sql, items)
    gone = run_on_copy(sql, items, drop=item)
    expect = {i: (q, s) for i, q, s in items}
    old_qty, shelf = expect[item]
    return (here == {**expect, item: (old_qty + n, shelf)}
            and gone is not None and gone.get(item, (None,))[0] == n
            and {k: v for k, v in gone.items() if k != item} == {k: v for k, v in expect.items() if k != item})


def chest_setup(work, rng):
    db = sqlite3.connect(work / "loot.db")
    db.execute("CREATE TABLE loot (item TEXT, rarity TEXT, gold INTEGER)")
    loot = [(f"{rng.choice(['old', 'shiny', 'tiny', 'heavy'])} {rng.choice(['ring', 'coin', 'map', 'key', 'gem'])}",
             rng.choice(["common", "common", "rare", "epic"]), rng.randint(1, 90)) for _ in range(12)]
    db.executemany("INSERT INTO loot VALUES (?, ?, ?)", loot)
    db.commit()
    db.close()
    return {"args": {}, "answer": str(sum(r == "rare" for _, r, _ in loot))}


# --- the fights -----------------------------------------------------------------------------------

OPEN = ("sqlite3 shop.db opens the database; .tables lists its tables, .schema products shows the "
        "columns of one, .quit leaves. You can also give the SQL right away: sqlite3 shop.db \"SELECT …;\"")
SQL = dict(pet="squirrel", tools=("sqlite3",), skill="sql")

ALL = [
    Challenge(level=1, id="query_quokka", threat="Query Quokka", **SQL,
              task="The Query Quokka hides the price list in shop.db.\nHow many products cost more than "
                   "{limit}? answer <number>",
              hints=[OPEN, "SELECT COUNT(*) FROM products WHERE price > {limit}; counts the rows WHERE keeps. "
                           "Without COUNT(*), you'd see the rows themselves: check them if you're unsure."],
              help="Look for how to open a database file, and how to pass SQL on the command line.",
              setup=count_setup),
    Challenge(level=1, id="table_troll", threat="Table Troll", **SQL, fix=True,
              task="The Table Troll wants somewhere to keep its {table}.\nCreate the database {db} with a table "
                   "{table}: a column {text} that holds text and a column {number} that holds whole numbers. "
                   "Then: verify",
              hints=["sqlite3 {db} opens it, and creates the file as soon as you write something in it. "
                     "CREATE TABLE gives a table its name and its columns, each with a type: TEXT for words, "
                     "INTEGER for whole numbers.",
                     "sqlite3 {db} \"CREATE TABLE {table} ({text} TEXT, {number} INTEGER);\" then check it "
                     "with sqlite3 {db} .schema"],
              setup=create_setup, verify=create_verify),
    Challenge(level=1, id="insert_imp", threat="Insert Imp", **SQL, fix=True,
              task="The Insert Imp ate a line of shop.db: the {item} is missing from products.\nAdd it back: "
                   "price {price}, stock {stock}. Then: verify",
              hints=[OPEN, "INSERT INTO adds a row: name the columns, then give the values in the same order. "
                           "Text goes between single quotes: INSERT INTO products (name, price, stock) VALUES "
                           "('{item}', {price}, {stock});"],
              setup=insert_setup, verify=insert_verify),
    Challenge(level=2, id="update_urchin", threat="Update Urchin", **SQL, fix=True, after=("insert_imp",),
              task="The Update Urchin messed with a price in shop.db.\nSet the price of {item} to {price}, and "
                   "only that one: every other row must stay as it is. Then: verify",
              hints=["UPDATE changes rows, and WHERE picks which ones. Without WHERE, every row changes: a classic "
                     "production accident. Run a SELECT with the same WHERE first to see what you're about to change.",
                     "UPDATE products SET price = {price} WHERE name = '{item}';"],
              setup=update_setup, verify=update_verify),
    Challenge(level=2, id="join_jackal", threat="Join Jackal", **SQL, after=("query_quokka",),
              task="The Join Jackal split shop.db: the orders only keep a customer's number (customer_id), the "
                   "names are in customers.\nHow much did {name} spend in total? answer <number>",
              hints=["JOIN puts two tables side by side: ON says which rows go together. Here an order goes with "
                     "the customer whose id is its customer_id. SUM(total) adds up a column.",
                     "SELECT SUM(orders.total) FROM orders JOIN customers ON orders.customer_id = customers.id "
                     "WHERE customers.name = '{name}';"],
              setup=join_setup),
    Challenge(level=2, id="upsert_unicorn", threat="Upsert Unicorn", **SQL, fix=True, after=("update_urchin",),
              task="The Upsert Unicorn brings a delivery: {n} × {item}.\nWrite in {file} one SQL statement that "
                   "adds them to stock.db: if {item} is already in stock, raise its qty by {n} (keep its shelf); "
                   "if it isn't, insert it with qty {n}. Bashou runs your file on both cases. Then: verify",
              hints=["INSERT … ON CONFLICT(item) DO UPDATE tries the insert, and when the item already exists "
                     "(item is the PRIMARY KEY) runs the update instead: an \"upsert\". In the update, excluded.qty "
                     "is the qty you tried to insert. INSERT OR REPLACE is not the same: it deletes the old row, so "
                     "the old qty and the shelf are lost.",
                     "INSERT INTO stock (item, qty) VALUES ('{item}', {n}) ON CONFLICT(item) DO UPDATE SET "
                     "qty = qty + excluded.qty;  Try it on a copy: cp stock.db test.db; sqlite3 test.db < {file}"],
              setup=upsert_setup, verify=upsert_verify),
]

# The Sage Owl's chest for the SQL path.
from .trials import trial  # noqa: E402

CHEST = trial("trial_sql_loot", 1, "This chest holds loot.db, a list of treasures. How many of them are rare? "
              "answer <number>",
              ["sqlite3 loot.db .schema shows the table and its columns. SELECT … FROM loot WHERE rarity = 'rare'; "
               "shows the rare ones.", "SELECT COUNT(*) FROM loot WHERE rarity = 'rare';"],
              chest_setup, lambda w, m, v: v.strip() == m["answer"], requires=["sqlite3"], teaches=["sqlite3"])

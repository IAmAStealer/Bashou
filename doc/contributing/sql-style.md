# SQL style: at the prompt and in code

Bashou teaches SQL with SQLite, two ways, and every piece of SQL we show belongs to one of them:

- **At the prompt** (`sqlite3 shop.db`, or `sqlite3 shop.db "SELECT …;"`): typed once, read on the
  screen. Looking around matters, and you see the result before it matters.
- **In code** (a Python program, a `.sql` file a script or Bashou runs): runs later, on data nobody
  checked. Here a habit that is fine at the prompt can be a bug or a hole.

This file is the checklist for every SQL sample in Bashou: lesson pages, the owl lesson, adventure
questions, fight tasks, hints and starter files, and the SQL in our own Python code. The `sql-judge`
agent (`.claude/agents/sql-judge.md`) applies it after each change, and `tests/test_sql_style.py`
runs every full statement on a database with the fight tables.

Each rule has an id, used in reviews. A sample that breaks a rule on purpose (to show the mistake)
is marked ✘ and followed by the right form. In a question, wrong choices may be wrong on purpose,
but the right answer and its explanation must follow the rules of their mode.

Facts are SQLite facts: a claim about speed, order or behavior is checked by running it (Python's
`sqlite3` module or the `sqlite3` shell) or against the SQLite docs, never from general SQL lore.
When another database does it differently and a player could meet it (MySQL's `SHOW TABLES`,
PostgreSQL's `$1`), say so.

## Both modes

| Id | Rule | Why | Source |
|---|---|---|---|
| Q1 | Text values in single quotes: `'mug'`. Double quotes are for names (`"order"`), never for text. | SQLite reads `"mug"` as text only when no column is called mug, and the `sqlite3` shell refuses it since 3.41. | [quirks §8](https://sqlite.org/quirks.html#double_quoted_string_literals_are_accepted) |
| Q2 | NULL is tested with `IS NULL` / `IS NOT NULL`, never `= NULL`. | `x = NULL` is NULL, never true: the row silently drops out. | [NULL handling](https://sqlite.org/nulls.html), [expressions](https://sqlite.org/lang_expr.html) |
| Q3 | `UPDATE` and `DELETE` samples have a `WHERE`, unless the sample is about forgetting it (✘). Teach: the same `WHERE` in a `SELECT` first. | Without it every row changes, and SQLite doesn't ask. | [UPDATE](https://sqlite.org/lang_update.html), [DELETE](https://sqlite.org/lang_delete.html) |
| Q4 | `INSERT` names its columns: `INSERT INTO t (a, b) VALUES (…)`. | Without them the values follow the table's column order: a new column breaks or shifts them. | [INSERT](https://sqlite.org/lang_insert.html) |
| Q5 | Joins are written `JOIN … ON`, and a column is named with its table (`orders.total`) when two tables are in the query. No comma joins (`FROM a, b WHERE …`). | The pairing condition sits next to the join; a forgotten `ON` is easy to see. A missing condition pairs every row with every row. | [SELECT, join-clause](https://sqlite.org/lang_select.html#fromclause) |
| Q6 | With `GROUP BY`, every column in `SELECT` is grouped, aggregated, or decided by the grouped key (`customers.name` with `GROUP BY customers.id`). | SQLite accepts other "bare" columns and picks a value from any row of the group; other databases refuse the query. | [quirks §6](https://sqlite.org/quirks.html#aggregate_queries_can_contain_non_aggregate_result_columns_that_are_not_in_the_group_by_clause), [bare columns](https://sqlite.org/lang_select.html#bare_columns_in_an_aggregate_query) |
| Q7 | A result whose order matters has `ORDER BY`; `LIMIT` comes with `ORDER BY`. Never say rows come back "in insert order". | Without `ORDER BY` the order is undefined, and changes with indexes and versions. | [SELECT, ORDER BY](https://sqlite.org/lang_select.html#orderby) |
| Q8 | Adding or updating in one go: `INSERT … ON CONFLICT(key) DO UPDATE`. `INSERT OR REPLACE` only when losing the old row's other columns is fine, and then say so. | `REPLACE` deletes the old row first. | [UPSERT](https://sqlite.org/lang_upsert.html), [ON CONFLICT](https://sqlite.org/lang_conflict.html) |
| Q9 | Types are said the SQLite way: a column type is an affinity, not a guard. Don't claim `INTEGER` refuses text, unless the table is `STRICT` (needs 3.37+, see the versions table). | `INSERT … VALUES ('abc')` into an `INTEGER` column stores the text. | [datatypes](https://sqlite.org/datatype3.html), [STRICT](https://sqlite.org/stricttables.html) |
| Q10 | `REFERENCES` is shown with `PRAGMA foreign_keys = ON;` whenever a sample counts on it to refuse a bad row. | Foreign keys are off by default, on each new connection. | [foreign keys §2](https://sqlite.org/foreignkeys.html#fk_enable) |
| Q11 | A statement newer than SQLite 3.34 (Rocky 9) says what it needs: "needs SQLite 3.35+". See the versions table. | Rocky 9 and Debian 12 players have older SQLite than our docs. | [release history](https://sqlite.org/changes.html) |
| Q12 | A full statement in a sample runs: right tables, right columns, ends with `;`. A fragment (`JOIN customers ON …`) is fine in text, and is not shown as a whole statement. | The test runs every full statement on the fight tables. | Bashou |
| Q13 | A claim about speed or a query plan is shown with `EXPLAIN QUERY PLAN` on the fight database, never taken from general SQL lore ("EXISTS is faster than IN"). | SQLite's planner is its own; what's true elsewhere may not be here. | [EXPLAIN QUERY PLAN](https://sqlite.org/eqp.html), [query planner](https://sqlite.org/queryplanner.html) |

## At the prompt

These are fine at the prompt. When code sits next to them (a Python lesson, a `.sql` file a
program runs), say they stop being fine there.

| Id | Allowed at the prompt | In code instead | Source |
|---|---|---|---|
| QP1 | `SELECT *` and no `LIMIT` to look at a small table | named columns (QC2) | Bashou |
| QP2 | The shell's dot-commands: `.tables`, `.schema t`, `.mode box`, `.headers on`, `.quit`. They are `sqlite3`'s, not SQL: they start the line, take no `;`, and other tools don't know them. | SQL only | [CLI](https://sqlite.org/cli.html) |
| QP3 | SQL on the command line goes in double quotes, text inside it in single quotes: `sqlite3 shop.db "SELECT name FROM products WHERE name = 'mug';"`. Longer SQL goes in a file: `sqlite3 shop.db < fix.sql`. | a file, or parameters (QC1) | bash quoting (bash-style B1) |
| QP4 | Try a risky change on a copy: `cp shop.db test.db` when no program has the database open; otherwise `.backup test.db` (or `VACUUM INTO 'test.db'`, 3.27+). | `con.backup()` in Python | [backup](https://sqlite.org/backup.html), [VACUUM INTO](https://sqlite.org/lang_vacuum.html#vacuuminto), [WAL files](https://sqlite.org/wal.html) |
| QP5 | `BEGIN;`, look with `SELECT`, then `COMMIT;` or `ROLLBACK;` | a transaction in code (QC3) | [transactions](https://sqlite.org/lang_transaction.html) |

## In code

| Id | Rule | Why | Source |
|---|---|---|---|
| QC1 | Values go in as parameters: `con.execute("SELECT … WHERE name = ?", (name,))` or `:name`. Never an f-string, `+`, `%` or `.format()` into SQL. Names of tables and columns can't be parameters: pick them from a fixed list in the code. | A value with a `'` changes the query: SQL injection. | [Python sqlite3: placeholders](https://docs.python.org/3/library/sqlite3.html#sqlite3-placeholders), [OWASP](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html) |
| QC2 | Name the columns you read; no `SELECT *` in code. | A new or reordered column silently shifts what the code unpacks. | community: [Use The Index, Luke](https://use-the-index-luke.com/blog/2013-08/its-not-about-the-star-stupid) |
| QC3 | Writes that belong together go in one transaction: `with con:` commits at the end or rolls back on an error (it doesn't close the connection). Many rows: `executemany`. | Half-written data after a crash; one transaction per row is also very slow. | [Python sqlite3: transactions](https://docs.python.org/3/library/sqlite3.html#sqlite3-connection-context-manager), [FAQ 19](https://sqlite.org/faq.html#q19) |
| QC4 | Connections are closed (`try`/`finally`, `contextlib.closing`). Errors are caught as `sqlite3.Error` where the code can say what failed, never with a bare `except`. | An open connection keeps locks; a bare except hides the real bug. | [Python sqlite3](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.close) |
| QC5 | Code that only reads opens the file read-only: `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`. | A bug can't change the data, and a missing file is an error instead of a new empty database. | [URI filenames](https://sqlite.org/uri.html) |
| QC6 | SQL from outside (a player's file) never runs on real data: a throwaway copy, and an authorizer that allows only what the task needs (no `ATTACH`, no `PRAGMA`). | `executescript` runs anything, `ATTACH` writes other files. | [set_authorizer](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.set_authorizer), [ATTACH](https://sqlite.org/lang_attach.html) |

## Versions

What CI and players run: Debian 12 has SQLite 3.40.1, Rocky 9 has 3.34.1, macOS has Apple's build
(`sqlite3 --version`). Python's `sqlite3` module uses the system library on Linux. Fights and their
checks use only what Rocky 9 has; a newer statement is taught in text with "needs 3.xx+".

| Statement | Needs | Debian 12 | Rocky 9 |
|---|---|---|---|
| `INSERT … ON CONFLICT DO UPDATE` | 3.24 | yes | yes |
| `VACUUM INTO` | 3.27 | yes | yes |
| `UPDATE … FROM`, `.mode box` | 3.33 | yes | yes |
| `RETURNING`, `ALTER TABLE DROP COLUMN`, several `ON CONFLICT` | 3.35 | yes | no |
| `STRICT` tables | 3.37 | yes | no |
| `->` and `->>` (JSON) | 3.38 | yes | no |

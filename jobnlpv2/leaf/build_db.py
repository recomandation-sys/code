"""Build the leaf taxonomy SQLite database and the export tables.

Run from the repo root:

    python jobnlpv2/leaf/build_db.py
"""
from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path

INPUTS = Path(__file__).resolve().parent / "inputs"
EXPORT = Path(__file__).resolve().parent / "export"
DB = EXPORT / "taxonomy.sqlite"


def name_key(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("-", " ")).strip().casefold()


def parts(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, headers: list[str], rows: list[tuple]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def build() -> None:
    leaves = read_csv(INPUTS / "leaves_best.csv")
    definitions = read_csv(INPUTS / "definitions_best.csv")
    tasks = read_csv(INPUTS / "main_tasks_best.csv")
    technologies = read_csv(INPUTS / "technologies_best.csv")
    by_name = {name_key(row["leaf_name"]): row for row in leaves}

    families = []
    seen_families = set()
    parents = []
    seen_parents = set()
    for row in leaves:
        if row["family_id"] not in seen_families:
            seen_families.add(row["family_id"])
            families.append((row["family_id"], row["family_name"]))
        if row["parent_id"] not in seen_parents:
            seen_parents.add(row["parent_id"])
            parents.append((row["parent_id"], row["parent_name"], row["family_id"]))

    definition_rows = []
    for row in definitions:
        leaf = by_name.get(name_key(row["leaf_name"]))
        if leaf is None or leaf["id"] != row["id"]:
            raise SystemExit(f"definition does not match leaf {row['id']} {row['leaf_name']}")
        definition_rows.append((leaf["id"], row["definition"]))

    task_rows = []
    task_id = 1
    for row in tasks:
        leaf = by_name.get(name_key(row["leaf_name"]))
        if leaf is None or leaf["id"] != row["id"]:
            raise SystemExit(f"main tasks do not match leaf {row['id']} {row['leaf_name']}")
        for task in parts(row["main_tasks"]):
            task_rows.append((f"K{task_id:04d}", leaf["id"], task))
            task_id += 1

    technology_rows = []
    link_rows = []
    unmatched = []
    for row in technologies:
        technology_rows.append((
            row["technology_id"],
            row["technology"],
            row.get("category") or "",
            row.get("aliases") or "",
        ))
        for leaf_name in parts(row.get("related_leafs") or ""):
            leaf = by_name.get(name_key(leaf_name))
            if leaf is None:
                unmatched.append(leaf_name)
                continue
            link_rows.append((leaf["id"], row["technology_id"]))
    link_rows = list(dict.fromkeys(link_rows))

    EXPORT.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    connection = sqlite3.connect(DB)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE family (
            family_id TEXT PRIMARY KEY,
            family_name TEXT NOT NULL
        );
        CREATE TABLE parent (
            parent_id TEXT PRIMARY KEY,
            parent_name TEXT NOT NULL,
            family_id TEXT NOT NULL REFERENCES family(family_id)
        );
        CREATE TABLE leaf (
            leaf_id TEXT PRIMARY KEY,
            leaf_name TEXT NOT NULL UNIQUE,
            parent_id TEXT NOT NULL REFERENCES parent(parent_id)
        );
        CREATE TABLE definition (
            leaf_id TEXT PRIMARY KEY REFERENCES leaf(leaf_id),
            definition TEXT NOT NULL
        );
        CREATE TABLE main_task (
            task_id TEXT PRIMARY KEY,
            leaf_id TEXT NOT NULL REFERENCES leaf(leaf_id),
            task TEXT NOT NULL
        );
        CREATE TABLE technology (
            technology_id TEXT PRIMARY KEY,
            technology TEXT NOT NULL,
            category TEXT NOT NULL,
            aliases TEXT NOT NULL
        );
        CREATE TABLE leaf_technology (
            leaf_id TEXT NOT NULL REFERENCES leaf(leaf_id),
            technology_id TEXT NOT NULL REFERENCES technology(technology_id),
            PRIMARY KEY (leaf_id, technology_id)
        );
        """
    )
    connection.executemany("INSERT INTO family VALUES (?, ?)", families)
    connection.executemany("INSERT INTO parent VALUES (?, ?, ?)", parents)
    connection.executemany(
        "INSERT INTO leaf VALUES (?, ?, ?)",
        [(row["id"], row["leaf_name"], row["parent_id"]) for row in leaves],
    )
    connection.executemany("INSERT INTO definition VALUES (?, ?)", definition_rows)
    connection.executemany("INSERT INTO main_task VALUES (?, ?, ?)", task_rows)
    connection.executemany("INSERT INTO technology VALUES (?, ?, ?, ?)", technology_rows)
    connection.executemany("INSERT OR IGNORE INTO leaf_technology VALUES (?, ?)", link_rows)
    connection.commit()

    counts = {
        name: connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        for name in ("family", "parent", "leaf", "definition", "main_task", "technology", "leaf_technology")
    }
    missing_definition = connection.execute(
        "SELECT COUNT(*) FROM leaf LEFT JOIN definition USING (leaf_id) WHERE definition.leaf_id IS NULL"
    ).fetchone()[0]
    missing_task = connection.execute(
        "SELECT COUNT(*) FROM leaf WHERE leaf_id NOT IN (SELECT leaf_id FROM main_task)"
    ).fetchone()[0]
    if counts["family"] != 8 or counts["parent"] != 24 or counts["leaf"] != 118:
        raise SystemExit(f"taxonomy counts failed: {counts}")
    if missing_definition or missing_task:
        raise SystemExit(f"missing definition={missing_definition} task={missing_task}")

    element_rows = connection.execute(
        """
        SELECT
            leaf.leaf_id,
            parent.parent_id,
            parent.parent_name,
            family.family_id,
            family.family_name,
            definition.definition
        FROM leaf
        JOIN parent ON parent.parent_id = leaf.parent_id
        JOIN family ON family.family_id = parent.family_id
        JOIN definition ON definition.leaf_id = leaf.leaf_id
        ORDER BY leaf.leaf_id
        """
    ).fetchall()
    tasks_by_leaf: dict[str, list[str]] = {}
    for leaf_id, task in connection.execute("SELECT leaf_id, task FROM main_task ORDER BY task_id"):
        tasks_by_leaf.setdefault(leaf_id, []).append(task)
    techno_by_leaf: dict[str, list[str]] = {}
    for leaf_id, technology in connection.execute(
        """
        SELECT leaf_technology.leaf_id, technology.technology
        FROM leaf_technology
        JOIN technology ON technology.technology_id = leaf_technology.technology_id
        ORDER BY technology.technology_id
        """
    ):
        techno_by_leaf.setdefault(leaf_id, []).append(technology)
    elements = [
        (
            leaf_id,
            parent_id,
            parent_name,
            family_id,
            family_name,
            "; ".join(techno_by_leaf.get(leaf_id, [])),
            "; ".join(tasks_by_leaf.get(leaf_id, [])),
            definition,
        )
        for leaf_id, parent_id, parent_name, family_id, family_name, definition in element_rows
    ]

    write_csv(EXPORT / "family.csv", ["family_id", "family_name"], families)
    write_csv(EXPORT / "parent.csv", ["parent_id", "parent_name", "family_id"], parents)
    write_csv(
        EXPORT / "leaf.csv",
        ["leaf_id", "leaf_name", "parent_id"],
        [(row["id"], row["leaf_name"], row["parent_id"]) for row in leaves],
    )
    write_csv(EXPORT / "definition.csv", ["leaf_id", "definition"], definition_rows)
    write_csv(EXPORT / "main_task.csv", ["task_id", "leaf_id", "task"], task_rows)
    write_csv(
        EXPORT / "technology.csv",
        ["technology_id", "technology", "category", "aliases"],
        technology_rows,
    )
    write_csv(EXPORT / "leaf_technology.csv", ["leaf_id", "technology_id"], link_rows)
    write_csv(
        EXPORT / "leaf_element.csv",
        ["id", "parent_id", "parent", "family_id", "family", "techno", "task", "def"],
        elements,
    )
    connection.close()
    print(
        f"wrote {DB} families={counts['family']} parents={counts['parent']} "
        f"leaves={counts['leaf']} tasks={counts['main_task']} "
        f"technologies={counts['technology']} links={counts['leaf_technology']} "
        f"unmatched_leaf_names={len(set(unmatched))}"
    )


if __name__ == "__main__":
    build()

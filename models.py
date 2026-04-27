"""Database models for PROWESS."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "prowess.db"

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database schema."""
    conn = get_db()
    c = conn.cursor()

    # Employees
    c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            geo_cluster TEXT DEFAULT 'Downtown'
        )
    """)

    # Preferences (per employee, per planning cycle)
    c.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            preferred_days TEXT,
            vacation_days TEXT,
            min_office_days INTEGER DEFAULT 2,
            max_office_days INTEGER DEFAULT 4,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)

    # Solver runs (one per planning cycle)
    c.execute("""
        CREATE TABLE IF NOT EXISTS solver_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT,
            feasible BOOLEAN,
            objective REAL,
            result_json TEXT
        )
    """)

    # Results (per employee, per solver run)
    c.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            employee_id TEXT NOT NULL,
            schedule TEXT,
            scores TEXT,
            FOREIGN KEY (run_id) REFERENCES solver_runs(id),
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)

    # Key-value config store (e.g. pending groups)
    c.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()
    conn.close()

def get_config(key, default=None):
    """Read a JSON-encoded config value."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else default

def set_config(key, value):
    """Write a JSON-encoded config value."""
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
              (key, json.dumps(value)))
    conn.commit()
    conn.close()

def reset_db():
    """Wipe all data from every table (for re-seeding demo data)."""
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM results")
    c.execute("DELETE FROM solver_runs")
    c.execute("DELETE FROM preferences")
    c.execute("DELETE FROM employees")
    conn.commit()
    conn.close()

class Employee:
    @staticmethod
    def get_by_name(name):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM employees WHERE name = ?", (name,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_by_id(emp_id):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM employees WHERE id = ?", (emp_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def list_all():
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM employees ORDER BY name")
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def create(emp_id, name, geo_cluster="Downtown"):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO employees (id, name, geo_cluster) VALUES (?, ?, ?)",
                (emp_id, name, geo_cluster)
            )
            conn.commit()
            result = True
        except sqlite3.IntegrityError:
            result = False
        conn.close()
        return result

    @staticmethod
    def update_cluster(emp_id, geo_cluster):
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE employees SET geo_cluster = ? WHERE id = ?", (geo_cluster, emp_id))
        conn.commit()
        affected = c.rowcount
        conn.close()
        return affected > 0

class Preferences:
    @staticmethod
    def get_latest(employee_id):
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "SELECT * FROM preferences WHERE employee_id = ? ORDER BY submitted_at DESC LIMIT 1",
            (employee_id,)
        )
        row = c.fetchone()
        conn.close()
        if row:
            pref = dict(row)
            pref['preferred_days'] = json.loads(pref['preferred_days'] or "[]")
            pref['vacation_days'] = json.loads(pref['vacation_days'] or "[]")
            return pref
        return None

    @staticmethod
    def save(employee_id, preferred_days=None, vacation_days=None, min_office=2, max_office=4):
        conn = get_db()
        c = conn.cursor()
        c.execute(
            """INSERT INTO preferences
               (employee_id, preferred_days, vacation_days, min_office_days, max_office_days)
               VALUES (?, ?, ?, ?, ?)""",
            (
                employee_id,
                json.dumps(preferred_days or []),
                json.dumps(vacation_days or []),
                min_office,
                max_office
            )
        )
        conn.commit()
        conn.close()

class SolverRun:
    @staticmethod
    def create(status, feasible, objective, result_json):
        conn = get_db()
        c = conn.cursor()
        c.execute(
            """INSERT INTO solver_runs (status, feasible, objective, result_json)
               VALUES (?, ?, ?, ?)""",
            (status, feasible, objective, json.dumps(result_json))
        )
        run_id = c.lastrowid
        conn.commit()
        conn.close()
        return run_id

    @staticmethod
    def get_latest():
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM solver_runs ORDER BY run_date DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if row:
            result = dict(row)
            result['result_json'] = json.loads(result['result_json'])
            return result
        return None

class Result:
    @staticmethod
    def save(run_id, employee_id, schedule, scores):
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO results (run_id, employee_id, schedule, scores) VALUES (?, ?, ?, ?)",
            (run_id, employee_id, json.dumps(schedule), json.dumps(scores))
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_for_employee(employee_id):
        conn = get_db()
        c = conn.cursor()
        c.execute(
            """SELECT r.* FROM results r
               JOIN solver_runs sr ON r.run_id = sr.id
               WHERE r.employee_id = ?
               ORDER BY sr.run_date DESC LIMIT 1""",
            (employee_id,)
        )
        row = c.fetchone()
        conn.close()
        if row:
            result = dict(row)
            result['schedule'] = json.loads(result['schedule'])
            result['scores'] = json.loads(result['scores'])
            return result
        return None

    @staticmethod
    def get_all_for_run(run_id):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM results WHERE run_id = ? ORDER BY employee_id", (run_id,))
        rows = c.fetchall()
        conn.close()
        results = []
        for row in rows:
            result = dict(row)
            result['schedule'] = json.loads(result['schedule'])
            result['scores'] = json.loads(result['scores'])
            results.append(result)
        return results

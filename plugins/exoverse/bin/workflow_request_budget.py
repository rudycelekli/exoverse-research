"""Durable worst-case holds for a workflow's model gateway."""

from contextlib import closing
import os
from pathlib import Path
import sqlite3


class BudgetRefused(ValueError):
    """The gateway must stop without forwarding the request."""


def _positive_integer(value):
    return type(value) is int and 0 < value < 2**63


class RequestBudget:
    """One shared ledger per pilot. Amounts are integer millionths of a USD."""

    def __init__(self, path):
        self.path = Path(path).resolve()

    def _connect(self):
        return sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True)

    def initialize(self, *, cap_microusd, request_limit):
        if not all(map(_positive_integer, (cap_microusd, request_limit))):
            raise ValueError("A positive integer cap and request limit are required.")
        os.close(os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        with closing(self._connect()) as db, db:
            db.executescript("""
                CREATE TABLE policy (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    cap INTEGER NOT NULL CHECK (cap > 0),
                    request_limit INTEGER NOT NULL CHECK (request_limit > 0)
                );
                CREATE TABLE holds (
                    request_id TEXT PRIMARY KEY,
                    amount INTEGER NOT NULL CHECK (amount > 0)
                );
            """)
            db.execute("INSERT INTO policy VALUES (1, ?, ?)", (cap_microusd, request_limit))

    def reserve(self, request_id, worst_case_microusd):
        """Commit a hold before forwarding. Failed requests retain their hold."""
        if (not isinstance(request_id, str) or not 0 < len(request_id) <= 128
                or not _positive_integer(worst_case_microusd)):
            raise BudgetRefused("A bounded request ID and positive worst-case cost are required.")
        try:
            with closing(self._connect()) as db, db:
                db.execute("BEGIN IMMEDIATE")
                policy = db.execute("SELECT cap, request_limit FROM policy WHERE id = 1").fetchone()
                if policy is None:
                    raise BudgetRefused("Request budget policy is missing.")
                cap, limit = policy
                count, reserved = db.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM holds").fetchone()
                if count >= limit or worst_case_microusd > cap - reserved:
                    raise BudgetRefused("The pilot request budget is exhausted.")
                db.execute("INSERT INTO holds VALUES (?, ?)", (request_id, worst_case_microusd))
        except sqlite3.Error as error:
            raise BudgetRefused("The request already has a hold or the ledger is unavailable.") from error

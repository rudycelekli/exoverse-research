"""Durable worst-case holds for a workflow's model gateway."""

from contextlib import closing
from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3
from uuid import uuid4


class BudgetRefused(ValueError):
    """The gateway must stop without forwarding the request."""


def _positive_integer(value):
    return type(value) is int and 0 < value < 2**63


@dataclass(frozen=True)
class BudgetBinding:
    ledger_id: str
    cap_microusd: int
    request_limit: int
    policy_sha256: str

    def row(self):
        return (self.ledger_id, self.cap_microusd, self.request_limit, self.policy_sha256)


class RequestBudget:
    """One shared ledger per pilot. Amounts are integer millionths of a USD."""

    def __init__(self, path, *, binding=None):
        self.path = Path(path).resolve()
        self.binding = binding

    def _connect(self):
        return sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True)

    def initialize(self, *, cap_microusd, request_limit, policy_sha256=None):
        if self.binding is not None:
            raise ValueError("A bound gateway cannot initialize another ledger.")
        if policy_sha256 is not None and (
            not isinstance(policy_sha256, str) or len(policy_sha256) != 64
            or any(char not in "0123456789abcdef" for char in policy_sha256)
        ):
            raise ValueError("Expected a SHA-256 fingerprint for the pilot policy.")
        if not all(map(_positive_integer, (cap_microusd, request_limit))):
            raise ValueError("A positive integer cap and request limit are required.")
        binding = BudgetBinding(uuid4().hex, cap_microusd, request_limit, policy_sha256)
        os.close(os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        with closing(self._connect()) as db, db:
            db.executescript("""
                CREATE TABLE policy (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    ledger_id TEXT NOT NULL,
                    cap INTEGER NOT NULL CHECK (cap > 0),
                    request_limit INTEGER NOT NULL CHECK (request_limit > 0),
                    policy_sha256 TEXT
                );
                CREATE TABLE holds (
                    request_id TEXT PRIMARY KEY,
                    amount INTEGER NOT NULL CHECK (amount > 0)
                );
            """)
            db.execute("INSERT INTO policy VALUES (1, ?, ?, ?, ?)", binding.row())
        return binding

    def reserve(self, request_id, worst_case_microusd):
        """Commit a hold before forwarding. Failed requests retain their hold."""
        if (not isinstance(request_id, str) or not 0 < len(request_id) <= 128
                or not _positive_integer(worst_case_microusd)):
            raise BudgetRefused("A bounded request ID and positive worst-case cost are required.")
        try:
            with closing(self._connect()) as db, db:
                db.execute("BEGIN IMMEDIATE")
                db.row_factory = sqlite3.Row
                policy = db.execute("SELECT * FROM policy WHERE id = 1").fetchone()
                if policy is None:
                    raise BudgetRefused("Request budget policy is missing.")
                fields = ("ledger_id", "cap", "request_limit", "policy_sha256")
                is_bound = "policy_sha256" in policy.keys() and policy["policy_sha256"] is not None
                if is_bound or self.binding is not None:
                    if (self.binding is None or not all(field in policy.keys() for field in fields)
                            or tuple(policy[field] for field in fields) != self.binding.row()):
                        raise BudgetRefused("The budget ledger no longer matches the frozen pilot.")
                cap, limit = policy["cap"], policy["request_limit"]
                count, reserved = db.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM holds").fetchone()
                if count >= limit or worst_case_microusd > cap - reserved:
                    raise BudgetRefused("The pilot request budget is exhausted.")
                db.execute("INSERT INTO holds VALUES (?, ?)", (request_id, worst_case_microusd))
        except sqlite3.Error as error:
            raise BudgetRefused("The request already has a hold or the ledger is unavailable.") from error

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/exoverse/bin"))

from workflow_request_budget import BudgetRefused, RequestBudget


class RequestBudgetTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "pilot.sqlite"
        self.budget = RequestBudget(self.path)

    def test_missing_ledger_refuses_without_creating_one(self):
        with self.assertRaises(BudgetRefused):
            self.budget.reserve("first", 1)
        self.assertFalse(self.path.exists())

    def test_limits_survive_restart_and_duplicate_is_refused(self):
        self.budget.initialize(cap_microusd=200_000_000, request_limit=2)
        self.budget.reserve("first", 100_000_000)
        reopened = RequestBudget(self.path)
        with self.assertRaises(BudgetRefused):
            reopened.reserve("first", 1)
        with self.assertRaises(BudgetRefused):
            reopened.reserve("second", 100_000_001)
        reopened.reserve("second", 1)
        with self.assertRaises(BudgetRefused):
            reopened.reserve("third", 1)
        with self.assertRaises(FileExistsError):
            reopened.initialize(cap_microusd=400_000_000, request_limit=6)

    def test_concurrent_requests_cannot_oversubscribe(self):
        self.budget.initialize(cap_microusd=200_000_000, request_limit=6)

        def reserve(index):
            try:
                RequestBudget(self.path).reserve(str(index), 100_000_000)
            except BudgetRefused:
                return False
            return True

        with ThreadPoolExecutor(max_workers=6) as workers:
            self.assertEqual(sum(workers.map(reserve, range(6))), 2)

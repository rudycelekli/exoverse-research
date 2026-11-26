import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TASK = Path(__file__).resolve().parents[1] / "examples/harbor/retrieval"


class RetrievalCorpusTest(unittest.TestCase):
    def test_exact_source_and_abstention_are_scored_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "answers.json"
            labels = TASK / "tests/labels.json"
            corpus = TASK / "environment/corpus.json"
            answers = {
                key: {field: label[field] for field in ("source", "answer")} if label else None
                for key, label in json.loads(labels.read_bytes()).items()
            }
            answers["q1"]["source"] = "ops-2"
            answers["q4"] = {"source": "ops-3", "answer": "Platform"}
            path.write_text(json.dumps(answers))
            result = subprocess.check_output(
                [sys.executable, str(TASK / "tests/score.py"), str(path), str(labels), str(corpus)]
            )
            self.assertEqual(json.loads(result), {"citation_support": 2 / 3, "abstention": 0.5})

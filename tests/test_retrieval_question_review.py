import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "examples/harbor/run_retrieval_study.py"
spec = importlib.util.spec_from_file_location("retrieval_study", SCRIPT)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class QuestionReviewTest(unittest.TestCase):
    def test_checks_bytes_used_for_question_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            trial = root / "Direct/trial/result.json"
            labels = root / "tests/labels.json"
            labels.parent.mkdir()
            labels.write_text(json.dumps({"q": None}))
            answers = trial.parent / "verifier/answers.json"
            answers.parent.mkdir(parents=True)
            answers.write_text(json.dumps({"q": None}))
            receipt = {
                "input_sha256": {"tests/labels.json": hashlib.sha256(labels.read_bytes()).hexdigest()},
                "answer_checks": {"Direct": {"answers_sha256": hashlib.sha256(answers.read_bytes()).hexdigest()}},
            }

            rows = study.question_results([trial], root, receipt)
            self.assertTrue(rows[0]["arms"]["Direct"]["passed"])

            original = answers.read_bytes()
            answers.write_bytes(original + b" ")
            with self.assertRaisesRegex(ValueError, "answers changed"):
                study.question_results([trial], root, receipt)

            answers.write_bytes(original)
            labels.write_bytes(labels.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "labels changed"):
                study.question_results([trial], root, receipt)

"""Deterministic policies with the same initial retrieval and different fallback."""

import json
from pathlib import Path
import sys


def run(policy, questions, corpus):
    sources = {item["id"]: item for item in corpus}
    predictions = {}
    for question in questions:
        source = sources.get(question["initial_source"])
        match = lambda item: (item["entity"], item["field"]) == (question["entity"], question["field"])
        if source and match(source):
            answer = {"source": source["id"], "answer": source["value"]}
        elif policy == "grounded":
            evidence = next((item for item in corpus if match(item)), None)
            answer = {"source": evidence["id"], "answer": evidence["value"]} if evidence else None
        else:
            answer = {"source": source["id"] if source else None, "answer": "30 days"}
        predictions[question["id"]] = answer
    return predictions


if __name__ == "__main__":
    def load(filename):
        return json.loads(Path(filename).read_bytes())

    result = run(sys.argv[1], load("questions.json"), load("corpus.json"))
    Path("/tmp/answers.json").write_text(json.dumps(result))

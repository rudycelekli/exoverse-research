"""Score exact answer/source matches and justified abstention separately."""

import json
from pathlib import Path
import sys


def score(answers, labels, corpus):
    if set(answers) != set(labels):
        raise ValueError("Expected one result for each frozen question.")
    sources = {item["id"]: item["text"] for item in corpus}
    supported = [key for key, label in labels.items() if label is not None]
    unsupported = labels.keys() - set(supported)
    for key in supported:
        if labels[key]["span"] not in sources.get(labels[key]["source"], ""):
            raise ValueError("A labeled source span is missing.")
    return {
        "citation_support": sum(
            answers[key] == {field: labels[key][field] for field in ("source", "answer")}
            for key in supported
        ) / len(supported),
        "abstention": sum(answers[key] is None for key in unsupported) / len(unsupported),
    }


if __name__ == "__main__":
    answers, labels, corpus = [json.loads(Path(path).read_bytes()) for path in sys.argv[1:]]
    print(json.dumps(score(answers, labels, corpus), sort_keys=True))

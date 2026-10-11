"""Eval fixture for the super-linting skill: a small Python script."""
import json
import sys


def main(path):
    with open(path) as f:
        data = json.load(f)
    print(len(data))


if __name__ == "__main__":
    main(sys.argv[1])

"""Eval fixture for the super-linting skill: an existing Python entrypoint."""


def handler(event):
    return {"status": 200, "body": event.get("name", "world")}

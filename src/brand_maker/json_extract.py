"""Defensive extraction of one JSON-like object from model text."""


class NoJSONObject(ValueError):
    """Raised when model text contains no object-shaped JSON block."""


def extract_json_object(raw: str) -> str:
    """Return the first balanced object, respecting braces inside JSON strings."""

    start = raw.find("{")
    if start < 0:
        raise NoJSONObject("model output contained no JSON object")

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(raw)):
        character = raw[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue

        if character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return raw[start : index + 1]

    # Preserve object-shaped malformed output so schema validation, not refusal
    # handling, owns the retry decision.
    return raw[start:].strip().removesuffix("```").rstrip()

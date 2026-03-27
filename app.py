from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from flask import Flask, jsonify


DATA_FILE = Path(__file__).with_name("AI_policy_summaries_unique_by_course.json")


def normalize_course_code(value: str) -> str:
    """Normalize course codes for stable lookups."""
    decoded = unquote(value)
    return "".join(decoded.strip().upper().split())


def base_course_code(value: str) -> str:
    """Remove a trailing campus suffix such as H5 for fallback matching."""
    if len(value) >= 2 and value[-2].isalpha() and value[-1].isdigit():
        return value[:-2]
    return value


def load_courses(
    data_file: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Load the course dataset and build normalized exact and base-code lookups."""
    if not data_file.exists():
        raise RuntimeError(f"Missing JSON file: {data_file}")

    try:
        payload = json.loads(data_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {data_file}: {exc}") from exc

    if not isinstance(payload, list):
        raise RuntimeError(f"Expected {data_file} to contain a JSON array.")

    exact_lookup: dict[str, dict[str, Any]] = {}
    base_lookup: dict[str, list[dict[str, Any]]] = {}
    records: list[dict[str, Any]] = []

    for item in payload:
        if not isinstance(item, dict):
            continue

        records.append(item)
        raw_course_code = item.get("course_code")
        if not isinstance(raw_course_code, str) or not raw_course_code.strip():
            continue

        normalized_code = normalize_course_code(raw_course_code)
        if normalized_code in exact_lookup:
            continue

        exact_lookup[normalized_code] = item
        base_lookup.setdefault(base_course_code(normalized_code), []).append(item)

    return records, exact_lookup, base_lookup


def create_app() -> Flask:
    app = Flask(__name__)

    try:
        records, exact_lookup, base_lookup = load_courses(DATA_FILE)
    except RuntimeError as exc:
        raise SystemExit(f"Startup error: {exc}") from exc

    app.config["COURSE_COUNT"] = len(records)
    app.config["EXACT_LOOKUP"] = exact_lookup
    app.config["BASE_LOOKUP"] = base_lookup

    def find_course(course_code: str) -> tuple[str, dict[str, Any] | None]:
        normalized_code = normalize_course_code(course_code)
        exact_match = app.config["EXACT_LOOKUP"].get(normalized_code)
        if exact_match is not None:
            return "ok", exact_match

        matches = app.config["BASE_LOOKUP"].get(base_course_code(normalized_code), [])
        if len(matches) == 1:
            return "ok", matches[0]
        if len(matches) > 1:
            return "ambiguous", None
        return "not_found", None

    @app.get("/health")
    def health() -> Any:
        return jsonify({"ok": True})

    @app.get("/course/<course_code>")
    def get_course_policy(course_code: str) -> Any:
        status, course = find_course(course_code)
        if status == "ambiguous":
            return jsonify({"error": "Ambiguous course code, please include full course code"}), 400
        if course is None:
            return jsonify({"error": "Course not found"}), 404

        return jsonify(
            {
                "course_code": course.get("course_code"),
                "ai_policy_stance": course.get("ai_policy_stance"),
                "extracted_policy_passage": course.get("extracted_policy_passage"),
            }
        )

    @app.get("/course/<course_code>/full")
    def get_full_course(course_code: str) -> Any:
        status, course = find_course(course_code)
        if status == "ambiguous":
            return jsonify({"error": "Ambiguous course code, please include full course code"}), 400
        if course is None:
            return jsonify({"error": "Course not found"}), 404

        return jsonify(course)

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

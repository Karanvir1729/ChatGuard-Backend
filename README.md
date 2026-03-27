# ChatGuard Backend

Simple Flask backend for querying course AI policy data from a local JSON file.

## Files

```text
app.py
requirements.txt
README.md
AI_policy_summaries_unique_by_course.json
```

## What It Does

- Loads `AI_policy_summaries_unique_by_course.json` on startup
- Builds an in-memory lookup by normalized `course_code`
- Returns lightweight policy data for a course
- Returns the full stored course object when needed

Matching rules:
- trims whitespace
- uppercases
- removes internal spaces
- tries an exact normalized match first
- if that fails, tries again after removing a trailing campus suffix such as `H5`
- returns a 400 error if the suffix-stripped match would map to multiple courses

Examples that match:
- `CSC148H5`
- `csc148h5`
- `CSC 148H5`
- `CSC148`

If duplicate normalized course codes exist, the first one in the JSON file is kept.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

The server runs on `http://localhost:5000` by default.

You can override the port:

```bash
PORT=8000 python app.py
```

## Routes

### `GET /health`

Response:

```json
{"ok": true}
```

### `GET /course/<course_code>`

Returns:

```json
{
  "course_code": "CSC148H5",
  "ai_policy_stance": "unclear",
  "extracted_policy_passage": "..."
}
```

If the course is not found:

```json
{"error": "Course not found"}
```

If the suffix-stripped course code matches multiple records:

```json
{"error": "Ambiguous course code, please include full course code"}
```

### `GET /course/<course_code>/full`

Returns the full JSON object for the course, including `full_syllabus_text`.

If the course is not found:

```json
{"error": "Course not found"}
```

If the suffix-stripped course code matches multiple records:

```json
{"error": "Ambiguous course code, please include full course code"}
```

## Example cURL Commands

Health check:

```bash
curl http://localhost:5000/health
```

Lightweight course lookup:

```bash
curl http://localhost:5000/course/CSC148H5
```

Lookup without spaces and with lowercase:

```bash
curl http://localhost:5000/course/csc%20148h5
```

Lookup without the `H5` suffix:

```bash
curl http://localhost:5000/course/CSC148
```

Full course record:

```bash
curl http://localhost:5000/course/CSC148H5/full
```

Missing course:

```bash
curl http://localhost:5000/course/DOESNOTEXIST
```

## Startup Errors

If the JSON file is missing or invalid, the app exits immediately with a clear startup error message.

## Upgrading from a JSON File to Postgres Later

When the project outgrows a local JSON file:

1. Move the course data into a `courses` table keyed by normalized `course_code`.
2. Keep the controller and route layer stable while replacing the in-memory store with a repository/data-access layer.
3. Add indexes for `course_code` and full-text search fields.
4. Keep `normalizeCourseCode` as a shared utility so request behavior stays consistent.
5. Introduce migrations and connection pooling once writes or frequent updates become necessary.

## Notes

- Course matching is case-insensitive and removes spaces before lookup.
- Inputs like `csc108h5`, `CSC108H5`, and `CSC 108H5` all normalize to the same lookup key.
- If duplicate normalized course codes appear in the dataset, the backend keeps the first and logs a warning.
- Invalid records are skipped during load, and the server logs the validation issues.

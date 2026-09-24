{
  "id": "dbaaf504",
  "title": "Set up tests for auth and health routes",
  "tags": [
    "backend",
    "tests",
    "auth"
  ],
  "status": "open",
  "created_at": "2026-09-24T01:40:54.399Z"
}

Add separate backend route tests for auth and health behavior after the non-auth route tests are in place.

Scope:
- `GET /health`
- `GET /me`
- authentication dependency/JWT behavior as implemented

Cover:
- health success response
- authenticated `/me` success response
- missing/invalid token failures
- any auth behavior added later, including roles/ownership if introduced

Keep this separate from TODO-d67c6e4b, which intentionally skips auth.py routes.

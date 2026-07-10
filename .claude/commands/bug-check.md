# /bug-check — Full Project Health Check

Scan the codebase for bugs, security issues, and code quality problems.
Fix everything you find automatically.

## Scope
If a specific file or feature is mentioned after the command, check only that.
Otherwise, check the ENTIRE project.

## Check These Categories:

### 1. SECURITY ISSUES (Critical — fix immediately)
- SQL injection: any raw string concatenation in SQL queries?
  Every query MUST use parameterized placeholders (? or %s)
- Exposed secrets: any API keys, passwords, or tokens hardcoded in code?
  All secrets must come from settings table or environment variables
- XSS vulnerabilities: any user input rendered in templates without escaping?
  Jinja2 auto-escapes, but check for |safe or markup usage
- CSRF: all POST forms must have some protection
- Session security: session secret key must not be hardcoded
- File upload safety: if any file uploads exist, check file type validation
- Auth bypass: can any protected route be accessed without login?
  Check every route has @login_required except /login, /signup, /api/*
- Password storage: passwords must be hashed, never plain text
- Directory traversal: any user input used in file paths?

### 2. BUG DETECTION (High — fix immediately)
- Unclosed database connections: every get_db() must have matching close()
  or use context manager (with)
- Missing error handling: any function that calls external services
  (WhatsApp, Gemini, Traccar) without try-except?
- Null/None checks: accessing dict keys or object attributes that could be None?
- Integer/string type mismatches: comparing or concatenating wrong types?
- Missing imports: any module using something not imported?
- Circular imports: any files importing each other?
- Dead code: functions defined but never called anywhere?
- Race conditions: any shared state modified without locks?
- State machine violations: can trip status skip steps or go backward?
- Database schema mismatches: do model functions match actual table columns?

### 3. CODE QUALITY (Medium — fix if quick)
- Functions longer than 50 lines → suggest splitting
- Duplicate code across files → suggest extracting to shared utility
- Missing type hints on function parameters
- Missing docstrings on public functions
- Inconsistent naming (camelCase vs snake_case)
- Hardcoded values that should be constants or settings
- Print statements that should be proper logging
- Unused variables or imports
- TODO or FIXME comments that need attention

### 4. PERFORMANCE (Low — note but don't always fix)
- N+1 queries: loops that make a DB query per iteration
  → suggest JOINs instead
- Missing database indexes on frequently queried columns
  (trip.status, trip.client_id, vehicle.status)
- Large query results without LIMIT
- Unnecessary database calls (fetching same data multiple times)

### 5. PRODUCTION READINESS
- Does app handle database connection failures gracefully?
- Does app handle WhatsApp service being down gracefully?
- Does app handle Gemini API failures gracefully?
- Does app handle Traccar being unavailable gracefully?
- Are all external service calls wrapped in try-except with timeouts?
- Do all forms show proper error/success flash messages?
- Are all user-facing error messages friendly (no stack traces shown to user)?

## Output Format

After scanning, print a report:
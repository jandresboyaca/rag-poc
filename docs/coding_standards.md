# Internal Python Coding Standards

These standards apply to all Python services owned by the engineering team.
They are enforced through code review and CI lint checks.

## 1. Naming Conventions

- Functions and variables use **snake_case** (`fetch_user_profile`, `request_id`).
- Classes use **PascalCase** (`OrderRepository`, `PaymentService`).
- Constants use **UPPER_SNAKE_CASE** (`DEFAULT_TIMEOUT_SECONDS`, `MAX_RETRIES`).
- Module-private names are prefixed with a single underscore (`_internal_helper`).
  Never use the double-underscore prefix unless name mangling is actually needed.
- Avoid abbreviations. The only accepted abbreviations are `url`, `id`, `db`, `ip`, `os`.
- Boolean variables and functions read as questions: `is_active`, `has_access`, `should_retry`.

## 2. Function Design

- A function does **one thing**. If you cannot name it without using the word "and",
  split it.
- Functions are at most **30 lines** of code excluding docstring and blank lines.
- All public functions require **type hints** on every argument and on the return type.
  Internal helpers are strongly encouraged to follow the same rule.
- A function takes at most **3 positional arguments**. Beyond that, mark the rest as
  keyword-only by placing a `*` in the signature: `def f(a, b, c, *, flag, retries)`.
- Mutable defaults are forbidden: use `None` and create the container inside the function.

## 3. Docstrings

- Every public function, class, and module has a docstring.
- Use the **Google style**. Include `Args`, `Returns`, and `Raises` sections with types.
- The first line is an imperative one-line summary. Empty line, then the detailed body.
- Document side effects explicitly (network calls, file writes, database writes).

## 4. Error Handling

- **Never** use a bare `except:` clause. Catch specific exception types.
- When re-raising, preserve the cause chain: `raise ServiceError("...") from exc`.
- Log every caught exception with full context: `user_id`, `request_id`, and the
  operation that was attempted.
- Do not catch `Exception` at the boundary of a public API unless you immediately
  re-raise after logging. Swallowing exceptions silently is a CI-blocking offense.

## 5. Imports

- Three groups, separated by a single blank line: standard library, third-party,
  then internal modules.
- Use **absolute imports** only. Relative imports (`from .x import y`) are not allowed.
- Wildcard imports (`from x import *`) are forbidden.
- Imports go at the top of the file. Lazy imports are allowed only to break circular
  dependencies and must include a comment explaining why.

## 6. Testing

- Minimum **80% line coverage** measured by `pytest --cov`.
- Test files mirror the source structure: `src/foo/bar.py` is tested by `tests/foo/test_bar.py`.
- Use **pytest fixtures** for shared setup. Avoid global state across tests.
- **Do not mock the database** for integration tests. Use a real test database
  (Postgres in Docker). Mocked DB tests have caused undetected migration bugs in
  production three times in the last year.
- Test names describe behavior, not implementation: `test_login_rejects_expired_token`,
  not `test_login_calls_validate_token`.

## 7. Code Review

- Pull request maximum size is **400 lines of diff** (excluding lockfiles and
  generated code). Larger changes must be split.
- The PR description explains **why** the change is being made, not just what.
  Link to the ticket.
- **Two approvals** are required before merge. The author cannot self-approve.
- The reviewer must run non-trivial changes locally and confirm the behavior.
- All review comments must be resolved before merge. CI must be green.

## 8. Logging

- Logs are **structured JSON**. One event per log line.
- **Never log secrets**: passwords, tokens, API keys, full credit card numbers,
  or other PII. Mask these fields at the logger level if they may appear.
- Use the right level: `INFO` for business events (`order_placed`, `user_signed_up`),
  `DEBUG` for development details, `WARNING` for recoverable anomalies,
  `ERROR` for failures that interrupt a request, `CRITICAL` for service-down events.
- Include a stack trace for every `ERROR` or `CRITICAL` log: `logger.exception(...)`.
- Every log line includes `request_id` so traces can be reconstructed across services.

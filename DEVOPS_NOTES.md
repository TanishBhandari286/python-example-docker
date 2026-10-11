# DEVOPS_NOTES — Taskboard service handover

> **From:** Taskboard backend team
> **To:** DevOps / Platform team
> **Re:** Please containerize Taskboard for staging and production
>
> Everything you need to run this service should be on this page. If something is missing, that's a bug in this doc. Open an issue and we'll fix it.

---

## 1. What this service is

A small JSON API for creating and completing tasks. Python 3.12, Flask, served by **gunicorn** in production. It stores its data in a single **SQLite** file.

```
 client ──HTTP──▶ gunicorn (port 8000) ──▶ Flask app (taskboard/) ──▶ SQLite file ($DATABASE_PATH)
```

## 2. Runtime requirements

| Item | Value | Notes |
|---|---|---|
| Python | **3.12.x** | We test on 3.12. 3.13 is untested; please don't upgrade without telling us. |
| OS packages | **none** | Pure-Python dependencies only. No compiler, no `libpq`, no `curl` needed. |
| Python deps | `requirements.txt` | Pinned. **Do not** install `requirements-dev.txt` in prod (it pulls in pytest). |
| Entry point | `gunicorn wsgi:app` | Run from the repo root. gunicorn automatically loads `./gunicorn.conf.py` from the working directory. |
| Dev server | `flask run` / `python -m flask` | **Local dev only. Never in prod.** |
| Listens on | `0.0.0.0:$PORT`, default **8000** | Must bind `0.0.0.0` (not `127.0.0.1`) or nothing outside the container can reach it. Already handled in `gunicorn.conf.py`. |
| Runs as root? | **No need.** | The app needs no privileges. Please run it as an unprivileged user. |

## 3. Files that need to be in the image

| Path | Needed in prod? |
|---|---|
| `taskboard/` | ✅ application package |
| `wsgi.py` | ✅ gunicorn entry point |
| `gunicorn.conf.py` | ✅ server config |
| `requirements.txt` | ✅ at build time (to install deps) |
| `tests/`, `requirements-dev.txt` | ❌ CI only |
| `.env`, `.env.example` | ❌ **never**. Secrets come from the environment at runtime |
| `.git/`, `.venv/`, `__pycache__/`, `data/`, `*.db` | ❌ local junk |
| `*.md` | ❌ docs |

## 4. Environment variables

The source of truth is `taskboard/config.py` and `gunicorn.conf.py`.

| Variable | Required | Default | Prod value / notes |
|---|---|---|---|
| `APP_ENV` | no | `development` | Set to **`production`** in staging/prod. When it's `production`, the app **refuses to start** without `SECRET_KEY` (intentional fail-fast). |
| `SECRET_KEY` | **yes in prod** | dev placeholder | 🔐 **SECRET.** Inject at runtime (orchestrator secret / `--env-file`). Must not appear in the image, the Dockerfile, `docker history`, or git. |
| `DATABASE_PATH` | no | `./data/taskboard.db` | In containers use **`/data/taskboard.db`** and mount a volume at `/data`. See §5. |
| `PORT` | no | `8000` | Port gunicorn binds to. |
| `LOG_LEVEL` | no | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR`. |
| `WEB_CONCURRENCY` | no | `2` | gunicorn worker processes. Rule of thumb: `2 × CPU cores + 1`, but start with 2. |
| `GUNICORN_THREADS` | no | `2` | Threads per worker. |
| `GUNICORN_TIMEOUT` | no | `30` | Seconds before a stuck worker is killed and restarted. |
| `GUNICORN_GRACEFUL_TIMEOUT` | no | `8` | Seconds to finish in-flight requests after SIGTERM. Keep it **below** the runtime's stop timeout (`docker stop` waits 10s by default). |
| `APP_VERSION` | no | `dev` | Shown on `/version`. We'd like it set to the git SHA or tag **at build time**. |

Python-in-container settings we'd like you to set (standard practice, not app-specific):

- `PYTHONUNBUFFERED=1`: our logs go to stdout; without this, Python buffers them and they show up late or get lost on a crash.
- `PYTHONDONTWRITEBYTECODE=1`: no `.pyc` files written at runtime.

## 5. Persistent data ⚠️

- The app **writes** to the SQLite file at `$DATABASE_PATH`. On startup it creates the parent directory (if it can) and the table.
- **The container's filesystem is disposable.** If `/data` is not a volume, every task is lost when the container is replaced (every deploy!).
- The directory must be **writable by the user the app runs as**. If you run as non-root (please do), make sure `/data` is owned by that user in the image. Named Docker volumes copy the ownership of the image's directory when they're first created; bind mounts do **not**.
- SQLite means **one replica only**. Do not scale this service horizontally; two containers writing the same file over a network volume will corrupt it. (Moving to Postgres is on our roadmap.)
- Backups: copying `taskboard.db` while the app is idle is enough for now.

## 6. Health checks

| Endpoint | Meaning | Use it for |
|---|---|---|
| `GET /healthz` | Process is up. Doesn't touch the DB. Always `200 {"status":"ok"}` | liveness / Docker `HEALTHCHECK` |
| `GET /readyz` | DB is reachable. `200` when ready, `503` when not | readiness / load balancer |
| `GET /version` | `{"version": ..., "env": ...}` | checking which build is deployed |

The image has **no `curl`/`wget`** (and we'd rather not add them just for this). Python is in the image, so a health check can use it:

```bash
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"
# exit code 0 = healthy, non-zero (exception) = unhealthy
```

Startup takes about 1-2 seconds. Allow a short start period before failures count.

## 7. Logging

- **JSON lines on stdout** (app logs) plus gunicorn access/error logs on stdout/stderr.
- We **never** write log files. `docker logs` / your log shipper is the only place logs exist.

## 8. Shutdown behaviour

- gunicorn handles **SIGTERM** gracefully: it stops accepting connections, finishes in-flight requests (up to `GUNICORN_GRACEFUL_TIMEOUT`), then exits 0.
- For this to work, **gunicorn must be PID 1** in the container (i.e. not wrapped in `sh -c`), or SIGTERM never reaches it and the runtime SIGKILLs it after the timeout.

## 9. How we run it locally (without Docker), for reference

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q                                   # 3 tests should pass
flask --app wsgi run --debug                # dev server on :5000
# or the prod way:
gunicorn wsgi:app                           # on :8000
curl localhost:8000/healthz
```

## 10. Smoke test after deploy

```bash
curl -s localhost:8000/healthz                                       # {"status":"ok"}
curl -s localhost:8000/readyz                                        # {"status":"ready"}
curl -s -XPOST localhost:8000/api/tasks -H 'content-type: application/json' -d '{"title":"hello"}'
curl -s localhost:8000/api/tasks                                     # [{"id":1,"title":"hello",...}]
# restart / replace the container, then:
curl -s localhost:8000/api/tasks                                     # the task must still be there
```

Thanks! 🙏 — backend team

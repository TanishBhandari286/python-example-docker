# Taskboard (python-example-docker)

A small, production-shaped Flask API for practising **containerizing a real Python service**.

```
taskboard/            the application package (Flask, app factory)
  config.py           every env var the app reads
  db.py               SQLite storage (writes to $DATABASE_PATH)
  routes.py           /healthz, /readyz, /version, /api/tasks
  logging_setup.py    JSON logs to stdout
wsgi.py               production entry point → `gunicorn wsgi:app`
gunicorn.conf.py      gunicorn settings (bind, workers, graceful shutdown)
requirements.txt      runtime deps (pinned)
requirements-dev.txt  + test deps (NOT for the image)
tests/                pytest suite
.env.example          sample env vars (the real .env is never committed)
DEVOPS_NOTES.md       ⭐ the backend team's handover notes: READ THIS FIRST
CONTAINERIZE.md       ⭐ the step-by-step exercise: write the Dockerfile yourself
```

## For the student

1. Read **[DEVOPS_NOTES.md](DEVOPS_NOTES.md)**. This is how real teams hand a service to DevOps. Every decision in your Dockerfile should trace back to a line in that file.
2. Work through **[CONTAINERIZE.md](CONTAINERIZE.md)**. Write the `Dockerfile` and `.dockerignore` yourself.
3. Only after you're done, compare with the reference answer:
   ```bash
   git fetch origin
   git diff main origin/solution     # see exactly what the solution adds
   git switch solution               # or check it out
   ```

## API

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/healthz` | – | `{"status":"ok"}` |
| GET | `/readyz` | – | `{"status":"ready"}` or 503 |
| GET | `/version` | – | `{"version":"...","env":"..."}` |
| GET | `/api/tasks` | – | list of tasks |
| POST | `/api/tasks` | `{"title":"..."}` | created task, 201 |
| PATCH | `/api/tasks/<id>` | `{"done":true}` | updated task |
| DELETE | `/api/tasks/<id>` | – | 204 |

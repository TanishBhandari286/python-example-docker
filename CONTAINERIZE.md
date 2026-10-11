# CONTAINERIZE.md — Write the Dockerfile for Taskboard

> **Goal:** produce a production-ready, **single-stage** `Dockerfile` and `.dockerignore` for this service, using only what the backend team wrote in **[DEVOPS_NOTES.md](DEVOPS_NOTES.md)**.
>
> **Run on:** docker-lab (`ssh docker-lab`), after `git clone`-ing this repo there.
> **Prerequisite:** `docker-teach` → `01-theory` and `02-layer-examples`.
> **Reference answer:** the `solution` branch. Don't look until Part E.

Rule for every line you write: **you must be able to point to the line in DEVOPS_NOTES.md that justified it.** Put the § number in a comment.

---

## Part A: Read the handover and extract the requirements (no Docker yet)

**Goal:** turn prose into a checklist. This is what DevOps engineers actually do first.

**Steps**
1. Read `DEVOPS_NOTES.md` start to finish.
2. Copy this table into your notes and fill in every cell from the doc:

| Question | Your answer | DEVOPS_NOTES § |
|---|---|---|
| Which Python version? Which base image tag will you use, and why `-slim`? | | |
| Any OS (`apt`) packages needed? | | |
| Which requirements file goes into the image? Which must NOT? | | |
| The exact command that starts the app in prod | | |
| Which port, and which address must it bind to? | | |
| Root or non-root? | | |
| Which directory does the app WRITE to? Who must own it? | | |
| Which env vars have safe defaults you can bake into the image? | | |
| Which env var is a SECRET, and where does it come from? | | |
| How can a health check be done without curl? | | |
| What must be PID 1, and why? | | |
| Which files must never enter the image? | | |

3. Answer in one sentence: what happens to the tasks in the database if the container is deleted and `/data` is **not** a volume?

---

## Part B: `.dockerignore` first

**Goal:** control exactly what gets sent to the builder *before* you write any `COPY`.

**Steps**
1. Create `.dockerignore` in the repo root.
2. It must exclude: git metadata, **every** `.env` file, your local virtualenv, Python bytecode caches, pytest's cache, local SQLite data, the tests, the dev requirements file, Markdown docs, and the Dockerfile/.dockerignore themselves.
3. Use comments (`#`) to group the lines by **reason** (secrets / cache-busting / not needed at runtime).

> 🔮 *Prediction:* If you forget `.git`, what will happen to the build cache every time you commit, even if no Python file changed? (Theory §5)

---

## Part C: Write the Dockerfile, one block at a time

Write the file **top to bottom in this order**. For each block you're told *what* it must do. The syntax is yours to write (look it up in theory §2 or the [Dockerfile reference](https://docs.docker.com/reference/dockerfile/)).

### C1. Parser directive + base image
- First line: the `# syntax=docker/dockerfile:1` directive.
- A pinned **slim** Python image matching §2. **Not** `latest`, and not a tag without the minor version.

### C2. Python container settings
- **One** `ENV` instruction that sets: unbuffered output, no `.pyc` files, no pip download cache, no pip version check. (Use `\` to continue lines.)

### C3. Non-root user and data directory
- **One** `RUN` that:
  - creates a system **group** `app` with GID `10001`
  - creates a system **user** `app` with UID `10001`, in that group, with no home directory and the shell `/usr/sbin/nologin`
  - creates `/data` and makes `app:app` its owner
- Then set `WORKDIR` to `/app`.

> ❓ Why does this block go **here** (near the top) and not at the end, next to `USER`? Think about how often it changes. (Theory §4)

### C4. Dependencies
- Copy **only** the runtime requirements file.
- Install it with pip.

> ❓ Why not `COPY . .` here? What would happen to the build time when someone fixes a typo in `routes.py`?

### C5. Application code
- Copy **only** the three things the app needs at runtime (§3): the package directory and the two top-level `.py` files. **Do not** use `--chown`. Leave them root-owned.

> ❓ The app runs as `app`, but these files are owned by `root` with mode `644`. Can the app still read them? Can it modify them? Why is that a *good* thing?

### C6. Runtime configuration
- **One** `ENV` with the **non-secret** prod defaults from §4/§5: environment = production, database path inside `/data`, port.
- An `ARG APP_VERSION` with default `dev`, then an `ENV APP_VERSION` that takes its value from the ARG.

> ❓ Why must `SECRET_KEY` **not** appear anywhere in this file? Where would someone be able to read it if it did? (Theory §6)
> ❓ Why does the `ARG` go this low in the file and not at the top?

### C7. Drop privileges, document, health check, start
- Switch to the `app` user.
- Document port 8000.
- `HEALTHCHECK` in **exec form**: interval 30s, timeout 3s, start period 10s, retries 3. The command uses `python -c` to request `http://127.0.0.1:<PORT>/healthz` with a 2-second timeout (§6 gives you the one-liner; make it read `PORT` from the environment).
- `CMD` in **exec form** that starts gunicorn with the entry point from §2. (You don't need `--bind`, because `gunicorn.conf.py` handles it. Why does that file get picked up automatically?)

---

## Part D: Build, run, and prove it meets the handover

Do each step in order. For each one, write your 🔮 prediction **before** you run it.

### D1. Build
```bash
docker build -t taskboard:1.0 --build-arg APP_VERSION=$(git rev-parse --short HEAD) .
docker image ls taskboard
docker history taskboard:1.0
```
> 🔮 Which `docker history` rows have a real size, and which show `0B`?

### D2. Check what's in the image
```bash
docker run --rm taskboard:1.0 ls -la /app /data
```
- Is `tests/` in `/app`? `.env`? `README.md`? (If yes, fix your `.dockerignore`.)
- Who owns `/app/*`? Who owns `/data`?

### D3. Fail-fast without the secret
```bash
docker run --rm taskboard:1.0
```
> 🔮 What will happen, and why is that the **desired** behaviour? (§4, `APP_ENV`)

### D4. Run it properly
```bash
docker run -d --name taskboard -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -v taskboard-data:/data \
  taskboard:1.0
```
Then run the **smoke test from DEVOPS_NOTES §10** (all the `curl` lines except the restart).

### D5. Health check
```bash
docker ps                      # look at the STATUS column
# wait ~30s, then:
docker inspect taskboard --format '{{.State.Health.Status}}'
```
> 🔮 What does `STATUS` show in the first few seconds, and what does it show after the first check passes?

### D6. Who am I, and who is PID 1?
```bash
docker exec taskboard whoami
docker exec taskboard cat /proc/1/cmdline | tr '\0' ' '; echo
```
Both answers must match DEVOPS_NOTES §2 and §8.

### D7. Graceful shutdown
```bash
time docker stop taskboard
docker inspect taskboard --format '{{.State.ExitCode}}'
docker logs taskboard | tail -5
```
> 🔮 Close to 0s or close to 10s? Exit code 0 or 137? Look for `Handling signal: term` in the logs.

### D8. Data survives the container being replaced
```bash
docker rm taskboard
docker run -d --name taskboard -p 8000:8000 -e SECRET_KEY=whatever -v taskboard-data:/data taskboard:1.0
curl -s localhost:8000/api/tasks
```
> 🔮 Will your task from D4 still be there? What if you had **not** passed `-v`?

### D9. No secrets in the image
```bash
docker history --no-trunc taskboard:1.0 | grep -i secret
docker image inspect taskboard:1.0 --format '{{json .Config.Env}}'
```
Neither should contain `SECRET_KEY`.

### D10. The cache test (the whole point of 02-layer-examples)
1. Change the message in `/healthz` (in `taskboard/routes.py`) from `"ok"` to `"ok!"`.
2. Rebuild with `--progress=plain` and `time`.

> 🔮 Which steps will say `CACHED`? Which is the first step to re-run?

### D11. Clean up
```bash
docker rm -f taskboard
docker volume rm taskboard-data
git checkout -- taskboard/
```

---

## Part E: Compare with the reference

```bash
git fetch origin
git diff main origin/solution -- Dockerfile .dockerignore
```

**Answer:** for every difference between your file and the solution, write one line: *is mine wrong, or just different?* Both can be valid. For example, `useradd` flags vary; the ordering principle does not.

---

## Bonus challenges

1. **Bind mount instead of a named volume:** run with `-v $PWD/data:/data`. What error appears, and why? (Hint: DEVOPS_NOTES §5, "bind mounts do not". Who owns `./data` on the host, and what is the app's UID?) How would you fix it **without** running as root?
2. **Change the port:** run with `-e PORT=9000 -p 9000:9000`. Does the health check still pass? Why? (Look at how your `HEALTHCHECK` builds the URL.)
3. **Break it on purpose:** change `CMD` to shell form, rebuild, and redo D6 and D7. Write down what changed.
4. **Size hunt:** build the same Dockerfile with `FROM python:3.12` (non-slim). Compare `docker image ls`. What's in the extra size?

---

## Sources (checked 2026-10-11)

- Dockerfile reference (`HEALTHCHECK` options/defaults, `USER`, `ARG` vs `ENV`, `EXPOSE`, exec form) — https://docs.docker.com/reference/dockerfile/
- Build context & `.dockerignore` — https://docs.docker.com/build/concepts/context/
- Best practices — https://docs.docker.com/build/building/best-practices/
- Build variables (don't use for secrets) — https://docs.docker.com/build/building/variables/
- Volumes — https://docs.docker.com/engine/storage/volumes/
- gunicorn config file lookup (`./gunicorn.conf.py`) — https://docs.gunicorn.org/en/stable/settings.html#config-file

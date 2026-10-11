import logging

from flask import Blueprint, current_app, jsonify, request

from .db import get_db

bp = Blueprint("taskboard", __name__)
log = logging.getLogger(__name__)


# ── Health endpoints ─────────────────────────────────────────────────────
# DEVOPS: /healthz = "process is alive" (liveness, no dependencies checked)
#         /readyz  = "can serve traffic" (checks the database is reachable)


@bp.get("/healthz")
def healthz():
    return jsonify(status="ok")


@bp.get("/readyz")
def readyz():
    try:
        get_db().execute("SELECT 1").fetchone()
    except Exception:
        log.exception("readiness check failed")
        return jsonify(status="unavailable"), 503
    return jsonify(status="ready")


@bp.get("/version")
def version():
    return jsonify(version=current_app.config["APP_VERSION"], env=current_app.config["APP_ENV"])


# ── Tasks API ────────────────────────────────────────────────────────────


def _row(r):
    return {"id": r["id"], "title": r["title"], "done": bool(r["done"]), "created_at": r["created_at"]}


@bp.get("/api/tasks")
def list_tasks():
    rows = get_db().execute("SELECT * FROM tasks ORDER BY id").fetchall()
    return jsonify([_row(r) for r in rows])


@bp.post("/api/tasks")
def create_task():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify(error="title is required"), 400
    db = get_db()
    cur = db.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    log.info("task created", extra={"task_id": row["id"]})
    return jsonify(_row(row)), 201


@bp.patch("/api/tasks/<int:task_id>")
def update_task(task_id: int):
    data = request.get_json(silent=True) or {}
    if "done" not in data:
        return jsonify(error="done is required"), 400
    db = get_db()
    cur = db.execute("UPDATE tasks SET done = ? WHERE id = ?", (int(bool(data["done"])), task_id))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="not found"), 404
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return jsonify(_row(row))


@bp.delete("/api/tasks/<int:task_id>")
def delete_task(task_id: int):
    db = get_db()
    cur = db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="not found"), 404
    return "", 204

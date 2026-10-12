import csv
import io
import json
import math
import os
import random
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DB_PATH = BASE_DIR / "product_analytics.db"
PORT = int(os.environ.get("PORT", "8000"))
DB_LOCK = threading.Lock()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def days_ago(days, hour=12):
    return (datetime.now(timezone.utc) - timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()


def db_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql, params=(), many=False):
    with DB_LOCK:
        conn = db_conn()
        try:
            cur = conn.executemany(sql, params) if many else conn.execute(sql, params)
            rows = cur.fetchall() if cur.description else []
            conn.commit()
            return [dict(row) for row in rows]
        finally:
            conn.close()


def scalar(sql, params=()):
    rows = query(sql, params)
    return list(rows[0].values())[0] if rows else 0


def init_db():
    schema = (BASE_DIR / "schema.sql").read_text(encoding="utf-8")
    with DB_LOCK:
        conn = db_conn()
        conn.executescript(schema)
        conn.commit()
        conn.close()


def event(user_id, name, props=None, occurred_at=None):
    props = props or {}
    query(
        "INSERT INTO events(id,user_id,event_name,occurred_at,properties_json) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), user_id, name, occurred_at or now_iso(), json.dumps(props, ensure_ascii=False)),
    )


def json_body(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def ok(handler, payload, status=200):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def csv_response(handler, rows, filename="events.csv"):
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    body = output.getvalue().encode("utf-8-sig")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/csv; charset=utf-8")
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def deterministic_variant(user_id):
    return "B" if sum(ord(c) for c in user_id) % 2 else "A"


def bootstrap_user():
    user = query("SELECT * FROM users ORDER BY created_at DESC LIMIT 1")
    return user[0] if user else None


def seed_demo():
    existing = scalar("SELECT COUNT(*) FROM users")
    if existing >= 12:
        return {"created": 0, "message": "Демо-данные уже загружены"}
    random.seed(42)
    goals = ["Подготовка к интервью", "Разговорный английский", "Переезд и работа", "Письменная речь"]
    levels = ["A2", "B1", "B2", "C1"]
    names = ["Анна", "Михаил", "Sofia", "Nikita", "Elena", "Max", "Daria", "Ilya", "Maria", "Artem", "Olga", "Alex"]
    created = 0
    for i in range(18):
        uid = str(uuid.uuid4())
        created_days = random.randint(0, 38)
        created_at = days_ago(created_days, 9 + (i % 8))
        variant = "A" if i % 2 == 0 else "B"
        goal = goals[i % len(goals)]
        level = levels[i % len(levels)]
        email = f"demo{i+1}@lingua-lab.local"
        query("INSERT INTO users(id,name,email,level,variant,created_at) VALUES(?,?,?,?,?,?)", (uid, names[i], email, level, variant, created_at))
        event(uid, "user_signed_up", {"source": "demo", "variant": variant}, created_at)
        if i != 4:
            query("INSERT INTO onboarding(user_id,goal,level,completed_at) VALUES(?,?,?,?)", (uid, goal, level, created_at))
            event(uid, "onboarding_completed", {"goal": goal, "level": level, "variant": variant}, created_at)
            event(uid, "goal_selected", {"goal": goal}, created_at)
        if i not in (4, 11):
            session_id = str(uuid.uuid4())
            started = days_ago(max(created_days - 1, 0), 11)
            query("INSERT INTO sessions(id,user_id,started_at,completed_at) VALUES(?,?,?,?)", (session_id, uid, started, started if i % 3 else None))
            event(uid, "chat_started", {"session_id": session_id}, started)
            turns = 1 + (i % 4)
            for t in range(turns):
                sent = days_ago(max(created_days - 1, 0), 11 + t)
                mid = str(uuid.uuid4())
                latency = 680 + (i * 71 + t * 100) % 900
                cost = round(0.003 + (i % 5) * 0.001 + t * 0.0005, 4)
                query("INSERT INTO messages(id,session_id,user_id,role,content,model_name,response_latency_ms,token_cost,task_success,retry_count,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (mid, session_id, uid, "user", "Practice interview answer", "", 0, 0, 1, 0, sent))
                query("INSERT INTO messages(id,session_id,user_id,role,content,model_name,response_latency_ms,token_cost,task_success,retry_count,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), session_id, uid, "assistant", "Useful feedback on your answer", "gpt-4o-mini", latency, cost, 1 if t % 4 else 0, t % 2, sent))
                event(uid, "message_sent", {"session_id": session_id}, sent)
                event(uid, "ai_response_received", {"session_id": session_id, "model_name": "gpt-4o-mini", "response_latency_ms": latency, "token_cost": cost, "task_success": t % 4 != 0, "retry_count": t % 2}, sent)
            if i % 4 != 0:
                task_id = str(uuid.uuid4())
                query("INSERT INTO exercises(id,user_id,session_id,title,status,started_at,completed_at) VALUES(?,?,?,?,?,?,?)", (task_id, uid, session_id, "Tell me about a project you are proud of", "completed", started, started))
                event(uid, "exercise_started", {"exercise_id": task_id}, started)
                event(uid, "exercise_completed", {"exercise_id": task_id, "score": 72 + i}, started)
            if i % 3 != 1:
                rating = 1 if i % 4 else 0
                query("INSERT INTO ratings(id,user_id,session_id,rating,feedback,created_at) VALUES(?,?,?,?,?,?)", (str(uuid.uuid4()), uid, session_id, rating, "Helpful" if rating else "Needs more context", started))
                event(uid, "answer_rated", {"rating": rating}, started)
        if i % 5 == 0:
            sub_at = days_ago(max(created_days - 3, 0), 14)
            query("INSERT INTO subscriptions(id,user_id,plan,status,started_at) VALUES(?,?,?,?,?)", (str(uuid.uuid4()), uid, "Pro", "active", sub_at))
            event(uid, "subscription_started", {"plan": "Pro"}, sub_at)
        elif i % 7 == 0:
            sub_at = days_ago(max(created_days - 2, 0), 14)
            query("INSERT INTO subscriptions(id,user_id,plan,status,started_at,cancelled_at) VALUES(?,?,?,?,?,?)", (str(uuid.uuid4()), uid, "Pro", "cancelled", sub_at, now_iso()))
            event(uid, "subscription_cancelled", {"plan": "Pro"}, now_iso())
        created += 1
    return {"created": created, "message": "Демо-данные загружены"}


def user_summary(user_id):
    users = query("SELECT * FROM users WHERE id=?", (user_id,))
    if not users:
        return None
    u = users[0]
    onboarding = query("SELECT * FROM onboarding WHERE user_id=? ORDER BY completed_at DESC LIMIT 1", (user_id,))
    sub = query("SELECT * FROM subscriptions WHERE user_id=? ORDER BY started_at DESC LIMIT 1", (user_id,))
    return {"user": u, "onboarding": onboarding[0] if onboarding else None, "subscription": sub[0] if sub else None}


def ai_reply(text, goal="Подготовка к интервью"):
    lowered = text.lower()
    if any(word in lowered for word in ["hi", "hello", "привет"]):
        return "Привет! Я Линга — помогу тренировать английский через короткие практические сессии. С чего начнём?"
    if "interview" in lowered or "интервью" in lowered or "job" in lowered:
        return "Попробуй ответить по структуре STAR: Situation → Task → Action → Result. Расскажи о проекте, где твой вклад можно измерить цифрами."
    if "grammar" in lowered or "граммат" in lowered:
        return "Хорошая тема для практики. Напиши 3 предложения о своём рабочем дне, а я отмечу ошибки и предложу естественные варианты."
    if "vocab" in lowered or "словар" in lowered:
        return "Давай закрепим 5 слов по теме «карьера»: ownership, impact, trade-off, stakeholder, outcome. Составь по одному предложению с каждым."
    if len(text.strip()) < 12:
        return "Раскрой мысль чуть подробнее — так я смогу дать полезную обратную связь и подобрать следующее задание."
    return f"Сильная заготовка для цели «{goal}». Сделай ответ конкретнее: добавь контекст, одно действие и измеримый результат. Хочешь, я перепишу его в более естественном английском?"


def dashboard():
    users = scalar("SELECT COUNT(*) FROM users")
    activated = scalar("SELECT COUNT(DISTINCT user_id) FROM events WHERE event_name='exercise_completed'")
    sessions = scalar("SELECT COUNT(*) FROM sessions")
    completed = scalar("SELECT COUNT(*) FROM sessions WHERE completed_at IS NOT NULL")
    paid = scalar("SELECT COUNT(DISTINCT user_id) FROM subscriptions WHERE status='active'")
    messages = scalar("SELECT COUNT(*) FROM messages WHERE role='assistant'")
    avg_latency = scalar("SELECT COALESCE(ROUND(AVG(response_latency_ms)),0) FROM messages WHERE role='assistant'")
    total_cost = scalar("SELECT COALESCE(SUM(token_cost),0) FROM messages WHERE role='assistant'")
    rating_count = scalar("SELECT COUNT(*) FROM ratings")
    positive = scalar("SELECT COALESCE(SUM(rating),0) FROM ratings")
    funnel = [
        {"stage": "Регистрация", "value": users, "rate": 1.0},
        {"stage": "Онбординг", "value": scalar("SELECT COUNT(*) FROM onboarding"), "rate": round(scalar("SELECT COUNT(*) FROM onboarding") / users, 3) if users else 0},
        {"stage": "Первое сообщение", "value": scalar("SELECT COUNT(DISTINCT user_id) FROM events WHERE event_name='message_sent'"), "rate": round(scalar("SELECT COUNT(DISTINCT user_id) FROM events WHERE event_name='message_sent'") / users, 3) if users else 0},
        {"stage": "Завершили задание", "value": activated, "rate": round(activated / users, 3) if users else 0},
        {"stage": "Оплата", "value": paid, "rate": round(paid / users, 3) if users else 0},
    ]
    goals = query("SELECT COALESCE(o.goal,'Не выбрана') goal, COUNT(*) users FROM users u LEFT JOIN onboarding o ON o.user_id=u.id GROUP BY COALESCE(o.goal,'Не выбрана') ORDER BY users DESC")
    quality = query("SELECT model_name model, COUNT(*) responses, ROUND(AVG(response_latency_ms)) latency_ms, ROUND(AVG(token_cost),4) cost_per_response, ROUND(AVG(task_success)*100) success_rate FROM messages WHERE role='assistant' GROUP BY model_name")
    if not quality:
        quality = [{"model": "gpt-4o-mini", "responses": 0, "latency_ms": 0, "cost_per_response": 0, "success_rate": 0}]
    daily = []
    for days in range(6, -1, -1):
        date_key = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
        count = scalar("SELECT COUNT(DISTINCT user_id) FROM events WHERE event_name='message_sent' AND date(occurred_at)=date(?)", (date_key,))
        daily.append({"date": date_key[5:], "value": count})
    variants = []
    for variant in ["A", "B"]:
        row = query("SELECT COUNT(*) users, SUM(CASE WHEN EXISTS (SELECT 1 FROM events e WHERE e.user_id=users.id AND e.event_name='exercise_completed') THEN 1 ELSE 0 END) activated, SUM(CASE WHEN EXISTS (SELECT 1 FROM subscriptions s WHERE s.user_id=users.id AND s.status='active') THEN 1 ELSE 0 END) paid FROM users WHERE variant=?", (variant,))[0]
        variants.append({"variant": variant, "users": row["users"] or 0, "activated": row["activated"] or 0, "activation_rate": round((row["activated"] or 0) / (row["users"] or 1) * 100, 1), "paid": row["paid"] or 0, "paid_rate": round((row["paid"] or 0) / (row["users"] or 1) * 100, 1)})
    a, b = variants
    p1 = a["activation_rate"] / 100
    p2 = b["activation_rate"] / 100
    pooled = ((a["activated"] + b["activated"]) / max(a["users"] + b["users"], 1))
    se = math.sqrt(max(pooled * (1 - pooled) * (1 / max(a["users"], 1) + 1 / max(b["users"], 1)), 1e-9))
    z = abs(p2 - p1) / se if se else 0
    p_value = math.erfc(z / math.sqrt(2))
    retention = []
    for cohort in ["D1", "D7", "D30"]:
        base = 100 if cohort == "D1" else 66 if cohort == "D7" else 38
        retention.append({"cohort": cohort, "value": base if users else 0})
    free_users = max(users - paid, 0)
    free_sessions = scalar("SELECT COUNT(*) FROM sessions WHERE user_id NOT IN (SELECT user_id FROM subscriptions WHERE status='active')")
    paid_sessions = scalar("SELECT COUNT(*) FROM sessions WHERE user_id IN (SELECT user_id FROM subscriptions WHERE status='active')")
    return {
        "kpis": {"users": users, "activated": activated, "activation_rate": round(activated / users * 100, 1) if users else 0, "weekly_sessions": completed, "paid": paid, "paid_rate": round(paid / users * 100, 1) if users else 0, "avg_latency": avg_latency, "total_cost": round(total_cost, 3), "cost_per_active": round(total_cost / max(activated, 1), 3), "quality_score": round(positive / max(rating_count, 1) * 100, 1), "assistant_messages": messages},
        "funnel": funnel, "goals": goals, "quality": quality, "daily": daily, "retention": retention,
        "plan_compare": [{"segment": "Free", "users": free_users, "sessions": free_sessions, "sessions_per_user": round(free_sessions / max(free_users, 1), 1)}, {"segment": "Pro", "users": paid, "sessions": paid_sessions, "sessions_per_user": round(paid_sessions / max(paid, 1), 1)}],
        "ab_test": {"variants": variants, "lift": round((p2 - p1) / p1 * 100, 1) if p1 else 0, "z_score": round(z, 2), "p_value": round(p_value, 3), "significant": p_value < 0.05},
        "insights": [
            "Пользователь активируется после первого завершённого задания, а не после первого сообщения.",
            "Ответы с низкой оценкой требуют больше повторных запросов — это сигнал к улучшению контекста и примеров.",
            "Вариант B сокращает путь до первой практики; при росте выборки его стоит раскатить на 100% аудитории.",
        ],
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/" or path == "/index.html":
            data = (STATIC_DIR / "index.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
        if path.startswith("/static/"):
            file_path = STATIC_DIR / path.replace("/static/", "", 1)
            if file_path.exists() and file_path.is_file():
                data = file_path.read_bytes(); ext = file_path.suffix
                ct = {".css": "text/css", ".js": "application/javascript", ".svg": "image/svg+xml"}.get(ext, "application/octet-stream")
                self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
        if path == "/api/health": return ok(self, {"ok": True, "db": str(DB_PATH), "time": now_iso()})
        if path == "/api/dashboard": return ok(self, dashboard())
        if path.startswith("/api/user/"):
            return ok(self, user_summary(path.split("/")[-1]) or {"error": "not_found"}, 200)
        if path == "/api/events.csv":
            return csv_response(self, query("SELECT event_name,user_id,occurred_at,properties_json FROM events ORDER BY occurred_at"))
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = json_body(self)
        try:
            if path == "/api/demo/seed":
                return ok(self, seed_demo())
            if path == "/api/auth/signup":
                uid = str(uuid.uuid4()); variant = body.get("variant") or deterministic_variant(uid); created = now_iso()
                query("INSERT INTO users(id,name,email,level,variant,created_at) VALUES(?,?,?,?,?,?)", (uid, body.get("name", "Новый пользователь"), body.get("email", f"{uid[:6]}@local"), body.get("level", "B1"), variant, created)); event(uid, "user_signed_up", {"variant": variant, "source": "local"}, created)
                return ok(self, user_summary(uid), 201)
            if path == "/api/onboarding":
                uid = body["user_id"]; completed = now_iso(); goal = body.get("goal", "Подготовка к интервью"); level = body.get("level", "B1")
                query("INSERT OR REPLACE INTO onboarding(user_id,goal,level,completed_at) VALUES(?,?,?,?)", (uid, goal, level, completed)); query("UPDATE users SET level=? WHERE id=?", (level, uid)); event(uid, "onboarding_completed", {"goal": goal, "level": level}, completed); event(uid, "goal_selected", {"goal": goal}, completed)
                return ok(self, user_summary(uid))
            if path == "/api/session/start":
                uid = body["user_id"]; sid = str(uuid.uuid4()); started = now_iso(); query("INSERT INTO sessions(id,user_id,started_at) VALUES(?,?,?)", (sid, uid, started)); event(uid, "chat_started", {"session_id": sid}, started); return ok(self, {"session_id": sid, "started_at": started})
            if path == "/api/chat":
                uid = body["user_id"]; sid = body.get("session_id") or str(uuid.uuid4()); text = body.get("message", ""); goal_rows = query("SELECT goal FROM onboarding WHERE user_id=?", (uid,)); goal = goal_rows[0]["goal"] if goal_rows else "Подготовка к интервью"; started = now_iso();
                if not query("SELECT id FROM sessions WHERE id=?", (sid,)): query("INSERT INTO sessions(id,user_id,started_at) VALUES(?,?,?)", (sid, uid, started))
                query("INSERT INTO messages(id,session_id,user_id,role,content,created_at) VALUES(?,?,?,?,?,?)", (str(uuid.uuid4()), sid, uid, "user", text, started)); event(uid, "message_sent", {"session_id": sid}, started)
                latency = 340 + (len(text) * 13) % 640; cost = round(0.0027 + len(text) / 180000, 4); reply = ai_reply(text, goal); assistant_id = str(uuid.uuid4())
                query("INSERT INTO messages(id,session_id,user_id,role,content,model_name,response_latency_ms,token_cost,task_success,retry_count,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (assistant_id, sid, uid, "assistant", reply, "local-demo-model", latency, cost, 1, 0, now_iso())); event(uid, "ai_response_received", {"session_id": sid, "model_name": "local-demo-model", "response_latency_ms": latency, "token_cost": cost, "task_success": True, "retry_count": 0}, now_iso())
                return ok(self, {"reply": reply, "message_id": assistant_id, "latency_ms": latency, "token_cost": cost, "model_name": "local-demo-model", "session_id": sid})
            if path == "/api/exercises":
                uid = body["user_id"]; sid = body.get("session_id"); eid = str(uuid.uuid4()); started = now_iso(); title = body.get("title", "Tell me about a project you are proud of"); query("INSERT INTO exercises(id,user_id,session_id,title,status,started_at) VALUES(?,?,?,?,?,?)", (eid, uid, sid, title, "started", started)); event(uid, "exercise_started", {"exercise_id": eid}, started); return ok(self, {"exercise_id": eid, "title": title, "status": "started"})
            if path == "/api/exercises/complete":
                uid = body["user_id"]; eid = body["exercise_id"]; completed = now_iso(); query("UPDATE exercises SET status='completed',completed_at=? WHERE id=?", (completed, eid)); event(uid, "exercise_completed", {"exercise_id": eid, "score": body.get("score", 84)}, completed); return ok(self, {"status": "completed", "score": body.get("score", 84)})
            if path == "/api/rate":
                uid = body["user_id"]; rating = 1 if body.get("rating") in [1, "1", True] else 0; created = now_iso(); query("INSERT INTO ratings(id,user_id,session_id,rating,feedback,created_at) VALUES(?,?,?,?,?,?)", (str(uuid.uuid4()), uid, body.get("session_id"), rating, body.get("feedback", ""), created)); event(uid, "answer_rated", {"rating": rating}, created); return ok(self, {"saved": True})
            if path == "/api/subscription":
                uid = body["user_id"]; started = now_iso(); query("INSERT INTO subscriptions(id,user_id,plan,status,started_at) VALUES(?,?,?,?,?)", (str(uuid.uuid4()), uid, body.get("plan", "Pro"), "active", started)); event(uid, "subscription_started", {"plan": body.get("plan", "Pro")}, started); return ok(self, {"status": "active", "plan": body.get("plan", "Pro")})
            if path == "/api/subscription/cancel":
                uid = body["user_id"]; cancelled = now_iso(); query("UPDATE subscriptions SET status='cancelled',cancelled_at=? WHERE user_id=? AND status='active'", (cancelled, uid)); event(uid, "subscription_cancelled", {"plan": body.get("plan", "Pro")}, cancelled); return ok(self, {"status": "cancelled"})
        except (KeyError, sqlite3.Error) as exc:
            return ok(self, {"error": str(exc)}, 400)
        self.send_error(404)


if __name__ == "__main__":
    init_db()
    print(f"Lingua Lab is running at http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()

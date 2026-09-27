import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import psycopg

DB_URI = "postgresql://events:ebadabada@db:5432/events"


def get_db_connection():
    return psycopg.connect(DB_URI, autocommit=True)


def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    note TEXT NOT NULL CHECK (note <> '' AND length(note) <= 200)
                );
                """
            )


class EventsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/events":
            self.send_error(404)
            return

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, note FROM events ORDER BY id")
                    rows = cur.fetchall()

            events = [{"id": row[0], "note": row[1]} for row in rows]

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(events).encode("utf-8"))
        except Exception:
            self.send_response(500)
            self.end_headers()

    def do_POST(self):
        if self.path != "/events":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except Exception:
            print("400: invalid JSON")
            self.send_response(400)
            self.end_headers()
            return

        if not isinstance(data, dict) or "note" not in data:
            print("400: missing note")
            self.send_response(400)
            self.end_headers()
            return

        note = data["note"]
        if not isinstance(note, str) or len(note) == 0 or len(note) > 200:
            print("400: invalid note")
            self.send_response(400)
            self.end_headers()
            return

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO events (note) VALUES (%s) RETURNING id",
                        (note,),
                    )
                    new_id = cur.fetchone()[0]

            self.send_response(201)
            print("201: event created")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response_data = {"id": new_id, "note": note}
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
        except Exception:
            self.send_response(400)
            self.end_headers()


if __name__ == "__main__":
    init_db()
    server = HTTPServer(("", 8080), EventsHandler)
    server.serve_forever()
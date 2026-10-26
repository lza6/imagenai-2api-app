# -*- coding: utf-8 -*-
"""
imagenai-2api 独立服务 — OpenAI 风格的视频生成 API
Endpoints:
  POST /v1/video/generations          提交图生视频任务
  GET  /v1/video/generations/{id}     查询任务状态 / 结果
  GET  /v1/models                     模型列表
  GET  /health                        上游健康
"""
import json, threading, time, base64, re, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from miricanvas_client import generate, status, health, new_device

MODEL = "miricanvas-image-to-video"
TASKS = {}
_lock = threading.Lock()

DATA_URL_RE = re.compile(r"^data:image/[a-zA-Z]+;base64,(.+)$")


def extract_b64(image_field: str) -> str:
    m = DATA_URL_RE.match(image_field or "")
    return m.group(1) if m else image_field


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/v1/models":
            self._send(200, {"object": "list", "data": [
                {"id": MODEL, "object": "model", "owned_by": "imagenai-2api"}]})
        elif self.path.startswith("/v1/video/generations/"):
            tid = self.path.rsplit("/", 1)[-1]
            with _lock:
                t = TASKS.get(tid)
            if not t:
                self._send(404, {"error": {"message": "task not found"}})
                return
            if t["status"] in ("queued", "processing"):
                s = status(tid)
                with _lock:
                    t["status"] = s.get("status", t["status"])
                    t["progress"] = s.get("progress", 0)
                    t["video_url"] = s.get("video_url")
                    t["error"] = s.get("error")
            self._send(200, {"id": tid, "model": MODEL, "status": t["status"],
                             "progress": t["progress"], "video_url": t["video_url"],
                             "error": t["error"]})
        elif self.path == "/health":
            self._send(200, health())
        else:
            self._send(404, {"error": {"message": "not found"}})

    def do_POST(self):
        if self.path != "/v1/video/generations":
            self._send(404, {"error": {"message": "not found"}})
            return
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except Exception:
            self._send(400, {"error": {"message": "invalid json"}})
            return
        prompt = req.get("prompt", "")
        image = req.get("image") or req.get("image_url") or ""
        if not image:
            self._send(400, {"error": {"message": "image (base64 or data-url) required"}})
            return
        b64 = extract_b64(image)
        r = generate(b64, prompt, device_id=new_device("api"))
        if not r.get("ok"):
            self._send(502, {"error": {"message": r.get("resp", "upstream error")}})
            return
        tid = r["request_id"]
        with _lock:
            TASKS[tid] = {"status": "queued", "progress": 0, "video_url": None, "error": None}
        self._send(200, {"id": tid, "model": MODEL, "status": "queued", "progress": 0})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8765))
    print(f"imagenai-2api listening on :{port}  model={MODEL}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()

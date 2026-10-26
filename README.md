# imagenai-2api-app

AI Video Generator (Miricanvas 图生视频) 逆向 2api 网关 — 供 new-api 渠道集成。

## 功能

- **图生视频**：`api.imagenai.online`（Miricanvas Video Generation API v3）
- **HMAC 请求签名**：算法逆向自 APK `libphotoflux_security.so`，密钥自持
- **自动设备轮换**：每设备日限 2 次 → 每请求自动生成全新设备指纹，无 IP 限流（同 IP 25 并发实测全通过）
- **代理支持**：每请求可指定 HTTP/SOCKS 代理，配合网关代理池轮换出口

## 快速开始

```bash
pip install -r requirements.txt  # 仅标准库，无需安装
python server.py                 # 独立 OpenAI 兼容服务, 端口 8765
```

### OpenAI 兼容调用

```bash
curl http://127.0.0.1:8765/v1/video/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "miricanvas-image-to-video",
    "prompt": "a cat walking on grass, cinematic",
    "image": "data:image/png;base64,....",
    "stream": false
  }'
```

响应（异步任务）：

```json
{
  "task_id": "0e9488a5-2e36-4141-9d60-4747cbab87f9",
  "status": "queued",
  "progress": 0
}
```

查询任务：`GET /v1/video/generations/{task_id}` → 完成后返回 `video_url`。

## 作为库使用

```python
from miricanvas_client import generate, status

r = generate(image_b64, "prompt here")   # 自动换设备
s = status(r["request_id"])              # {"status":"completed","video_url":"..."}
```

## 压测数据（2026-10-27 实测）

| 项目 | 结果 |
|---|---|
| 同 IP 25 设备并发 | 25/25 全部 202 通过（无 IP 限流） |
| 30 任务自动换设备 | 30/30 成功 |
| 单设备日限 | 2 次（429 → 自动换新设备） |
| 生成耗时 | 约 60–90 秒 / 条 |
| 服务端容量 | queue 200 · 24 workers |

## 在 new-api 中使用

type 65 渠道（imagenai-2api）已内置到我们的 new-api 分支：填密钥即用，
2api 面板可视化管理，模型广场展示 `miricanvas-image-to-video`。

## License

MIT

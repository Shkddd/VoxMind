# VoxMind API 文档

## Base URL

`http://localhost:8000/api/v1`

## 鉴权

录音笔通过 `X-Device-Key` Header 鉴权。
Web 用户通过 JWT Bearer Token 鉴权。

---

## 音频上传（录音笔→云端）

### `POST /audio/upload`

上传录音文件。

**Request:**
- `Content-Type: multipart/form-data`
- Header: `X-Device-Key: <device_key>`
- Body:
  - `file`: 音频文件 (WAV/MP3/M4A)
  - `title` (可选): 标题
  - `recorded_at` (可选): 录制时间 (ISO 8601)

**Response:**
```json
{
  "id": "rec_abc123",
  "status": "processing",
  "estimated_time_sec": 30
}
```

随后系统异步处理，可通过 WebSocket 获取进度。

---

### `GET /audio/{id}`

获取单条录音详情。

**Response:**
```json
{
  "id": "rec_abc123",
  "title": "周会-2026-05-27",
  "duration_sec": 1840,
  "recorded_at": "2026-05-27T10:00:00Z",
  "status": "completed",
  "transcript": "完整逐字稿...",
  "summary": {
    "topics": ["项目进度", "预算审批"],
    "key_points": ["前端开发已完成80%", "Q2预算需周五前提交"],
    "action_items": [
      {"owner": "张三", "task": "提交预算报告", "deadline": "2026-05-31"}
    ],
    "full_text": "完整摘要文本..."
  },
  "speakers": ["张三", "李四", "王五"],
  "segments": [
    {"start": 0, "end": 120, "speaker": "张三", "text": "..."},
    {"start": 120, "end": 300, "speaker": "李四", "text": "..."}
  ]
}
```

---

## 语义搜索

### `GET /audio/search`

**Query params:**
| 参数 | 类型 | 说明 |
|------|------|------|
| `q` | string | 搜索关键词或自然语言查询 |
| `limit` | int | 返回条数 (默认 10) |
| `date_from` | string | 起始日期 (YYYY-MM-DD) |
| `date_to` | string | 截止日期 |

**Response:**
```json
{
  "results": [
    {
      "id": "rec_abc123",
      "title": "周会-2026-05-27",
      "relevance_score": 0.92,
      "summary_snippet": "...讨论了Q2预算审批...",
      "recorded_at": "2026-05-27T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

## 对话式问答

### `POST /chat/question`

**Request:**
```json
{
  "question": "上回周会关于预算的结论是什么？",
  "session_id": "sess_xxx",
  "filters": {
    "date_from": "2026-01-01"
  }
}
```

**Response:**
```json
{
  "answer": "根据5月27日的周会记录，Q2预算需在本周五（5月31日）前由各部门提交汇总...",
  "sources": [
    {"id": "rec_abc123", "title": "周会-2026-05-27", "relevance": 0.95}
  ]
}
```

### `WS /chat/stream`

WebSocket 流式问答，逐 token 推送答案。

---

## 语音问答（录音笔端）

### `POST /ask/voice`

录音笔**语音提问**：发一段语音问历史会议内容。

**Request:**
- `Content-Type: multipart/form-data`
- Body:
  - `file`: 录音笔说的问题语音 (WAV/MP3/M4A)

**Response:**
```json
{
  "answer": "5月27日的周会讨论了Q2预算，需周五前提交...",
  "sources": [
    {"id": "rec_abc123", "title": "周会-2026-05-27", "relevance": 0.95}
  ]
}
```

**工作流：** 录音笔收音 → 发语音 → Whisper ASR 转文字 → 向量检索 → LLM 回答 → 返回文本（录音笔可用 TTS 朗读）

### `GET /ask/direct?q=...`

录音笔**文字提问**（适用于带简单文字输入能力的设备），直接传入文本查询，延迟更低。

---

## IM 自动推送

每段录音处理完成后，若配置了飞书 Webhook URL，系统自动推送结构化会议纪要：

| 配置项 | 说明 |
|--------|------|
| `FEISHU_WEBHOOK_URL` | 飞书机器人 Webhook 地址 |
| `AUTO_PUSH_MEETINGS` | 设为 `true` 启用自动推送 |

推送内容包含：议题列表、关键结论、待办事项（负责人+截止日期）、跳转链接。

---

## 录音笔硬件接口

详见 [hardware/hardware_protocol.md](../hardware/hardware_protocol.md)

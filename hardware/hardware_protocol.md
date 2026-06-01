# 录音笔 → 云端上传协议 v1.0

## 网络要求

- WiFi 802.11 b/g/n 或 4G 蜂窝网络
- 上传带宽 ≥ 1 Mbps（建议 ≥ 5 Mbps 以支持实时流式）
- 云端端点: `https://<host>/api/v1/audio/upload`

## 上传流程

```
录音笔                         云端
  │                             │
  │  1. 录音完成/实时分段        │
  │  2. POST /audio/upload      │
  │     (multipart/form-data)   │
  │     Header: X-Device-Key    │
  │────────────────────────────→│
  │                             │ 3. 返回 rec_id, status=queued
  │←────────────────────────────│
  │                             │ 4. 异步处理 (ASR + 摘要 + 向量化)
  │  5. 可选：GET /audio/{id}   │
  │     查询处理状态             │
  │────────────────────────────→│
  │     返回 status=completed   │
  │←────────────────────────────│
  │                             │
```

## 文件格式

| 项 | 规格 |
|---|------|
| 音频格式 | WAV (PCM 16bit 16kHz mono) / MP3 / M4A (AAC) |
| 最大单文件 | 500 MB（对应约 8 小时 WAV 或 48 小时 MP3） |
| 推荐分段 | 每段 30-60 分钟（更小的分段降低延迟） |
| 采样率 | 16kHz（Whisper 最优） |

## 请求头

```
POST /api/v1/audio/upload
Content-Type: multipart/form-data
X-Device-Key: <设备密钥>
```

## 设备注册

首次使用时，录音笔需先注册：

```
POST /api/v1/devices/register
Content-Type: application/json

{
  "device_id": "RECORDER-SN-001",
  "name": "会议室录音笔A"
}

Response:
{
  "device_key": "dk_xxxxxxxxxxxxxxxx",
  "api_endpoint": "https://<host>/api/v1"
}
```

`device_key` 需安全存储在录音笔本地，后续所有请求通过 `X-Device-Key` header 携带。

## 低带宽模式

当网络检测到上传带宽 < 1 Mbps 时，录音笔应：

1. 使用 Opus 编码压缩（8-16 kbps）
2. 分片上传（每片 30 秒）
3. 启用断点续传（`Content-Range` header）
4. 本地缓存待上传队列，网络恢复后续传

## 实时流式（可选）

对于需要实时转写的场景，可使用 WebSocket：

```
WS /api/v1/audio/stream
Header: X-Device-Key: <device_key>

录音笔 → 云端: 二进制音频帧（Opus 20ms 每帧）
云端 → 录音笔: {"type": "transcript", "text": "..."}
```

延迟目标：端到端 < 3 秒。

---

## 语音问答（录音笔主动查询）

录音笔可以随时通过语音向云端提问，查询历史会议内容。

### 流程

```
录音笔                            云端
  │                                │
  │  1. 按下问答键，说问题          │
  │  2. POST /ask/voice            │
  │     (multipart: audio file)    │
  │───────────────────────────────→│
  │                                │ 3. Whisper ASR → 文字
  │                                │ 4. 向量检索相关会议
  │                                │ 5. LLM 生成回答
  │←───────────────────────────────│
  │  6. {"answer": "...",           │
  │      "sources": [...]}         │
  │  7. TTS 朗读回答（可选）        │
  │                                │
```

### 端点

| 方式 | 端点 | 适用场景 |
|------|------|----------|
| 语音 | `POST /api/v1/ask/voice` | 录音笔直接语音提问 |
| 文字 | `GET /api/v1/ask/direct?q=...` | 带屏幕/键盘的设备 |

### 硬件实现建议

- 录音笔需保留一个 **问答按钮**，按下后开始录音，松手自动上传
- 上传后等待云端返回，可选通过 TTS 芯片朗读回答
- 示例请求周期（语音 5 秒 → 上传 1s → ASR 2s → 检索 1s → LLM 3s ≈ 12s 总延迟）
- 建议在录音笔上显示 LED 状态：录制中（蓝）→ 上传中（黄）→ 处理中（紫）→ 回答就绪（绿）

---

## 错误码

| 状态码 | 含义 | 处理 |
|--------|------|------|
| 200 | 成功 | — |
| 401 | 设备未授权 | 检查 device_key |
| 413 | 文件过大 | 分段后重试 |
| 429 | 频率限制 | 等待后重试 |
| 503 | 服务繁忙 | 指数退避重试 |

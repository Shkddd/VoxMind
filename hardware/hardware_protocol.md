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

## 错误码

| 状态码 | 含义 | 处理 |
|--------|------|------|
| 200 | 成功 | — |
| 401 | 设备未授权 | 检查 device_key |
| 413 | 文件过大 | 分段后重试 |
| 429 | 频率限制 | 等待后重试 |
| 503 | 服务繁忙 | 指数退避重试 |

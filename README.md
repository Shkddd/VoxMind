# VoxMind — 云端智能录音笔系统

录音笔负责录音并上传至云端，云端完成语音识别、会议纪要与摘要、向量化存储，用户可通过语音询问或 Web 界面检索历史会议内容。

## 系统架构

```
┌─────────────┐     HTTPS/WS      ┌──────────────────────────────────┐
│  录音笔硬件   │ ──────────────→  │          VoxMind Cloud           │
│  (audio/*)   │  上传音频文件     │                                  │
└─────────────┘                   │  ┌─────────┐  ┌──────────────┐  │
                                  │  │ Whisper  │  │   LLM 引擎   │  │
┌─────────────┐                   │  │  (ASR)   │  │ (会议摘要/QA) │  │
│  Web 浏览器  │ ←──────────────  │  └────┬────┘  └──────┬───────┘  │
│  (前端页面)   │   REST + WebSocket│       │              │          │
└─────────────┘                   │       ▼              ▼          │
                                  │  ┌──────────────────────────┐   │
                                  │  │     ChromaDB 向量库       │   │
                                  │  │   (语义检索 + 全文搜索)   │   │
                                  │  └──────────────────────────┘   │
                                  │         ▲                       │
                                  │         │                       │
                                  │  ┌──────┴──────┐               │
                                  │  │  会话管理     │               │
                                  │  │  (WebSocket) │               │
                                  └──┴─────────────┴───────────────┘
```

## 功能特性

| 功能 | 描述 |
|------|------|
| 🎙 音频上传 | 录音笔通过 HTTP 上传音频，支持断点续传 |
| 📝 语音转文字 | 基于 Whisper 的高精度 ASR，支持多说话人识别 |
| 📋 会议摘要 | LLM 自动生成结构化会议纪要（议题/结论/待办） |
| 🔍 语义搜索 | 基于 ChromaDB 的向量检索，自然语言查询历史会议 |
| 💬 实时问答 | 针对已处理会议内容进行多轮对话式问答 |
| 🌐 Web 门户 | 管理后台：浏览记录、搜索、问答、播放音频 |
| 🎤 语音交互 | 录音笔端直接语音询问，云端返回答案 |

## 快速启动

```bash
# 1. 克隆仓库
git clone https://github.com/Shkddd/VoxMind.git
cd VoxMind

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM API Key

# 3. 启动（Docker Compose）
docker compose up -d

# 4. 打开前端
open http://localhost:8000
```

## 配置

环境变量（`.env`）：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_PROVIDER` | LLM 提供商 (openai/anthropic) | openai |
| `LLM_API_KEY` | API Key | — |
| `LLM_MODEL` | 模型名 | gpt-4o-mini |
| `WHISPER_MODEL` | Whisper 模型大小 | base |
| `CHROMA_PERSIST_DIR` | 向量库持久化路径 | ./chromadb |
| `UPLOAD_DIR` | 音频文件存储路径 | ./uploads |
| `SECRET_KEY` | JWT 密钥 | (自动生成) |

## API 概览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/audio/upload` | POST | 录音笔上传音频 |
| `/api/v1/audio/search` | GET | 语义搜索会议记录 |
| `/api/v1/audio/{id}` | GET | 获取单条记录详情 |
| `/api/v1/audio/{id}/summary` | GET | 获取会议摘要 |
| `/api/v1/chat/question` | POST | 对历史内容提问 |
| `/api/v1/chat/stream` | WS | WebSocket 流式问答 |

## 录音笔上传协议

见 [hardware/hardware_protocol.md](hardware/hardware_protocol.md)

## 技术栈

- **后端**: Python FastAPI + uvicorn
- **ASR**: OpenAI Whisper (faster-whisper)
- **LLM**: OpenAI / Anthropic API
- **向量库**: ChromaDB
- **前端**: 原生 HTML/CSS/JS (可替换为 React/Vue)
- **容器**: Docker Compose

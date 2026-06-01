"""Meeting summarization and QA using LLM."""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _get_llm_client(provider: str = "openai", api_key: str = ""):
    """Get LLM client."""
    if provider == "openai":
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    elif provider == "anthropic":
        from anthropic import Anthropic
        return Anthropic(api_key=api_key)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def summarize(transcript: str, provider: str = "openai",
              api_key: str = "", model: str = "gpt-4o-mini") -> dict:
    """Generate structured meeting summary from transcript."""
    client = _get_llm_client(provider, api_key)

    system_prompt = """你是一个专业的会议纪要助手。请根据提供的会议逐字稿，生成结构化摘要。
请以 JSON 格式返回，包含以下字段：
- topics: 会议讨论的主要议题列表
- key_points: 关键结论和要点列表
- action_items: 待办事项列表，每项包含 owner（负责人）、task（任务描述）、deadline（截止日期，如未提及则为null）
- full_text: 一段连贯的摘要文本"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"以下是会议逐字稿：\n\n{transcript}"},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        result = {
            "topics": [],
            "key_points": [content],
            "action_items": [],
            "full_text": content,
        }

    return result


def answer_question(question: str, context: str, provider: str = "openai",
                    api_key: str = "", model: str = "gpt-4o-mini") -> str:
    """Answer a question based on meeting context."""
    client = _get_llm_client(provider, api_key)

    system_prompt = "你是一个会议内容助手。根据提供的会议记录，回答用户的问题。如果信息不足，请如实说明。用中文回答。"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"会议记录：\n{context}\n\n问题：{question}"},
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content

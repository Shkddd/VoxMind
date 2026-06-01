"""IM push service - send meeting summaries and QA responses to Feishu/IM."""

import json
import logging
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError

logger = logging.getLogger(__name__)


def push_to_feishu(webhook_url: str, title: str, content: str,
                   msg_type: str = "interactive") -> bool:
    """Send a message to a Feishu group via incoming webhook.

    Supports two msg_types:
    - "text": plain text message
    - "interactive": rich card message (default)
    """
    if not webhook_url:
        logger.warning("Feishu webhook URL not configured, skipping push")
        return False

    if msg_type == "text":
        payload = {
            "msg_type": "text",
            "content": json.dumps({"text": content}),
        }
    else:
        # Rich card with meeting summary
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"🎙 {title}"},
                    "template": "blue",
                },
                "elements": [
                    {"tag": "markdown", "content": content},
                    {
                        "tag": "hr",
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {"tag": "plain_text", "content": "VoxMind · 智能录音笔云端系统"}
                        ],
                    },
                ],
            },
        }

    data = json.dumps(payload).encode("utf-8")
    req = Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        resp = urlopen(req, timeout=10)
        body = json.loads(resp.read())
        if body.get("code") == 0:
            logger.info("Feishu push succeeded")
            return True
        else:
            logger.error(f"Feishu push failed: {body}")
            return False
    except HTTPError as e:
        logger.error(f"Feishu push HTTP error: {e.code} {e.read().decode()}")
        return False
    except Exception as e:
        logger.error(f"Feishu push error: {e}")
        return False


def format_meeting_summary_for_im(summary: dict, title: str,
                                   duration: float = 0) -> str:
    """Format meeting summary into IM-friendly markdown."""
    lines = [f"**{title}**", f"时长: {duration/60:.0f} 分钟\n"]

    if summary.get("topics"):
        lines.append("**📋 议题**")
        for t in summary["topics"]:
            lines.append(f"• {t}")
        lines.append("")

    if summary.get("key_points"):
        lines.append("**✅ 关键结论**")
        for p in summary["key_points"]:
            lines.append(f"• {p}")
        lines.append("")

    if summary.get("action_items"):
        lines.append("**📌 待办事项**")
        for item in summary["action_items"]:
            owner = item.get("owner", "")
            task = item.get("task", "")
            deadline = item.get("deadline", "")
            parts = [f"• {task}"]
            if owner:
                parts.append(f"  👤 {owner}")
            if deadline:
                parts.append(f"  📅 {deadline}")
            lines.append("\n".join(parts))

    if summary.get("full_text"):
        lines.append(f"\n**📝 摘要**\n{summary['full_text'][:500]}")
        if len(summary["full_text"]) > 500:
            lines.append("...（完整内容请登录 VoxMind 查看）")

    return "\n".join(lines)


def auto_push_meeting(webhook_url: str, meeting_id: str, title: str,
                       summary: dict, duration: float = 0):
    """Auto-push meeting summary to IM after processing."""
    content = format_meeting_summary_for_im(summary, title, duration)
    content += f"\n\n🔗 查看详情: /#/detail/{meeting_id}"
    push_to_feishu(webhook_url, f"会议纪要: {title}", content)

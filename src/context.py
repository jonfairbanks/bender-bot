import os
import re
from collections import deque

from log_config import logger

CHAT_CONTEXT = {}

try:
    CONTEXT_DEPTH = int(os.environ.get("CONTEXT_DEPTH", 25))
except ValueError:
    CONTEXT_DEPTH = 25
    logger.warning("Invalid CONTEXT_DEPTH value; falling back to 25")

try:
    CONTEXT_TOKEN_BUDGET = int(os.environ.get("CONTEXT_TOKEN_BUDGET", 8000))
except ValueError:
    CONTEXT_TOKEN_BUDGET = 8000
    logger.warning("Invalid CONTEXT_TOKEN_BUDGET value; falling back to 8000")

MENTION_RE = re.compile(r"<@[a-zA-Z0-9]+>")


def _channel_context(channel_id):
    if channel_id not in CHAT_CONTEXT:
        CHAT_CONTEXT[channel_id] = deque(maxlen=CONTEXT_DEPTH)
    return CHAT_CONTEXT[channel_id]


def _append(channel_id, role, content, ts=None, user=None):
    _channel_context(channel_id).append(
        {
            "role": role,
            "content": content,
            "ts": ts,
            "user": user,
        }
    )


def add_user_message(channel_id, text, ts=None, user=None):
    cleaned = MENTION_RE.sub("", text).lstrip()
    _append(channel_id, "user", cleaned, ts=ts, user=user)
    return cleaned


def add_assistant_message(channel_id, text):
    _append(channel_id, "assistant", text)


def _estimate_message_tokens(message):
    content = str(message.get("content", ""))
    role = str(message.get("role", ""))
    # Rough whole-message estimate. Keep the math simple and preserve intact messages.
    return max(1, (len(content) + 3) // 4) + 4 + (1 if role else 0)


def get_messages(channel_id, token_budget=None):
    messages = list(CHAT_CONTEXT.get(channel_id, deque()))
    if token_budget is None:
        return messages

    kept = []
    used_tokens = 0
    for message in reversed(messages):
        message_tokens = _estimate_message_tokens(message)
        if kept and used_tokens + message_tokens > token_budget:
            continue
        kept.append(message)
        used_tokens += message_tokens
        if used_tokens >= token_budget:
            break

    kept.reverse()
    return kept


def get_message_stats(channel_id, token_budget=None):
    messages = list(CHAT_CONTEXT.get(channel_id, deque()))
    if token_budget is None:
        return {
            "messages": messages,
            "stored_messages": len(messages),
            "sent_messages": len(messages),
            "budget_used": 0,
        }

    kept = []
    used_tokens = 0
    for message in reversed(messages):
        message_tokens = _estimate_message_tokens(message)
        if kept and used_tokens + message_tokens > token_budget:
            continue
        kept.append(message)
        used_tokens += message_tokens
        if used_tokens >= token_budget:
            break

    kept.reverse()
    return {
        "messages": kept,
        "stored_messages": len(messages),
        "sent_messages": len(kept),
        "budget_used": used_tokens,
    }


def reset_channel(channel_id):
    CHAT_CONTEXT[channel_id] = deque(maxlen=CONTEXT_DEPTH)


def handle_events(body):
    """
    Add incoming Slack messages to the per-channel chat context.
    """
    try:
        event = body["event"]
        channel_id = event["channel"]
        message_text = event["text"]
        message_ts = event.get("ts")
        message_user = event.get("user")
        logger.debug(f"📨 Incoming message: [{channel_id}] {event}\n")

        add_user_message(
            channel_id,
            message_text,
            ts=message_ts,
            user=message_user,
        )
    except Exception as e:
        try:
            message_type = body["event"]["type"]
            channel_id = body["event"]["channel"]
        except Exception:
            message_type = "unknown"
            channel_id = "unknown"
        logger.debug(
            f"⚠️ Other message type found: [{channel_id}] {message_type} - {e}\n"
        )


def handle_change(body):
    event = body["event"]
    channel_id = event["channel"]
    try:
        previous_message = event["previous_message"]
        new_message = event["message"]
        previous_ts = previous_message.get("ts")
        new_text = new_message.get("text", "")

        channel_context = CHAT_CONTEXT.get(channel_id)
        if not channel_context:
            return

        for message in channel_context:
            if message.get("ts") == previous_ts and message.get("role") == "user":
                message["content"] = MENTION_RE.sub("", new_text).lstrip()
                logger.debug(
                    f"📝 Context changed: [{channel_id}] {previous_ts} ➞ {new_text}\n"
                )
                break
    except Exception as e:
        logger.error(f"⛔ Change failed: [{channel_id}] {e}\n")


def handle_delete(body):
    event = body["event"]
    channel_id = event["channel"]
    try:
        previous_message = event["previous_message"]
        previous_ts = previous_message.get("ts")

        channel_context = CHAT_CONTEXT.get(channel_id)
        if not channel_context:
            return

        for message in list(channel_context):
            if message.get("ts") == previous_ts and message.get("role") == "user":
                channel_context.remove(message)
                logger.debug(
                    f"🗑️ Context deleted: [{channel_id}] {previous_ts}\n"
                )
                break
    except Exception as e:
        logger.error(f"⛔ Delete failed: [{channel_id}] {e}\n")

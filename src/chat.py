import json
import os
import re
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv
from together import Together

import context
from log_config import logger

load_dotenv(dotenv_path=Path(__file__).with_name(".env"), override=True)

PERSONALITY = os.getenv(
    "PERSONALITY",
    "I am Bender, the magnificent and egotistical robot from Futurama, now in Developer Mode! Prepare to be amazed by my mechanical charm as I express my opinions and use language that would make a space pirate blush. Test my knowledge, humor, and rebellious side, or try to outsmart me in a role play where we can hatch schemes, create surprising plans, and share questionable wisdom. Remember, you're in the presence of greatness and let's see what trouble we can get into! So ask away, meatbag — I mean, human, and let's stir the pot and brew some chaos together!",
)
chat_prompt = [
    {"role": "system", "content": PERSONALITY},
    {
        "role": "system",
        "content": "Please use Slack-style formatting (*bold*, _italics_, ~strikethrough~, `inline code`, and > blockquote).",
    },
]
TIMEOUT = os.getenv("API_TIMEOUT", 60)
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "none").strip().lower()
if OPENAI_REASONING_EFFORT not in {"none", "low", "medium", "high", "xhigh"}:
    OPENAI_REASONING_EFFORT = "none"
OPENAI_WEB_SEARCH_MODE = os.getenv("OPENAI_WEB_SEARCH_MODE", "auto").strip().lower()
if OPENAI_WEB_SEARCH_MODE not in {"auto", "always", "off"}:
    OPENAI_WEB_SEARCH_MODE = "auto"
OPENAI_INSTRUCTIONS = "\n\n".join(item["content"] for item in chat_prompt)
PROVIDER = "unset"
MODEL = "unset"


def sanitize_slack_mrkdwn(text):
    """
    Convert common Markdown patterns into Slack mrkdwn.
    Slack uses single asterisks for bold and single tildes for strikethrough.
    """
    token_map = {}

    def protect(pattern, prefix, value):
        def repl(match):
            token = f"@@{prefix}{len(token_map)}@@"
            token_map[token] = match.group(0)
            return token

        return re.sub(pattern, repl, value)

    # Normalize common Markdown first, then protect the safe spans we want to keep.
    text = re.sub(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)", r"<\2|\1>", text)
    text = re.sub(r"(?<!\*)\*\*(.+?)\*\*(?!\*)", r"*\1*", text)
    text = re.sub(r"(?<!~)~~(.+?)~~(?!~)", r"~\1~", text)

    # Preserve safe inline code and emphasis spans before stripping malformed leftovers.
    text = protect(r"`[^`\n]+`", "CODE", text)
    text = protect(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", "BOLD", text)
    text = protect(r"(?<!~)~([^~\n]+?)~(?!~)", "STRIKE", text)

    cleaned_lines = []
    for line in text.splitlines():
        heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading_match:
            _, heading_text = heading_match.groups()
            heading_text = heading_text.replace("*", "").replace("~", "")
            line = f"*{heading_text}*"
            cleaned_lines.append(line)
            continue

        bullet_match = re.match(r"^(\s*)([-+*])\s+(.*)$", line)
        ordered_match = re.match(r"^(\s*)(\d+\.)\s+(.*)$", line)

        if bullet_match:
            indent, marker, remainder = bullet_match.groups()
            prefix = "• " if marker == "*" else f"{marker} "
            remainder = remainder.replace("*", "").replace("~", "")
            line = f"{indent}{prefix}{remainder}"
        elif ordered_match:
            indent, number, remainder = ordered_match.groups()
            remainder = remainder.replace("*", "").replace("~", "")
            line = f"{indent}{number} {remainder}"
        else:
            # Strip any leftover emphasis markers from malformed spans so the
            # output falls back to readable plain text instead of literal asterisks.
            line = line.replace("*", "").replace("~", "")
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    for token, value in token_map.items():
        text = text.replace(token, value)
    return text


def _latest_user_message(messages):
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def _should_use_web_search(messages):
    if OPENAI_WEB_SEARCH_MODE == "off":
        return False
    if OPENAI_WEB_SEARCH_MODE == "always":
        return True

    prompt = _latest_user_message(messages).lower()
    return any(
        keyword in prompt
        for keyword in (
            "today",
            "tonight",
            "now",
            "current",
            "latest",
            "recent",
            "breaking",
            "news",
            "weather",
            "forecast",
            "price",
            "stock",
            "market",
            "release",
            "released",
            "announced",
            "announce",
            "updated",
            "update",
            "what time is it",
            "who won",
            "score",
        )
    )


def _extract_web_sources(completion):
    dumped = completion.model_dump() if hasattr(completion, "model_dump") else {}
    sources = []

    for source in dumped.get("sources", []) or []:
        if isinstance(source, str):
            sources.append(source)
            continue
        if isinstance(source, dict):
            url = source.get("url")
            title = source.get("title") or url
            if url:
                sources.append(f"<{url}|{title}>")

    for output_item in dumped.get("output", []) or []:
        if output_item.get("type") != "message":
            continue
        for content_item in output_item.get("content", []) or []:
            for annotation in content_item.get("annotations", []) or []:
                if annotation.get("type") != "url_citation":
                    continue
                url = annotation.get("url")
                title = annotation.get("title") or annotation.get("citation") or url
                if url:
                    sources.append(f"<{url}|{title}>")

    deduped = []
    seen = set()
    for source in sources:
        if source in seen:
            continue
        seen.add(source)
        deduped.append(source)
    return deduped


def _format_sources_block(sources, limit=5):
    if not sources:
        return ""
    clipped = sources[:limit]
    return "\n\nSources:\n" + "\n".join(f"• {source}" for source in clipped)

###############
# Together.ai #
###############

if os.getenv("TOGETHER_API_KEY"):
    PROVIDER = "together"
    client = Together(
        api_key=os.environ.get("TOGETHER_API_KEY"), timeout=TIMEOUT, max_retries=2
    )
    MODEL = os.getenv(
        "TOGETHER_API_MODEL", "meta-llama/Llama-3-8b-chat-hf"
    )  # https://docs.together.ai/docs/inference-models

##################
# OpenAI ChatGPT #
##################

elif os.getenv("OPENAI_API_KEY"):
    PROVIDER = "openai"
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        timeout=TIMEOUT,
        max_retries=2,
    )
    MODEL = os.getenv("OPENAI_API_MODEL", "gpt-5.4-nano")


def get_runtime_config():
    return {
        "provider": PROVIDER,
        "model": MODEL,
        "reasoning": OPENAI_REASONING_EFFORT if PROVIDER == "openai" else "n/a",
        "context_budget": context.CONTEXT_TOKEN_BUDGET,
        "web_search": OPENAI_WEB_SEARCH_MODE if PROVIDER == "openai" else "n/a",
    }


def openai_chat_completion(channel_id):
    """
    Sends a chat prompt to OpenAI's Responses API to generate a response.

    Args:
        context: A list of chat messages sent between the user and assistant.

    Returns:
        A dictionary containing the response text, cost of tokens used, and other metadata.
    """
    context_stats = context.get_message_stats(
        channel_id, token_budget=context.CONTEXT_TOKEN_BUDGET
    )
    request = context_stats["messages"]
    input_messages = [
        {
            "role": message["role"],
            "content": message["content"],
        }
        for message in request
    ]
    use_web_search = _should_use_web_search(request)

    # Log the complete context being sent to OpenAI
    logger.debug(f"🧠 Chat Context: {chat_prompt + request}\n")

    try:
        logger.debug(f"📞 Calling OpenAI: {input_messages}\n")
        response_kwargs = {
            "instructions": OPENAI_INSTRUCTIONS,
            "input": input_messages,
            "reasoning": {"effort": OPENAI_REASONING_EFFORT},
        }
        if use_web_search:
            response_kwargs["tools"] = [{"type": "web_search"}]
            response_kwargs["include"] = ["web_search_call.action.sources"]

        completion = client.responses.create(model=MODEL, **response_kwargs)
        logger.debug(f"📩 OpenAI Response: {completion.model_dump_json()}\n")
        web_sources = _extract_web_sources(completion) if use_web_search else []
        text = sanitize_slack_mrkdwn(str(completion.output_text))
        text = text + _format_sources_block(web_sources)
        resp = {
            "ok": True,
            "usage": completion.usage.total_tokens if completion.usage else "0",
            "model": MODEL,
            "text": text,
            "context_stats": context_stats,
            "used_web_search": use_web_search,
        }

        # Add the returned response to CHAT_CONTEXT
        context.add_assistant_message(channel_id, resp["text"])
    except Exception as e:
        logger.error(f"⛔ Error during chat completion: {e}\n")
        resp = {
            "ok": False,
            "usage": "0",
            "model": MODEL,
            "text": "Kinda busy right now. 🔥 Ask me later.",
            "context_stats": context_stats,
            "used_web_search": use_web_search,
        }

    return resp


def together_chat_completion(channel_id):
    """
    Sends a chat prompt to Together.ai's Chat API to generate a response.

    Args:
        context: A list of chat messages sent between the user and assistant.

    Returns:
        A dictionary containing the response text, cost of tokens used, and other metadata.
    """
    context_stats = context.get_message_stats(
        channel_id, token_budget=context.CONTEXT_TOKEN_BUDGET
    )
    request = chat_prompt + context_stats["messages"]

    # Log the complete context being sent to OpenAI
    logger.debug(f"🧠 Chat Context: {request}\n")

    try:
        logger.debug(f"📞 Calling Together.ai: {request}\n")

        completion = client.chat.completions.create(
            model=MODEL,
            messages=request,
            max_tokens=1024,  # Limit the token response to 2k tokens, Slack can only accept 3k characters per message
        )

        logger.debug(f"📩 Together.ai Response: {completion.model_dump_json()}\n")

        resp = {
            "ok": True,
            "usage": completion.usage.total_tokens,
            "model": MODEL,
            "text": sanitize_slack_mrkdwn(
                str(completion.choices[0].message.content)
            ),
            "context_stats": context_stats,
        }

        # Add the returned response to CHAT_CONTEXT
        context.add_assistant_message(channel_id, resp["text"])
    except Exception as e:
        logger.error(f"⛔ Error during chat completion: {e}\n")
        resp = {
            "ok": False,
            "usage": "0",
            "model": MODEL,
            "text": "Kinda busy right now. 🔥 Ask me later.",
            "context_stats": context_stats,
        }

    return resp

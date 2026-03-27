import asyncio
import json
import os
import sys
import time
from pathlib import Path

import context

from chat import openai_chat_completion
from chat import together_chat_completion
from log_config import logger

from dotenv import load_dotenv
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

load_dotenv(dotenv_path=Path(__file__).with_name(".env"), override=True)

# Determine Mode -- RESPOND or LISTEN
mode = os.getenv("BOT_MODE", "RESPOND")
if mode.upper() == "RESPOND":
    slack_mode = "app_mention"
elif mode.upper() == "LISTEN":
    slack_mode = {"type": "message", "subtype": None}
else:
    logger.warning(
        "⚠️ BOT_MODE should be of type RESPOND or LISTEN; defaulting to RESPOND"
    )
    slack_mode = "app_mention"

# Setup Slack app
app = AsyncApp(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)


# Handle message changes
@app.event(event={"type": "message", "subtype": "message_changed"})
async def handle_change_events(body):
    try:
        context.handle_change(body)
    except Exception as e:
        logger.debug(f"⛔ Change failed: {e}")


# Handle message deletion
@app.event(event={"type": "message", "subtype": "message_deleted"})
async def handle_delete_events(body):
    try:
        context.handle_delete(body)
    except Exception as e:
        logger.debug(f"⛔ Delete failed: {e}")


# Handle message events
@app.event(slack_mode)
async def handle_app_mentions(ack, body, say, client):
    await ack()
    # Add an emoji to the incoming requests
    try:
        channel_id = body["event"]["channel"]
        message_ts = body["event"]["ts"]
        await client.reactions_add(
            channel=channel_id, timestamp=message_ts, name="eyes"
        )
    except Exception as e:
        logger.error(f"⛔ Slackmoji failed: {e}")

    try:
        context.handle_events(body)
    except Exception as e:
        logger.error(f"⛔ Event error: {e} - {body}")

    # Make a call to Together/OpenAI
    start_time = time.time()
    if os.getenv("TOGETHER_API_KEY"):
        ai_resp = together_chat_completion(channel_id)
    elif os.getenv("OPENAI_API_KEY"):
        ai_resp = openai_chat_completion(channel_id)
    else:
        logger.warning("No OpenAI or Together API key configured; skipping reply")
        return await say("No chat provider is configured for this bot.")
    end_time = time.time()
    elapsed_time = f"{(end_time - start_time):.2f}"

    # Respond to the user
    return await say(
        text=ai_resp["text"],
        blocks=[
            {"type": "section", "text": {"type": "mrkdwn", "text": ai_resp["text"]}},
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "plain_text",
                        "text": "Response Time: "
                        + str(elapsed_time)
                        + "s || Model: "
                        + str(ai_resp["model"].upper())
                        + " || Context Depth: "
                        + str(len(context.CHAT_CONTEXT[channel_id]))
                        + " || Complexity: "
                        + str(ai_resp["usage"]),
                        "emoji": True,
                    }
                ],
            },
        ],
    )


# Respond to /context commands
@app.command("/context")
async def get_context(ack, body, respond):
    await ack()
    channel_id = body["channel_id"]
    channel_context = json.dumps(context.CHAT_CONTEXT.get(channel_id, []))
    await respond(f"Channel Context: ```{channel_context}```")
    return


# Respond to /reset commands
@app.command("/reset")
async def reset_context(ack, body, respond):
    await ack()
    channel_id = body["channel_id"]
    context.CHAT_CONTEXT.setdefault(channel_id, []).clear()
    await respond("Hmm, I forgot what we were talking about 🤔")


# Catch all (should be last handler)
@app.event("message")
async def handle_message_events(ack, body):
    await ack()
    context.handle_events(body)


async def main():
    try:
        handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
        await handler.start_async()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

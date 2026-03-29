import asyncio
import json
import os
import sys
import time

import context

from chat import get_runtime_config
from chat import openai_chat_completion
from chat import together_chat_completion
from log_config import logger

from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

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
    channel_id = None
    message_ts = None
    # Add an emoji to the incoming requests
    try:
        channel_id = body["event"]["channel"]
        message_ts = body["event"]["ts"]
        await client.reactions_add(
            channel=channel_id, timestamp=message_ts, name="eyes"
        )
    except Exception as e:
        logger.error(f"⛔ Slackmoji failed: {e}")
        channel_id = body.get("event", {}).get("channel")
        message_ts = body.get("event", {}).get("ts")

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
        ai_resp = {
            "ok": False,
            "usage": "0",
            "model": "none",
            "text": "No chat provider is configured for this bot.",
        }
    end_time = time.time()
    elapsed_time = f"{(end_time - start_time):.2f}"
    context_stats = ai_resp.get("context_stats", {})
    stored_messages = context_stats.get(
        "stored_messages", len(context.get_messages(channel_id))
    )
    sent_messages = context_stats.get("sent_messages", stored_messages)
    budget_used = context_stats.get("budget_used", 0)

    # Respond to the user
    try:
        response = await say(
            text=ai_resp["text"],
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": ai_resp["text"]},
                },
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "plain_text",
                            "text": "Response Time: "
                            + str(elapsed_time)
                            + "s || Model: "
                            + str(ai_resp["model"])
                            + " || Stored Messages: "
                            + str(stored_messages)
                            + " || Sent Messages: "
                            + str(sent_messages)
                            + " || Tokens Used: "
                            + str(budget_used),
                            "emoji": True,
                        }
                    ],
                },
            ],
        )
        try:
            await client.reactions_remove(
                channel=channel_id, timestamp=message_ts, name="eyes"
            )
            if not ai_resp["ok"]:
                await client.reactions_add(
                    channel=channel_id, timestamp=message_ts, name="warning"
                )
        except Exception as e:
            logger.error(f"⛔ Reaction update failed: {e}")
        return response
    except Exception as e:
        logger.error(f"⛔ Slack reply failed: {e}")
        try:
            await client.reactions_remove(
                channel=channel_id, timestamp=message_ts, name="eyes"
            )
            await client.reactions_add(
                channel=channel_id, timestamp=message_ts, name="warning"
            )
        except Exception as reaction_error:
            logger.error(f"⛔ Reaction fallback failed: {reaction_error}")
        raise


# Respond to /context commands
@app.command("/context")
async def get_context(ack, body, respond):
    await ack()
    channel_id = body["channel_id"]
    channel_context = json.dumps(context.get_messages(channel_id))
    await respond(f"Channel Context: ```{channel_context}```")
    return


# Respond to /reset commands
@app.command("/reset")
async def reset_context(ack, body, respond):
    await ack()
    channel_id = body["channel_id"]
    context.reset_channel(channel_id)
    await respond("Hmm, I forgot what we were talking about 🤔")


# Catch all (should be last handler)
@app.event("message")
async def handle_message_events(ack, body):
    await ack()
    context.handle_events(body)


async def main():
    try:
        runtime = get_runtime_config()
        logger.info(
            "Startup: provider=%s model=%s reasoning=%s context_budget=%s",
            runtime["provider"],
            runtime["model"],
            runtime["reasoning"],
            runtime["context_budget"],
        )
        handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
        await handler.start_async()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

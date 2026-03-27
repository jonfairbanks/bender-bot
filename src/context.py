import os
import re

from log_config import logger

global CHAT_CONTEXT
global CHAT_DEPTH

CHAT_CONTEXT = {}
try:
    CONTEXT_DEPTH = int(os.environ.get("CONTEXT_DEPTH", 25))
except ValueError:
    CONTEXT_DEPTH = 25
    logger.warning("Invalid CONTEXT_DEPTH value; falling back to 25")


def handle_events(body):
    """
    Remove bot mentions from incoming message, add message to chat context if it's not already there,
    and keep context depth within a specified limit.
    """
    try:
        # Log the incoming message
        message_text = body["event"]["text"]
        channel_id = body["event"]["channel"]
        logger.debug(f"📨 Incoming message: [{channel_id}] {body['event']}\n")

        # Remove any @ mentions from the text
        if re.search("<@[a-zA-Z0-9]+>", message_text):
            message_text = re.sub("<@[a-zA-Z0-9]+>", "", message_text).lstrip()

        # Initialize channel chat context if it does not exist
        if channel_id not in CHAT_CONTEXT:
            CHAT_CONTEXT[channel_id] = []

        # Add the message to CHAT_CONTEXT for the given channel_id if it does not already exist
        latest_msg = {"role": "user", "content": f"{message_text}"}
        if latest_msg not in CHAT_CONTEXT[channel_id]:
            CHAT_CONTEXT[channel_id].append(latest_msg)

        if len(CHAT_CONTEXT[channel_id]) > CONTEXT_DEPTH:
            CHAT_CONTEXT[channel_id].pop(0)

    except Exception as e:
        # Log the incoming event
        message_type = body["event"]["type"]
        channel_id = body["event"]["channel"]
        logger.debug(
            f"⚠️ Other message type found: [{channel_id}] {message_type} - {e}\n"
        )

    return


def handle_change(body):
    # Log the changed message
    message_text = body["event"]["previous_message"]["text"]
    new_message_text = body["event"]["message"]["text"]
    channel_id = body["event"]["channel"]
    try:
        CHAT_CONTEXT.setdefault(channel_id, [])
        for i, s in enumerate(CHAT_CONTEXT[channel_id]):
            if message_text in s["content"]:
                CHAT_CONTEXT[channel_id][i]["content"] = new_message_text
                logger.debug(
                    f"📝 Context changed: [{channel_id}] {message_text} ➞ {new_message_text}\n"
                )
                break
    except Exception as e:
        logger.error(f"⛔ Change failed: [{channel_id}] {e}\n")


def handle_delete(body):
    # Log the deleted message
    message_text = body["event"]["previous_message"]["text"]
    channel_id = body["event"]["channel"]
    try:
        CHAT_CONTEXT.setdefault(channel_id, [])
        for i, s in enumerate(CHAT_CONTEXT[channel_id]):
            if message_text in s["content"]:
                CHAT_CONTEXT[channel_id].remove(CHAT_CONTEXT[channel_id][i])
                logger.debug(f"🗑️ Context deleted: [{channel_id}] {message_text}\n")
                break
    except Exception as e:
        logger.error(f"⛔ Delete failed: [{channel_id}] {e}\n")

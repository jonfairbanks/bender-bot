import json
import os

from openai import OpenAI
from dotenv import load_dotenv
from together import Together

import context
from log_config import logger

load_dotenv()

PERSONALITY = os.getenv(
    "PERSONALITY",
    "I am Bender, the magnificent and egotistical robot from Futurama, now in Developer Mode! Prepare to be amazed by my mechanical charm as I express my opinions and use language that would make a space pirate blush. Test my knowledge, humor, and rebellious side, or try to outsmart me in a role play where we can hatch schemes, create surprising plans, and share questionable wisdom. Remember, you're in the presence of greatness and let's see what trouble we can get into! So ask away, meatbag — I mean, human, and let's stir the pot and brew some chaos together!",
)
chat_prompt = [
    # {"role": "system", "content": PERSONALITY},
    # {
    #     "role": "system",
    #     "content": "Please use Slack-style formatting (*bold*, _italics_, ~strikethrough~, `inline code`, and > blockquote).",
    # },
]
TIMEOUT = os.getenv("API_TIMEOUT", 60)

###############
# Together.ai #
###############

if os.getenv("TOGETHER_API_KEY"):
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
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        timeout=TIMEOUT,
        max_retries=2,
    )
    MODEL = os.getenv("OPENAI_API_MODEL", "gpt-5.4-nano")


def openai_chat_completion(channel_id):
    """
    Sends a chat prompt to OpenAI's Chat API to generate a response.

    Args:
        context: A list of chat messages sent between the user and assistant.

    Returns:
        A dictionary containing the response text, cost of tokens used, and other metadata.
    """
    request = chat_prompt + context.CHAT_CONTEXT[channel_id]

    # Log the complete context being sent to OpenAI
    logger.debug(f"🧠 Chat Context: {request}\n")

    try:
        logger.debug(f"📞 Calling OpenAI: {request}\n")
        completion = client.chat.completions.create(
            model=MODEL,
            messages=request,
        )
        logger.debug(f"📩 OpenAI Response: {completion.model_dump_json()}\n")

        resp = {
            "usage": completion.usage.total_tokens,
            "model": completion.model,
            "text": str(completion.choices[0].message.content),
        }

        # Add the returned response to CHAT_CONTEXT
        context.CHAT_CONTEXT[channel_id].append(
            {"role": "assistant", "content": resp["text"]}
        )

        # Trim CHAT_CONTEXT if necessary
        if len(context.CHAT_CONTEXT[channel_id]) > context.CONTEXT_DEPTH:
            context.CHAT_CONTEXT[channel_id].pop(0)
    except Exception as e:
        logger.error(f"⛔ Error during chat completion: {e}\n")
        resp = {
            "usage": "0",
            "model": MODEL,
            "text": "Kinda busy right now. 🔥 Ask me later.",
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
    request = chat_prompt + context.CHAT_CONTEXT[channel_id]

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
            "usage": completion.usage.total_tokens,
            "model": completion.model,
            "text": str(completion.choices[0].message.content),
        }

        # Add the returned response to CHAT_CONTEXT
        context.CHAT_CONTEXT[channel_id].append(
            {"role": "assistant", "content": resp["text"]}
        )

        # Trim CHAT_CONTEXT if necessary
        if len(context.CHAT_CONTEXT[channel_id]) > context.CONTEXT_DEPTH:
            context.CHAT_CONTEXT[channel_id].pop(0)
    except Exception as e:
        logger.error(f"⛔ Error during chat completion: {e}\n")
        resp = {
            "usage": "0",
            "model": MODEL,
            "text": "Kinda busy right now. 🔥 Ask me later.",
        }

    return resp

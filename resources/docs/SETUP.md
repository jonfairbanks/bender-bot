## Setup

#### Requirements

- Python 3.14+
- [A Slack app token](https://api.slack.com/apps)
	- Create a Slack app from scratch
		- NEW: Create a new app using a Slack [app manifest](../manifest.yml)
	- Install the app into your Slack workspace
- An API key for Chat capabilities (If both keys are set, Together.ai will be used as the default)
	- [Together.ai API key](https://platform.openai.com/account/api-keys) for open-source models (ex: Llama)
	- [OpenAI API key](https://platform.openai.com/account/api-keys) for ChatGPT models

(Note: Python packages `slack` and `slackclient` are no longer supported. Please use `slack_bolt`.)

#### Local

- Setup pipenv: `pip install pipenv && pipenv shell`
- Install dependencies: `pipenv install`
- Launch the service with your Slack token: `SLACK_APP_TOKEN='xapp-xxxxx' SLACK_BOT_TOKEN='xoxb-xxxxx' SLACK_SIGNING_SECRET='xxxxx' OPENAI_API_KEY='xxxxx' python3 index.py`
- Invite the bot to a channel and send a sample message

#### Docker

bender-bot is also available for deployment via Docker:
```
docker run -d --env-file .env jonfairbanks/bender-bot
```

#### Docker-Compose

bender-bot can also be stood up using Docker Compose:
```
docker compose up
```

Remember to rename _.env.sample_ to _.env_ and change values

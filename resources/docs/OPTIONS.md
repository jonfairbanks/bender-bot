## Options

Options can be overridden or enabled using the following env variables:

- **DEBUG**: Enables additional logging of events, requests, responses and chat context
- **SLACK_APP_TOKEN**: Required; used to create the Slack bot instance
- **SLACK_BOT_TOKEN**: Required; used to authenticate with Slack APIs
- **SLACK_SIGNING_SECRET**: Required; used to authenticate with Slack APIs
- **OPENAI_API_KEY**: Required; used to authenticate with OpenAI Chat Completion API
- **OPENAI_API_MODEL**: Model to use when calling OpenAI (Default: `gpt-4`)
- **OPENAI_API_TIMEOUT**: Amount of seconds to wait for OpenAI responses (Default: `90`)
- **PERSONALITY**: Overwrite the current prompt used to establish bot identity
- **BOT_MODE**: Switch between RESPONSE mode (@BOT) and LISTEN mode (Default: `RESPONSE`)

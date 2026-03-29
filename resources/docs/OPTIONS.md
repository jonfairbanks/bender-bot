## Options

Options can be overridden or enabled using the following env variables:

- **DEBUG**: Enables additional logging of events, requests, responses and chat context
- **SLACK_APP_TOKEN**: Required; used to create the Slack bot instance
- **SLACK_BOT_TOKEN**: Required; used to authenticate with Slack APIs
- **SLACK_SIGNING_SECRET**: Required; used to authenticate with Slack APIs
- **OPENAI_API_KEY**: Required; used to authenticate with OpenAI Chat Completion API
- **OPENAI_API_MODEL**: Model to use when calling OpenAI (Default: `gpt-5.4-nano`)
- **OPENAI_REASONING_EFFORT**: Reasoning depth for OpenAI GPT-5-family Responses API calls (`none`, `low`, `medium`, `high`, `xhigh`; Default: `none`)
- **OPENAI_WEB_SEARCH_MODE**: Whether to use web search for time-sensitive prompts (`auto`, `always`, `off`; Default: `auto`)
- **API_TIMEOUT**: Amount of seconds to wait for OpenAI responses (Default: `60`)
- **CONTEXT_TOKEN_BUDGET**: Approximate token budget for retained conversation history (Default: `8000`)
- **PERSONALITY**: Overwrite the current prompt used to establish bot identity
- **BOT_MODE**: Switch between RESPONSE mode (@BOT) and LISTEN mode (Default: `RESPONSE`)

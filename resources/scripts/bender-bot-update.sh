#!/bin/sh

# Exit on Errors
set -e

# Starting
echo "Starting bender-bot update..."

# Clean-up old instance
docker stop bender-bot
docker rm bender-bot
docker rmi jonfairbanks/bender-bot

# Launch a new instance
docker run -d \
-e SLACK_APP_TOKEN=$SLACK_APP_TOKEN \
-e SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN \
-e SLACK_SIGNING_SECRET=$SLACK_SIGNING_SECRET \
-e OPENAI_API_KEY=$OPENAI_API_KEY \
-e DEBUG=True \
--name=bender-bot \
--restart=always \
jonfairbanks/bender-bot

# Show Logs after updating
sleep 10s
docker ps -a
docker logs bender-bot

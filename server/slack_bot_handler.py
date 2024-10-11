import logging
from typing import Any

from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from server.slack.app import app

logger = logging.getLogger()


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    logger.info(f"Received event: {event}")

    # Lambada関数でSlack Boltアプリを実行するためのアダプター
    # ref: https://github.com/slackapi/bolt-python/tree/main/examples/aws_lambda
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)

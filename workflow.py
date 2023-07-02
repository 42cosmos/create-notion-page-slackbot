import os
import re

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import logging
from notion_client import Notion

# Initializes your app with your bot token and socket mode handler
load_dotenv()
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")

assert SLACK_BOT_TOKEN and SLACK_APP_TOKEN, "Missing Slack tokens"

# visit https://slack.dev/bolt-python/api-docs/slack_bolt/kwargs_injection/args.html
app = App(token=SLACK_BOT_TOKEN)
notion = Notion()

logger = logging.getLogger(__name__)


@app.event("app_mention")
def handle_app_mention_events(body, say):
    event_ts = body["event"]["ts"]
    channel_id = body["event"]["channel"]
    text = body["event"]["text"]

    title = text.split("\n")[0]
    contents = "\n".join(text.split("\n")[1:])

    page_title = re.sub(r"\<\@[\w\d]+\>", "", title).strip()

    try:
        check_create_page = notion.create_page(title=page_title,
                                               contents=contents)
        say(channel=channel_id,
            text=f"Please Check this page: {check_create_page['url']}",
            thread_ts=event_ts)
    except:
        check_create_page = "Sorry! Fail to create page"
        say(text=check_create_page,
            channel=channel_id,
            thread_ts=event_ts)


# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()

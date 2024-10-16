import logging
import os
from typing import Callable, Sequence

from langchain_aws import BedrockEmbeddings, ChatBedrock
from slack_bolt import App, BoltRequest, Say
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from server.rag import Rag
from server.slack.utils import format_rag_result, remove_mention
from server.utils.env import getenv_or_raise

SlackRequestHandler.clear_all_log_handlers()  # NOTE: このメソッド呼び出し以前に記述されたlogger呼び出しはログ出力されない模様
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)

# ボットトークンと署名シークレットを使ってアプリを初期化する
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True,
)

llm = ChatBedrock(
    model="anthropic.claude-3-haiku-20240307-v1:0",
    region="us-east-1",
    client=None,
    model_kwargs={
        "temperature": 0,
    },
)
embedding = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v2:0", region_name="us-east-1", client=None
)
rag = Rag(
    llm=llm,
    embedding=embedding,
    index_name=getenv_or_raise("PINECONE_INDEX_NAME"),
    bucket_name=getenv_or_raise("RAG_DOCSTORE_BUCKET_NAME"),
    langfuse_secret_key=getenv_or_raise("LANGFUSE_SECRET_KEY"),
    langfuse_public_key=getenv_or_raise("LANGFUSE_PUBLIC_KEY"),
    langfuse_host=getenv_or_raise("LANGFUSE_HOST"),
)


# タイムアウトによるリトライをスキップするためのミドルウェア
@app.middleware
def skip_timeout_retry(
    request: BoltRequest, next: Callable[[], None], logger: logging.Logger
):
    logger.debug(f"request.headers: {request.headers}")

    retry_num = request.headers.get("x-slack-retry-num", [])
    retry_reason = request.headers.get("x-slack-retry-reason", [])
    logger.debug(f"retry_num: {retry_num}, retry_reason: {retry_reason}")

    if is_timeout_retry(retry_num=retry_num, retry_reason=retry_reason):
        logger.info("Skip retry request")
        return

    logger.info("Continue to the next middleware")
    next()


def is_timeout_retry(*, retry_num: Sequence[str], retry_reason: Sequence[str]) -> bool:
    if retry_num == []:
        return False

    # 本来は"http_timeout"のみをチェックすべきだが、正常にレスポンスされた場合でもリトライ理由が"http_error"になることがあるため、両方をチェックする
    if retry_reason == ["http_timeout"] or retry_reason == ["http_error"]:
        return True

    return False


# ボットへのメンションに対するイベントリスナー
def handle_app_mention(event, say: Say, logger: logging.Logger):
    logger.debug(f"app_mention event: {event}")

    text = event["text"]
    channel = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]

    say(channel=channel, thread_ts=thread_ts, text="考え中です...少々お待ちください...")

    payload = remove_mention(text)
    logger.debug(f"payload: {payload}")

    try:
        rag_result = rag.invoke(payload)
        logger.debug(f"rag_result: {rag_result}")

        say(channel=channel, thread_ts=thread_ts, text=format_rag_result(rag_result))
    except Exception as e:
        logger.exception("エラーが発生しました")
        say(channel=channel, thread_ts=thread_ts, text=f"エラーが発生しました: {e}")


def noop_ack():
    pass


# 3秒以内にレスポンスを返さないとリトライが発生してしまうため、それを防ぐためにLazyリスナーとして登録する
# この対応を行っても、コールドスタート時には3秒を超えてしまうようでリトライが発生する
# ref:
# - https://api.slack.com/apis/events-api#retries
# - https://slack.dev/bolt-python/ja-jp/concepts#lazy-listeners
# - https://github.com/slackapi/bolt-python/issues/678#issuecomment-1171837818
app.event("app_mention")(ack=noop_ack, lazy=[handle_app_mention])

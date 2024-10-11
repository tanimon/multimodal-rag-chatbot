FROM public.ecr.aws/lambda/python:3.12

# poetryをインストール
ENV POETRY_HOME=/etc/poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.8.3

# poetryのパスを通す
ENV PATH="${PATH}:${POETRY_HOME}/bin"

# poetryで管理している依存パッケージをインストール
COPY pyproject.toml poetry.lock ./
RUN poetry export --with main --format requirements.txt --output requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

COPY ./server ${LAMBDA_TASK_ROOT}/server

COPY slack_bot_handler.py ${LAMBDA_TASK_ROOT}

CMD [ "slack_bot_handler.handler" ]

import os


def getenv_or_raise(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        raise Exception(f"環境変数が設定されていません: {key}")
    return value

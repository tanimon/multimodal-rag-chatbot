import re

from server.rag import AnswerStatement, MetadataTypedDocument, RagResult


def remove_mention(text: str) -> str:
    """メンションを除去する"""

    mention_regex = r"<@.*>"
    return re.sub(mention_regex, "", text).strip()


def format_rag_result(rag_result: RagResult) -> str:
    answer_text = ""
    cited_source_ids = set[int]()

    for answer_statement in rag_result["answer"].statements:
        # TODO: チャンク化されたドキュメントから引用しているため、大本のドキュメントが同一でも複数の引用番号に分かれてしまう場合があるのを修正する
        answer_text += f"{_format_answer_statement(answer_statement)}\n"
        cited_source_ids.update(answer_statement.citations)

    retrieved_docs = rag_result["retrieved_docs"]
    cited_sources_text = "\n".join(
        [
            _format_source(cited_source_id, retrieved_docs)
            for cited_source_id in cited_source_ids
        ]
    )

    non_cited_source_ids = set(range(len(retrieved_docs))) - cited_source_ids
    non_cited_source_text = "\n".join(
        [
            _format_source(non_cited_source_id, retrieved_docs)
            for non_cited_source_id in non_cited_source_ids
        ]
    )

    print("non_cited_source_ids", non_cited_source_ids)

    text = f"{answer_text}\n\n参照したドキュメント\n{cited_sources_text}\n\n検索にヒットしたその他のドキュメント\n{non_cited_source_text}"
    return text


def _format_answer_statement(answer_statement: AnswerStatement) -> str:
    """answer_statementを以下の形式でフォーマットする

    {回答文} [{引用番号}]

    例: 日本の首都は東京です [1][2]

    Args:
        answer_statement (AnswerStatement): フォーマット対象のAnswerStatement

    Returns:
        str: フォーマットされた回答文
    """

    citations_text = "".join(
        [f"[{citation}]" for citation in answer_statement.citations]
    )
    return f"{answer_statement.statement} {citations_text}"


def _format_source(cited_source_id: int, docs: list[MetadataTypedDocument]) -> str:
    cited_doc = docs[cited_source_id]
    link = _format_slack_link(text=cited_doc.metadata.title, url=cited_doc.metadata.url)
    formatted_source = f"[{cited_source_id}]: {link}"

    return formatted_source


def _format_slack_link(*, text: str, url: str) -> str:
    return f"<{url}|{text}>"

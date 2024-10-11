from typing import Generic, TypedDict, TypeVar

from langchain_core.documents import Document as LangChainDocument
from pydantic import BaseModel, Field

from server.rag.ingestion.model import DocumentMetadata

TMetadata = TypeVar("TMetadata", bound=BaseModel)


class MetadataTypedDocument(BaseModel, Generic[TMetadata]):
    page_content: str
    metadata: TMetadata

    @staticmethod
    def from_langchain_document(
        doc: LangChainDocument, metadata_cls: type[TMetadata]
    ) -> "MetadataTypedDocument[TMetadata]":
        return MetadataTypedDocument(
            page_content=doc.page_content,
            metadata=metadata_cls.model_validate(doc.metadata),
        )

    def to_langchain_document(self) -> LangChainDocument:
        return LangChainDocument(
            page_content=self.page_content,
            metadata=self.metadata.model_dump(),
        )


class AnswerStatement(BaseModel):
    """与えられた情報源のみに基づいて、ユーザーの質問に答えてください。"""

    statement: str = Field(
        ...,
        description="与えられた情報源のみに基づく、ユーザーの質問に対する回答。",
    )
    citations: list[int] = Field(
        ...,
        description="回答の根拠となる特定の情報源に対する整数のID。",
    )


class CitedAnswer(BaseModel):
    """与えられた情報源のみに基づいて、ユーザーの質問に回答し、使用した情報源を引用してください。
    回答は、各文に使用した情報源への引用を含む文のリストである必要があります。
    """

    statements: list[AnswerStatement] = Field(
        ..., description="ユーザーの質問に対する回答文のリスト。"
    )


# NOTE:
# rag_chainの実行結果の型は実際にはlangchain_core.runnables.utils.AddableDictになっている
# ref: https://api.python.langchain.com/en/v0.1/runnables/langchain_core.runnables.utils.AddableDict.html
# より厳密に型付けしたいため、ここではTypedDictを使用している
# pydanticのBaseModelを用いて型付けすると、ランタイムの型と合致せずエラーが発生することに注意
class RagResult(TypedDict):
    retrieved_docs: list[MetadataTypedDocument[DocumentMetadata]]
    answer: CitedAnswer

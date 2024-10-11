from operator import itemgetter

from langchain_core.documents import Document as LangChainDocument
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    Runnable,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from langfuse.callback import CallbackHandler  # type: ignore

from server.rag.ingestion.model import (
    DocumentMetadata,
    ImageDocumentMetadata,
    TextDocumentMetadata,
)
from server.rag.model import CitedAnswer, MetadataTypedDocument, RagResult
from server.rag.retriever import create_retriever

_TEXT_MESSAGE_TEMPLATE = {
    "type": "text",
    "text": """\
You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.

Question: {question} 

Context: {context} 

Answer:
""",
}


class Rag:
    _langfuse_handler: CallbackHandler
    _rag_chain: Runnable[str, RagResult]

    def __init__(
        self,
        index_name: str,
        bucket_name: str,
        llm: BaseChatModel,
        embedding: Embeddings,
        langfuse_secret_key: str,
        langfuse_public_key: str,
        langfuse_host: str,
    ):
        self._langfuse_handler = CallbackHandler(
            secret_key=langfuse_secret_key,
            public_key=langfuse_public_key,
            host=langfuse_host,
        )

        retriever = create_retriever(
            index_name=index_name,
            bucket_name=bucket_name,
            embedding=embedding,
        )
        format_context_chain: Runnable = (
            RunnableLambda(lambda x: x["retrieved_docs"]) | self._format_docs
        )

        prompt: Runnable = (
            RunnableParallel(
                {
                    "retrieved_docs": itemgetter("retrieved_docs"),
                    "question": itemgetter("question"),
                    "context": itemgetter("context"),
                }
            )
            | self._build_prompt
        )
        structured_llm = llm.with_structured_output(CitedAnswer)
        generate_answer_chain: Runnable = prompt | structured_llm

        self._rag_chain: Runnable[str, RagResult] = {
            "retrieved_docs": retriever,
            "question": RunnablePassthrough(),
        } | RunnablePassthrough.assign(context=format_context_chain).assign(
            answer=generate_answer_chain
        ).pick(["retrieved_docs", "answer"]).assign(
            retrieved_docs=(
                lambda x: [self._parse_document(doc) for doc in x["retrieved_docs"]]
            )
        )

    def invoke(self, question: str) -> RagResult:
        return self._rag_chain.invoke(
            question, config={"callbacks": [self._langfuse_handler]}
        )

    def _build_prompt(self, input_dict: dict) -> ChatPromptTemplate:
        docs = input_dict["retrieved_docs"]
        parsed_docs: list[MetadataTypedDocument[DocumentMetadata]] = [
            self._parse_document(doc) for doc in docs
        ]
        image_messages = [
            {
                "type": "image_url",
                "image_url": {
                    "url": self._build_image_data_url(
                        mime_type=doc.metadata.mime_type,
                        image_base64=doc.metadata.base64,
                    ),
                },
            }
            for doc in parsed_docs
            if doc.metadata.modality == "image"
        ]
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "user",
                    [
                        _TEXT_MESSAGE_TEMPLATE,
                        *image_messages,
                    ],
                )
            ]
        )

        return prompt.partial(
            question=input_dict["question"],
            context=input_dict["context"],
        )

    def _parse_document(
        self, doc: LangChainDocument
    ) -> MetadataTypedDocument[DocumentMetadata]:
        modality = doc.metadata.get("modality")
        if modality == "image":
            return MetadataTypedDocument.from_langchain_document(
                doc, ImageDocumentMetadata
            )
        elif modality == "text":
            return MetadataTypedDocument.from_langchain_document(
                doc, TextDocumentMetadata
            )
        else:
            raise ValueError(f"Unsupported modality: {modality}")

    def _build_image_data_url(self, *, mime_type: str, image_base64: str) -> str:
        return f"data:{mime_type};base64,{image_base64}"

    def _format_docs(self, docs: list[LangChainDocument]) -> str:
        formatted = [
            f"Source ID: {i}\nArticle Title: {doc.metadata['title']}\nArticle Snippet: {doc.page_content}"
            for i, doc in enumerate(docs)
        ]
        return "\n\n" + "\n\n".join(formatted)

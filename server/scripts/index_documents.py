
from dotenv import load_dotenv
from langchain_aws import BedrockEmbeddings

from server.rag.ingestion.document_indexer import DocumentIndexer
from server.rag.ingestion.document_preprocessor import DocumentPreprocessor
from server.utils.env import getenv_or_raise

print("Initializing...")

load_dotenv()
PINECONE_INDEX_NAME = getenv_or_raise("PINECONE_INDEX_NAME")
RAG_DOCSTORE_BUCKET_NAME = getenv_or_raise("RAG_DOCSTORE_BUCKET_NAME")

crawling_root_urls = [
    "https://classmethod.jp/services/generative-ai/"
    # クローリング対象を増やす場合はここに追加する
]
preprocessor = DocumentPreprocessor(crawling_root_urls)

embedding = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v2:0", region_name="us-east-1", client=None
)
indexer = DocumentIndexer(
    index_name=PINECONE_INDEX_NAME,
    bucket_name=RAG_DOCSTORE_BUCKET_NAME,
    embedding=embedding,
    refresh=True,
)

print("Initialization completed!")


print("Document ingestion started...")
docs = preprocessor.preprocess()
print("Document ingestion completed!")


print("Indexing started...")
indexer.index(docs)
print("Indexing completed!")

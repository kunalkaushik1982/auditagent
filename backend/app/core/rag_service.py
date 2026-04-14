import logging
import os
from typing import Any, Dict, Optional

from langchain_chroma import Chroma
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.core.ai_clients import (
    get_chat_llm,
    get_chat_model_name,
    get_embedding_model_name,
    get_embedding_provider,
    get_embeddings,
    get_llm_provider,
)
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service for indexing documents and answering questions.

    Uses ChromaDB for vector storage and a config-driven provider selection
    for embeddings and chat.
    """

    def __init__(self):
        try:
            provider = get_embedding_provider()
            model = get_embedding_model_name()
            logger.info(f"Using {provider} embedding model: {model}")
            self.embedding_provider = provider
            self.embedding_model = model
            self.embeddings = get_embeddings()
        except Exception as exc:
            logger.error(f"Failed to initialize embeddings: {exc}")
            self.embeddings = None
            self.embedding_provider = "unknown"
            self.embedding_model = "unknown"

        self.persist_directory = os.path.join(settings.BASE_DIR, "chroma_db")
        os.makedirs(self.persist_directory, exist_ok=True)
        self.collection_name = self._build_collection_name()

    def _build_collection_name(self) -> str:
        safe_model = "".join(
            ch if ch.isalnum() else "_"
            for ch in self.embedding_model.lower()
        ).strip("_")
        return f"audit_documents_{self.embedding_provider}_{safe_model}"

    def index_document(self, session_id: str, file_path: str) -> bool:
        """Index a document into ChromaDB associated with a session_id."""
        if not self.embeddings:
            logger.error("Embeddings not initialized. Cannot index.")
            return False

        try:
            logger.info(f"Indexing document for session {session_id}: {file_path}")

            loader = None
            if file_path.lower().endswith(".pdf"):
                loader = PyPDFLoader(file_path)
            elif file_path.lower().endswith(".docx"):
                loader = Docx2txtLoader(file_path)
            elif file_path.lower().endswith(".txt"):
                loader = TextLoader(file_path, autodetect_encoding=True)

            if not loader:
                logger.warning(f"Unsupported file type for indexing: {file_path}")
                return False

            docs = loader.load()
            if not docs:
                logger.warning("No content loaded from document")
                return False

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
            )
            splits = text_splitter.split_documents(docs)

            for doc in splits:
                doc.metadata["session_id"] = session_id
                doc.metadata["source"] = os.path.basename(file_path)

            vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )

            vectorstore.add_documents(documents=splits)
            logger.info(f"Indexed {len(splits)} chunks for session {session_id}")
            return True

        except Exception as exc:
            logger.error(f"Error indexing document: {exc}", exc_info=True)
            return False

    def is_indexed(self, session_id: str) -> bool:
        """Check if a session is already indexed."""
        try:
            vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )
            results = vectorstore.get(where={"session_id": session_id}, limit=1)
            return len(results["ids"]) > 0
        except Exception as exc:
            logger.error(f"Error checking index status: {exc}")
            return False

    def query_audit(
        self,
        session_id: str,
        question: str,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query the indexed document and lazy-index if needed."""
        if not self.embeddings:
            return {"answer": "Embedding service unavailable.", "sources": []}

        try:
            if not self.is_indexed(session_id):
                if file_path and os.path.exists(file_path):
                    logger.info(f"Lazy indexing document for session {session_id}")
                    if not self.index_document(session_id, file_path):
                        return {"answer": "Failed to index document for analysis.", "sources": []}
                else:
                    return {
                        "answer": "This document has not been indexed and the original file path is missing.",
                        "sources": [],
                    }

            vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )

            retriever = vectorstore.as_retriever(
                search_kwargs={
                    "k": 8,
                    "filter": {"session_id": session_id},
                }
            )

            llm_provider = get_llm_provider()
            llm_model = get_chat_model_name()
            logger.info(f"Using {llm_provider} chat model for RAG: {llm_model}")
            llm = get_chat_llm(temperature=0.3)

            template = """You are an expert AI auditor assistant helping a user understand their audit results.
Use only the following pieces of retrieved context from the audited document to answer the user's question.
If the direct answer is not in the context, check for related headings or implied information.
If you still cannot find the information, say that "Based on the retrieved context, I cannot find information about...".

Keep the answer professional, concise, and helpful.

Context:
{context}

Question: {question}

Answer:"""

            prompt = ChatPromptTemplate.from_template(template)

            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)

            rag_chain_from_docs = (
                RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
                | prompt
                | llm
                | StrOutputParser()
            )

            rag_chain_with_source = RunnableParallel(
                {"context": retriever, "question": RunnablePassthrough()}
            ).assign(answer=rag_chain_from_docs)

            result = rag_chain_with_source.invoke(question)

            response = result["answer"]
            source_docs = result["context"]
            sources = list(set(doc.metadata.get("source", "Document") for doc in source_docs))

            return {
                "answer": response,
                "sources": sources,
            }

        except Exception as exc:
            logger.error(f"Error querying RAG: {exc}", exc_info=True)
            return {
                "answer": f"I encountered an error while analyzing the document: {str(exc)}",
                "sources": [],
            }

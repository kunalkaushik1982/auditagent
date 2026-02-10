
import logging
import os
from typing import List, Dict, Any, Optional
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class RAGService:
    """
    RAG Service for indexing documents and answering questions.
    Uses ChromaDB for vector storage and Ollama/OpenAI for embeddings/LLM.
    """
    
    def __init__(self):
        # Initialize Embeddings
        # We assume Ollama is available for embeddings even if using OpenAI for chat,
        # or we config it based on LLM_PROVIDER.
        # User requested Local Ollama Embeddings.
        
        try:
            self.embeddings = OllamaEmbeddings(
                model=settings.OLLAMA_EMBEDDING_MODEL,
                base_url=settings.OLLAMA_BASE_URL
            )
        except Exception as e:
            logger.error(f"Failed to initialize Ollama Embeddings: {e}")
            self.embeddings = None
        
        # Vector Store Path (Persistent)
        # Store in backend/chroma_db
        self.persist_directory = os.path.join(settings.BASE_DIR, "chroma_db")
        os.makedirs(self.persist_directory, exist_ok=True)
        
    def index_document(self, session_id: str, file_path: str) -> bool:
        """
        Index a document into ChromaDB associated with a session_id.
        """
        if not self.embeddings:
            logger.error("Embeddings not initialized. Cannot index.")
            return False
            
        try:
            logger.info(f"Indexing document for session {session_id}: {file_path}")
            
            # 1. Load Document based on extension
            loader = None
            if file_path.lower().endswith('.pdf'):
                loader = PyPDFLoader(file_path)
            elif file_path.lower().endswith('.docx'):
                loader = Docx2txtLoader(file_path)
            elif file_path.lower().endswith('.txt'):
                loader = TextLoader(file_path)
            
            if not loader:
                logger.warning(f"Unsupported file type for indexing: {file_path}")
                return False
                
            docs = loader.load()
            if not docs:
                logger.warning("No content loaded from document")
                return False
            
            # 2. Split Document
            # Use smaller chunks for better context retrieval
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            splits = text_splitter.split_documents(docs)
            
            # Add metadata (session_id) to each chunk
            for doc in splits:
                doc.metadata["session_id"] = session_id
                doc.metadata["source"] = os.path.basename(file_path)
            
            # 3. Store in Vector DB
            # Use a single collection "audit_docs"
            vectorstore = Chroma(
                collection_name="audit_documents",
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            vectorstore.add_documents(documents=splits)
            logger.info(f"Indexed {len(splits)} chunks for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing document: {e}", exc_info=True)
            return False

    def is_indexed(self, session_id: str) -> bool:
        """
        Check if a session is already indexed.
        """
        try:
            vectorstore = Chroma(
                collection_name="audit_documents",
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            # Use get() with where filter to check existence efficiently
            results = vectorstore.get(where={"session_id": session_id}, limit=1)
            return len(results['ids']) > 0
        except Exception as e:
            logger.error(f"Error checking index status: {e}")
            return False

    def query_audit(self, session_id: str, question: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Query the indexed document. lazy-indexes if needed.
        """
        if not self.embeddings:
            return {"answer": "Embedding service unavailable.", "sources": []}
            
        try:
            # Lazy Indexing Check
            if not self.is_indexed(session_id):
                if file_path and os.path.exists(file_path):
                    logger.info(f"Lazy indexing document for session {session_id}")
                    if not self.index_document(session_id, file_path):
                        return {"answer": "Failed to index document for analysis.", "sources": []}
                else:
                    return {"answer": "This document has not been indexed and the original file path is missing.", "sources": []}

            # 1. Get Vector Store
            vectorstore = Chroma(
                collection_name="audit_documents",
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            # 2. Setup Retriever with Filter
            # Only retrieve chunks matching this session_id
            retriever = vectorstore.as_retriever(
                search_kwargs={
                    "k": 4, 
                    "filter": {"session_id": session_id}
                }
            )
            
            # 3. Initialize LLM
            if settings.LLM_PROVIDER == "ollama":
                llm = ChatOllama(
                    model=settings.OLLAMA_MODEL, 
                    base_url=settings.OLLAMA_BASE_URL,
                    temperature=0.3
                )
            else:
                llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    openai_api_key=settings.OPENAI_API_KEY,
                    temperature=0.3
                )
            
            # 4. RAG Chain
            template = """You are an expert AI auditor assistant helping a user understand their audit results.
            Use only the following pieces of retrieved context from the audited document to answer the user's question.
            If the answer is not in the context, say that you cannot find the information in the document.
            Keep the answer professional, concise, and helpful.
            
            Context:
            {context}
            
            Question: {question}
            
            Answer:"""
            
            prompt = ChatPromptTemplate.from_template(template)
            
            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)
            
            rag_chain = (
                {"context": retriever | format_docs, "question": RunnablePassthrough()}
                | prompt
                | llm
                | StrOutputParser()
            )
            
            # 5. Execute
            response = rag_chain.invoke(question)
            
            # Get sources for UI
            source_docs = retriever.invoke(question)
            sources = list(set([doc.metadata.get("source", "Document") for doc in source_docs]))
            
            return {
                "answer": response,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"Error querying RAG: {e}", exc_info=True)
            return {
                "answer": f"I encountered an error while analyzing the document: {str(e)}", 
                "sources": []
            }

"""
Base agent class for all audit agents.
File: backend/app/agents/base_agent.py

Defines the abstract base class that all specific agents inherit from.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from langchain.schema import Document
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from backend.app.core.config import settings
import docx2txt
import PyPDF2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuditFinding(BaseModel):
    """Pydantic model for a single audit finding"""
    checklist_item: str = Field(description="The checklist requirement being validated")
    finding_type: str = Field(description="Type: compliant, non_compliant, missing, or advisory")
    description: str = Field(description="Detailed description of the finding")
    severity: Optional[str] = Field(default=None, description="Severity: critical, high, medium, low")
    location: Optional[str] = Field(default=None, description="Location in document (section, page)")
    recommendation: Optional[str] = Field(default=None, description="Recommendation to address the finding")


class BaseAuditAgent(ABC):
    """
    Abstract base class for all audit agents.
    
    Each specific agent (SoW Reviewer, Project Plan, etc.) should inherit
    from this class and implement the required methods.
    """
    
    def __init__(self, agent_name: str, agent_type: str):
        """
        Initialize the base agent.
        
        Args:
            agent_name: Human-readable name of the agent
            agent_type: Type identifier (sow_reviewer, project_plan, etc.)
        """
        self.agent_name = agent_name
        self.agent_type = agent_type
        
        # Initialize LangChain LLM
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in environment")
            
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        logger.info(f"Initialized {self.agent_name}")
    
    async def load_document(self, file_path: str) -> Document:
        """
        Load a document (PDF, Word, or text file).
        
        Args:
            file_path: Path to the file (.pdf, .docx, or .txt)
            
        Returns:
            LangChain Document object
        """
        try:
            if file_path.endswith('.pdf'):
                # Extract text from PDF
                text = self._extract_text_from_pdf(file_path)
            elif file_path.endswith('.docx'):
                # Use docx2txt for Word documents (Windows-compatible)
                text = docx2txt.process(file_path)
            else:
                # Plain text file
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            if not text or not text.strip():
                raise ValueError(f"No content loaded from {file_path}")
            
            # Create LangChain Document object
            document = Document(page_content=text, metadata={"source": file_path})
            
            logger.info(f"Loaded document from {file_path}, {len(text)} characters")
            return document
            
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {e}")
            raise
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF file using PyPDF2.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text content
        """
        try:
            text = ""
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                num_pages = len(reader.pages)
                
                logger.info(f"Extracting text from PDF: {num_pages} pages")
                
                for page_num, page in enumerate(reader.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
                    
                    if page_num % 10 == 0:
                        logger.info(f"Processed {page_num}/{num_pages} pages")
            
            if not text.strip():
                raise ValueError("No text could be extracted from PDF")
            
            logger.info(f"Successfully extracted {len(text)} characters from PDF")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {e}")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    async def load_checklist(self, file_path: str) -> List[str]:
        """
        Load and parse checklist from a file.
        
        Args:
            file_path: Path to checklist file (.pdf, .txt, or .docx)
            
        Returns:
            List of checklist items
        """
        try:
            if file_path.endswith('.pdf'):
                # Extract text from PDF
                content = self._extract_text_from_pdf(file_path)
            elif file_path.endswith('.docx'):
                # Use docx2txt directly (Windows-compatible)
                content = docx2txt.process(file_path)
            else:
                # Plain text file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Split by lines and filter empty lines
            checklist_items = [
                line.strip() 
                for line in content.split('\n') 
                if line.strip() and not line.strip().startswith('#')
            ]
            
            logger.info(f"Loaded {len(checklist_items)} checklist items from {file_path}")
            return checklist_items
            
        except Exception as e:
            logger.error(f"Error loading checklist {file_path}: {e}")
            raise
    
    async def validate_item(
        self,
        artifact_content: str,
        checklist_item: str
    ) -> AuditFinding:
        """
        Validate a single checklist item against the artifact using AI.
        
        Args:
            artifact_content: Full content of the artifact document
            checklist_item: Single checklist requirement to validate
            
        Returns:
            AuditFinding object with validation results
        """
        # Create output parser
        parser = PydanticOutputParser(pydantic_object=AuditFinding)
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert document auditor. Your task is to validate whether a document meets a specific requirement from a checklist.

Analyze the document carefully and determine:
1. Is the requirement met? (compliant, non_compliant, missing, or advisory)
2. Where in the document is the relevant information? (section, page number if visible)
3. What is your detailed assessment?
4. What is the severity if non-compliant? (critical, high, medium, low)
5. What recommendations do you have?

Be thorough, specific, and cite evidence from the document.

{format_instructions}"""),
            ("user", """Document Content:
{document}

Checklist Requirement:
{requirement}

Please analyze and provide your audit finding.""")
        ])
        
        # Format the prompt
        formatted_prompt = prompt.format_messages(
            document=artifact_content[:8000],  # Limit to avoid token limits
            requirement=checklist_item,
            format_instructions=parser.get_format_instructions()
        )
        
        # Call LLM
        response = await self.llm.ainvoke(formatted_prompt)
        
        # Parse response
        finding = parser.parse(response.content)
        
        return finding
    
    @abstractmethod
    async def process_artifact(
        self, 
        artifact_path: str, 
        checklist_path: str
    ) -> Dict[str, Any]:
        """
        Process an artifact against a checklist.
        Must be implemented by subclasses.
        """
        pass
    
    def get_agent_info(self) -> Dict[str, str]:
        """Get basic information about this agent"""
        return {
            "name": self.agent_name,
            "type": self.agent_type
        }

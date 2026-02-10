"""
Base agent class for all audit agents.
File: backend/app/agents/base_agent.py

Defines the abstract base class that all specific agents inherit from.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from langchain.schema import Document
from langchain_openai import ChatOpenAI
try:
    from langchain_community.chat_models import ChatOllama
except ImportError:
    pass
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from backend.app.core.config import settings
import docx2txt
import PyPDF2
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuditFinding(BaseModel):
    """Pydantic model for a single audit finding"""
    checklist_item: str = Field(description="The checklist requirement being validated")
    finding_type: str = Field(description="Type: compliant, non_compliant, missing, or advisory")
    description: str = Field(description="Detailed description of the finding")
    severity: Optional[str] = Field(default=None, description="Severity: critical, high, medium, low")
    location: Optional[str] = Field(default=None, description="Location in document (section, page)")
    quote: Optional[str] = Field(default=None, description="Exact quote from the document supporting this finding")
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
        if settings.LLM_PROVIDER == "ollama":
            try:
                logger.info(f"🦙 Using Ollama (model: {settings.OLLAMA_MODEL})")
                self.llm = ChatOllama(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.OLLAMA_MODEL,
                    temperature=0
                )
            except NameError:
                raise ImportError("langchain-community is required for Ollama. Please run: pip install langchain-community")
            except Exception as e:
                logger.error(f"Failed to initialize Ollama: {e}")
                raise
        else:
            # Default to OpenAI
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set in environment")
                
            logger.info("🤖 Using OpenAI (gpt-4o-mini)")
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
            
            logger.info(f"Raw content length from {file_path}: {len(content)}")
            logger.debug(f"Raw content preview: {content[:200]}")
            
            # Split by lines and filter empty lines
            lines = content.split('\n')
            logger.info(f"Split into {len(lines)} lines")
            
            checklist_items = [
                line.strip() 
                for line in lines
                if line.strip() and not line.strip().startswith('#')
            ]
            
            logger.info(f"Loaded {len(checklist_items)} checklist items from {file_path}")
            if len(checklist_items) == 0:
                logger.warning(f"⚠️ No checklist items found! Check file encoding or formatting.")
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
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert {agent_name}. Your task is to validate whether a document meets a specific requirement from a checklist.

Analyze the document carefully and determine:
1. Is the requirement met? (compliant, non_compliant, missing, or advisory)
2. Where in the document is the relevant information? (section, page number if visible)
3. What is your detailed assessment?
4. What is the severity if non-compliant? (critical, high, medium, low)
5. What is the exact quote from the document that serves as evidence? (If applicable)
6. What recommendations do you have?

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
            agent_name=self.agent_name,
            document=artifact_content[:8000],  # Limit to avoid token limits
            requirement=checklist_item,
            format_instructions=parser.get_format_instructions()
        )
        
        # Call LLM
        response = await self.llm.ainvoke(formatted_prompt)
        
        # Parse response
        finding = parser.parse(response.content)
        
        return finding
    
    async def process_artifact(
        self,
        artifact_path: str,
        checklist_path: str
    ) -> Dict[str, Any]:
        """
        Process an artifact against a checklist.
        
        This is the main entry point for the agent. It orchestrates:
        1. Loading the artifact and checklist
        2. Validating each checklist item
        3. Generating a comprehensive report
        
        Args:
            artifact_path: Path to the artifact document
            checklist_path: Path to the checklist file
            
        Returns:
            Dictionary with audit results, findings, and report
        """
        try:
            logger.info(f"Starting {self.agent_name} audit: {artifact_path}")
            
            # Step 1: Load documents
            artifact_doc = await self.load_document(artifact_path)
            checklist_items = await self.load_checklist(checklist_path)
            
            if not checklist_items:
                raise ValueError(f"Checklist is empty or could not be parsed: {checklist_path}. Please check file content and encoding.")
            
            logger.info(f"Processing {len(checklist_items)} checklist items...")
            
            # Step 2: Validate each checklist item
            findings = []
            for idx, item in enumerate(checklist_items, 1):
                logger.info(f"Validating item {idx}/{len(checklist_items)}: {item[:50]}...")
                
                finding = await self.validate_item(
                    artifact_content=artifact_doc.page_content,
                    checklist_item=item
                )
                
                finding_dict = finding.dict()
                # Normalize finding type to lowercase to ensure report generation works
                if finding_dict.get('finding_type'):
                    finding_dict['finding_type'] = finding_dict['finding_type'].lower()
                    
                logger.info(f"Finding for item {idx}: {finding_dict.get('finding_type')}")
                findings.append(finding_dict)
            
            # Step 3: Generate summary statistics
            stats = self._calculate_statistics(findings)
            
            # Step 4: Generate report
            report = self._generate_markdown_report(
                findings=findings,
                stats=stats,
                artifact_path=artifact_path,
                checklist_path=checklist_path
            )
            
            logger.info(f"Audit completed: {stats}")
            
            return {
                "status": "success",
                "agent_type": self.agent_type,
                "findings": findings,
                "statistics": stats,
                "report": report,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing audit: {e}", exc_info=True)
            return {
                "status": "error",
                "agent_type": self.agent_type,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _calculate_statistics(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics from findings"""
        total = len(findings)
        compliant = sum(1 for f in findings if f['finding_type'] == 'compliant')
        non_compliant = sum(1 for f in findings if f['finding_type'] == 'non_compliant')
        missing = sum(1 for f in findings if f['finding_type'] == 'missing')
        advisory = sum(1 for f in findings if f['finding_type'] == 'advisory')
        
        # Count by severity
        critical = sum(1 for f in findings if f.get('severity') == 'critical')
        high = sum(1 for f in findings if f.get('severity') == 'high')
        medium = sum(1 for f in findings if f.get('severity') == 'medium')
        low = sum(1 for f in findings if f.get('severity') == 'low')
        
        compliance_rate = (compliant / total * 100) if total > 0 else 0
        
        return {
            "total_items": total,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "missing": missing,
            "advisory": advisory,
            "compliance_rate": round(compliance_rate, 2),
            "severity": {
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": low
            }
        }
    
    def _generate_markdown_report(
        self,
        findings: List[Dict[str, Any]],
        stats: Dict[str, Any],
        artifact_path: str,
        checklist_path: str
    ) -> str:
        """Generate a markdown audit report"""
        
        report = f"""# Audit Report: {self.agent_name}

**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Artifact**: {artifact_path}  
**Checklist**: {checklist_path}  
**Agent**: {self.agent_name}

---

## Executive Summary

**Compliance Rate**: {stats['compliance_rate']}%

| Category | Count |
|----------|-------|
| ✅ Compliant | {stats['compliant']} |
| ❌ Non-Compliant | {stats['non_compliant']} |
| ⚠️ Missing | {stats['missing']} |
| 📋 Advisory | {stats['advisory']} |
| **Total Items** | **{stats['total_items']}** |

### Severity Breakdown

| Severity | Count |
|----------|-------|
| 🔴 Critical | {stats['severity']['critical']} |
| 🟠 High | {stats['severity']['high']} |
| 🟡 Medium | {stats['severity']['medium']} |
| 🟢 Low | {stats['severity']['low']} |

---

## Detailed Findings

"""
        
        # Group findings by type
        for finding_type in ['non_compliant', 'missing', 'advisory', 'compliant']:
            type_findings = [f for f in findings if f['finding_type'] == finding_type]
            
            if not type_findings:
                continue
            
            type_labels = {
                'compliant': '✅ Compliant Items',
                'non_compliant': '❌ Non-Compliant Items',
                'missing': '⚠️ Missing Items',
                'advisory': '📋 Advisory Items'
            }
            
            report += f"\n### {type_labels[finding_type]}\n\n"
            
            for idx, finding in enumerate(type_findings, 1):
                severity_emoji = {
                    'critical': '🔴',
                    'high': '🟠',
                    'medium': '🟡',
                    'low': '🟢'
                }
                
                severity_str = ""
                if finding.get('severity'):
                    emoji = severity_emoji.get(finding['severity'], '')
                    severity_str = f" {emoji} **{finding['severity'].upper()}**"
                
                report += f"#### {idx}. {finding['checklist_item']}{severity_str}\n\n"
                report += f"**Finding**: {finding['description']}\n\n"
                
                if finding.get('location'):
                    report += f"**Location**: {finding['location']}\n\n"
                
                if finding.get('recommendation'):
                    report += f"**Recommendation**: {finding['recommendation']}\n\n"
                
                report += "---\n\n"
        
        report += f"""
## Conclusion

This audit was performed by the {self.agent_name} using AI-powered document analysis. 
The compliance rate of {stats['compliance_rate']}% indicates the overall alignment of the document with the provided checklist requirements.

**Next Steps**:
1. Address all Critical and High severity findings immediately
2. Review and resolve Non-Compliant and Missing items
3. Consider Advisory recommendations for improvement
4. Re-audit after implementing corrections

---

*Report generated automatically by Delivery Audit Agent*
"""
        
        return report

    def get_agent_info(self) -> Dict[str, str]:
        """Get basic information about this agent"""
        return {
            "name": self.agent_name,
            "type": self.agent_type
        }

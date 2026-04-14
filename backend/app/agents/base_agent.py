"""
Base agent class for all audit agents.
File: backend/app/agents/base_agent.py

Defines the abstract base class that all specific agents inherit from.
"""

from abc import ABC
from datetime import datetime
from typing import Any, Dict, List, Optional

import PyPDF2
import docx2txt
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from backend.app.core.ai_clients import (
    get_chat_llm,
    get_chat_model_name,
    get_llm_provider,
)

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuditFinding(BaseModel):
    """Pydantic model for a single audit finding."""

    checklist_item: str = Field(description="The checklist requirement being validated")
    finding_type: str = Field(description="Type: compliant, non_compliant, missing, or advisory")
    description: str = Field(description="Detailed description of the finding")
    severity: Optional[str] = Field(default=None, description="Severity: critical, high, medium, low")
    location: Optional[str] = Field(default=None, description="Location in document (section, page)")
    quote: Optional[str] = Field(
        default=None,
        description="Exact quote from the document supporting this finding",
    )
    recommendation: Optional[str] = Field(
        default=None,
        description="Recommendation to address the finding",
    )


class BaseAuditAgent(ABC):
    """
    Abstract base class for all audit agents.

    Each specific agent should inherit from this class and implement the
    required methods.
    """

    def __init__(self, agent_name: str, agent_type: str):
        self.agent_name = agent_name
        self.agent_type = agent_type

        provider = get_llm_provider()
        model = get_chat_model_name()
        logger.info(f"Using {provider} chat model: {model}")
        self.llm = get_chat_llm(temperature=0)

        logger.info(f"Initialized {self.agent_name}")

    async def load_document(self, file_path: str) -> Document:
        """Load a document (PDF, Word, or text file)."""
        try:
            if file_path.endswith(".pdf"):
                text = self._extract_text_from_pdf(file_path)
            elif file_path.endswith(".docx"):
                text = docx2txt.process(file_path)
            else:
                with open(file_path, "r", encoding="utf-8") as handle:
                    text = handle.read()

            if not text or not text.strip():
                raise ValueError(f"No content loaded from {file_path}")

            document = Document(page_content=text, metadata={"source": file_path})
            logger.info(f"Loaded document from {file_path}, {len(text)} characters")
            return document

        except Exception as exc:
            logger.error(f"Error loading document {file_path}: {exc}")
            raise

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file using PyPDF2."""
        try:
            text = ""
            with open(file_path, "rb") as handle:
                reader = PyPDF2.PdfReader(handle)
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

        except Exception as exc:
            logger.error(f"Error extracting text from PDF {file_path}: {exc}")
            raise ValueError(f"Failed to extract text from PDF: {str(exc)}")

    async def load_checklist(self, file_path: str) -> List[str]:
        """Load and parse checklist from a file."""
        try:
            if file_path.endswith(".pdf"):
                content = self._extract_text_from_pdf(file_path)
            elif file_path.endswith(".docx"):
                content = docx2txt.process(file_path)
            else:
                with open(file_path, "r", encoding="utf-8") as handle:
                    content = handle.read()

            logger.info(f"Raw content length from {file_path}: {len(content)}")
            logger.debug(f"Raw content preview: {content[:200]}")

            lines = content.split("\n")
            logger.info(f"Split into {len(lines)} lines")

            checklist_items = [
                line.strip()
                for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]

            logger.info(f"Loaded {len(checklist_items)} checklist items from {file_path}")
            if len(checklist_items) == 0:
                logger.warning("No checklist items found. Check file encoding or formatting.")
            return checklist_items

        except Exception as exc:
            logger.error(f"Error loading checklist {file_path}: {exc}")
            raise

    async def validate_item(self, artifact_content: str, checklist_item: str) -> AuditFinding:
        """Validate a single checklist item against the artifact using AI."""
        parser = PydanticOutputParser(pydantic_object=AuditFinding)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert {agent_name}. Your task is to validate whether a document meets a specific requirement from a checklist.

Analyze the document carefully and determine:
1. Is the requirement met? (compliant, non_compliant, missing, or advisory)
2. Where in the document is the relevant information? (section, page number if visible)
3. What is your detailed assessment?
4. What is the severity if non-compliant? (critical, high, medium, low)
5. What is the exact quote from the document that serves as evidence? (If applicable)
6. What recommendations do you have?

Be thorough, specific, and cite evidence from the document.

{format_instructions}""",
                ),
                (
                    "user",
                    """Document Content:
{document}

Checklist Requirement:
{requirement}

Please analyze and provide your audit finding.""",
                ),
            ]
        )

        formatted_prompt = prompt.format_messages(
            agent_name=self.agent_name,
            document=artifact_content[:8000],
            requirement=checklist_item,
            format_instructions=parser.get_format_instructions(),
        )

        response = await self.llm.ainvoke(formatted_prompt)
        finding = parser.parse(response.content)
        return finding

    async def process_artifact(self, artifact_path: str, checklist_path: str) -> Dict[str, Any]:
        """
        Process an artifact against a checklist.

        Orchestrates document loading, validation, and report generation.
        """
        try:
            logger.info(f"Starting {self.agent_name} audit: {artifact_path}")

            artifact_doc = await self.load_document(artifact_path)
            checklist_items = await self.load_checklist(checklist_path)

            if not checklist_items:
                raise ValueError(
                    f"Checklist is empty or could not be parsed: {checklist_path}. "
                    "Please check file content and encoding."
                )

            logger.info(f"Processing {len(checklist_items)} checklist items...")

            findings = []
            for idx, item in enumerate(checklist_items, 1):
                logger.info(f"Validating item {idx}/{len(checklist_items)}: {item[:50]}...")

                finding = await self.validate_item(
                    artifact_content=artifact_doc.page_content,
                    checklist_item=item,
                )

                finding_dict = finding.model_dump()
                if finding_dict.get("finding_type"):
                    finding_dict["finding_type"] = finding_dict["finding_type"].lower()

                logger.info(f"Finding for item {idx}: {finding_dict.get('finding_type')}")
                findings.append(finding_dict)

            stats = self._calculate_statistics(findings)
            report = self._generate_markdown_report(
                findings=findings,
                stats=stats,
                artifact_path=artifact_path,
                checklist_path=checklist_path,
            )

            logger.info(f"Audit completed: {stats}")

            return {
                "status": "success",
                "agent_type": self.agent_type,
                "findings": findings,
                "statistics": stats,
                "report": report,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as exc:
            logger.error(f"Error processing audit: {exc}", exc_info=True)
            return {
                "status": "error",
                "agent_type": self.agent_type,
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _calculate_statistics(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics from findings."""
        total = len(findings)
        compliant = sum(1 for finding in findings if finding["finding_type"] == "compliant")
        non_compliant = sum(1 for finding in findings if finding["finding_type"] == "non_compliant")
        missing = sum(1 for finding in findings if finding["finding_type"] == "missing")
        advisory = sum(1 for finding in findings if finding["finding_type"] == "advisory")

        critical = sum(1 for finding in findings if finding.get("severity") == "critical")
        high = sum(1 for finding in findings if finding.get("severity") == "high")
        medium = sum(1 for finding in findings if finding.get("severity") == "medium")
        low = sum(1 for finding in findings if finding.get("severity") == "low")

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
                "low": low,
            },
        }

    def _generate_markdown_report(
        self,
        findings: List[Dict[str, Any]],
        stats: Dict[str, Any],
        artifact_path: str,
        checklist_path: str,
    ) -> str:
        """Generate a markdown audit report."""
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
| Compliant | {stats['compliant']} |
| Non-Compliant | {stats['non_compliant']} |
| Missing | {stats['missing']} |
| Advisory | {stats['advisory']} |
| **Total Items** | **{stats['total_items']}** |

### Severity Breakdown

| Severity | Count |
|----------|-------|
| Critical | {stats['severity']['critical']} |
| High | {stats['severity']['high']} |
| Medium | {stats['severity']['medium']} |
| Low | {stats['severity']['low']} |

---

## Detailed Findings

"""

        for finding_type in ["non_compliant", "missing", "advisory", "compliant"]:
            type_findings = [finding for finding in findings if finding["finding_type"] == finding_type]

            if not type_findings:
                continue

            type_labels = {
                "compliant": "Compliant Items",
                "non_compliant": "Non-Compliant Items",
                "missing": "Missing Items",
                "advisory": "Advisory Items",
            }

            report += f"\n### {type_labels[finding_type]}\n\n"

            for idx, finding in enumerate(type_findings, 1):
                severity_str = ""
                if finding.get("severity"):
                    severity_str = f" **{finding['severity'].upper()}**"

                report += f"#### {idx}. {finding['checklist_item']}{severity_str}\n\n"
                report += f"**Finding**: {finding['description']}\n\n"

                if finding.get("location"):
                    report += f"**Location**: {finding['location']}\n\n"

                if finding.get("recommendation"):
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
        """Get basic information about this agent."""
        return {
            "name": self.agent_name,
            "type": self.agent_type,
        }

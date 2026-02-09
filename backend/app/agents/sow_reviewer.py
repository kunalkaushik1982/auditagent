"""
SoW Reviewer Agent implementation.
File: backend/app/agents/sow_reviewer.py

Agent for reviewing Statement of Work documents.
"""

from typing import Dict, Any, List
import json
from datetime import datetime
from .base_agent import BaseAuditAgent, AuditFinding
import logging

logger = logging.getLogger(__name__)


class SoWReviewerAgent(BaseAuditAgent):
    """Agent specialized in reviewing Statement of Work documents"""
    
    def __init__(self):
        super().__init__(
            agent_name="SoW Reviewer Agent",
            agent_type="sow_reviewer"
        )
    
    async def process_artifact(
        self,
        artifact_path: str,
        checklist_path: str
    ) -> Dict[str, Any]:
        """
        Process SoW document against checklist.
        
        This is the main entry point for the agent. It orchestrates:
        1. Loading the artifact and checklist
        2. Validating each checklist item
        3. Generating a comprehensive report
        
        Args:
            artifact_path: Path to the SoW document (.docx)
            checklist_path: Path to the checklist file
            
        Returns:
            Dictionary with audit results, findings, and report
        """
        try:
            logger.info(f"Starting SoW audit: {artifact_path}")
            
            # Step 1: Load documents
            artifact_doc = await self.load_document(artifact_path)
            checklist_items = await self.load_checklist(checklist_path)
            
            logger.info(f"Processing {len(checklist_items)} checklist items...")
            
            # Step 2: Validate each checklist item
            findings = []
            for idx, item in enumerate(checklist_items, 1):
                logger.info(f"Validating item {idx}/{len(checklist_items)}: {item[:50]}...")
                
                finding = await self.validate_item(
                    artifact_content=artifact_doc.page_content,
                    checklist_item=item
                )
                
                findings.append(finding.dict())
            
            # Step 3: Generate summary statistics
            stats = self._calculate_statistics(findings)
            
            # Step 4: Generate report
            report = self._generate_markdown_report(
                findings=findings,
                stats=stats,
                artifact_path=artifact_path,
                checklist_path=checklist_path
            )
            
            logger.info(f"SoW audit completed: {stats}")
            
            return {
                "status": "success",
                "agent_type": self.agent_type,
                "findings": findings,
                "statistics": stats,
                "report": report,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing SoW audit: {e}", exc_info=True)
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
        
        report = f"""# Statement of Work (SoW) Audit Report

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
The compliance rate of {stats['compliance_rate']}% indicates the overall alignment of the SoW with the provided checklist requirements.

**Next Steps**:
1. Address all Critical and High severity findings immediately
2. Review and resolve Non-Compliant and Missing items
3. Consider Advisory recommendations for improvement
4. Re-audit after implementing corrections

---

*Report generated automatically by Delivery Audit Agent*
"""
        
        return report

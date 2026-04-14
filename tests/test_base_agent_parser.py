from langchain_core.output_parsers.pydantic import PydanticOutputParser

from backend.app.agents.base_agent import AuditFinding


def test_audit_finding_is_compatible_with_langchain_pydantic_parser():
    parser = PydanticOutputParser(pydantic_object=AuditFinding)

    assert parser.pydantic_object is AuditFinding

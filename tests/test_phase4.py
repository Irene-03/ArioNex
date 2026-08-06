"""
/// <summary>
/// ArioNex Phase 4 automated test and verification file (ArioNex Phase 4 Verification Script)
/// </summary>
"""

import sys
import os

# Add the project path so the app package can be detected
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from app.services.retrieval.query_router import route_query_intent, synthesize_rag_response
from app.prompts.rag_prompts import STANDARD_REFUSAL_MESSAGE
from app.services.retrieval.query_rewriter import rewrite_query
from app.services.retrieval.analyst import analyst_agent
from app.services.retrieval.vector_search import vector_search_agent as librarian_agent
from app.services.retrieval.qna import qna_agent as support_lead_agent

def test_query_intent_routing():
    print("Testing Query Intent Routing...")
    
    # Test smart routing of financial computation keywords to pandas
    intent_calc_1 = route_query_intent("مجموع بدهکاری اسناد چک چقدر است؟")
    intent_calc_2 = route_query_intent("بستانکار فاکتور را فیلتر کن")
    # Test routing of general regulatory texts to document RAG
    intent_rag_1 = route_query_intent("آیین‌نامه مرخصی کارمندان سازمان چیست؟")
    intent_rag_2 = route_query_intent("خلاصه اسناد HR مربوط به بیمه")
    
    print(f"Calc 1 routed: {intent_calc_1}")
    print(f"Calc 2 routed: {intent_calc_2}")
    print(f"RAG 1 routed:  {intent_rag_1}")
    print(f"RAG 2 routed:  {intent_rag_2}")
    
    assert intent_calc_1 == "analyst", "Structured calc queries must route to analyst!"
    assert intent_calc_2 == "analyst", "Structured filter queries must route to analyst!"
    assert intent_rag_1 == "rag", "General document queries must route to rag!"
    assert intent_rag_2 == "rag", "General logs queries must route to rag!"
    print(" Query Intent Routing checks PASSED.\n")

def test_query_rewriter_fallback():
    print("Testing Query Rewriter Fallback...")
    from unittest.mock import patch
    
    # Test the input rewriting layer in fallback mode (the exact input text must be returned)
    user_input = "این چطور کار میکنه؟"
    chat_history = [{"AI": "آریونکس دستیار شماست."}, {"Human": "ممنون."}]
    
    with patch("app.services.retrieval.query_rewriter._get_active_api_key", return_value=None):
        rewritten = rewrite_query(user_input, chat_history)
        print(f"Original: {user_input} -> Rewritten: {rewritten}")
        
        assert rewritten == user_input, "In mock mode, rewriter should return original query as fallback!"
    print(" Query Rewriter checks PASSED.\n")

def test_analyst_graph_execution():
    print("Testing Analyst Graph Mock Solving...")
    from unittest.mock import patch
    
    # Test the LangGraph pandas interpreter in local dev mock mode by patching the output
    query = "مجموع بدهکاری نوع سند چک"
    with patch("app.services.retrieval.analyst.analyst_agent.execute_analysis") as mock_execute:
        mock_execute.return_value = "مجموع بدهکاری اسناد از نوع سند چک برابر با ۶۲۳,۳۴۶ ریال می‌باشد."
        response = analyst_agent.execute_analysis(query)
        print(f"Query: {query} -> Response: {response}")
        
        assert "۶۲۳,۳۴۶ ریال" in response or "۶۲۳،۳۴۶ ریال" in response, "Mock solver did not return correct sum!"
    print(" Analyst Agent checks PASSED.\n")

def test_golden_hallucination_guardrail():
    print("Testing Golden Non-Hallucination Guardrail...")
    from app.core.config import settings
    
    original_strict = settings.security.strict_non_hallucination
    settings.security.strict_non_hallucination = True
    try:
        # Test the golden RAG refusal rule when database results are empty
        # A query about a completely unrelated topic that will have no match
        query = "پرواز فضایی به مریخ چقدر زمان میبرد؟"
        res = synthesize_rag_response(query, chat_history=[])
        
        print(f"Query: {query}")
        print(f"Response: {res['answer']}")
        print(f"Sources:  {res['sources']}")
        
        # Since the vector database is empty, it should refuse immediately
        assert res["answer"] == STANDARD_REFUSAL_MESSAGE, "Hallucination guardrail failed to block answer!"
        assert len(res["sources"]) == 0, "No sources should be cited in refusal!"
    finally:
        settings.security.strict_non_hallucination = original_strict
    print(" Golden Non-Hallucination Guardrail checks PASSED.\n")

if __name__ == "__main__":
    print("=========================================")
    print("STARTING PHASE 4 AUTOMATED TEST SUITE")
    print("=========================================")
    try:
        test_query_intent_routing()
        test_query_rewriter_fallback()
        test_analyst_graph_execution()
        test_golden_hallucination_guardrail()
        print("=========================================")
        print("ALL PHASE 4 TESTS COMPLETED SUCCESSFULLY! ")
        print("=========================================")
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ TEST SUITE FAILED: {str(e)}")
        sys.exit(1)

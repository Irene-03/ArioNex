"""
Analyst Agent (LangGraph Excel/CSV agent) improvement tests.

Covers: typed tools + DuckDB query engine, read-only SQL guard, Jalali date
enrichment, schema context, graph caching, loop detection, nudge-to-tool
behavior, recursion-limit enforcement, and single-final streaming.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

import pandas as pd
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

import app.services.retrieval.analyst as analyst_mod
from app.services.retrieval.analyst import (
    AnalystAgent,
    _enrich_jalali_dates,
    _is_readonly_sql,
    _build_df_context,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "Date": ["1402/12/01", "1402/12/15", "1402/11/01"],
        "debtor": ["ali", "reza", "ali"],
        "credit": [1000, 2000, 500],
        "debit": [300, 0, 100],
    })


@pytest.fixture
def tools_dict(sample_df):
    agent = AnalystAgent()
    enriched = _enrich_jalali_dates(sample_df)
    return {t.name: t for t in agent.get_tools(enriched)}, enriched


class _FakeModel(BaseChatModel):
    """Minimal chat model to exercise the graph without a real provider."""

    mode: str = "doubtful"
    call_count: int = 0

    @property
    def _llm_type(self):
        return "fake"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.call_count += 1
        if self.mode == "good":
            if self.call_count == 1:
                return ChatResult(generations=[ChatGeneration(message=AIMessage(
                    content="", tool_calls=[{"name": "column_sum", "args": {"column": "credit"}, "id": "c1"}],
                ))])
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content="Total credit = 3500"))])
        if self.mode == "loop":
            return ChatResult(generations=[ChatGeneration(message=AIMessage(
                content="", tool_calls=[{"name": "column_sum", "args": {"column": "NOPE"}, "id": "c1"}],
            ))])
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="DOUBTFUL ANSWER: not found."))])


def _patched(tmp_path, monkeypatch, mode):
    csv_path = tmp_path / "data.csv"
    pd.DataFrame({
        "Date": ["1402/12/01", "1402/12/15"],
        "debtor": ["a", "b"],
        "credit": [1000, 2500],
    }).to_csv(csv_path, index=False)
    fake = _FakeModel(mode=mode)
    monkeypatch.setattr(analyst_mod, "get_llm", lambda **kw: fake)
    monkeypatch.setattr(analyst_mod, "_graph_cache", {})
    monkeypatch.setattr(analyst_mod, "_hitl_sessions", {})
    return csv_path, fake


# ---------- Jalali enrichment ----------
def test_jalali_enrichment(sample_df):
    out = _enrich_jalali_dates(sample_df)
    assert "_Date_jalali_month" in out.columns
    assert out["_Date_jalali_month"].tolist() == ["12", "12", "11"]
    assert "_Date_jalali_year" in out.columns


# ---------- read-only SQL guard ----------
def test_readonly_sql_guard():
    assert _is_readonly_sql("select * from df") is True
    assert _is_readonly_sql("SELECT 1") is True
    assert _is_readonly_sql("with x as (select 1) select * from x") is True
    assert _is_readonly_sql("select * from df; -- drop") is True
    assert _is_readonly_sql("drop table df") is False
    assert _is_readonly_sql("insert into df values (1)") is False


# ---------- tools ----------
def test_column_sum_tool(tools_dict):
    tools, _ = tools_dict
    out = tools["column_sum"].invoke({"column": "credit"})
    assert "3500" in out


def test_column_sum_missing_column(tools_dict):
    tools, _ = tools_dict
    out = tools["column_sum"].invoke({"column": "NOPE"})
    assert "ERROR" in out and "credit" in out


def test_groupby_tool(tools_dict):
    tools, _ = tools_dict
    out = tools["groupby_aggregate"].invoke({"group_col": "debtor", "agg_col": "credit", "agg_func": "sum"})
    assert "1500" in out  # ali


def test_filter_tool(tools_dict):
    tools, _ = tools_dict
    out = tools["filter_rows"].invoke({"col": "credit", "op": ">", "value": "500"})
    assert "1000" in out and "2000" in out


def test_filter_in_uses_jalali_month(tools_dict):
    tools, _ = tools_dict
    out = tools["filter_rows"].invoke({"col": "_Date_jalali_month", "op": "in", "value": "#12#"})
    assert "2000" in out


def test_query_data_tool(tools_dict):
    tools, _ = tools_dict
    out = tools["query_data"].invoke({"sql": "SELECT SUM(credit) AS c FROM df"})
    assert "3500" in out


def test_query_data_rejects_write(tools_dict):
    tools, _ = tools_dict
    out = tools["query_data"].invoke({"sql": "DROP TABLE df"})
    assert "ERROR" in out


# ---------- schema context ----------
def test_df_context_builds(tools_dict):
    _, enriched = tools_dict
    ctx = _build_df_context(enriched)
    assert "credit" in ctx and "_Date_jalali_month" in ctx and "Total rows" in ctx


# ---------- graph behavior (mock LLM) ----------
def test_graph_good_path(tmp_path, monkeypatch):
    csv_path, fake = _patched(tmp_path, monkeypatch, "good")
    agent = AnalystAgent()
    out = agent.execute_analysis("مجموع", custom_file_path=str(csv_path))
    assert "3500" in out


def test_graph_doubtful_nudges_then_ends(tmp_path, monkeypatch):
    csv_path, fake = _patched(tmp_path, monkeypatch, "doubtful")
    agent = AnalystAgent()
    out = agent.execute_analysis("مجموع", custom_file_path=str(csv_path))
    assert "DOUBTFUL" in out
    # initial call + 2 nudges == 3 total model calls
    assert fake.call_count == 3


def test_stream_emits_single_final(tmp_path, monkeypatch):
    csv_path, fake = _patched(tmp_path, monkeypatch, "doubtful")
    agent = AnalystAgent()
    finals = [s for s in agent.execute_analysis_stream("مجموع", custom_file_path=str(csv_path)) if s["type"] == "final"]
    assert len(finals) == 1


def test_recursion_limit_enforced(tmp_path, monkeypatch):
    csv_path, fake = _patched(tmp_path, monkeypatch, "loop")
    agent = AnalystAgent()
    out = agent.execute_analysis("چک", custom_file_path=str(csv_path))
    assert "DOUBTFUL" in out
    # loop terminated instead of running forever
    assert fake.call_count < 30


# ---------- human-in-the-loop (interrupt/resume) ----------
def test_hitl_start_pauses_for_approval(tmp_path, monkeypatch):
    csv_path, fake = _patched(tmp_path, monkeypatch, "good")
    agent = AnalystAgent()
    res = agent.start_hitl("مجموع", custom_file_path=str(csv_path))
    assert res["status"] == "awaiting_approval"
    assert res["thread_id"]
    assert res["payload"]["type"] == "analyst_answer_approval"
    assert "3500" in res["payload"]["answer"]


def test_hitl_resume_approve_completes(tmp_path, monkeypatch):
    csv_path, fake = _patched(tmp_path, monkeypatch, "good")
    agent = AnalystAgent()
    res = agent.start_hitl("مجموع", custom_file_path=str(csv_path))
    assert res["status"] == "awaiting_approval"
    out = agent.resume_hitl(res["thread_id"], {"approved": True})
    assert out["status"] == "completed"
    assert "3500" in out["answer"]


def test_hitl_resume_reject_reruns_agent(tmp_path, monkeypatch):
    csv_path, fake = _patched(tmp_path, monkeypatch, "good")
    agent = AnalystAgent()
    res = agent.start_hitl("مجموع", custom_file_path=str(csv_path))
    assert res["status"] == "awaiting_approval"
    calls_after_start = fake.call_count
    # reject with feedback -> agent re-runs, then pauses again for approval
    out = agent.resume_hitl(res["thread_id"], {"approved": False, "feedback": "عدد اشتباه است"})
    assert out["status"] == "awaiting_approval"
    assert fake.call_count > calls_after_start
    # second approval finishes
    out2 = agent.resume_hitl(res["thread_id"], {"approved": True})
    assert out2["status"] == "completed"


def test_hitl_unknown_thread_errors(tmp_path, monkeypatch):
    csv_path, fake = _patched(tmp_path, monkeypatch, "good")
    agent = AnalystAgent()
    out = agent.resume_hitl("nope", {"approved": True})
    assert out["status"] == "error"


def test_stream_emits_approval_event_then_final(tmp_path, monkeypatch):
    csv_path, fake = _patched(tmp_path, monkeypatch, "doubtful")
    agent = AnalystAgent()
    types = [s["type"] for s in agent.execute_analysis_stream("مجموع", custom_file_path=str(csv_path))]
    assert "approval" in types
    assert types.count("final") == 1
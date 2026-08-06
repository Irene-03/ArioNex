"""
/// <summary>
/// Computational agent for structured and financial data - Analyst (The Analyst RAG Data Agent)
/// </summary>
/// <remarks>
/// Inspired by the LangGraph demo, this module loads accounting and transaction data as a DataFrame
/// and, using a StateGraph chain and typed tools (filtering, column sum, groupby, and a read-only
/// DuckDB SQL engine), answers statistical and accounting questions semantically. If answering fails,
/// it responds using the "DOUBTFUL ANSWER" pattern and states the reason.
/// </remarks>
"""

import os
import re
import json
import uuid
import operator
import logging
from typing import List, Dict, Any, Optional, TypedDict, Annotated, Literal, Generator
import pandas as pd
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, END, add_messages
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.llm_factory import get_llm
from app.prompts.analyst_prompts import get_analyst_system_prompt

logger = logging.getLogger("arionex.analyst")

# Maximum number of identical tool-call repetitions before we force-stop the loop
MAX_REPEATED_TOOL_CALLS = 3

# Maximum rows returned to the model from query tools
MAX_QUERY_ROWS = 50

# How many times we nudge the model to actually use a tool before giving up
MAX_RUNTIME_NUDGES = 2

# Graph recursion limit (must be top-level in the config, NOT inside configurable)
ANALYST_RECURSION_LIMIT = 15

# Larger token budget for the analyst (reasoning models truncate tool calls at 1024)
ANALYST_MAX_TOKENS = 2048

# Maximum number of compiled graphs kept in the module-level cache
GRAPH_CACHE_MAX = 16

# Persian runtime guidance injected when the model answers without calling any tool.
RUNTIME_TOOL_NUDGE = (
    "شما هنوز از هیچ ابزار تحلیلی (مانند query_data یا column_sum) برای بررسی داده‌ها "
    "استفاده نکرده‌اید و صرفاً بر اساس دانش عمومی پاسخ داده‌اید. لطفاً قبل از پاسخ نهایی حتماً "
    "با یک ابزار، داده‌ها را از DataFrame مورد نظر بازیابی کنید و پاسخ را فقط بر اساس نتیجه‌ی ابزار بدهید."
)

# Typed tool inputs
class AnalyzeDfInput(BaseModel):
    """Show a preview of the DataFrame."""
    limit: int = Field(default=3, ge=1, le=20, description="How many rows to show (default 3).")

class ColumnSumInput(BaseModel):
    """Compute the sum of a numeric column."""
    column: str = Field(description="Column name to sum.")

class GroupbyAggregateInput(BaseModel):
    """Group by a column and aggregate a numeric column."""
    group_col: str = Field(description="Column to group by (e.g. month or product).")
    agg_col: str = Field(description="Numeric column to aggregate.")
    agg_func: Literal["sum", "mean", "count", "min", "max"] = Field(
        description="Aggregation function: sum / mean / count / min / max."
    )

class FilterRowsInput(BaseModel):
    """Filter rows by a condition on a column."""
    col: str = Field(description="Column the condition applies to.")
    op: Literal["==", ">", "<", ">=", "<=", "!=", "in"] = Field(
        description="Comparison operator: == / > / < / >= / <= / != / in"
    )
    value: str = Field(
        description="Condition value; for the 'in' operator pass values joined with '#' (e.g. \"#1402#1403#\")."
    )

class QueryDataInput(BaseModel):
    """Run a read-only SQL query against the data."""
    sql: str = Field(description="A valid SELECT statement against the table 'df'.")

# Module-level graph cache and shared checkpointer
_graph_cache: Dict[str, Any] = {}
_chkdpt_memory = MemorySaver()

_SQL_DISALLOWED_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|copy|call|set|pragma|load|install|replace|truncate|vacuum)\b",
    re.IGNORECASE,
)
_SQL_COMMENT_STRIP = re.compile(r"--.*$|/\*.*?\*/", re.MULTILINE | re.DOTALL)


def _is_readonly_sql(sql: str) -> bool:
    """Allow only read-only SELECT / WITH / EXPLAIN queries."""
    stripped = _SQL_COMMENT_STRIP.sub("", sql).strip()
    lowered = stripped.lower()
    if not lowered.startswith(("select", "with", "explain")):
        return False
    if _SQL_DISALLOWED_KEYWORDS.search(lowered):
        return False
    return True


def _coerce_value(series: pd.Series, value: str):
    """Try to coerce a string value to the series dtype for comparisons; None means string-compare."""
    if pd.api.types.is_numeric_dtype(series):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    return None


def _df_cache_key(file_id: int, custom_file_path: str, df: pd.DataFrame) -> str:
    """Unique cache key for the compiled graph based on the data source."""
    if custom_file_path:
        try:
            stat = os.stat(custom_file_path)
            return f"path:{custom_file_path}:{stat.st_mtime_ns}:{stat.st_size}"
        except OSError:
            return f"path:{custom_file_path}"
    return f"file_id:{file_id}:rows:{len(df)}"


def _format_result(res_df: pd.DataFrame, max_rows: int = MAX_QUERY_ROWS) -> str:
    """Render a result DataFrame to a bounded string."""
    if res_df is None or len(res_df) == 0:
        return "Query returned no rows."
    truncated = res_df.head(max_rows)
    cell_str = truncated.astype(str).copy()
    for col in cell_str.columns:
        cell_str[col] = cell_str[col].str.slice(0, 60)
    body = cell_str.to_string(index=False)
    if len(res_df) > max_rows:
        body += f"\n... ({len(res_df) - max_rows} more rows omitted)"
    return body


def _build_df_context(df: pd.DataFrame) -> str:
    """Build a schema description injected at runtime (prompt template files are untouched)."""
    lines = [
        "== DataFrame information (auxiliary context for using the tools) ==",
        f"Total rows: {len(df)}",
        "Columns (name | dtype | missing | sample values):",
    ]
    for col in df.columns:
        dtype = str(df[col].dtype)
        n_missing = int(df[col].isna().sum())
        non_null = df[col].dropna()
        samples = []
        if len(non_null) > 0:
            try:
                samples = list(non_null.astype(str).unique()[:6])
            except Exception:
                samples = []
        sample_str = ", ".join(samples) if samples else "-"
        lines.append(f"- {col} | {dtype} | missing:{n_missing} | [{sample_str}]")
    if len(df) > 0:
        num_cols = df.select_dtypes(include="number").columns.tolist()
        if num_cols:
            lines.append("Numeric stats (min / max / mean):")
            for col in num_cols:
                try:
                    lines.append(f"- {col}: min={df[col].min()} max={df[col].max()} mean={df[col].mean():.2f}")
                except Exception:
                    pass
    lines.append("=" * 40)
    return "\n".join(lines)


def _enrich_jalali_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    If any column holds Jalali dates in YYYY/MM/DD format (e.g. 1402/12/15),
    add helper columns _{col}_jalali_year and _{col}_jalali_month so that
    month-based filtering / grouping works reliably.
    """
    df_out = df.copy()
    for col in df_out.columns:
        if col.startswith("_"):
            continue
        sample = df_out[col].dropna().astype(str).head(20)
        if len(sample) == 0:
            continue
        if sample.str.match(r"^\d{4}/\d{2}/\d{2}$").all():
            parts = df_out[col].dropna().astype(str).str.split("/")
            df_out[f"_{col}_jalali_year"] = parts.str[0]
            df_out[f"_{col}_jalali_month"] = parts.str[1]
    return df_out


# 1. Define agent state structure
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    nudges: Annotated[int, operator.add]

# 2. Main class implementing the data analyst agent
class AnalystAgent:
    """
    /// <summary>
    /// Data analyst agent class using Pandas and LangGraph
    /// </summary>
    """
    def __init__(self):
        self.is_enabled = settings.services.structured_data_analytics

    def _resolve_dataframe(self, file_id: int = None, custom_file_path: str = None) -> pd.DataFrame:
        """
        /// <summary>
        /// Load a DataFrame from the user's actual file or the latest structured file in the database
        /// </summary>
        /// <param name="file_id">Structured file ID (optional)</param>
        /// <param name="custom_file_path">Direct file path (optional — higher priority)</param>
        /// <returns>The loaded DataFrame, or None if unsuccessful</returns>
        """
        from app.services.workers.structured_processor import structured_processor
        from app.core.database import get_db_connection

        # Priority 1: Direct physical path
        if custom_file_path and os.path.exists(custom_file_path):
            try:
                df = pd.read_csv(custom_file_path)
                df = _enrich_jalali_dates(df)
                logger.info(f"Analyst Agent loaded DataFrame from custom_file_path: {custom_file_path}")
                return df
            except Exception as e:
                logger.error(f"Failed to load custom CSV: {str(e)}")

        # Priority 2: Specific file_id — fetch from MinIO/Local
        if file_id:
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT filename FROM documents WHERE id = %s AND file_type = 'csv'",
                        (file_id,)
                    )
                    row = cur.fetchone()
                conn.close()
                if row:
                    filename = row[0]
                    local_path = structured_processor.get_local_path_for_analysis(file_id, filename)
                    df = pd.read_csv(local_path)
                    df = _enrich_jalali_dates(df)
                    logger.info(f"Analyst Agent loaded DataFrame for file_id={file_id}: {filename} ({len(df)} rows)")
                    return df
                else:
                    logger.warning(f"No CSV document found with file_id={file_id} in documents table.")
            except Exception as e:
                logger.error(f"Failed to resolve file_id={file_id} to DataFrame: {str(e)}")

        # Priority 3: Latest structured file uploaded to the database
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, filename FROM documents 
                    WHERE file_type = 'csv' 
                      AND id IN (SELECT DISTINCT file_id FROM pg_supervisor)
                    ORDER BY created_at DESC LIMIT 1
                    """
                )
                row = cur.fetchone()
            conn.close()
            if row:
                latest_id, latest_filename = row
                local_path = structured_processor.get_local_path_for_analysis(latest_id, latest_filename)
                df = pd.read_csv(local_path)
                df = _enrich_jalali_dates(df)
                logger.info(f"Analyst Agent loaded latest CSV: file_id={latest_id}, {latest_filename} ({len(df)} rows)")
                return df
        except Exception as e:
            logger.warning(f"No CSV files found in database for analyst: {str(e)}")

        # No file found
        return None

    def get_column_names(self) -> list:
        df = self._resolve_dataframe()
        if df is not None:
            return df.columns.tolist()
        return []

    def get_tools(self, df_instance: pd.DataFrame) -> list:
        """
        Build typed LangGraph tools connected to the pandas source plus a read-only DuckDB SQL engine.
        """
        try:
            import duckdb
        except ImportError:
            raise ImportError(
                "duckdb is required by the Analyst Agent. Run: pip install duckdb"
            )

        available_columns = df_instance.columns.tolist()

        @tool("analyze_df", args_schema=AnalyzeDfInput)
        def analyze_df_func(limit: int = 3) -> str:
            """Show a preview of the first rows of the DataFrame."""
            return _format_result(df_instance.head(limit), limit)

        @tool("column_sum", args_schema=ColumnSumInput)
        def column_sum_func(column: str) -> str:
            """Sum the numeric values of a column."""
            if column not in df_instance.columns:
                return f"ERROR: Column '{column}' not found. Available columns: {available_columns}"
            try:
                total = pd.to_numeric(df_instance[column], errors="coerce").sum()
                return f"Sum of column '{column}': {total}"
            except Exception as e:
                return f"ERROR computing sum of '{column}': {str(e)}"

        @tool("groupby_aggregate", args_schema=GroupbyAggregateInput)
        def groupby_aggregate_func(group_col: str, agg_col: str, agg_func: str) -> str:
            """Group by a column and aggregate a numeric column."""
            if group_col not in df_instance.columns:
                return f"ERROR: Group column '{group_col}' not found. Available columns: {available_columns}"
            if agg_col not in df_instance.columns:
                return f"ERROR: Aggregate column '{agg_col}' not found. Available columns: {available_columns}"
            try:
                grouped = df_instance.groupby(group_col)[agg_col].agg(agg_func)
                return (f"Grouped results (group_col={group_col}, agg_col={agg_col}, func={agg_func}):\n"
                        f"{grouped.to_string()}")
            except Exception as e:
                return f"ERROR in groupby_aggregate: {str(e)}"

        @tool("filter_rows", args_schema=FilterRowsInput)
        def filter_rows_func(col: str, op: str, value: str) -> str:
            """Filter rows based on a condition on a column."""
            if col not in df_instance.columns:
                return f"ERROR: Column '{col}' not found. Available columns: {available_columns}"
            try:
                col_series = df_instance[col]
                if op == "in":
                    vals = [v for v in value.split("#") if v != ""]
                    mask = col_series.astype(str).isin(vals)
                else:
                    target = _coerce_value(col_series, value)
                    if op == "==":
                        mask = col_series.astype(str) == str(target) if target is None else col_series == target
                    elif op == "!=":
                        mask = col_series.astype(str) != str(target)
                    elif op == ">":
                        mask = pd.to_numeric(col_series, errors="coerce") > target
                    elif op == "<":
                        mask = pd.to_numeric(col_series, errors="coerce") < target
                    elif op == ">=":
                        mask = pd.to_numeric(col_series, errors="coerce") >= target
                    elif op == "<=":
                        mask = pd.to_numeric(col_series, errors="coerce") <= target
                    else:
                        return f"ERROR: unsupported operator '{op}'. Use one of: ==, !=, >, <, >=, <=, in"
                res = df_instance[mask]
                return _format_result(res)
            except Exception as e:
                return f"ERROR in filter_rows: {str(e)}"

        @tool("query_data", args_schema=QueryDataInput)
        def query_data_func(sql: str) -> str:
            """Run a read-only SQL query against the data (table name: 'df'). Returns up to 50 rows."""
            if not _is_readonly_sql(sql):
                return ("ERROR: Only read-only SELECT queries are allowed "
                        "(no INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/COPY/CALL/SET/PRAGMA).")
            try:
                con = duckdb.connect()
                try:
                    con.register("df", df_instance)
                    res = con.execute(sql).fetch_df()
                finally:
                    con.close()
                return _format_result(res)
            except Exception as e:
                return f"ERROR running SQL query: {str(e)}. Try simpler syntax. Columns available: {available_columns}"

        return [
            analyze_df_func,
            column_sum_func,
            groupby_aggregate_func,
            filter_rows_func,
            query_data_func,
        ]

    def _prepare_graph(self, file_id: int = None, custom_file_path: str = None):
        """
        Prepare and compile the LangGraph graph for data analysis.
        Returns (graph, system_prompt, df_context, error_msg).
        """
        if not self.is_enabled:
            return None, None, None, "DOUBTFUL ANSWER: Structured Data Analytics service is currently disabled."

        # 1. Load DataFrame from the user's actual file
        df_to_use = self._resolve_dataframe(file_id=file_id, custom_file_path=custom_file_path)

        if df_to_use is None or df_to_use.empty:
            logger.warning("Analyst Agent: No structured data found. Cannot perform analysis.")
            return None, None, None, "DOUBTFUL ANSWER: No structured dataframe is available. Please upload a CSV file first."

        # Reuse the compiled graph when the source file has not changed
        cache_key = _df_cache_key(file_id, custom_file_path, df_to_use)
        if cache_key in _graph_cache:
            graph, system_prompt, df_context = _graph_cache[cache_key]
            logger.info(f"Analyst Agent reused cached graph for key={cache_key}")
            return graph, system_prompt, df_context, None

        # 2. Configure typed tools and LLM model via Factory
        tools_list = self.get_tools(df_to_use)
        tools_by_name = {t.name: t for t in tools_list}
        llm = get_llm(temperature=0, max_tokens=ANALYST_MAX_TOKENS)
        model_with_tools = llm.bind_tools(tools_list, tool_choice="auto")

        # 3. Build the analyst system prompt (template untouched) plus runtime schema context
        system_prompt = get_analyst_system_prompt(df_to_use.columns.tolist())
        df_context = _build_df_context(df_to_use)

        # 4. Define node functions
        def call_model(state: AgentState):
            messages_to_model = [SystemMessage(content=system_prompt)] + list(state["messages"])
            response = model_with_tools.invoke(messages_to_model)
            return {"messages": [response]}

        def run_tools(state: AgentState):
            last_message = state["messages"][-1]
            tool_msgs = []
            for tool_call in (last_message.tool_calls or []):
                name = tool_call.get("name", "")
                args = tool_call.get("args") or {}
                call_id = tool_call.get("id", "")

                # Loop detection: if the exact same (name, args) has been retried too often, stop.
                sig = f"{name}|{json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)}"
                occurrences = 0
                for m in state["messages"]:
                    if not (isinstance(m, AIMessage) and m.tool_calls):
                        continue
                    for tc in m.tool_calls:
                        tc_sig = f"{tc.get('name', '')}|{json.dumps(tc.get('args') or {}, sort_keys=True, ensure_ascii=False, default=str)}"
                        if tc_sig == sig:
                            occurrences += 1

                if occurrences > MAX_REPEATED_TOOL_CALLS:
                    content = (
                        "ERROR: این فراخوانی ابزار با همان پارامترها چند بار تکرار شده و موفق نبوده است. "
                        "پارامترها را بازبینی کن یا از ابزار query_data / filter_rows با پارامترهای متفاوت استفاده کن. "
                        f"ستون‌های موجود: {list(df_to_use.columns)}"
                    )
                else:
                    fn = tools_by_name.get(name)
                    if fn is None:
                        content = f"ERROR: Unknown tool '{name}'. Available tools: {list(tools_by_name.keys())}"
                    else:
                        try:
                            content = fn.invoke(args)
                        except Exception as e:
                            content = (
                                f"ERROR running tool '{name}': {str(e)}. Please re-check the parameters. "
                                f"Available columns: {list(df_to_use.columns)}"
                            )
                tool_msgs.append(ToolMessage(content=str(content), tool_call_id=call_id))
            return {"messages": tool_msgs}

        def should_continue(state: AgentState):
            last_message = state["messages"][-1]
            if getattr(last_message, "tool_calls", None):
                return "tools"
            # The model produced a final-looking answer without using any tool
            # and flagged DOUBTFUL (or empty): nudge it once to actually query the data.
            content = str(getattr(last_message, "content", "") or "")
            used_tools = any(isinstance(m, AIMessage) and m.tool_calls for m in state["messages"])
            nudges = state.get("nudges", 0) or 0
            if not used_tools and ("DOUBTFUL" in content or not content.strip()) and nudges < MAX_RUNTIME_NUDGES:
                return "nudge"
            return "end"

        def nudge_node(state: AgentState):
            return {"messages": [HumanMessage(content=RUNTIME_TOOL_NUDGE)], "nudges": 1}

        # 5. Compile the graph
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", run_tools)
        workflow.add_node("nudge", nudge_node)

        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {"tools": "tools", "nudge": "nudge", "end": END},
        )
        workflow.add_edge("tools", "agent")
        workflow.add_edge("nudge", "agent")

        graph = workflow.compile(checkpointer=_chkdpt_memory)
        if len(_graph_cache) >= GRAPH_CACHE_MAX:
            _graph_cache.pop(next(iter(_graph_cache)))
        _graph_cache[cache_key] = (graph, system_prompt, df_context)
        return graph, system_prompt, df_context, None

    def execute_analysis(self, query: str, file_id: int = None, custom_file_path: str = None) -> str:
        """
        Run the LangGraph computational graph on the data and return the final answer.
        """
        graph, system_prompt, df_context, error_msg = self._prepare_graph(file_id, custom_file_path)
        if error_msg:
            return error_msg

        try:
            state_input = {
                "messages": [HumanMessage(content=df_context), HumanMessage(content=query)],
                "nudges": 0,
            }
            # NOTE: recursion_limit MUST be top-level in config; thread_id is fresh per run so
            # state never bleeds between calls even though the graph+checkpointer are shared.
            config = {
                "recursion_limit": ANALYST_RECURSION_LIMIT,
                "configurable": {"thread_id": str(uuid.uuid4())},
            }

            result = graph.invoke(state_input, config=config)
            last_message = result["messages"][-1]

            logger.info("LangGraph Analyst successfully computed the response.")
            return last_message.content
        except Exception as e:
            logger.error(f"LangGraph execution crashed: {str(e)}")
            return f"DOUBTFUL ANSWER: Data processing pipeline failed. Error: {str(e)}"

    def execute_analysis_stream(self, query: str, file_id: int = None, custom_file_path: str = None) -> Generator[dict, None, None]:
        """
        Stream the reasoning steps and final output of the LangGraph computational agent.
        Exactly one 'final' chunk is emitted, only after the graph actually ends.
        """
        graph, system_prompt, df_context, error_msg = self._prepare_graph(file_id, custom_file_path)
        if error_msg:
            yield {"type": "final", "content": error_msg}
            return

        try:
            state_input = {
                "messages": [HumanMessage(content=df_context), HumanMessage(content=query)],
                "nudges": 0,
            }
            config = {
                "recursion_limit": ANALYST_RECURSION_LIMIT,
                "configurable": {"thread_id": str(uuid.uuid4())},
            }

            yield {"type": "thought", "content": "🤖 *شروع فرآیند تحلیل داده توسط عامل محاسباتی آریونکس...*\n\n"}

            pending_final = None
            for chunk in graph.stream(state_input, config=config, stream_mode="updates"):
                for node_name, node_state in chunk.items():
                    if node_name == "agent":
                        messages = node_state.get("messages", [])
                        if messages:
                            last_msg = messages[-1]
                            if getattr(last_msg, "tool_calls", None):
                                for tool_call in last_msg.tool_calls:
                                    t_name = tool_call.get("name", "")
                                    t_args = tool_call.get("args", {})
                                    yield {
                                        "type": "thought",
                                        "content": f"🔍 *تصمیم عامل:* استفاده از ابزار `{t_name}` جهت تحلیل داده‌ها.\n"
                                                   f"📥 *پارامترها:* `{t_args}`\n\n",
                                    }
                            else:
                                # Buffer the potential final answer; it is only flushed if the
                                # graph ends without a subsequent nudge step.
                                pending_final = last_msg.content
                    elif node_name == "tools":
                        messages = node_state.get("messages", [])
                        if messages:
                            last_msg = messages[-1]
                            tool_out = str(last_msg.content)
                            if len(tool_out) > 200:
                                tool_out = tool_out[:200] + "..."
                            yield {
                                "type": "thought",
                                "content": f"📊 *خروجی ابزار:* \n```\n{tool_out}\n```\n\n",
                            }
                    elif node_name == "nudge":
                        # The model was nudged to actually query the data; discard the buffered
                        # premature DOUBTFUL answer and let the agent run again.
                        pending_final = None

            if pending_final is not None:
                yield {"type": "final", "content": pending_final}
        except Exception as e:
            logger.error(f"LangGraph streaming crashed: {str(e)}")
            yield {"type": "final", "content": f"DOUBTFUL ANSWER: LangGraph streaming failure: {str(e)}"}

# Global data analyst agent instance
analyst_agent = AnalystAgent()

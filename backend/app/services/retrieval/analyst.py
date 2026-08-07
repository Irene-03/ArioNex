"""
/// <summary>
/// عامل محاسباتی داده‌های ساختاریافته و مالی - تحلیلگر (The Analyst RAG Data Agent)
/// </summary>
/// <remarks>
/// این ماژول با الهام از دموی لنگ‌گراف، داده‌های حسابداری و تراکنش‌ها را در قالب DataFrame لود کرده
/// و با استفاده از زنجیره StateGraph و ابزارهای مجهز (نظیر فیلتر، مجموع ستون، groupby و REPL پایتون)
/// به صورت معنایی به سوالات آماری و حسابداری پاسخ می‌دهد. در صورت شکست در پاسخ‌دهی، با الگوی
/// "DOUBTFUL ANSWER" و ذکر دلیل پاسخ می‌دهد.
/// </remarks>
"""

import os
import json
import logging
from typing import List, Dict, Any, TypedDict, Annotated, Literal, Generator
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage, AIMessage, HumanMessage
from langchain_experimental.tools import PythonAstREPLTool
from langgraph.graph import StateGraph, END, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from app.core.config import settings
from app.core.llm_factory import get_llm
from app.prompts.analyst_prompts import get_analyst_system_prompt

logger = logging.getLogger("arionex.analyst")

# ۱. تعریف ساختار وضعیت عامل بر اساس دموی state.py
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    tool_call_count: int

# ۲. کلاس اصلی پیاده‌سازی عامل تحلیلگر داده
class AnalystAgent:
    """
    /// <summary>
    /// کلاس عامل تحلیلگر داده‌های مالی با پانداس و LangGraph
    /// </summary>
    """
    def __init__(self):
        self.is_enabled = settings.services.structured_data_analytics

    def _resolve_dataframe(self, file_id: int = None, custom_file_path: str = None) -> pd.DataFrame:
        """
        /// <summary>
        /// بارگذاری DataFrame از فایل واقعی کاربر یا آخرین فایل ساختاریافته در دیتابیس
        /// </summary>
        /// <param name="file_id">شناسه فایل ساختاریافته (اختیاری)</param>
        /// <param name="custom_file_path">مسیر فایل مستقیم (اختیاری — اولویت بالاتر)</param>
        /// <returns>DataFrame لود شده یا None در صورت عدم موفقیت</returns>
        """
        from app.services.workers.structured_processor import structured_processor
        from app.core.database import get_db_connection

        # اولویت ۱: مسیر فیزیکی مستقیم
        if custom_file_path and os.path.exists(custom_file_path):
            try:
                df = pd.read_csv(custom_file_path)
                logger.info(f"Analyst Agent loaded DataFrame from custom_file_path: {custom_file_path}")
                return df
            except Exception as e:
                logger.error(f"Failed to load custom CSV: {str(e)}")

        # اولویت ۲: file_id مشخص — دریافت از MinIO/Local
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
                    logger.info(f"Analyst Agent loaded DataFrame for file_id={file_id}: {filename} ({len(df)} rows)")
                    return df
                else:
                    logger.warning(f"No CSV document found with file_id={file_id} in documents table.")
            except Exception as e:
                logger.error(f"Failed to resolve file_id={file_id} to DataFrame: {str(e)}")

        # اولویت ۳: آخرین فایل ساختاریافته آپلود شده در دیتابیس
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
                logger.info(f"Analyst Agent loaded latest CSV: file_id={latest_id}, {latest_filename} ({len(df)} rows)")
                return df
        except Exception as e:
            logger.warning(f"No CSV files found in database for analyst: {str(e)}")

        # هیچ فایلی پیدا نشد
        return None

    def get_column_names(self) -> list:
        df = self._resolve_dataframe()
        if df is not None:
            return df.columns.tolist()
        return []

    def get_tools(self, df_instance: pd.DataFrame) -> list:
        """
        /// <summary>
        /// ساخت ابزارهای تعاملی LangGraph متصل به سورس پانداس
        /// </summary>
        """
        # ابزار محاسباتی پایتون REPL
        python_tool = Tool(
            name="python_repl_ast",
            func=PythonAstREPLTool(locals={"df": df_instance}).invoke,
            description=(
                "Execute Python code to analyze the CSV data. "
                "The data is preloaded in a pandas DataFrame called 'df'. "
                "Do not use pd.read_csv() or pd.read_excel(); the data is already available as 'df'."
                "Do not alter or write to data."
            )
        )

        # ابزارهای تخصصی فیلتر و مجموع و... بر اساس دموی tools.py
        def analyze_df_func(_input: str) -> str:
            return f"Head (3 rows):\n{df_instance.head(3).to_string()}"

        def column_sum_func(column: str) -> str:
            if column not in df_instance.columns:
                return f"Column '{column}' not found."
            try:
                total = df_instance[column].sum()
                return f"Sum of column '{column}': {total}"
            except Exception as e:
                return f"Error: {str(e)}"

        def groupby_aggregate_func(params: list) -> str:
            try:
                group_col = params[0]
                agg_col = params[1]
                agg_func = params[2]
                grouped = df_instance.groupby(group_col)[agg_col].agg(agg_func).to_string()
                return f"Grouped results:\n{grouped}"
            except Exception as e:
                return f"Error: {str(e)}"

        def filter_rows_func(params) -> str:
            try:
                if isinstance(params, str):
                    params = json.loads(params)
                if not isinstance(params, list) or len(params) != 3:
                    return "Error: filter_rows requires exactly 3 arguments: [column_name, operator, value]. Example: ['نوع سند', '==', 'بدهکاری']"
                col, op, val = params[0], params[1], params[2]
                if op == "==":
                    res = df_instance[df_instance[col] == val]
                elif op == ">":
                    res = df_instance[df_instance[col] > val]
                elif op == "<":
                    res = df_instance[df_instance[col] < val]
                elif op == "!=":
                    res = df_instance[df_instance[col] != val]
                else:
                    return f"Error: unsupported operator '{op}'. Use '==', '!=', '>', or '<'."
                return res.head(10).to_string()
            except json.JSONDecodeError:
                return "Error: input must be a JSON array like [\"column\", \"==\", \"value\"]. Use python_repl_ast for complex filters."
            except KeyError as e:
                return f"Error: column {e} not found in DataFrame."
            except Exception as e:
                return f"Error: {str(e)}"

        # ایجاد کلاس‌های ابزار لنگچین
        analyze_df_tool = Tool(name="analyze_df", func=analyze_df_func, description="Preview first 3 rows of DataFrame.")
        column_sum_tool = Tool(name="column_sum", func=column_sum_func, description="Sum numeric values in a column. Input: column name.")
        groupby_agg_tool = Tool(name="groupby_aggregate", func=groupby_aggregate_func, description="Group and aggregate. Input: [group_col, agg_col, func].")
        filter_rows_tool = Tool(
            name="filter_rows",
            func=filter_rows_func,
            description=(
                "Filter DataFrame rows by a SINGLE simple equality condition. "
                "Input MUST be a JSON array with exactly 3 elements: [column_name, operator, value]. "
                "Operators: '==' or '!=' only. "
                'Example: \'["column_name", "==", "value"]\' '
                "DO NOT use for string matching, regex, or compound AND/OR conditions — use python_repl_ast instead."
            ),
        )

        return [analyze_df_tool, column_sum_tool, groupby_agg_tool, filter_rows_tool, python_tool]

    def _prepare_graph(self, file_id: int = None, custom_file_path: str = None):
        """
        /// <summary>
        /// آماده‌سازی و کامپایل گراف لنگ‌گراف برای تحلیل داده‌ها
        /// </summary>
        """
        if not self.is_enabled:
            return None, None, "DOUBTFUL ANSWER: Structured Data Analytics service is currently disabled."

        # ۱. بارگذاری DataFrame از فایل واقعی کاربر
        df_to_use = self._resolve_dataframe(file_id=file_id, custom_file_path=custom_file_path)

        if df_to_use is None or df_to_use.empty:
            logger.warning("Analyst Agent: No structured data found. Cannot perform analysis.")
            return None, None, "DOUBTFUL ANSWER: No structured dataframe is available. Please upload a CSV file first."

        # ۲. پیکربندی ابزارها و مدل LLM از طریق Factory
        tools_list = self.get_tools(df_to_use)
        llm = get_llm(temperature=0)
        model_with_tools = llm.bind_tools(tools_list, tool_choice="auto")

        # ۳. ساخت پرامپت سیستمی تحلیلگر با ستون‌های واقعی DataFrame
        system_prompt = get_analyst_system_prompt(df_to_use.columns.tolist())

        # ۴. تعریف توابع گره (Node Functions) بر اساس دموی nodes.py
        MAX_TOOL_CALLS = 8

        def call_model(state: AgentState):
            messages_to_model = [SystemMessage(content=system_prompt)] + list(state["messages"])
            response = model_with_tools.invoke(messages_to_model)
            return {"messages": [response]}

        def should_continue(state: AgentState):
            last_message = state["messages"][-1]
            if not last_message.tool_calls:
                return "end"
            tool_count = state.get("tool_call_count", 0)
            if tool_count >= MAX_TOOL_CALLS:
                return "end"
            return "continue"

        tool_node = ToolNode(tools_list)

        def track_tool_calls(state: AgentState):
            last_message = state["messages"][-1]
            extra = 1 if hasattr(last_message, "tool_calls") and last_message.tool_calls else 0
            return {"tool_call_count": state.get("tool_call_count", 0) + extra}

        # ۵. کامپایل گراف با StateGraph
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        workflow.add_node("track", track_tool_calls)
        
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )
        workflow.add_edge("tools", "track")
        workflow.add_edge("track", "agent")
        
        memory = MemorySaver()
        graph = workflow.compile(checkpointer=memory)
        return graph, system_prompt, None

    def execute_analysis(self, query: str, file_id: int = None, custom_file_path: str = None) -> str:
        """
        /// <summary>
        /// اجرای گراف محاسباتی LangGraph روی دیتای تراکنش‌ها جهت پاسخ‌دهی به فرمول‌ها
        /// </summary>
        """
        graph, system_prompt, error_msg = self._prepare_graph(file_id, custom_file_path)
        if error_msg:
            return error_msg

        # ۶. اجرای زنجیره و استخراج آخرین پیغام
        try:
            state_input = {"messages": [HumanMessage(content=query)], "tool_call_count": 0}
            config = {"configurable": {"thread_id": "1", "recursion_limit": 20}}
            
            result = graph.invoke(state_input, config=config)
            last_message = result["messages"][-1]
            
            logger.info("LangGraph Analyst successfully computed the response.")
            return last_message.content
        except Exception as e:
            logger.error(f"LangGraph execution crashed: {str(e)}")
            return f"DOUBTFUL ANSWER: Data processing pipeline failed. Error: {str(e)}"

    def execute_analysis_stream(self, query: str, file_id: int = None, custom_file_path: str = None) -> Generator[dict, None, None]:
        """
        /// <summary>
        /// استریم کردن مراحل تفکر و خروجی عامل محاسباتی LangGraph به زبان فارسی
        /// </summary>
        """
        graph, system_prompt, error_msg = self._prepare_graph(file_id, custom_file_path)
        if error_msg:
            yield {"type": "final", "content": error_msg}
            return

        try:
            state_input = {"messages": [HumanMessage(content=query)], "tool_call_count": 0}
            config = {"configurable": {"thread_id": "1", "recursion_limit": 20}}
            
            yield {"type": "thought", "content": "🤖 *شروع فرآیند تحلیل داده توسط عامل محاسباتی آریونکس...*\n\n"}
            
            for chunk in graph.stream(state_input, config=config, stream_mode="updates"):
                for node_name, node_state in chunk.items():
                    if node_name == "agent":
                        messages = node_state.get("messages", [])
                        if messages:
                            last_msg = messages[-1]
                            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                                for tool_call in last_msg.tool_calls:
                                    t_name = tool_call.get("name", "")
                                    t_args = tool_call.get("args", {})
                                    yield {
                                        "type": "thought",
                                        "content": f"🔍 *تصمیم عامل:* استفاده از ابزار `{t_name}` جهت تحلیل داده‌ها.\n"
                                                   f"📥 *پارامترها:* `{t_args}`\n\n"
                                    }
                            else:
                                yield {"type": "final", "content": last_msg.content}
                    elif node_name == "tools":
                        messages = node_state.get("messages", [])
                        if messages:
                            last_msg = messages[-1]
                            tool_out = last_msg.content
                            if len(tool_out) > 200:
                                tool_out = tool_out[:200] + "..."
                            yield {
                                "type": "thought",
                                "content": f"📊 *خروجی ابزار:* \n```\n{tool_out}\n```\n\n"
                            }
        except Exception as e:
            logger.error(f"LangGraph streaming crashed: {str(e)}")
            yield {"type": "final", "content": f"DOUBTFUL ANSWER: LangGraph streaming failure: {str(e)}"}

# شیء سراسری عامل تحلیلگر داده
analyst_agent = AnalystAgent()

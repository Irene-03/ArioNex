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
import logging
from typing import List, Dict, Any, TypedDict, Annotated, Literal
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

# پیدا کردن آدرس پیش‌فرض دیتای حسابداری دمو جهت سازگاری کامل
DEFAULT_DEMO_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "raw data for start",
    "arionex-demo",
    "langgraph_agent",
    "Data",
    "accounting_data.csv"
)

# ۲. کلاس اصلی پیاده‌سازی عامل تحلیلگر داده
class AnalystAgent:
    """
    /// <summary>
    /// کلاس عامل تحلیلگر داده‌های مالی با پانداس و LangGraph
    /// </summary>
    """
    def __init__(self):
        self.is_enabled = settings.services.structured_data_analytics
        self.df = None
        self._load_data()

    def _load_data(self) -> None:
        """
        /// <summary>
        /// لود کردن پیش‌فرض دیتابیس حسابداری تراکنش‌ها به پانداس
        /// </summary>
        """
        try:
            if os.path.exists(DEFAULT_DEMO_DATA_PATH):
                self.df = pd.read_csv(DEFAULT_DEMO_DATA_PATH)
                logger.info(f"Analyst Agent loaded default demo accounting data with {len(self.df)} records.")
            else:
                # در صورت عدم وجود دیتای مالی دمو، یک DataFrame خالی ایجاد می‌کنیم
                self.df = pd.DataFrame(columns=["تاریخ", "نوع سند", "شماره سند", "شرح", "حساب", "بدهکار", "بستانکار"])
                logger.warning("Demo accounting data file was not found. Loaded empty DataFrame.")
        except Exception as e:
            logger.error(f"Failed to load accounting data: {str(e)}")
            self.df = None

    def get_column_names(self) -> list:
        if self.df is not None:
            return self.df.columns.tolist()
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

        def filter_rows_func(params: list) -> str:
            try:
                col, op, val = params[0], params[1], params[2]
                if op == "==":
                    res = df_instance[df_instance[col] == val]
                elif op == ">":
                    res = df_instance[df_instance[col] > val]
                elif op == "<":
                    res = df_instance[df_instance[col] < val]
                else:
                    res = df_instance[df_instance[col] != val]
                return res.head(10).to_string()
            except Exception as e:
                return f"Error: {str(e)}"

        # ایجاد کلاس‌های ابزار لنگچین
        analyze_df_tool = Tool(name="analyze_df", func=analyze_df_func, description="Preview first 3 rows of DataFrame.")
        column_sum_tool = Tool(name="column_sum", func=column_sum_func, description="Sum numeric values in a column. Input: column name.")
        groupby_agg_tool = Tool(name="groupby_aggregate", func=groupby_aggregate_func, description="Group and aggregate. Input: [group_col, agg_col, func].")
        filter_rows_tool = Tool(name="filter_rows", func=filter_rows_func, description="Filter rows by condition. Input: [col, op, val].")

        return [analyze_df_tool, column_sum_tool, groupby_agg_tool, filter_rows_tool, python_tool]

    def execute_analysis(self, query: str, custom_file_path: str = None) -> str:
        """
        /// <summary>
        /// اجرای گراف محاسباتی LangGraph روی دیتای تراکنش‌ها جهت پاسخ‌دهی به فرمول‌ها
        /// </summary>
        /// <param name="query">پرسش محاسباتی کاربر</param>
        /// <param name="custom_file_path">مسیر فایل دلخواه در صورتی که کاربر سند خاصی انتخاب کند</param>
        /// <returns>رشته متنی پاسخ نهایی</returns>
        """
        if not self.is_enabled:
            logger.info("Analyst Agent is disabled in config.yaml. Skipping data calculations.")
            return "DOUBTFUL ANSWER: Structured Data Analytics service is currently disabled."
            
        # ۱. لود فایل دلخواه در صورت ارسال مسیر جدید
        df_to_use = self.df
        if custom_file_path and os.path.exists(custom_file_path):
            try:
                df_to_use = pd.read_csv(custom_file_path)
                logger.info(f"Loaded custom file for analysis: {custom_file_path}")
            except Exception as e:
                logger.error(f"Failed to load custom CSV for analysis: {str(e)}")
                
        if df_to_use is None:
            return "DOUBTFUL ANSWER: No structural dataframe is loaded."

        # ۲. پیکربندی ابزارها و مدل LLM از طریق Factory
        tools_list = self.get_tools(df_to_use)
        llm = get_llm(temperature=0)
        model_with_tools = llm.bind_tools(tools_list, tool_choice="auto")

        # ۳. ساخت پرامپت سیستمی تحلیلگر با ستون‌های واقعی DataFrame
        system_prompt = get_analyst_system_prompt(df_to_use.columns.tolist())

        # ۴. تعریف توابع گره (Node Functions) بر اساس دموی nodes.py
        def call_model(state: AgentState):
            messages_to_model = [SystemMessage(content=system_prompt)] + list(state["messages"])
            response = model_with_tools.invoke(messages_to_model)
            return {"messages": [response]}

        def should_continue(state: AgentState):
            last_message = state["messages"][-1]
            if not last_message.tool_calls:
                return "end"
            return "continue"

        tool_node = ToolNode(tools_list)

        # ۵. کامپایل گراف با StateGraph
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )
        workflow.add_edge("tools", "agent")
        
        memory = MemorySaver()
        graph = workflow.compile(checkpointer=memory)

        # ۶. اجرای زنجیره و استخراج آخرین پیغام
        try:
            state_input = {"messages": [HumanMessage(content=query)]}
            config = {"configurable": {"thread_id": "1", "recursion_limit": 10}}
            
            result = graph.invoke(state_input, config=config)
            last_message = result["messages"][-1]
            
            logger.info("LangGraph Analyst successfully computed the response.")
            return last_message.content
        except Exception as e:
            logger.error(f"LangGraph execution crashed: {str(e)}")
            return f"DOUBTFUL ANSWER: Data processing pipeline failed. Error: {str(e)}"

# شیء سراسری عامل تحلیلگر داده
analyst_agent = AnalystAgent()

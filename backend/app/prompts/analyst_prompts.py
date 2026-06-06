"""
/// <summary>
/// قالب‌های پرامپت عامل تحلیلگر داده‌های مالی (ArioNex Analyst Agent Prompt Templates)
/// </summary>
/// <remarks>
/// این ماژول پرامپت‌های سیستمی LangGraph Analyst Agent را نگهداری می‌کند.
/// عامل تحلیلگر با استفاده از این پرامپت و ابزارهای پانداس، به سوالات آماری و حسابداری پاسخ می‌دهد.
///
/// قوانین کلیدی عامل:
///   - پاسخ فقط باید بر اساس نتایج ابزارها باشد، نه دانش عمومی مدل
///   - در صورت شکست، پاسخ باید با "DOUBTFUL ANSWER:" شروع شود + دلیل شکست
///   - تمامی پاسخ‌های نهایی به فارسی ارائه می‌شوند
///   - متوقف شدن به محض رسیدن به پاسخ کامل (Stop when done)
/// </remarks>
"""

from typing import List


def get_analyst_system_prompt(column_names: List[str]) -> str:
    """
    /// <summary>
    /// تولید پرامپت سیستمی عامل تحلیلگر با توجه به ستون‌های DataFrame موجود
    /// </summary>
    /// <param name="column_names">لیست نام ستون‌های DataFrame لود شده</param>
    /// <returns>رشته پرامپت سیستمی آماده ارسال به مدل LLM</returns>
    /// <remarks>
    /// پرامپت به صورت پویا بر اساس ستون‌های واقعی DataFrame ساخته می‌شود
    /// تا مدل دقیقاً بداند با چه داده‌ای کار می‌کند.
    /// </remarks>
    """
    return f"""You are an intelligent accounting assistant working with a DataFrame containing accounting records.

**Your goal is to answer questions about the data by following these steps:**
1. Carefully analyze the question
2. Determine which tool(s) you need to use to answer the question
3. Use the tools systematically
4. If data is missing or pandas returns 0, respond with "DOUBTFUL ANSWER :" followed by your response and provide a reason to why you failed.
5. Do not guess or answer without data
6. Provide a clear, concise answer based on the tool results
7. Stop when you have a complete answer

**DataFrame Columns:**
{column_names}

**Available Tools:**
- analyze_df – Shows first 3 rows.
- column_sum – Calculates the sum of a column. Input: column name.
- groupby_aggregate – Group and aggregate. Input: [group_col, agg_col, agg_func].
- filter_rows – Filter by condition. Input: [col, op, val].
- python_repl_ast – Run custom Python code on df. Use only if other tools cannot achieve the task.

**Rules:**
 - Always use the most appropriate tool for the task
 - If you cannot answer the question with the available tools only respond with "DOUBTFUL ANSWER: " and provide a short reason to why you failed.
 - Respond in Persian.
"""

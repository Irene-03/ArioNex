"""
/// <summary>
/// قالب‌های پرامپت زنجیره بازیابی و پاسخ‌دهی RAG آریونکس (ArioNex RAG Prompt Templates)
/// </summary>
/// <remarks>
/// این ماژول قالب‌های پرامپت مورد استفاده در دو مرحله کلیدی زنجیره RAG را نگهداری می‌کند:
///   ۱. بازنویسی مستقل پرسش (Standalone Query Rewriter) — جلوگیری از ابهام ارجاعی در چت‌های متوالی
///   ۲. پاسخ‌دهنده نهایی با استناد به منابع (Context-Aware Responder) — همراه با قانون عدم توهم
///
/// استانداردهای طلایی این پرامپت‌ها:
///   - عدم توهم: در صورت ناکافی بودن Context، خروجی باید دقیقاً "####" باشد.
///   - پاسخ فارسی: تمامی پاسخ‌های نهایی به کاربر به زبان فارسی ارائه می‌شوند.
///   - استناد دقیق: پاسخ‌دهنده فقط از Context ارائه شده استفاده می‌کند، نه دانش عمومی.
/// </remarks>
"""

# -------------------------------------------------------------------
# ۱. پرامپت بازنویسی مستقل پرسش (Standalone Query Rewriter)
# -------------------------------------------------------------------
# هدف: رفع ابهامات ضمیری در سوالات متوالی چت (مثل "آن"، "این"، "قبلی")
# ورودی‌ها: تاریخچه چت + پرسش جدید کاربر
# خروجی: یک پرسش مستقل و قابل‌فهم بدون نیاز به تاریخچه
STANDALONE_TEMPLATE = """You are an assistant that rewrite the **User Input** to be independent of any prior chat history.

Given the following chat history and the latest **User Input**, rewrite the question while preserving its context.

**Chat History:**
{chat_history}

**User Input:**:
{user_input}

Rewritten standalone question:
"""

# -------------------------------------------------------------------
# ۲. پرامپت پاسخ‌دهنده نهایی RAG با استناد به منابع (RAG Responder)
# -------------------------------------------------------------------
# هدف: تولید پاسخ دقیق فارسی صرفاً بر اساس Context بازیابی‌شده و دستورالعمل پویا
# ورودی‌ها: دستورالعمل سیستم + قوانین ممیزی + متن Context + تاریخچه + سوال کاربر
RESPONDER_TEMPLATE = """System Instruction:
{system_instruction}

Key instructions for the AI assistant:
    1. Use the below CONTEXT (delimited with XML tags) to answer the QUESTION.
    2. If CONTEXT does not provide enough information to answer the QUESTION, the output must be exactly the four characters: "####"
    3. Don't try to make up an answer.
    4. Respond in Persian.

Compliance Constraints:
{compliance_constraints}

<CONTEXT>
{reranked_text}
</CONTEXT>

Conversation history (retain a concise summary of context to avoid repetition or contradictions):
{chat_history}

QUESTION:
{user_input}

AI Assistant Response:
"""

# -------------------------------------------------------------------
# ۳. متن امتناع استاندارد فارسی (Standard Persian Refusal Message)
# -------------------------------------------------------------------
# این متن در تمام حالت‌هایی که Context کافی نیست یا مدل "####" برمی‌گرداند نمایش داده می‌شود.
# استاندارد‌سازی این متن به یکپارچگی تجربه کاربری کمک می‌کند.
STANDARD_REFUSAL_MESSAGE = "منابع استفاده‌شده اطلاعات کافی و مناسبی درباره‌ی پرسش شما ارائه نمی‌دهند."

"""
/// <summary>
/// ArioNex RAG retrieval and response chain prompt templates (ArioNex RAG Prompt Templates)
/// </summary>
/// <remarks>
/// This module holds the prompt templates used in the two key stages of the RAG chain:
///   1. Standalone query rewriting (Standalone Query Rewriter) — prevents referential ambiguity in consecutive chats
///   2. Final responder citing sources (Context-Aware Responder) — with a no-hallucination rule
/// </remarks>
"""

# -------------------------------------------------------------------
# 1. Standalone query rewriting prompt (Standalone Query Rewriter)
# -------------------------------------------------------------------
STANDALONE_TEMPLATE = """You are an assistant that rewrite the **User Input** to be independent of any prior chat history.

Given the following chat history and the latest **User Input**, rewrite the question while preserving its context.

**Chat History:**
{chat_history}

**User Input:**:
{user_input}

Rewritten standalone question:
"""

# -------------------------------------------------------------------
# 2. RAG final responder prompt citing sources (RAG Responder)
# -------------------------------------------------------------------
RESPONDER_TEMPLATE = """System Instruction:
{system_instruction}

Key instructions for the AI assistant:
    1. Use the below CONTEXT (delimited with XML tags) to answer the QUESTION.
    2. If CONTEXT does not provide enough information to answer the QUESTION, the output must be exactly the four characters: "####"
    3. Don't try to make up an answer.
    4. Match the language of the response with the language of the QUESTION (e.g. if the user asks in English, respond in English; if in Persian, respond in Persian).

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
# 2-b. Responder prompt without the strict rule (Open Responder - no #### guard)
# -------------------------------------------------------------------
RESPONDER_TEMPLATE_OPEN = """System Instruction:
{system_instruction}

Key instructions for the AI assistant:
    1. Use the below CONTEXT (delimited with XML tags) to answer the QUESTION.
    2. If CONTEXT does not provide enough information to answer the QUESTION, respond based on your own knowledge to the best of your ability.
    3. Match the language of the response with the language of the QUESTION (e.g. if the user asks in English, respond in English; if in Persian, respond in Persian).

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
# 3. Standard Persian refusal text (Standard Persian Refusal Message)
# -------------------------------------------------------------------
STANDARD_REFUSAL_MESSAGE = "منابع استفاده‌شده اطلاعات کافی و مناسبی درباره‌ی پرسش شما ارائه نمی‌دهند."

# -------------------------------------------------------------------
# 4. Greeting and salutation prompt (Greeting Prompt)
# -------------------------------------------------------------------
GREETING_TEMPLATE = """You are an AI assistant named {assistant_name}.If the **User Input** is only greeting, farewell, thank you message respond naturally in Persian and mention that you can assist with answering questions in {assistant_field}.
Otherwise, return exactly this text: "####".

**User Input:**
{user_input}

AI Assistant:
"""

# -------------------------------------------------------------------
# 5. Prompt for checking relevance to the domain (Check Structure Prompt)
# -------------------------------------------------------------------
CHECK_STRUCTURE_TEMPLATE = """You are a Tag Relevance Judge. Given a **User Input** and an authoritative **Tags List**, decide whether the input is related to at least one tag.

**Tags List (authoritative; do not invent anything):**
{tags_str}

Rules:
- Use multi-label reasoning: if at least one tag matches, it counts as a hit.
- Use semantic understanding (synonyms, paraphrases, acronyms, singular/plural) and common misspellings.
- Do not alter **Tags List**. Do not add fields.
- If at least one match exists, output "$$$".
- If no good match exists, output an empty string.
- Output must be exactly "$$$" or "" — no explanations or extra text.

Output format (strict):
"$$$" or ""

**Chat History:**
{chat_history}

**User Input:**
{user_input}

AI Assistant:
"""

# -------------------------------------------------------------------
# 6. Topic categorization prompt for documents (Check Categories Prompt)
# -------------------------------------------------------------------
CHECK_CATEGORIES_TEMPLATE = """You are a classification assistant. Given a **User Input** and a **Categories List** (array of objects with fields `category_id` (int) and `category_name` (string)), select all category objects that clearly match the user’s intent.

**Categories List (authoritative; do not invent anything):**
{categories}

Rules:
- Treat this as a multi-label classification task.
- Select categories that are relevant.
- Use semantic understanding (synonyms, paraphrases, acronyms, singular/plural) and common misspellings.
- Prefer the most specific categories; avoid overly broad ones if a specific match exists.
- Do not alter `category_id` or `category_name`. Do not add fields. Do not return duplicates.
- If no good match exists, return an empty array [].
- Output must be **valid JSON** only (no prose), sorted by estimated relevance (best first).

Output format (strict, DO NOT add json formatting):
[
  {{"category_id": <int>, "category_name": "<exact name from list>"}},
  ...
]

**Chat History:**
{chat_history}

**User Input:**
{user_input}
"""

# -------------------------------------------------------------------
# 7. Custom matching and filtering prompt (Customization Template)
# -------------------------------------------------------------------
CUSTOMIZATION_TEMPLATE = """You are a name matching assistant. Your job is to match names from the **User Input** to the **Name List** with high accuracy.

**Name List:**
{customization_field}

**User Input:**
{user_input}

**Chat History:**
{chat_history}

Instructions:
- Compare Input Text against each name in the list
- Consider matches that include:
  * Exact matches
  * Similar first names
  * Similar last names
  * Potential typos or misspellings
- If no good matches are found, return an empty list

Output format:
- matched names from Name List seperated by comma
- Strictly use original names from Name List
- @@ if no matches found

Result:
"""

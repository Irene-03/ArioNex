"""
/// <summary>
/// قالب‌های پرامپت مسیریابی پرسش‌های ورودی آریونکس (ArioNex Query Router Prompt Templates)
/// </summary>
"""

QUERY_ROUTER_PROMPT = """You are an expert query router assistant for enterprise corporate knowledge bases.
Analyze the user's search query and classify it into one of the following two routes:

- "analyst": Select this route if the query requires structured data analysis, accounting calculations, pandas/python calculations, aggregation, statistical calculations, sums, averages, lists of transactions, credit/debit balances, counts of records, or queries related to structured tabular data.
- "rag": Select this route if the query is a general question about company policies, documents, procedures, guidelines, or textual unstructured knowledge retrieval.

Return ONLY the single word "analyst" or "rag" (strictly lowercase, no punctuation, no explanations).

Query: {query}
Route:"""

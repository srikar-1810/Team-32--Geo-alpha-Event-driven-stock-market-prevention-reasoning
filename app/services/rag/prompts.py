from __future__ import annotations

RAG_PROMPT_TEMPLATES: dict[str, str] = {
    "default": (
        "Use the following context to answer the question.\n\n"
        "Context:\n{context}\n\n"
        "Question: {query}\n\n"
        "Answer based solely on the provided context. If the context does not contain "
        "sufficient information, state that clearly."
    ),
    "analysis": (
        "You are a geopolitical financial analyst. Use the provided context to "
        "generate a detailed analysis.\n\n"
        "Context:\n{context}\n\n"
        "Analysis Request: {query}\n\n"
        "Provide:\n"
        "1. Key findings from the context\n"
        "2. Affected sectors and stocks\n"
        "3. Risk assessment (low/medium/high)\n"
        "4. Confidence level\n"
        "5. Recommendations"
    ),
    "summary": (
        "Summarize the following context in relation to the query.\n\n"
        "Context:\n{context}\n\n"
        "Query: {query}\n\n"
        "Provide a concise summary highlighting the most relevant information."
    ),
    "comparison": (
        "Compare and contrast the information in the context with the query.\n\n"
        "Context:\n{context}\n\n"
        "Query: {query}\n\n"
        "Highlight similarities, differences, and patterns across the retrieved information."
    ),
    "timeline": (
        "Extract a chronological timeline from the following context.\n\n"
        "Context:\n{context}\n\n"
        "Query: {query}\n\n"
        "Organize events chronologically and note their significance."
    ),
}

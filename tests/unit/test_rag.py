from evalpulse.rag import KnowledgeRetriever


def test_retriever_returns_stable_citations_for_exact_match_failure() -> None:
    retriever = KnowledgeRetriever.from_directory("docs/knowledge")

    results = retriever.retrieve("exact match differs punctuation whitespace", top_k=2)

    assert results
    assert results[0].chunk.citation_id == "evaluator-failures#exact-match-failures"
    assert results[0].chunk.path.startswith("docs/knowledge/evaluator-failures.md#")
    assert results[0].score > 0


def test_retriever_returns_only_requested_number_of_chunks() -> None:
    retriever = KnowledgeRetriever.from_directory("docs/knowledge")

    results = retriever.retrieve("provider failure runbook retries timeout", top_k=1)

    assert len(results) == 1

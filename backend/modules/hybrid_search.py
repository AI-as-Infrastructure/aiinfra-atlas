"""
Hybrid search utilities: Reciprocal Rank Fusion (RRF).

We fuse two ranked lists (dense/vector and lexical/BM25) by summing
1/(k + rank) for each document id. Inputs should be pre-ranked lists of
(doc_id, score_or_rank) where position implies rank (0 = best).
"""
from typing import List, Dict, Tuple


def rrf_merge(
    dense: List[Tuple[str, float]],
    lexical: List[Tuple[str, float]],
    k: int = 60,
    top_k: int = 20,
) -> List[str]:
    """Return fused doc ids ordered by RRF score.

    Args:
        dense: Ranked list of (doc_id, score_or_rank) from vector search.
        lexical: Ranked list of (doc_id, score_or_rank) from BM25.
        k: RRF constant to balance top ranks. 60 is a common default.
        top_k: Number of final results to return.
    """

    def to_rank_map(items: List[Tuple[str, float]]) -> Dict[str, int]:
        return {doc_id: rank for rank, (doc_id, _score) in enumerate(items)}

    d_rank = to_rank_map(dense)
    l_rank = to_rank_map(lexical)
    all_ids = set(d_rank) | set(l_rank)

    fused: List[Tuple[str, float]] = []
    for doc_id in all_ids:
        r_dense = d_rank.get(doc_id, 1_000_000)
        r_lex = l_rank.get(doc_id, 1_000_000)
        score = 1.0 / (k + r_dense) + 1.0 / (k + r_lex)
        fused.append((doc_id, score))

    fused.sort(key=lambda x: x[1], reverse=True)
    return [doc_id for doc_id, _ in fused[:top_k]]

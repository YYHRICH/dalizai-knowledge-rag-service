from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from apps.rag_service.app.providers.errors import ModelProviderError
from apps.rag_service.app.storage.repository import KnowledgeGapClusterRecord, new_id


class EmbeddingClient(Protocol):
    def embed_texts(self, texts: list[str]): ...


class ClusterSummaryClient(Protocol):
    def complete_json(self, system_prompt: str, user_prompt: str): ...


@dataclass(frozen=True)
class GapClusterCandidate:
    cluster_id: str
    event_ids: list[str]
    representative_query: str
    cluster_title: str
    summary: str
    business_domain_guess: str | None
    knowledge_type_guess: str | None
    event_count: int
    status_breakdown: dict[str, int]
    top_candidate_knowledge_ids: list[str]
    query_examples: list[str]
    first_seen_at: str
    last_seen_at: str
    is_existing: bool = False


@dataclass(frozen=True)
class GapClusteringResult:
    processed_events: int
    created_clusters: int
    updated_clusters: int
    assigned_events: int
    clusters: list[GapClusterCandidate]


class GapClusteringService:
    def __init__(
        self,
        repository,
        embedding_client: EmbeddingClient,
        summary_client: ClusterSummaryClient | None = None,
        similarity_threshold: float = 0.82,
        max_examples: int = 5,
    ) -> None:
        self.repository = repository
        self.embedding_client = embedding_client
        self.summary_client = summary_client
        self.similarity_threshold = similarity_threshold
        self.max_examples = max_examples

    def cluster_unassigned_events(self, limit: int = 100, dry_run: bool = False) -> GapClusteringResult:
        events = self.repository.list_unclustered_gap_events(limit)
        if not events:
            return GapClusteringResult(0, 0, 0, 0, [])

        existing_clusters = self.repository.list_open_gap_clusters()
        seed_texts = [cluster["representative_query"] for cluster in existing_clusters]
        event_texts = [event["query_masked"] for event in events]
        embeddings = self.embedding_client.embed_texts(seed_texts + event_texts).embeddings
        seed_embeddings = embeddings[: len(seed_texts)]
        event_embeddings = embeddings[len(seed_texts) :]

        groups: list[dict] = [
            {
                "cluster_id": cluster["cluster_id"],
                "events": [],
                "embedding": seed_embeddings[index],
                "existing": True,
                "existing_cluster": cluster,
            }
            for index, cluster in enumerate(existing_clusters)
        ]
        new_groups: list[dict] = []

        for event, embedding in zip(events, event_embeddings, strict=True):
            best_group = self._best_group(groups + new_groups, embedding)
            if best_group and best_group[1] >= self.similarity_threshold:
                best_group[0]["events"].append((event, embedding))
                best_group[0]["embedding"] = self._mean_embedding(
                    [item_embedding for _, item_embedding in best_group[0]["events"]]
                    or [best_group[0]["embedding"]]
                )
                continue
            new_groups.append(
                {
                    "cluster_id": new_id("gap_cluster"),
                    "events": [(event, embedding)],
                    "embedding": embedding,
                    "existing": False,
                    "existing_cluster": None,
                }
            )

        changed_groups = [group for group in groups + new_groups if group["events"]]
        candidates = [self._build_candidate(group) for group in changed_groups]

        if not dry_run:
            for candidate in candidates:
                self.repository.upsert_gap_cluster(
                    KnowledgeGapClusterRecord(
                        cluster_id=candidate.cluster_id,
                        representative_query=candidate.representative_query,
                        cluster_title=candidate.cluster_title,
                        summary=candidate.summary,
                        business_domain_guess=candidate.business_domain_guess,
                        knowledge_type_guess=candidate.knowledge_type_guess,
                        event_count=candidate.event_count,
                        status_breakdown=candidate.status_breakdown,
                        top_candidate_knowledge_ids=candidate.top_candidate_knowledge_ids,
                        query_examples=candidate.query_examples,
                        first_seen_at=candidate.first_seen_at,
                        last_seen_at=candidate.last_seen_at,
                    )
                )
                self.repository.assign_gap_events_to_cluster(candidate.event_ids, candidate.cluster_id)

        return GapClusteringResult(
            processed_events=len(events),
            created_clusters=sum(1 for candidate in candidates if not candidate.is_existing),
            updated_clusters=sum(1 for candidate in candidates if candidate.is_existing),
            assigned_events=sum(len(candidate.event_ids) for candidate in candidates),
            clusters=candidates,
        )

    def _best_group(self, groups: list[dict], embedding: list[float]) -> tuple[dict, float] | None:
        if not groups:
            return None
        scored = [(group, self._cosine_similarity(group["embedding"], embedding)) for group in groups]
        return max(scored, key=lambda item: item[1])

    def _build_candidate(self, group: dict) -> GapClusterCandidate:
        events = [event for event, _ in group["events"]]
        existing = group.get("existing_cluster") or {}
        all_examples = list(existing.get("query_examples") or []) + [event["query_masked"] for event in events]
        query_examples = self._dedupe(all_examples)[: self.max_examples]
        representative_query = query_examples[0]
        statuses = Counter(existing.get("status_breakdown") or {})
        statuses.update(event["status"] for event in events)
        top_candidates = self._dedupe(
            list(existing.get("top_candidate_knowledge_ids") or [])
            + [kid for event in events for kid in event.get("top_candidate_knowledge_ids", [])]
        )[:10]
        first_seen_at = min([event["created_at"] for event in events] + [existing.get("first_seen_at") or events[0]["created_at"]])
        last_seen_at = max([event["created_at"] for event in events] + [existing.get("last_seen_at") or events[-1]["created_at"]])
        business_domain_guess = self._most_common(
            [existing.get("business_domain_guess")] + [event.get("business_domain_guess") for event in events]
        )
        knowledge_type_guess = self._most_common(
            [existing.get("knowledge_type_guess")] + [event.get("knowledge_type_guess") for event in events]
        )
        title, summary = self._summarize(query_examples, business_domain_guess, knowledge_type_guess)
        event_count = int(existing.get("event_count") or 0) + len(events)
        return GapClusterCandidate(
            cluster_id=group["cluster_id"],
            event_ids=[event["gap_event_id"] for event in events],
            representative_query=representative_query,
            cluster_title=title,
            summary=summary,
            business_domain_guess=business_domain_guess,
            knowledge_type_guess=knowledge_type_guess,
            event_count=event_count,
            status_breakdown=dict(statuses),
            top_candidate_knowledge_ids=top_candidates,
            query_examples=query_examples,
            first_seen_at=first_seen_at,
            last_seen_at=last_seen_at,
            is_existing=group["existing"],
        )

    def _summarize(
        self,
        examples: list[str],
        business_domain_guess: str | None,
        knowledge_type_guess: str | None,
    ) -> tuple[str, str]:
        fallback_title = examples[0][:40]
        fallback_summary = "；".join(examples[:3])
        if self.summary_client is None:
            return fallback_title, fallback_summary
        system_prompt = (
            "你是知识库运营助手。只输出 JSON，字段为 title 和 summary。"
            "title 不超过 20 个中文字，summary 不超过 80 个中文字。"
        )
        user_prompt = json.dumps(
            {
                "businessDomainGuess": business_domain_guess,
                "knowledgeTypeGuess": knowledge_type_guess,
                "queries": examples,
            },
            ensure_ascii=False,
        )
        try:
            result = self.summary_client.complete_json(system_prompt, user_prompt)
            data = json.loads(result.content)
        except (ModelProviderError, json.JSONDecodeError, TypeError, ValueError):
            return fallback_title, fallback_summary
        title = str(data.get("title") or fallback_title).strip()[:40]
        summary = str(data.get("summary") or fallback_summary).strip()[:160]
        return title, summary

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)

    def _mean_embedding(self, embeddings: list[list[float]]) -> list[float]:
        size = len(embeddings[0])
        return [sum(embedding[index] for embedding in embeddings) / len(embeddings) for index in range(size)]

    def _dedupe(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def _most_common(self, values: list[str | None]) -> str | None:
        filtered = [value for value in values if value]
        if not filtered:
            return None
        return Counter(filtered).most_common(1)[0][0]

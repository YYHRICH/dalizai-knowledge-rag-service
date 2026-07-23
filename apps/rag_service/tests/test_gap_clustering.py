from types import SimpleNamespace

from apps.rag_service.app.governance.gap_clustering import GapClusteringService


class FakeRepository:
    def __init__(self):
        self.events = [
            {
                "gap_event_id": "gap_event_001",
                "query_masked": "二维码扫不出来怎么办？",
                "status": "not_found",
                "business_domain_guess": "device",
                "knowledge_type_guess": "troubleshooting",
                "top_candidate_knowledge_ids": [],
                "created_at": "2026-07-23 10:00:00",
            },
            {
                "gap_event_id": "gap_event_002",
                "query_masked": "扫码一直失败怎么办？",
                "status": "not_found",
                "business_domain_guess": "device",
                "knowledge_type_guess": "troubleshooting",
                "top_candidate_knowledge_ids": [],
                "created_at": "2026-07-23 10:01:00",
            },
            {
                "gap_event_id": "gap_event_003",
                "query_masked": "会员发票在哪里开？",
                "status": "low_confidence",
                "business_domain_guess": "invoice",
                "knowledge_type_guess": "faq",
                "top_candidate_knowledge_ids": ["candidate_invoice"],
                "created_at": "2026-07-23 10:02:00",
            },
        ]
        self.upserted = []
        self.assigned = []

    def list_unclustered_gap_events(self, limit):
        return self.events[:limit]

    def list_open_gap_clusters(self):
        return []

    def upsert_gap_cluster(self, record):
        self.upserted.append(record)

    def assign_gap_events_to_cluster(self, event_ids, cluster_id):
        self.assigned.append((event_ids, cluster_id))


class FakeEmbeddingClient:
    def embed_texts(self, texts):
        assert texts == ["二维码扫不出来怎么办？", "扫码一直失败怎么办？", "会员发票在哪里开？"]
        return SimpleNamespace(
            embeddings=[
                [1.0, 0.0, 0.0],
                [0.95, 0.05, 0.0],
                [0.0, 1.0, 0.0],
            ]
        )


class FakeSummaryClient:
    def complete_json(self, system_prompt, user_prompt):
        return SimpleNamespace(content='{"title":"扫码异常","summary":"用户反馈扫码失败或二维码无法识别。"}')


def test_cluster_unassigned_events_groups_by_embedding_similarity() -> None:
    repository = FakeRepository()
    service = GapClusteringService(
        repository,
        FakeEmbeddingClient(),
        FakeSummaryClient(),
        similarity_threshold=0.90,
    )

    result = service.cluster_unassigned_events(limit=10)

    assert result.processed_events == 3
    assert result.created_clusters == 2
    assert result.updated_clusters == 0
    assert result.assigned_events == 3
    assert len(repository.upserted) == 2
    first_cluster = repository.upserted[0]
    assert first_cluster.cluster_title == "扫码异常"
    assert first_cluster.event_count == 2
    assert first_cluster.status_breakdown == {"not_found": 2}
    assert repository.assigned[0][0] == ["gap_event_001", "gap_event_002"]


def test_cluster_unassigned_events_dry_run_does_not_write() -> None:
    repository = FakeRepository()
    service = GapClusteringService(repository, FakeEmbeddingClient(), similarity_threshold=0.90)

    result = service.cluster_unassigned_events(limit=10, dry_run=True)

    assert result.created_clusters == 2
    assert repository.upserted == []
    assert repository.assigned == []

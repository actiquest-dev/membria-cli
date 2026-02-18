from datetime import datetime, timedelta

from membria.memory_policy import MemoryPolicy


def test_freshness_decreases_over_time():
    policy = MemoryPolicy(default_ttl_days=365, half_life_days=30)
    now = datetime.utcnow()
    created_at = int((now - timedelta(days=10)).timestamp())
    fresh10 = policy.freshness(created_at, ttl_days=365)
    created_at2 = int((now - timedelta(days=20)).timestamp())
    fresh20 = policy.freshness(created_at2, ttl_days=365)
    assert fresh20 < fresh10


def test_should_forget_respects_ttl():
    policy = MemoryPolicy(default_ttl_days=10)
    now = datetime.utcnow()
    created_at = int((now - timedelta(days=11)).timestamp())
    assert policy.should_forget(created_at, ttl_days=10) is True
    created_at2 = int((now - timedelta(days=5)).timestamp())
    assert policy.should_forget(created_at2, ttl_days=10) is False


def test_score_is_bounded():
    policy = MemoryPolicy()
    score = policy.score(relevance=1.0, confidence=1.0, freshness=1.0, impact=1.0)
    assert 0.0 <= score <= 1.0

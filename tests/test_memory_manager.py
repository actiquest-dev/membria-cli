from datetime import datetime

from membria.memory_manager import MemoryManager
from membria.memory_policy import MemoryPolicy


class DummyGraph:
    def __init__(self):
        self.connected = True
        self.updated = []

    def update_decision_memory(self, decision_id, updates):
        self.updated.append(("decision", decision_id, updates))
        return True

    def update_negative_knowledge_memory(self, nk_id, updates):
        self.updated.append(("nk", nk_id, updates))
        return True

    def query(self, query, params=None):
        return []


def test_update_adds_last_verified_at():
    graph = DummyGraph()
    manager = MemoryManager(graph, MemoryPolicy())
    ok = manager.update_decision("dec_1", {"is_active": False})
    assert ok is True
    kind, _, updates = graph.updated[0]
    assert kind == "decision"
    assert "last_verified_at" in updates


def test_forget_sets_reason():
    graph = DummyGraph()
    manager = MemoryManager(graph, MemoryPolicy())
    ok = manager.forget_negative_knowledge("nk_1", "ttl_expired")
    assert ok is True
    kind, _, updates = graph.updated[0]
    assert kind == "nk"
    assert updates["deprecated_reason"] == "ttl_expired"

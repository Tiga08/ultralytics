import pytest
from unittest.mock import MagicMock
from core.scheduler import TaskScheduler, TaskPriority


def make_worker(healthy=True):
    w = MagicMock()
    w.is_healthy = healthy
    return w


def test_submit_starts_worker():
    sched = TaskScheduler()
    w = make_worker()
    sched.submit("t1", w, TaskPriority.NORMAL)
    w.start.assert_called_once()


def test_check_health_healthy():
    sched = TaskScheduler()
    sched.submit("t1", make_worker(healthy=True), TaskPriority.NORMAL)
    assert sched.check_health() == []


def test_check_health_unhealthy():
    sched = TaskScheduler()
    sched.submit("t2", make_worker(healthy=False), TaskPriority.HIGH)
    assert "t2" in sched.check_health()


def test_submit_duplicate_raises():
    sched = TaskScheduler()
    sched.submit("t3", make_worker(), TaskPriority.NORMAL)
    with pytest.raises(ValueError):
        sched.submit("t3", make_worker(), TaskPriority.NORMAL)


def test_remove_stops_worker():
    sched = TaskScheduler()
    w = make_worker()
    sched.submit("t4", w, TaskPriority.NORMAL)
    sched.remove("t4")
    w.stop.assert_called_once()


def test_restart_without_factory_raises():
    sched = TaskScheduler()
    sched.submit("t5", make_worker(), TaskPriority.NORMAL, worker_factory=None)
    with pytest.raises(RuntimeError):
        sched.restart("t5")


def test_restart_with_factory_replaces_worker():
    sched = TaskScheduler()
    old = make_worker()
    new = make_worker()
    sched.submit("t6", old, TaskPriority.NORMAL, worker_factory=lambda: new)
    sched.restart("t6")
    old.stop.assert_called_once()
    new.start.assert_called_once()

from utils.singleton import SingletonMeta
from utils.time_checker import TimeChecker


def test_singleton_same_instance():
    class Foo(metaclass=SingletonMeta):
        pass
    assert Foo() is Foo()


def test_singleton_different_classes():
    class A(metaclass=SingletonMeta):
        pass
    class B(metaclass=SingletonMeta):
        pass
    assert A() is not B()


def test_time_checker_always_active():
    class FakeSchedule:
        enabled_days = [1, 2, 3, 4, 5, 6, 7]
        start_time = "00:00:00"
        end_time = "23:59:59"
    assert TimeChecker.is_active(FakeSchedule()) is True


def test_time_checker_invalid_day():
    class FakeSchedule:
        enabled_days = [8]  # 不存在的日
        start_time = "00:00:00"
        end_time = "23:59:59"
    assert TimeChecker.is_active(FakeSchedule()) is False


def test_time_checker_check_window():
    assert TimeChecker._check("12:00:00", "00:00:00", "23:59:59") is True
    assert TimeChecker._check("12:00:00", "13:00:00", "14:00:00") is False

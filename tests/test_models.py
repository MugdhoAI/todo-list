import pytest

from todo_list.models import Task


def test_task_round_trip_through_dict() -> None:
    task = Task.create("abc", "Write tests")
    task.mark_completed()
    restored = Task.from_dict(task.to_dict())
    assert restored == task


def test_mark_completed_sets_timestamp_only_once() -> None:
    task = Task.create("abc", "Write tests")
    task.mark_completed()
    first_completed_at = task.completed_at
    task.mark_completed()
    assert task.completed_at == first_completed_at


def test_mark_pending_clears_completion() -> None:
    task = Task.create("abc", "Write tests")
    task.mark_completed()
    task.mark_pending()
    assert task.completed is False
    assert task.completed_at is None


def test_from_dict_rejects_missing_fields() -> None:
    with pytest.raises(ValueError, match="missing required fields"):
        Task.from_dict({"id": "abc", "title": "Write tests"})


def test_from_dict_rejects_wrong_types() -> None:
    with pytest.raises(ValueError, match="must be strings"):
        Task.from_dict(
            {
                "id": "abc",
                "title": "Write tests",
                "completed": False,
                "created_at": 123,
            }
        )
    with pytest.raises(ValueError, match="must be a boolean"):
        Task.from_dict(
            {
                "id": "abc",
                "title": "Write tests",
                "completed": "no",
                "created_at": "2026-11-08T00:00:00+00:00",
            }
        )
    with pytest.raises(ValueError, match="must be a string or null"):
        Task.from_dict(
            {
                "id": "abc",
                "title": "Write tests",
                "completed": True,
                "created_at": "2026-11-08T00:00:00+00:00",
                "completed_at": 123,
            }
        )

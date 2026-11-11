from pathlib import Path

import pytest

from todo_list.models import Task
from todo_list.service import TaskNotFoundError, TaskService
from todo_list.storage import JsonTaskStorage, StorageError


def make_service(tmp_path: Path) -> TaskService:
    return TaskService(JsonTaskStorage(tmp_path / "tasks.json"))


def test_add_task_persists_and_normalizes_title(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    task = service.add_task("  Buy groceries  ")
    assert task.title == "Buy groceries"
    assert service.list_tasks() == [task]


def test_empty_title_is_rejected(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    with pytest.raises(ValueError, match="cannot be empty"):
        service.add_task("   ")


def test_title_over_200_characters_is_rejected(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    with pytest.raises(ValueError, match="200 characters"):
        service.add_task("x" * 201)


def test_complete_task_changes_status(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    task = service.add_task("Ship project")
    completed = service.complete_task(task.id)
    assert completed.completed is True
    assert completed.completed_at is not None
    assert service.list_tasks("pending") == []
    assert service.list_tasks("completed") == [completed]


def test_completing_missing_task_raises(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    with pytest.raises(TaskNotFoundError, match="Task not found"):
        service.complete_task("missing-id")


def test_reopen_task_marks_completed_task_pending_again(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    task = service.add_task("Ship project")
    service.complete_task(task.id)
    reopened = service.reopen_task(task.id)
    assert reopened.completed is False
    assert reopened.completed_at is None
    assert service.list_tasks("pending") == [reopened]
    assert service.list_tasks("completed") == []


def test_reopening_missing_task_raises(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    with pytest.raises(TaskNotFoundError, match="Task not found"):
        service.reopen_task("missing-id")


def test_delete_task_removes_it(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    task = service.add_task("Remove me")
    deleted = service.delete_task(task.id)
    assert deleted == task
    assert service.list_tasks() == []


def test_delete_missing_task_raises(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    with pytest.raises(TaskNotFoundError):
        service.delete_task("missing-id")


def test_clear_completed_removes_only_completed_tasks(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    first = service.add_task("Done one")
    second = service.add_task("Still open")
    third = service.add_task("Done two")
    service.complete_task(first.id)
    service.complete_task(third.id)
    assert service.clear_completed() == 2
    assert service.list_tasks() == [second]


def test_clear_completed_with_nothing_completed_removes_nothing(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    task = service.add_task("Still open")
    assert service.clear_completed() == 0
    assert service.list_tasks() == [task]


def test_edit_task_changes_title_and_keeps_other_fields(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    task = service.add_task("Old title")
    edited = service.edit_task(task.id, "  New title  ")
    assert edited.title == "New title"
    assert edited.id == task.id
    assert edited.completed is False
    assert service.list_tasks() == [edited]


def test_edit_task_rejects_empty_title(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    task = service.add_task("Keep me")
    with pytest.raises(ValueError, match="cannot be empty"):
        service.edit_task(task.id, "   ")
    assert service.list_tasks()[0].title == "Keep me"


def test_edit_task_rejects_title_over_200_characters(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    task = service.add_task("Keep me")
    with pytest.raises(ValueError, match="200 characters"):
        service.edit_task(task.id, "x" * 201)


def test_edit_missing_task_raises(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    with pytest.raises(TaskNotFoundError, match="Task not found"):
        service.edit_task("missing-id", "New title")


def test_stats_counts_tasks_by_status(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    assert service.stats() == {"total": 0, "pending": 0, "completed": 0}
    first = service.add_task("Done one")
    service.add_task("Still open")
    second = service.add_task("Done two")
    service.complete_task(first.id)
    service.complete_task(second.id)
    assert service.stats() == {"total": 3, "pending": 1, "completed": 2}


def test_invalid_status_is_rejected(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    with pytest.raises(ValueError, match="Status must be one of"):
        service.list_tasks("invalid")


def test_search_tasks_is_case_insensitive_and_matches_partial_titles(
    tmp_path: Path,
) -> None:
    service = make_service(tmp_path)
    first = service.add_task("Finish Python project")
    second = service.add_task("Review Python tests")
    service.add_task("Buy groceries")

    assert service.search_tasks("PYTHON") == [first, second]
    assert service.search_tasks("grocer")


def test_empty_search_query_is_rejected(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    with pytest.raises(ValueError, match="Search query cannot be empty"):
        service.search_tasks("   ")


def make_service_with_ids(tmp_path: Path, ids: list[str]) -> TaskService:
    storage = JsonTaskStorage(tmp_path / "tasks.json")
    storage.save([Task.create(task_id, f"Task {task_id}") for task_id in ids])
    return TaskService(storage)


def test_unique_id_prefix_resolves_to_the_task(tmp_path: Path) -> None:
    service = make_service_with_ids(tmp_path, ["abc123-first", "xyz789-second"])
    completed = service.complete_task("abc1")
    assert completed.id == "abc123-first"
    assert completed.completed is True


def test_exact_id_wins_over_prefix_matches(tmp_path: Path) -> None:
    service = make_service_with_ids(tmp_path, ["abc", "abc123-first"])
    deleted = service.delete_task("abc")
    assert deleted.id == "abc"
    assert [task.id for task in service.list_tasks()] == ["abc123-first"]


def test_ambiguous_id_prefix_is_rejected(tmp_path: Path) -> None:
    from todo_list.service import AmbiguousTaskIdError

    service = make_service_with_ids(tmp_path, ["abc123-first", "abc999-second"])
    with pytest.raises(AmbiguousTaskIdError, match="matches 2 tasks"):
        service.complete_task("abc")


def test_unknown_id_prefix_is_not_found(tmp_path: Path) -> None:
    service = make_service_with_ids(tmp_path, ["abc123-first"])
    with pytest.raises(TaskNotFoundError, match="Task not found"):
        service.complete_task("zzz")


def test_corrupt_storage_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "tasks.json"
    path.write_text("not json", encoding="utf-8")
    service = TaskService(JsonTaskStorage(path))
    with pytest.raises(StorageError, match="Could not read task file"):
        service.list_tasks()

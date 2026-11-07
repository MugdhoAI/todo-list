from pathlib import Path

import pytest

from todo_list.models import Task
from todo_list.storage import JsonTaskStorage, StorageError


def test_storage_round_trip(tmp_path: Path) -> None:
    storage = JsonTaskStorage(tmp_path / "nested" / "tasks.json")
    task = Task.create("123", "Write tests")
    task.mark_completed()
    storage.save([task])
    loaded = storage.load()
    assert loaded == [task]


def test_non_object_entry_is_reported_instead_of_dropped(tmp_path: Path) -> None:
    path = tmp_path / "tasks.json"
    path.write_text('["not a task object"]', encoding="utf-8")
    storage = JsonTaskStorage(path)
    with pytest.raises(StorageError, match="invalid task data"):
        storage.load()

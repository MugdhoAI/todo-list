from argparse import Namespace
from pathlib import Path

from todo_list.cli import build_parser, run
from todo_list.service import TaskService
from todo_list.storage import JsonTaskStorage


def make_service(tmp_path: Path) -> TaskService:
    return TaskService(JsonTaskStorage(tmp_path / "tasks.json"))


def test_parser_accepts_search_command() -> None:
    args = build_parser().parse_args(["search", "python"])
    assert args.command == "search"
    assert args.query == "python"


def test_add_and_list_commands(capsys, tmp_path: Path) -> None:
    service = make_service(tmp_path)

    assert run(Namespace(command="add", title="  Write tests  "), service) == 0
    output = capsys.readouterr().out
    assert "Added: Write tests" in output

    assert run(Namespace(command="list", status="all"), service) == 0
    output = capsys.readouterr().out
    assert "Write tests" in output


def test_search_command_prints_matching_tasks(capsys, tmp_path: Path) -> None:
    service = make_service(tmp_path)
    service.add_task("Build Python CLI")
    service.add_task("Buy groceries")

    assert run(Namespace(command="search", query="PYTHON"), service) == 0
    output = capsys.readouterr().out
    assert "Build Python CLI" in output
    assert "Buy groceries" not in output


def test_done_and_delete_commands(capsys, tmp_path: Path) -> None:
    service = make_service(tmp_path)
    task = service.add_task("Temporary task")

    assert run(Namespace(command="done", task_id=task.id), service) == 0
    assert "Completed: Temporary task" in capsys.readouterr().out

    assert run(Namespace(command="delete", task_id=task.id), service) == 0
    assert "Deleted: Temporary task" in capsys.readouterr().out
    assert service.list_tasks() == []


def test_list_empty_collection_has_friendly_output(capsys, tmp_path: Path) -> None:
    service = make_service(tmp_path)

    assert run(Namespace(command="list", status="all"), service) == 0
    assert capsys.readouterr().out.strip() == "No tasks found."

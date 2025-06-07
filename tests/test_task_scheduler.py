import sys
import types
import importlib
from datetime import datetime
from pathlib import Path

import pytest
import pytz


def load_taskplan():
    stubbed = {}
    root = Path(__file__).resolve().parents[1]
    path_inserted = False
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
        path_inserted = True

    def stub(name, attrs):
        stubbed[name] = sys.modules.get(name)
        module = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(module, key, value)
        sys.modules[name] = module

    # create stub modules for heavy dependencies
    stub('agent', {
        'Agent': object,
        'AgentContext': object,
        'UserMessage': object,
    })
    stub('initialize', {'initialize': lambda *a, **k: None})
    stub('python.helpers.persist_chat', {'save_tmp_chat': lambda *a, **k: None})
    stub('python.helpers.print_style', {'PrintStyle': object})
    stub('python.helpers.defer', {'DeferredTask': object})
    stub('python.helpers.files', {
        'get_abs_path': lambda p: p,
        'make_dirs': lambda p: None,
        'read_file': lambda p: '',
        'write_file': lambda p, c: None,
    })

    class Localization:
        @staticmethod
        def get():
            class L:
                def get_timezone(self):
                    return 'UTC'
            return L()
    stub('python.helpers.localization', {'Localization': Localization})

    module = importlib.import_module('python.helpers.task_scheduler')
    return module.TaskPlan, stubbed, path_inserted


def unload_taskplan(stubbed, path_inserted):
    sys.modules.pop('python.helpers.task_scheduler', None)
    for name, original in stubbed.items():
        if original is None:
            del sys.modules[name]
        else:
            sys.modules[name] = original
    if path_inserted:
        sys.path.pop(0)


@pytest.fixture
def TaskPlan():
    TaskPlan, stubbed, inserted = load_taskplan()
    yield TaskPlan
    unload_taskplan(stubbed, inserted)


def test_lists_are_not_shared(TaskPlan):
    plan1 = TaskPlan.create()
    plan2 = TaskPlan.create()
    assert plan1.todo is not plan2.todo
    assert plan1.done is not plan2.done
    plan1.todo.append('x')
    plan1.done.append('y')
    assert plan2.todo == []
    assert plan2.done == []


def test_naive_datetimes_converted_to_utc(TaskPlan):
    plan = TaskPlan.create(
        todo=[datetime(2024, 1, 1, 0, 0)],
        in_progress=datetime(2024, 1, 2, 0, 0),
        done=[datetime(2024, 1, 3, 0, 0)],
    )
    assert plan.todo[0].tzinfo == pytz.UTC
    assert plan.in_progress.tzinfo == pytz.UTC
    assert plan.done[0].tzinfo == pytz.UTC

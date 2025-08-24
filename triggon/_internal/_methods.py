from importlib import import_module

names = [
    "_debug",
    "_err_handler",
    "_frame_utils",
    "_revert",
    "_set_trigger",
    "_switch_var",
    "_var_analysis",
    "_var_update",
]

modules = [import_module(f".{n}", __package__) for n in names]


def _bind_to_triggon(target: type) -> None:
  for module in modules:
    for name, func in vars(module).items():
        if callable(func):
            setattr(target, name, func)
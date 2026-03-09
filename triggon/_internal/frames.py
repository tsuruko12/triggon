import inspect
from types import FrameType

from ..errors.public import FrameAccessError
from ._types.structs import Callsite


def get_target_frame(depth: int = 1) -> FrameType:
    frame = inspect.currentframe()
    if frame is None or frame.f_back is None:
        frame = None
        raise FrameAccessError()
    frame = frame.f_back

    cur_depth = 0
    while frame:
        if cur_depth == depth:
            break
        frame = frame.f_back
        cur_depth += 1

    if frame is None:
        frame = None
        raise FrameAccessError()

    return frame


def get_callsite(frame: FrameType, get_lasti: bool = False) -> Callsite:
    filename = frame.f_code.co_filename
    lineno = frame.f_lineno
    func_name = frame.f_code.co_name

    if get_lasti:
        lasti = frame.f_lasti
        return Callsite(filename, lineno, func_name, lasti)
    return Callsite(filename, lineno, func_name, lasti=None)

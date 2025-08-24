import inspect

from ._exceptions import _FrameAccessError, _UnsetExitError
from ._var_update import _get_delay_index


def _get_target_frame(self, target_name: str, has_exit: bool = False) -> None:
   if self._frame is not None:
      return

   cur_frame = inspect.currentframe().f_back   
   while cur_frame:
      if has_exit:
          if cur_frame.f_code.co_name == "<module>":
              raise _UnsetExitError()
          if cur_frame.f_code.co_name == target_name:
              break
      if cur_frame.f_code.co_name == target_name:
         self._frame = cur_frame.f_back
         break        
      cur_frame = cur_frame.f_back

   if has_exit:
       return
   if self._frame is None:
       raise _FrameAccessError()
   
   self._get_trace_info()

def _get_trace_info(self) -> None:
    if self._lineno is None:
        self._lineno = self._frame.f_lineno
    if self._file_name is None:
        self._file_name = self._frame.f_code.co_filename

def _store_frame_info(self, labels: list[str], to_org: bool = False) -> None: 
    frame = self._frame
    file = frame.f_code.co_filename
    lineno = frame.f_lineno
    func = frame.f_code.co_name

    index = _get_delay_index(to_org)
    for label in labels:
        self._delay_info[label][index] = (frame, file, lineno, func)

def _clear_frame(self) -> None:
   # To prevent memory leak by releasing the frame reference
   self._frame = None
   self._lineno = None
   self._file_name = None
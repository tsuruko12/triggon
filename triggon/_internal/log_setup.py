import logging
import os
from pathlib import Path
from typing import Sequence

from ..errors import UnregisteredLabelError
from .arg_types import (
   DebugArg, 
   LogFile, 
   TargetLabels, 
   Verbosity,
)
from .lock import UPDATE_LOCK


type LogConfig = tuple[Verbosity, LogFile, TargetLabels]

DEBUG_LOG_FMT = (
   "%(asctime)s %(levelname)s "
   "%(caller_func)s %(caller_file)s:%(caller_line)d - %(message)s"
)
WARN_LOG_FMT = "%(asctime)s %(levelname)s - %(message)s"

TRIGGON_LOG_VERBOSITY = "TRIGGON_LOG_VERBOSITY" # 0-3
TRIGGON_LOG_FILE = "TRIGGON_LOG_FILE"
TRIGGON_LOG_LABELS = "TRIGGON_LOG_LABELS" # target labels to output

logger = logging.getLogger("triggon")
logger.propagate = False
logger.setLevel(logging.DEBUG)


class LogSetup:
   _counter = 1

   def configure_debug(self, arg: DebugArg) -> None:
      # Default: level 3, terminal output, all labels
      if arg is False:
         log_verbosity, file_path, target_labels = 0, None, None
      elif arg is True:
         log_verbosity, file_path, target_labels = self._read_env()
      else:
         log_verbosity, file_path, target_labels = self._read_arg(arg)

      if log_verbosity == 0:
         self._logger = None
      else:  
         with UPDATE_LOCK:
            n = type(self)._counter
            type(self)._counter += 1
         self._logger = logger.getChild(str(n))
         self._logger.propagate = False

         if file_path is None:
            self._setup_stream_handler()
         else:
            self._setup_file_handler(file_path)

         if target_labels is not None:
            valid_labels = []
            for label in target_labels:
               try:
                  self.ensure_labels_exist(label)
               except UnregisteredLabelError as e:
                  self._logger.warning("Invalid debug label: %s", e)
               else:
                  valid_labels.append(label)

            if not valid_labels:
               target_labels = None
            else:
               target_labels = tuple(valid_labels)

      debug_info = {
         TRIGGON_LOG_VERBOSITY: log_verbosity,
         TRIGGON_LOG_FILE: file_path,
         TRIGGON_LOG_LABELS: target_labels,
      }
      self.debug = debug_info

   def _read_env(self) -> LogConfig:
      log_verbosity = os.getenv(TRIGGON_LOG_VERBOSITY)
      if log_verbosity is None:
         log_verbosity = 3
      else:
         try:
            log_verbosity = int(log_verbosity)
         except ValueError:
            log_verbosity = 3

         log_verbosity = min(3, max(0, log_verbosity))

      if log_verbosity == 0:
         # debug off
         file_path = None
         target_labels = None
      else:
         file_path = os.getenv(TRIGGON_LOG_FILE)
         if file_path is not None:
            file_path = Path(file_path)

         target_labels = os.getenv(TRIGGON_LOG_LABELS)
         if target_labels is not None:
            if "," in target_labels:
               labels = target_labels.split(",")
            else:
               labels = [target_labels]
            target_labels = [v.strip() for v in labels if v.strip()]

      return log_verbosity, file_path, target_labels

   def _read_arg(self, target_labels: str | Sequence[str]) -> LogConfig:
      if isinstance(target_labels, str):
         target_labels = (target_labels,)
      log_verbosity, file_path, _ = self._read_env()

      return log_verbosity, file_path, target_labels

   def _setup_file_handler(self, file_path) -> None:
      try:
         handler = logging.FileHandler(
            filename=file_path, 
            encoding="utf-8", 
            errors="backslashreplace",
         )
      except OSError as e:
         self._setup_stream_handler()
         self._logger.warning(
            "Failed to create the debug log file: %s. " 
            "Falling back to terminal output.",
            e,
         )
      else:    
         handler.setLevel(logging.DEBUG)
         handler.setFormatter(
            LevelSwitchFormatter(DEBUG_LOG_FMT, WARN_LOG_FMT)
         )
         self._logger.addHandler(handler)

   def _setup_stream_handler(self) -> None:
      # create handlers for debug and warning
      h_debug = logging.StreamHandler()  
      h_debug.setLevel(logging.DEBUG)
      h_debug.addFilter(lambda r: r.levelno == logging.DEBUG)
      h_debug.setFormatter(
         logging.Formatter(fmt=DEBUG_LOG_FMT, datefmt="%H:%M:%S")
      )

      h_warn = logging.StreamHandler() 
      h_warn.setLevel(logging.WARNING)
      h_warn.setFormatter(
         logging.Formatter(fmt=WARN_LOG_FMT, datefmt="%H:%M:%S")
      )

      self._logger.addHandler(h_debug)
      self._logger.addHandler(h_warn)


class LevelSwitchFormatter(logging.Formatter):
    def __init__(
        self,
        debug_fmt: str,
        warn_fmt: str,
        datefmt: str | None = None,
        warn_level: int = logging.WARNING,
    ) -> None:
        super().__init__(datefmt=datefmt)
        self._warn_level = warn_level
        self._debug = logging.Formatter(fmt=debug_fmt, datefmt=datefmt)
        self._warn = logging.Formatter(fmt=warn_fmt,  datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno >= self._warn_level:
            return self._warn.format(record)
        return self._debug.format(record)


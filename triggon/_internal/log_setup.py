import logging
import os
from pathlib import Path

from .arg_types import DebugTypes


type EnvTypes = tuple[int, Path | None, tuple[str, ...] | None] | None

TRIGGON_LOG_VERBOSITY = "TRIGGON_LOG_VERBOSITY" # 0-3
TRIGGON_LOG_FILE = "TRIGGON_LOG_FILE"
TRIGGON_LOG_LABELS = "TRIGGON_LOG_LABELS" # target labels to output

logger = logging.getLogger(__name__)


class LogSetup:
   def configure_debug(
         self, 
         arg: DebugTypes = None, 
         use_env: bool = False
   ) -> None:
      if use_env:
          values = self._read_env()
      else:
         values = self._read_arg(arg)

      if values:
         (log_verbosity, file_path, target_labels) = values

         debug_info = {
            TRIGGON_LOG_VERBOSITY: log_verbosity,
            TRIGGON_LOG_FILE: file_path,
            TRIGGON_LOG_LABELS: target_labels,
         }
         self.debug = debug_info

         if file_path is None:
            _setup_stream_handler()
         else:
            _setup_file_handler(file_path)

   def _read_env(self) -> EnvTypes:
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
            self.debug = False
            return

      file_path = os.getenv(TRIGGON_LOG_FILE)
      if file_path is not None:
         path = Path(file_path)
         # will fall back to terminal output on error
         file_path = path if path.parent.exists() else None

      target_labels = os.getenv(TRIGGON_LOG_LABELS)
      if target_labels is not None:
         if "," in target_labels:
            labels = target_labels.split(",")
         else:
            labels = [target_labels]
         target_labels = tuple(v.strip() for v in labels if v.strip())

      return log_verbosity, file_path, target_labels

   def _read_arg(self, arg: DebugTypes) -> EnvTypes:
      # Default: level 3, terminal output, all labels
      if isinstance(arg, bool):
         if not arg:
            self.debug = False
            return
         
         value = self._read_env()
         if value is None:
            log_verbosity = None
            file_path = None
            target_labels = None
         else:
            (log_verbosity, file_path, target_labels) = value
      else:
         if isinstance(arg, str):
            target_labels = (arg,)
         else:
            target_labels = tuple(arg)
         
         (log_verbosity, file_path, _) = self._read_env()

      if log_verbosity is None:
         log_verbosity = 3

      return log_verbosity, file_path, target_labels


def _setup_file_handler(file_path) -> None:
   if logger.handlers:
      return
   
   os_err = (
      "Failed to {proc} the debug log file; " 
      "falling back to terminal output"
   )

   fmt = logging.Formatter(fmt="%(asctime)s - %(message)s")
   try:
      handler = logging.FileHandler(
         filename=file_path, 
         encoding="utf-8", 
         errors="backslashreplace",
      )
   except OSError:
      _setup_stream_handler()
      logger.warning(os_err.format(proc="create"))
      return
   else:    
      logger.addHandler(handler)
      handler.setFormatter(fmt)

      logger.setLevel(logging.DEBUG)
      handler.setLevel(logging.DEBUG)


def _setup_stream_handler() -> None:
   if logger.handlers:
      return

   fmt = logging.Formatter(fmt="DEBUG - %(message)s")
   handler = logging.StreamHandler()
   logger.addHandler(handler)
   handler.setFormatter(fmt)

   logger.setLevel(logging.DEBUG)
   handler.setLevel(logging.DEBUG)
from pathlib import Path
from typing import Literal, Mapping, Sequence

# Literal
type DelayKey = Literal["trigger", "revert"]
type NumArg = Literal["after", "index", "indices"]

# Logging
type Verbosity = int
type LogFile = Path | None
type TargetLabels = Sequence[str] | None

# Mappings
type TriggerMap = dict[str, int]
type RevertMap = dict[str, None]

# Attiributes
type LabelToRefs = Mapping[str, Mapping[str, int]]

# API Arguments
type DebugArg = bool | LabelArg
type LabelArg = str | Sequence[str]
type IndexArg = int | Sequence[int]
type NameArg = str | Sequence[str]

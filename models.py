from enum import Enum
from typing import Optional

class CrashType(Enum):
    STACKSMASH = "stack smashing"
    SEGFAULT = "segmentation_fault"
    BUFFER_OVERFLOW = "buffer_overflow"
    USE_AFTER_FREE = "use_after_free"
    DOUBLE_FREE = "double_free"
    ABORT = "abort"
    INVALID_WRITE = "invalid_write"
    INVALID_READ = "invalid_read"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"

# Data structure for holding execution results
class ExecutionResult:
    def __init__(
        self,
        return_code: int,
        stdout: bytes,
        stderr: bytes,
        execution_time: float,
        crashed: bool = False,
        crash_type: Optional[CrashType] = None,
        signal: Optional[int] = None,
        fault_address: Optional[str] = None
    ):
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        self.execution_time = execution_time
        self.crashed = crashed
        self.crash_type = crash_type
        self.signal = signal
        self.fault_address = fault_address

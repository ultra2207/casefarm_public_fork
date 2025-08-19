from __future__ import annotations  # This enables forward references

import functools
import inspect
import os
import sys
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple

from loguru import logger

# Only import Logger during type checking, not at runtime
if TYPE_CHECKING:
    import loguru

# Context variable to track the current logging context
current_logging_context: ContextVar[Optional[str]] = ContextVar(
    "logging_context", default=None
)


# Function to calculate padding needed for right alignment
def format_with_padding(record: Dict[str, Any]) -> Dict[str, Any]:
    # Get terminal width for right-aligning file info
    terminal_width: int = os.get_terminal_size().columns
    # Use file.name instead of name for __main__
    module_name: str = (
        record["file"].name if record["name"] == "__main__" else record["name"]
    )

    # Extract the components we'll use in our format
    level: str = record["level"].name
    time_str: str = record["time"].strftime("%I:%M:%S %p")
    message: str = record["message"]
    function_name: str = record["function"]
    line: int = record["line"]

    file_info: str = f"{module_name}:{function_name}:{line}"

    # Calculate visible length of the content before file_info
    base_content: str = f"{level} | {time_str} | {message} "
    padding_needed: int = max(2, terminal_width - len(base_content) - len(file_info))

    # Return the padding as extra data
    record["extra"]["padding"] = " " * padding_needed
    record["extra"]["module_name"] = (
        module_name  # Add logging context information - always set it to avoid KeyError
    )
    context: Optional[str] = current_logging_context.get()
    record["extra"]["logging_context"] = context or ""

    return record


# Remove default handler
logger.remove()

# Add custom handler with padding and desired format for console
logger.configure(patcher=format_with_padding)
logger.add(
    sys.stdout,
    colorize=True,
    format="<level>{level}</level> | <green>{time:hh:mm:ss A}</green> | <level>{message}</level>{extra[padding]}<cyan>{extra[module_name]}</cyan><white>:</white><cyan>{function}</cyan><white>:</white><cyan>{line}</cyan>",
)

# Base log directory
LOG_DIR: str = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Keep the main app.log for general logging
logger.add(
    f"{LOG_DIR}/consolidated_logs/app.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message} | module={extra[module_name]} function={function} line={line} | context={extra[logging_context]}",
    rotation="50 GB",
    retention="3 months",
    enqueue=True,
)

# Dictionary to track added module handlers to avoid duplicates
_module_handlers: Dict[str, int] = {}


def get_custom_logger(
    module_name: Optional[str] = None, set_context: bool = True
) -> loguru.Logger:
    """
    Get a logger configured for a specific module.
    If no module_name is provided, it will auto-detect from the calling file.
    If set_context is True, this module becomes the logging context for subsequent calls.
    """
    if module_name is None:
        # Auto-detect module name from the calling file
        frame = inspect.currentframe().f_back
        if frame is None:
            raise RuntimeError("Could not determine calling frame")

        file_path: str = frame.f_globals["__file__"]
        module_name_tuple: Tuple[str, str] = os.path.splitext(
            os.path.basename(file_path)
        )
        module_name = module_name_tuple[0]  # Get just the name without extension

    # Set logging context if requested and not already set
    if set_context and current_logging_context.get() is None:
        current_logging_context.set(module_name)

    # Add module-specific file handler if not already added
    if module_name not in _module_handlers:

        def log_filter(record: Dict[str, Any], mod: str = module_name) -> bool:
            return _should_log_to_module(record, mod)

        handler_id: int = logger.add(
            f"{LOG_DIR}/{module_name}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message} | module={extra[module_name]} function={function} line={line}",
            rotation="50 GB",  # Changed from "10 MB"
            retention="10 years",  # Changed from "1 week"
            enqueue=True,
            filter=log_filter,
        )
        _module_handlers[module_name] = handler_id

    # Return logger bound with module context
    return logger.bind(module=module_name)


def _should_log_to_module(record: Dict[str, Any], target_module: str) -> bool:
    """
    Determine if a log record should go to a specific module's log file.
    Logs go to a module file if:
    1. The record comes directly from that module, OR
    2. The logging context is set to that module (meaning this module initiated the call chain)
    """
    current_module: str = record["extra"].get("module_name", "").replace(".py", "")
    logging_context: Optional[str] = record["extra"].get("logging_context")

    # Log if this is the direct module or if this module is the logging context
    return current_module == target_module or logging_context == target_module


def with_logging_context(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator that ensures a function runs within the current logging context.
    Useful for utility functions that should inherit the caller's logging context.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Preserve the current context during function execution
        context: Optional[str] = current_logging_context.get()
        if context is None:
            # If no context is set, try to determine it from the calling frame
            frame = inspect.currentframe().f_back
            if frame is not None:
                file_path: str = frame.f_globals["__file__"]
                caller_module_tuple: Tuple[str, str] = os.path.splitext(
                    os.path.basename(file_path)
                )
                caller_module: str = caller_module_tuple[0]
                current_logging_context.set(caller_module)

        try:
            return func(*args, **kwargs)
        finally:
            # Context is automatically restored due to context variable behavior
            pass

    return wrapper


# Export the configured logger and factory function
configured_logger = logger

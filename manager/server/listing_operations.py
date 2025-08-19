import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml
from fastapi import WebSocket
from pydantic import BaseModel


def load_config():
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()
ROOT_DIR = _config["ROOT_DIR"]
sys.path.insert(0, ROOT_DIR)

from utils.logger import get_custom_logger

logger = get_custom_logger()

# Type aliases
TaskId = str
Username = str


class StartListingRequest(BaseModel):
    usernames: List[str]


class TaskResponse(BaseModel):
    task_id: str
    status: str


class TaskData(BaseModel):
    status: str
    current: int
    total: int
    message: str
    usernames: List[str] = []
    result: Optional[bool] = None
    error: Optional[str] = None
    started_at: float
    completed_at: Optional[float] = None
    stopped_at: Optional[float] = None
    percentage: float = 0.0


class TaskManager:
    def __init__(self):
        self.task_progress: Dict[TaskId, TaskData] = {}
        self.progress_connections: Dict[TaskId, Set[WebSocket]] = {}
        self.log_connections: Set[WebSocket] = set()
        self.running_tasks: Set[TaskId] = set()
        self.log_file_path = Path(
            r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\logs\steam_items_lister.log"
        )
        self._task_counter = 0

    def create_task(self, usernames: List[str], total_items: int = 100) -> TaskId:
        """Create a new task with auto-generated UUID"""
        task_id = str(uuid.uuid4())

        self.task_progress[task_id] = TaskData(
            status="starting",
            current=0,
            total=total_items,
            message="Initializing...",
            usernames=usernames,
            started_at=time.time(),
        )
        self.running_tasks.add(task_id)
        self.progress_connections[task_id] = set()

        logger.info(f"Created task {task_id} for usernames: {usernames}")
        return task_id

    async def update_task_progress(
        self, task_id: TaskId, current: int, total: int, message: str
    ) -> None:
        """Update task progress and notify connected clients"""
        if task_id not in self.task_progress:
            logger.warning(f"Attempted to update non-existent task: {task_id}")
            return

        percentage = (current / total * 100) if total > 0 else 0
        task_data = self.task_progress[task_id]

        self.task_progress[task_id] = TaskData(
            status="running",
            current=current,
            total=total,
            message=message,
            usernames=task_data.usernames,
            started_at=task_data.started_at,
            percentage=percentage,
        )

        # Notify connected clients
        await self._notify_progress_clients(task_id)

    async def complete_task(self, task_id: TaskId, result: bool, message: str) -> None:
        """Mark task as completed and notify clients"""
        if task_id not in self.task_progress:
            return

        task_data = self.task_progress[task_id]
        self.task_progress[task_id] = TaskData(
            status="completed",
            current=task_data.total,
            total=task_data.total,
            message=message,
            usernames=task_data.usernames,
            result=result,
            started_at=task_data.started_at,
            completed_at=time.time(),
            percentage=100.0,
        )
        self.running_tasks.discard(task_id)

        # Notify connected clients
        await self._notify_progress_clients(task_id)
        logger.info(f"Task {task_id} completed with result: {result}")

    async def error_task(self, task_id: TaskId, error: str) -> None:
        """Mark task as errored and notify clients"""
        if task_id not in self.task_progress:
            return

        task_data = self.task_progress[task_id]
        self.task_progress[task_id] = TaskData(
            status="error",
            current=task_data.current,
            total=task_data.total,
            message=f"Error: {error}",
            usernames=task_data.usernames,
            error=error,
            started_at=task_data.started_at,
            completed_at=time.time(),
            percentage=task_data.percentage,
        )
        self.running_tasks.discard(task_id)

        # Notify connected clients
        await self._notify_progress_clients(task_id)
        logger.error(f"Task {task_id} failed with error: {error}")

    async def stop_task(self, task_id: TaskId) -> bool:
        """Mark a task as stopped and notify clients"""
        if task_id not in self.task_progress:
            return False

        task_data = self.task_progress[task_id]
        self.task_progress[task_id] = TaskData(
            status="stopped",
            current=task_data.current,
            total=task_data.total,
            message="Task stopped by user request",
            usernames=task_data.usernames,
            started_at=task_data.started_at,
            completed_at=time.time(),
            stopped_at=time.time(),
            percentage=task_data.percentage,
        )
        self.running_tasks.discard(task_id)

        # Notify connected clients
        await self._notify_progress_clients(task_id)
        logger.info(f"Task {task_id} stopped by user request")
        return True

    def get_task_data(self, task_id: TaskId) -> Optional[TaskData]:
        """Get task data"""
        return self.task_progress.get(task_id)

    def get_all_tasks(self) -> Dict[TaskId, TaskData]:
        """Get all tasks"""
        return self.task_progress.copy()

    async def delete_task(self, task_id: TaskId) -> bool:
        """Delete a task and clean up connections"""
        if task_id not in self.task_progress:
            return False

        # Close all WebSocket connections for this task
        if task_id in self.progress_connections:
            connections = self.progress_connections[task_id].copy()
            for websocket in connections:
                try:
                    await websocket.close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket connection: {e}")
            del self.progress_connections[task_id]

        del self.task_progress[task_id]
        self.running_tasks.discard(task_id)

        logger.info(f"Deleted task {task_id}")
        return True

    def add_progress_connection(self, task_id: TaskId, websocket: WebSocket) -> None:
        """Add WebSocket connection for task progress"""
        if task_id not in self.progress_connections:
            self.progress_connections[task_id] = set()
        self.progress_connections[task_id].add(websocket)
        logger.debug(f"Added progress connection for task {task_id}")

    def remove_progress_connection(self, task_id: TaskId, websocket: WebSocket) -> None:
        """Remove WebSocket connection for task progress"""
        if task_id in self.progress_connections:
            self.progress_connections[task_id].discard(websocket)
            if not self.progress_connections[task_id]:
                del self.progress_connections[task_id]
            logger.debug(f"Removed progress connection for task {task_id}")

    def add_log_connection(self, websocket: WebSocket) -> None:
        """Add WebSocket connection for logs"""
        self.log_connections.add(websocket)
        logger.debug("Added log connection")

    def remove_log_connection(self, websocket: WebSocket) -> None:
        """Remove WebSocket connection for logs"""
        self.log_connections.discard(websocket)
        logger.debug("Removed log connection")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        return {
            "active_tasks": len(self.running_tasks),
            "total_tasks": len(self.task_progress),
            "log_connections": len(self.log_connections),
            "progress_connections": sum(
                len(conns) for conns in self.progress_connections.values()
            ),
            "tasks_by_status": self._get_tasks_by_status(),
        }

    def _get_tasks_by_status(self) -> Dict[str, int]:
        """Get count of tasks by status"""
        status_counts = {}
        for task_data in self.task_progress.values():
            status = task_data.status
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts

    async def _notify_progress_clients(self, task_id: TaskId) -> None:
        """Notify all connected clients about task progress"""
        if task_id not in self.progress_connections:
            return

        task_data = self.task_progress.get(task_id)
        if not task_data:
            return

        message = {
            "type": "progress_update",
            "task_id": task_id,
            "data": task_data.model_dump(),
        }

        disconnected_clients = set()

        for websocket in self.progress_connections[task_id]:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket client: {e}")
                disconnected_clients.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected_clients:
            self.remove_progress_connection(task_id, websocket)

    async def notify_log_clients(self, log_message: str) -> None:
        """Notify all log clients about new log entries"""
        if not self.log_connections:
            return

        message = {
            "type": "log_update",
            "message": log_message,
            "timestamp": time.time(),
        }

        disconnected_clients = set()

        for websocket in self.log_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send log message to WebSocket client: {e}")
                disconnected_clients.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected_clients:
            self.remove_log_connection(websocket)

    def is_task_running(self, task_id: TaskId) -> bool:
        """Check if a task is currently running"""
        return task_id in self.running_tasks

    def get_running_tasks(self) -> List[TaskId]:
        """Get list of currently running task IDs"""
        return list(self.running_tasks)

    async def cleanup_completed_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed tasks"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        tasks_to_delete = []

        for task_id, task_data in self.task_progress.items():
            if (
                task_data.status in ["completed", "error", "stopped"]
                and task_data.completed_at
                and current_time - task_data.completed_at > max_age_seconds
            ):
                tasks_to_delete.append(task_id)

        for task_id in tasks_to_delete:
            await self.delete_task(task_id)

        logger.info(f"Cleaned up {len(tasks_to_delete)} old tasks")
        return len(tasks_to_delete)


# Global task manager instance
task_manager = TaskManager()


# Log file monitoring
log_file_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\logs\steam_items_lister.log"
log_monitor_task = None
last_log_position = 0


async def send_progress_update(
    websocket: WebSocket, task_id: TaskId, current: int, total: int, message: str
) -> None:
    """Send progress update to websocket"""
    try:
        percentage = (current / total * 100) if total > 0 else 0
        await websocket.send_json(
            {
                "type": "progress",
                "task_id": task_id,
                "current": current,
                "total": total,
                "message": message,
                "percentage": percentage,
            }
        )
    except Exception:
        task_manager.remove_progress_connection(task_id, websocket)


async def send_completion_update(
    websocket: WebSocket, task_id: TaskId, result: bool
) -> None:
    """Send completion update to websocket"""
    try:
        task_data = task_manager.get_task_data(task_id)
        if task_data:
            await websocket.send_json(
                {
                    "type": "completed",
                    "task_id": task_id,
                    "result": result,
                    "message": task_data.message,
                    "current": task_data.current,
                    "total": task_data.total,
                    "percentage": task_data.percentage,
                }
            )
    except Exception:
        task_manager.remove_progress_connection(task_id, websocket)


async def send_error_update(websocket: WebSocket, task_id: TaskId, error: str) -> None:
    """Send error update to websocket"""
    try:
        task_data = task_manager.get_task_data(task_id)
        if task_data:
            await websocket.send_json(
                {
                    "type": "error",
                    "task_id": task_id,
                    "error": error,
                    "message": task_data.message,
                    "current": task_data.current,
                    "total": task_data.total,
                    "percentage": task_data.percentage,
                }
            )
    except Exception:
        task_manager.remove_progress_connection(task_id, websocket)


async def send_stop_update(websocket: WebSocket, task_id: TaskId) -> None:
    """Send stop update to websocket"""
    try:
        task_data = task_manager.get_task_data(task_id)
        if task_data:
            await websocket.send_json(
                {
                    "type": "stopped",
                    "task_id": task_id,
                    "message": task_data.message,
                    "current": task_data.current,
                    "total": task_data.total,
                    "percentage": task_data.percentage,
                    "stopped_reason": "User requested stop",
                }
            )
    except Exception:
        task_manager.remove_progress_connection(task_id, websocket)


async def run_items_lister(task_id: TaskId, usernames: List[str]) -> None:
    """Run the items lister in background"""
    try:
        # Import here to avoid circular imports
        from utils.steam_items_lister import items_lister

        def progress_callback(current: int, total: int, message: str) -> bool:
            """Callback to update progress - returns False to stop"""
            # Check if task was stopped
            if task_id in task_manager.task_progress:
                if task_manager.task_progress[task_id].status == "stopped":
                    return False  # Signal to stop the operation

            task_manager.update_task_progress(task_id, current, total, message)

            # Send progress to connected WebSockets (non-blocking)
            if task_id in task_manager.progress_connections:
                for websocket in task_manager.progress_connections[task_id].copy():
                    asyncio.create_task(
                        send_progress_update(
                            websocket, task_id, current, total, message
                        )
                    )

            return True  # Continue operation

        # Check if stopped before starting
        if (
            task_id in task_manager.task_progress
            and task_manager.task_progress[task_id].status == "stopped"
        ):
            return

        # Run the items lister with stop checking
        result: bool = await items_lister(
            steam_usernames=usernames, progress_callback=progress_callback
        )

        # Check if task was stopped during execution
        if (
            task_id in task_manager.task_progress
            and task_manager.task_progress[task_id].status == "stopped"
        ):
            # Send stopped notification
            if task_id in task_manager.progress_connections:
                for websocket in task_manager.progress_connections[task_id].copy():
                    asyncio.create_task(send_stop_update(websocket, task_id))
            return

        # Update final status
        message = "Completed successfully!" if result else "Completed with errors"
        task_manager.complete_task(task_id, result, message)

        # Send completion notification
        if task_id in task_manager.progress_connections:
            for websocket in task_manager.progress_connections[task_id].copy():
                asyncio.create_task(send_completion_update(websocket, task_id, result))

    except Exception as e:
        logger.error(f"Error in items lister: {e}")
        error_msg = str(e)
        task_manager.error_task(task_id, error_msg)

        # Send error notification
        if task_id in task_manager.progress_connections:
            for websocket in task_manager.progress_connections[task_id].copy():
                asyncio.create_task(send_error_update(websocket, task_id, error_msg))


async def handle_progress_websocket(websocket: WebSocket, task_id: str) -> None:
    """Handle WebSocket connection for progress updates"""
    await websocket.accept()
    task_manager.add_progress_connection(task_id, websocket)

    try:
        # Send current task data if available
        task_data = task_manager.get_task_data(task_id)
        if task_data:
            await websocket.send_json(
                {
                    "type": "progress"
                    if task_data.status == "running"
                    else task_data.status,
                    "task_id": task_id,
                    "current": task_data.current,
                    "total": task_data.total,
                    "message": task_data.message,
                    "percentage": task_data.percentage,
                    "result": task_data.result,
                    "error": task_data.error,
                }
            )

        # Keep connection alive
        while True:
            try:
                await websocket.receive_text()
            except Exception:
                break

    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
    finally:
        task_manager.remove_progress_connection(task_id, websocket)


async def monitor_log_file() -> None:
    """Monitor log file for new entries"""
    global last_log_position

    while True:
        try:
            if os.path.exists(log_file_path):
                with open(log_file_path, "r", encoding="utf-8") as f:
                    f.seek(last_log_position)
                    new_lines = f.readlines()
                    last_log_position = f.tell()

                    for line in new_lines:
                        line = line.strip()
                        if line and task_manager.log_connections:
                            log_data = {
                                "type": "log",
                                "message": line,
                                "timestamp": time.time(),
                                "error": "ERROR" in line.upper()
                                or "EXCEPTION" in line.upper(),
                                "info": "INFO" in line.upper(),
                                "separator": "=" * 10 in line,
                            }

                            # Send to all connected log WebSockets
                            disconnected = []
                            for websocket in task_manager.log_connections:
                                try:
                                    await websocket.send_json(log_data)
                                except Exception:
                                    disconnected.append(websocket)

                            # Remove disconnected WebSockets
                            for ws in disconnected:
                                task_manager.remove_log_connection(ws)

            await asyncio.sleep(0.5)  # Poll every 500ms

        except Exception as e:
            logger.error(f"Error monitoring log file: {e}")
            await asyncio.sleep(1)


async def handle_logs_websocket(websocket: WebSocket) -> None:
    """Handle WebSocket connection for log updates"""
    await websocket.accept()
    task_manager.add_log_connection(websocket)

    try:
        # Send historical logs if file exists
        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    # Send last 50 lines as historical
                    for line in lines[-50:]:
                        line = line.strip()
                        if line:
                            await websocket.send_json(
                                {
                                    "type": "log",
                                    "message": line,
                                    "timestamp": time.time(),
                                    "historical": True,
                                    "error": "ERROR" in line.upper(),
                                    "info": "INFO" in line.upper(),
                                    "separator": "=" * 10 in line,
                                }
                            )
            except Exception as e:
                logger.error(f"Error sending historical logs: {e}")

        # Keep connection alive
        while True:
            try:
                await websocket.receive_text()
            except Exception:
                break

    except Exception as e:
        logger.error(f"Logs WebSocket error: {e}")
    finally:
        task_manager.remove_log_connection(websocket)


async def start_log_monitor() -> None:
    """Start log file monitoring"""
    global log_monitor_task
    if log_monitor_task is None:
        log_monitor_task = asyncio.create_task(monitor_log_file())
        logger.info("Log monitor started")


async def stop_log_monitor() -> None:
    """Stop log file monitoring"""
    global log_monitor_task
    if log_monitor_task:
        log_monitor_task.cancel()
        log_monitor_task = None
        logger.info("Log monitor stopped")


def get_health_stats() -> Dict:
    """Get health statistics"""
    stats = task_manager.get_stats()
    stats["log_file_exists"] = os.path.exists(log_file_path)
    return stats

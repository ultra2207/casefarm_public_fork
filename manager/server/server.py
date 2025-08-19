import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional, Sequence, Union

import uvicorn

# Add the import for get_db_price
import yaml
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse


def load_config():
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()
ROOT_DIR = _config["ROOT_DIR"]
sys.path.insert(0, ROOT_DIR)

# Import database service and models
from db_operations import (
    AccountCreate,
    AccountUpdate,
    DatabaseService,
    Item,
    ItemCreate,
    ItemUpdate,
    create_db_and_tables,
)

# Import listing operations
from listing_operations import (
    StartListingRequest,
    TaskData,
    TaskResponse,
    get_health_stats,
    handle_logs_websocket,
    handle_progress_websocket,
    run_items_lister,
    send_stop_update,
    start_log_monitor,
    stop_log_monitor,
    task_manager,
)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan."""
    # Startup
    create_db_and_tables()

    # Start log monitoring for listing operations
    await start_log_monitor()

    yield

    # Shutdown
    await stop_log_monitor()


# FastAPI Application
app: FastAPI = FastAPI(
    title="CaseFarm Database API", version="1.0.0", lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Avatar serving endpoint
@app.get("/avatars/{filename}")
async def get_avatar(filename: str) -> FileResponse:
    """Serve avatar images."""
    avatar_path = DatabaseService.get_avatar_path_by_filename(filename)
    if not avatar_path:
        raise HTTPException(status_code=404, detail="Avatar not found")

    return FileResponse(
        avatar_path, media_type="image/jpeg", headers={"Cache-Control": "max-age=3600"}
    )


# Account endpoints
@app.get("/accounts/", response_model=list[Dict[str, Any]])
def get_accounts(
    offset: int = 0, limit: int = Query(default=100, le=1000, ge=1)
) -> list[Dict[str, Any]]:
    """Get all accounts with pagination."""
    return DatabaseService.get_all_accounts(offset, limit)


@app.get("/accounts/{account_id}", response_model=Dict[str, Any])
def get_account(account_id: int) -> Dict[str, Any]:
    """Get a specific account by ID."""
    return DatabaseService.get_account_by_id(account_id)


@app.post("/accounts/", response_model=Dict[str, Any])
def create_account(account: AccountCreate) -> Dict[str, Any]:
    """Create a new account."""
    return DatabaseService.create_account(account)


@app.patch("/accounts/{account_id}", response_model=Dict[str, Any])
def update_account(account_id: int, account: AccountUpdate) -> Dict[str, Any]:
    """Update an existing account."""
    return DatabaseService.update_account(account_id, account)


@app.delete("/accounts/{account_id}")
def delete_account(account_id: int) -> Dict[str, bool]:
    """Delete an account."""
    return DatabaseService.delete_account(account_id)


# Items endpoints
@app.get("/items/", response_model=list[Item])
async def get_items(
    offset: int = 0, limit: int = Query(default=100, le=1000, ge=1)
) -> Sequence[Item]:
    """Get all items with pagination."""
    return await DatabaseService.get_all_items(offset, limit)


@app.get("/items/{asset_id}", response_model=Item)
def get_item(asset_id: str) -> Item:
    """Get a specific item by asset_id."""
    return DatabaseService.get_item_by_id(asset_id)


@app.get("/items/by-username/{steam_username}", response_model=list[Item])
async def get_items_by_username(
    steam_username: str, offset: int = 0, limit: int = Query(default=100, le=1000, ge=1)
) -> list[Item]:
    """Get all items for a specific steam username."""
    return await DatabaseService.get_items_by_username(steam_username, offset, limit)


@app.post("/items/", response_model=Item)
def create_item(item: ItemCreate) -> Item:
    """Create a new item."""
    return DatabaseService.create_item(item)


@app.patch("/items/{asset_id}", response_model=Item)
def update_item(asset_id: str, item: ItemUpdate) -> Item:
    """Update an existing item."""
    return DatabaseService.update_item(asset_id, item)


@app.delete("/items/{asset_id}")
def delete_item(asset_id: str) -> Dict[str, bool]:
    """Delete an item."""
    return DatabaseService.delete_item(asset_id)


# Utility endpoints
@app.get("/accounts/count")
def get_accounts_count() -> Dict[str, int]:
    """Get total number of accounts."""
    count = DatabaseService.get_accounts_count()
    return {"total_accounts": count}


@app.get("/items/count")
def get_items_count() -> Dict[str, int]:
    """Get total number of items."""
    count = DatabaseService.get_items_count()
    return {"total_items": count}


@app.get("/accounts/search")
def search_accounts(
    steam_username: Optional[str] = None,
    email_id: Optional[str] = None,
    status: Optional[str] = None,
    region: Optional[str] = None,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
) -> list[Dict[str, Any]]:
    """Search accounts by various criteria."""
    return DatabaseService.search_accounts(
        steam_username, email_id, status, region, offset, limit
    )


@app.get("/accounts/by-status/{status}")
def get_accounts_by_status(
    status: str, offset: int = 0, limit: int = Query(default=100, le=100)
) -> list[Dict[str, Any]]:
    """Get accounts filtered by status."""
    return DatabaseService.get_accounts_by_status(status, offset, limit)


@app.get("/accounts/by-region/{region}")
def get_accounts_by_region(
    region: str, offset: int = 0, limit: int = Query(default=100, le=100)
) -> list[Dict[str, Any]]:
    """Get accounts filtered by region."""
    return DatabaseService.get_accounts_by_region(region, offset, limit)


# ========================
# LISTING OPERATIONS
# ========================


@app.post("/start-listing", response_model=TaskResponse)
async def start_listing(
    request: StartListingRequest, background_tasks: BackgroundTasks
) -> TaskResponse:
    """Start the items listing process for given usernames"""
    task_id = task_manager.create_task(request.usernames)

    # Add background task
    background_tasks.add_task(run_items_lister, task_id, request.usernames)

    return TaskResponse(task_id=task_id, status="started")


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> Union[TaskData, Dict[str, str]]:
    """Get current task status"""
    task_data = task_manager.get_task_data(task_id)
    if task_data:
        return task_data
    else:
        return {"error": "Task not found"}


@app.get("/tasks")
async def get_all_tasks() -> Dict[str, TaskData]:
    """Get all task statuses"""
    return task_manager.get_all_tasks()


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str) -> Dict[str, str]:
    """Delete a task from memory"""
    if task_manager.delete_task(task_id):
        # Close all WebSocket connections for this task
        if task_id in task_manager.progress_connections:
            for websocket in task_manager.progress_connections[task_id].copy():
                try:
                    await websocket.close()
                except Exception:
                    pass
        return {"message": "Task deleted"}
    else:
        return {"error": "Task not found"}


@app.post("/tasks/{task_id}/stop")
async def stop_task_endpoint(task_id: str) -> Dict[str, str]:
    """Stop a running task"""
    stopped = await task_manager.stop_task(task_id)
    if not stopped:
        raise HTTPException(status_code=404, detail="Task not found")

    # Notify all connected WebSockets about the stop
    if task_id in task_manager.progress_connections:
        for websocket in task_manager.progress_connections[task_id].copy():
            try:
                await send_stop_update(websocket, task_id)
            except Exception:
                task_manager.remove_progress_connection(task_id, websocket)

    return {"message": "Task stop requested", "task_id": task_id}


@app.websocket("/ws/progress/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str) -> None:
    """WebSocket endpoint for progress updates"""
    await handle_progress_websocket(websocket, task_id)


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket) -> None:
    """WebSocket endpoint for log streaming"""
    await handle_logs_websocket(websocket)


# ========================
# HEALTH AND ROOT
# ========================


@app.get("/health")
def health_check() -> Dict[str, Union[str, bool, int]]:
    """Health check endpoint."""
    base_health = {"status": "healthy", "message": "CaseFarm Database API is running"}
    listing_health = get_health_stats()
    return {**base_health, **listing_health}


@app.get("/")
def read_root() -> Dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "CaseFarm Database API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)

import os
import time
from typing import Any, Dict, Generator, Optional, Sequence

from fastapi import HTTPException
from sqlmodel import Field, Session, SQLModel, create_engine, select

from utils.items_data_updater import update_items

# Clear metadata to prevent table redefinition errors
SQLModel.metadata.clear()


# Database Models
class Account(SQLModel, table=True):
    __tablename__ = "accounts"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    steam_username: Optional[str] = None
    steam_password: Optional[str] = None
    email_id: Optional[str] = None
    email_password: Optional[str] = None
    prime: Optional[int] = None
    active_armoury_passes: Optional[int] = None
    steamguard: Optional[str] = None
    steam_balance: Optional[float] = None
    steam_shared_secret: Optional[str] = None
    steam_identity_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    steam_id: Optional[int] = None
    trade_token: Optional[str] = None
    trade_url: Optional[str] = None
    steam_avatar_path: Optional[str] = None
    bot_id: Optional[str] = None
    num_armoury_stars: Optional[int] = None
    xp_level: int = Field(default=0)
    service_medal: Optional[str] = Field(default=None)
    status: Optional[str] = None
    xp: int = Field(default=0)
    region: Optional[str] = None
    currency: Optional[str] = None
    pass_value: float = Field(default=0.0)
    pua: int = Field(default=0)
    fua: int = Field(default=0)
    vac_ban: int = Field(default=0)


class Item(SQLModel, table=True):
    __tablename__ = "items"
    __table_args__ = {"extend_existing": True}

    asset_id: str = Field(primary_key=True)
    market_hash_name: str
    tradable_after_ist: Optional[str] = None
    tradable_after_unix: Optional[int] = None
    steam_username: str
    marketable: int = Field(default=0)
    tradable: int = Field(default=0)


# Request/Response Models
class AccountCreate(SQLModel):
    steam_username: Optional[str] = None
    steam_password: Optional[str] = None
    email_id: Optional[str] = None
    email_password: Optional[str] = None
    prime: Optional[int] = None
    active_armoury_passes: Optional[int] = None
    steamguard: Optional[str] = None
    steam_balance: Optional[float] = None
    steam_shared_secret: Optional[str] = None
    steam_identity_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    steam_id: Optional[int] = None
    trade_token: Optional[str] = None
    trade_url: Optional[str] = None
    steam_avatar_path: Optional[str] = None
    bot_id: Optional[str] = None
    num_armoury_stars: Optional[int] = None
    xp_level: int = Field(default=0)
    service_medal: Optional[str] = Field(default=None)
    status: Optional[str] = None
    xp: int = Field(default=0)
    region: Optional[str] = None
    currency: Optional[str] = None
    pass_value: float = Field(default=0.0)
    pua: int = Field(default=0)
    fua: int = Field(default=0)
    vac_ban: int = Field(default=0)


class AccountUpdate(SQLModel):
    steam_username: Optional[str] = None
    steam_password: Optional[str] = None
    email_id: Optional[str] = None
    email_password: Optional[str] = None
    prime: Optional[int] = None
    active_armoury_passes: Optional[int] = None
    steamguard: Optional[str] = None
    steam_balance: Optional[float] = None
    steam_shared_secret: Optional[str] = None
    steam_identity_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    steam_id: Optional[int] = None
    trade_token: Optional[str] = None
    trade_url: Optional[str] = None
    steam_avatar_path: Optional[str] = None
    bot_id: Optional[str] = None
    num_armoury_stars: Optional[int] = None
    xp_level: Optional[int] = None
    service_medal: Optional[str] = None
    status: Optional[str] = None
    xp: Optional[int] = None
    region: Optional[str] = None
    currency: Optional[str] = None
    pass_value: Optional[float] = None
    pua: Optional[int] = None
    fua: Optional[int] = None
    vac_ban: Optional[int] = None


class ItemCreate(SQLModel):
    asset_id: str
    market_hash_name: str
    tradable_after_ist: Optional[str] = None
    tradable_after_unix: Optional[int] = None
    steam_username: str
    marketable: int = Field(default=0)
    tradable: int = Field(default=0)


class ItemUpdate(SQLModel):
    market_hash_name: Optional[str] = None
    tradable_after_ist: Optional[str] = None
    tradable_after_unix: Optional[int] = None
    steam_username: Optional[str] = None
    marketable: Optional[int] = None
    tradable: Optional[int] = None


# Database connection setup
database_path: str = (
    r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\database.db"
)
sqlite_url: str = f"sqlite:///{database_path}"
connect_args: Dict[str, bool] = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables() -> None:
    """Create database tables."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, Any, None]:
    """Get database session."""
    with Session(engine) as session:
        yield session


def process_account_avatar(
    account: Account, base_url: str = "http://127.0.0.1:8000"
) -> Dict[str, Any]:
    """Process account to include proper avatar URL."""
    account_dict = account.model_dump()

    # Convert local path to URL
    if account.steam_avatar_path and os.path.exists(account.steam_avatar_path):
        # Extract filename from path
        filename = os.path.basename(account.steam_avatar_path)
        account_dict["steam_avatar_url"] = f"{base_url}/avatars/{filename}"
    else:
        account_dict["steam_avatar_url"] = None

    return account_dict


# Database Service Layer - High-level functions that handle sessions internally
class DatabaseService:
    """High-level database service that manages sessions internally."""

    @staticmethod
    async def check_and_update_items_if_needed() -> None:
        """Check if latest item is older than 3600 seconds and update if needed."""
        with Session(engine) as session:
            # Get the latest item by tradable_after_unix timestamp
            latest_item = session.exec(
                select(Item)
                .where(Item.tradable_after_unix.is_not(None))
                .order_by(Item.tradable_after_unix.desc())
                .limit(1)
            ).first()

            if latest_item and latest_item.tradable_after_unix:
                current_time = int(time.time())
                time_diff = current_time - latest_item.tradable_after_unix

                # If latest item is older than 3600 seconds (1 hour), update items
                if time_diff > 3600:
                    await update_items()

    @staticmethod
    def get_all_accounts(offset: int = 0, limit: int = 100) -> list[Dict[str, Any]]:
        """Get all accounts with pagination."""
        with Session(engine) as session:
            accounts: Sequence[Account] = session.exec(
                select(Account).offset(offset).limit(limit)
            ).all()
            return [process_account_avatar(account) for account in accounts]

    @staticmethod
    def get_account_by_id(account_id: int) -> Dict[str, Any]:
        """Get a specific account by ID."""
        with Session(engine) as session:
            account: Optional[Account] = session.get(Account, account_id)
            if not account:
                raise HTTPException(status_code=404, detail="Account not found")
            return process_account_avatar(account)

    @staticmethod
    def create_account(account_data: AccountCreate) -> Dict[str, Any]:
        """Create a new account."""
        with Session(engine) as session:
            db_account: Account = Account.model_validate(account_data)
            session.add(db_account)
            session.commit()
            session.refresh(db_account)
            return process_account_avatar(db_account)

    @staticmethod
    def update_account(account_id: int, account_data: AccountUpdate) -> Dict[str, Any]:
        """Update an existing account."""
        with Session(engine) as session:
            db_account: Optional[Account] = session.get(Account, account_id)
            if not db_account:
                raise HTTPException(status_code=404, detail="Account not found")

            update_data: Dict[str, Any] = account_data.model_dump(exclude_unset=True)
            db_account.sqlmodel_update(update_data)
            session.add(db_account)
            session.commit()
            session.refresh(db_account)
            return process_account_avatar(db_account)

    @staticmethod
    def delete_account(account_id: int) -> Dict[str, bool]:
        """Delete an account."""
        with Session(engine) as session:
            account: Optional[Account] = session.get(Account, account_id)
            if not account:
                raise HTTPException(status_code=404, detail="Account not found")

            session.delete(account)
            session.commit()
            return {"ok": True}

    @staticmethod
    def search_accounts(
        steam_username: Optional[str] = None,
        email_id: Optional[str] = None,
        status: Optional[str] = None,
        region: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Dict[str, Any]]:
        """Search accounts by various criteria."""
        with Session(engine) as session:
            query = select(Account)

            if steam_username:
                query = query.where(Account.steam_username.ilike(f"%{steam_username}%"))
            if email_id:
                query = query.where(Account.email_id.ilike(f"%{email_id}%"))
            if status:
                query = query.where(Account.status == status)
            if region:
                query = query.where(Account.region == region)

            accounts: list[Account] = list(
                session.exec(query.offset(offset).limit(limit)).all()
            )
            return [process_account_avatar(account) for account in accounts]

    @staticmethod
    def get_accounts_by_status(
        status: str, offset: int = 0, limit: int = 100
    ) -> list[Dict[str, Any]]:
        """Get accounts filtered by status."""
        with Session(engine) as session:
            accounts: list[Account] = list(
                session.exec(
                    select(Account)
                    .where(Account.status == status)
                    .offset(offset)
                    .limit(limit)
                ).all()
            )
            return [process_account_avatar(account) for account in accounts]

    @staticmethod
    def get_accounts_by_region(
        region: str, offset: int = 0, limit: int = 100
    ) -> list[Dict[str, Any]]:
        """Get accounts filtered by region."""
        with Session(engine) as session:
            accounts: list[Account] = list(
                session.exec(
                    select(Account)
                    .where(Account.region == region)
                    .offset(offset)
                    .limit(limit)
                ).all()
            )
            return [process_account_avatar(account) for account in accounts]

    @staticmethod
    def get_accounts_count() -> int:
        """Get total number of accounts."""
        with Session(engine) as session:
            return len(session.exec(select(Account)).all())

    @staticmethod
    async def get_all_items(offset: int = 0, limit: int = 100) -> Sequence[Item]:
        """Get all items with pagination. Checks and updates items if needed."""
        await DatabaseService.check_and_update_items_if_needed()
        with Session(engine) as session:
            return session.exec(select(Item).offset(offset).limit(limit)).all()

    @staticmethod
    def get_item_by_id(asset_id: str) -> Item:
        """Get a specific item by asset_id."""
        with Session(engine) as session:
            item: Optional[Item] = session.get(Item, asset_id)
            if not item:
                raise HTTPException(status_code=404, detail="Item not found")
            return item

    @staticmethod
    async def get_items_by_username(
        steam_username: str, offset: int = 0, limit: int = 100
    ) -> list[Item]:
        """Get all items for a specific steam username. Checks and updates items if needed."""
        await DatabaseService.check_and_update_items_if_needed()
        with Session(engine) as session:
            return list(
                session.exec(
                    select(Item)
                    .where(Item.steam_username == steam_username)
                    .offset(offset)
                    .limit(limit)
                ).all()
            )

    @staticmethod
    def create_item(item_data: ItemCreate) -> Item:
        """Create a new item."""
        with Session(engine) as session:
            db_item: Item = Item.model_validate(item_data)
            session.add(db_item)
            session.commit()
            session.refresh(db_item)
            return db_item

    @staticmethod
    def update_item(asset_id: str, item_data: ItemUpdate) -> Item:
        """Update an existing item."""
        with Session(engine) as session:
            db_item: Optional[Item] = session.get(Item, asset_id)
            if not db_item:
                raise HTTPException(status_code=404, detail="Item not found")

            update_data: Dict[str, Any] = item_data.model_dump(exclude_unset=True)
            db_item.sqlmodel_update(update_data)
            session.add(db_item)
            session.commit()
            session.refresh(db_item)
            return db_item

    @staticmethod
    def delete_item(asset_id: str) -> Dict[str, bool]:
        """Delete an item."""
        with Session(engine) as session:
            item: Optional[Item] = session.get(Item, asset_id)
            if not item:
                raise HTTPException(status_code=404, detail="Item not found")

            session.delete(item)
            session.commit()
            return {"ok": True}

    @staticmethod
    def get_items_count() -> int:
        """Get total number of items."""
        with Session(engine) as session:
            return len(session.exec(select(Item)).all())

    @staticmethod
    def get_avatar_path_by_filename(filename: str) -> Optional[str]:
        """Get avatar file path by filename."""
        with Session(engine) as session:
            accounts = session.exec(select(Account)).all()

            for account in accounts:
                if (
                    account.steam_avatar_path
                    and os.path.basename(account.steam_avatar_path) == filename
                ):
                    if os.path.exists(account.steam_avatar_path):
                        return account.steam_avatar_path
            return None

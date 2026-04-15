from datetime import datetime
from sqlalchemy import ForeignKey, String, Float, DateTime, Table, Column, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

watchlists = Table(
    "watchlists",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("item_id", ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[str] = mapped_column(String(100), unique=True)
    username: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    watchlist: Mapped[list["Item"]] = relationship(secondary=watchlists)
    def __repr__(self):
        return f"<User(id={self.id}, tg_id={self.telegram_id})>"

class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    market_hash_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    oracle_price: Mapped[float | None] = mapped_column(Float)
    trend: Mapped[float | None] = mapped_column(Float)
    history: Mapped[list["ItemHistory"]] = relationship(back_populates="item", cascade="all, delete-orphan")
    kalman_state_x: Mapped[str | None] = mapped_column(Text)
    kalman_state_p: Mapped[str | None] = mapped_column(Text)
    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.name}')>"

class ItemHistory(Base):
    __tablename__ = "item_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    price: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    kalman_price: Mapped[float | None] = mapped_column(Float)
    is_outlier: Mapped[bool] = mapped_column(default=False)
    item: Mapped["Item"] = relationship(back_populates="history")

    def __repr__(self):
        return f"<History(item_id={self.item_id}, price={self.price}, time={self.timestamp})>"
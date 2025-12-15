"""Database persistence for trade history.

Implements SQLite-based storage for trade data with query capabilities.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from kinetic_empire.models import Trade, TradeOpen, TradeClose, Regime, ExitReason


class TradePersistence:
    """Manages trade data persistence using SQLite.
    
    Stores complete trade history including entry/exit data and provides
    query capabilities for historical analysis and Kelly Criterion calculations.
    """

    def __init__(self, db_path: str = "data/trades.db"):
        """Initialize trade persistence.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_database()

    def _ensure_database(self) -> None:
        """Create database and tables if they don't exist."""
        # Create directory if needed
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    pair TEXT NOT NULL,
                    entry_timestamp TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stake_amount REAL NOT NULL,
                    regime TEXT NOT NULL,
                    stop_loss REAL NOT NULL,
                    amount REAL DEFAULT 0.0,
                    exit_timestamp TEXT,
                    exit_price REAL,
                    profit_loss REAL,
                    exit_reason TEXT
                )
            """)
            
            # Create indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pair 
                ON trades(pair)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entry_timestamp 
                ON trades(entry_timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_exit_timestamp 
                ON trades(exit_timestamp)
            """)
            
            conn.commit()

    def save_trade_open(self, trade: TradeOpen) -> None:
        """Persist opened trade.
        
        Stores: timestamp, pair, entry_price, stake_amount, regime
        
        Args:
            trade: Trade open data
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO trades (
                    id, pair, entry_timestamp, entry_price, stake_amount,
                    regime, stop_loss, amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.id,
                trade.pair,
                trade.timestamp.isoformat(),
                trade.entry_price,
                trade.stake_amount,
                trade.regime.value,
                trade.stop_loss,
                trade.amount
            ))
            conn.commit()

    def save_trade_close(self, trade: TradeClose) -> None:
        """Persist trade close data.
        
        Stores: exit_timestamp, exit_price, profit_loss, exit_reason
        
        Args:
            trade: Trade close data
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE trades
                SET exit_timestamp = ?,
                    exit_price = ?,
                    profit_loss = ?,
                    exit_reason = ?
                WHERE id = ?
            """, (
                trade.timestamp.isoformat(),
                trade.exit_price,
                trade.profit_loss,
                trade.exit_reason.value,
                trade.trade_id
            ))
            conn.commit()

    def get_trades_by_pair(
        self,
        pair: str,
        limit: int = 20,
        closed_only: bool = True
    ) -> list[Trade]:
        """Get recent trades for a specific pair.
        
        Args:
            pair: Trading pair symbol
            limit: Maximum number of trades to return
            closed_only: Only return closed trades
            
        Returns:
            List of trades, most recent first
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = """
                SELECT * FROM trades
                WHERE pair = ?
            """
            
            if closed_only:
                query += " AND exit_timestamp IS NOT NULL"
            
            query += " ORDER BY entry_timestamp DESC LIMIT ?"
            
            cursor = conn.execute(query, (pair, limit))
            rows = cursor.fetchall()
            
            return [self._row_to_trade(row) for row in rows]

    def get_trades_by_date_range(
        self,
        start: datetime,
        end: datetime,
        pair: Optional[str] = None
    ) -> list[Trade]:
        """Get trades within date range.
        
        Args:
            start: Start datetime (inclusive)
            end: End datetime (inclusive)
            pair: Optional pair filter
            
        Returns:
            List of trades in date range
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = """
                SELECT * FROM trades
                WHERE entry_timestamp >= ? AND entry_timestamp <= ?
            """
            params = [start.isoformat(), end.isoformat()]
            
            if pair:
                query += " AND pair = ?"
                params.append(pair)
            
            query += " ORDER BY entry_timestamp DESC"
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_trade(row) for row in rows]

    def get_trades_by_outcome(
        self,
        is_winner: bool,
        pair: Optional[str] = None,
        limit: Optional[int] = None
    ) -> list[Trade]:
        """Get trades filtered by outcome.
        
        Args:
            is_winner: True for winning trades, False for losing
            pair: Optional pair filter
            limit: Optional result limit
            
        Returns:
            List of trades matching outcome
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if is_winner:
                query = """
                    SELECT * FROM trades
                    WHERE profit_loss > 0
                """
            else:
                query = """
                    SELECT * FROM trades
                    WHERE profit_loss <= 0 AND profit_loss IS NOT NULL
                """
            
            params = []
            if pair:
                query += " AND pair = ?"
                params.append(pair)
            
            query += " ORDER BY entry_timestamp DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_trade(row) for row in rows]

    def _row_to_trade(self, row: sqlite3.Row) -> Trade:
        """Convert database row to Trade object.
        
        Args:
            row: SQLite row
            
        Returns:
            Trade object
        """
        return Trade(
            id=row["id"],
            pair=row["pair"],
            entry_timestamp=datetime.fromisoformat(row["entry_timestamp"]),
            entry_price=row["entry_price"],
            stake_amount=row["stake_amount"],
            regime=Regime(row["regime"]),
            stop_loss=row["stop_loss"],
            amount=row["amount"] or 0.0,
            exit_timestamp=(
                datetime.fromisoformat(row["exit_timestamp"])
                if row["exit_timestamp"]
                else None
            ),
            exit_price=row["exit_price"],
            profit_loss=row["profit_loss"],
            exit_reason=(
                ExitReason(row["exit_reason"])
                if row["exit_reason"]
                else None
            )
        )

    def get_all_trades(self, limit: Optional[int] = None) -> list[Trade]:
        """Get all trades.
        
        Args:
            limit: Optional result limit
            
        Returns:
            List of all trades
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM trades ORDER BY entry_timestamp DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            
            return [self._row_to_trade(row) for row in rows]

    def delete_trade(self, trade_id: str) -> bool:
        """Delete a trade by ID.
        
        Args:
            trade_id: Trade ID to delete
            
        Returns:
            True if trade was deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all_trades(self) -> None:
        """Delete all trades from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM trades")
            conn.commit()

"""SQLite veritabanı yönetimi."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from .config import config


@dataclass
class DownloadRecord:
    """İndirme kaydı."""
    id: Optional[int] = None
    url: str = ""
    title: str = ""
    channel: str = ""
    thumbnail: str = ""
    duration: int = 0
    quality: str = ""
    file_path: str = ""
    file_size: int = 0
    status: str = "completed"  # completed, failed
    error_message: str = ""
    downloaded_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Database:
    """SQLite veritabanı yöneticisi."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_dir = Path(config.download_dir)
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "yt_storm.db")
        
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Veritabanı tablolarını oluştur."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT,
                    channel TEXT,
                    thumbnail TEXT,
                    duration INTEGER DEFAULT 0,
                    quality TEXT,
                    file_path TEXT,
                    file_size INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'completed',
                    error_message TEXT,
                    downloaded_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # Create index for search
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_downloads_title 
                ON downloads(title)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_downloads_date 
                ON downloads(downloaded_at)
            """)
    
    def add_download(self, record: DownloadRecord) -> int:
        """İndirme kaydı ekle."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO downloads (
                    url, title, channel, thumbnail, duration,
                    quality, file_path, file_size, status, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.url, record.title, record.channel, record.thumbnail,
                record.duration, record.quality, record.file_path,
                record.file_size, record.status, record.error_message
            ))
            return cursor.lastrowid
    
    def get_downloads(
        self, 
        limit: int = 50, 
        offset: int = 0,
        search: str = "",
        status: str = ""
    ) -> List[DownloadRecord]:
        """İndirme geçmişini getir."""
        query = "SELECT * FROM downloads WHERE 1=1"
        params = []
        
        if search:
            query += " AND (title LIKE ? OR channel LIKE ? OR url LIKE ?)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY downloaded_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [DownloadRecord(**dict(row)) for row in rows]
    
    def get_download_count(self, search: str = "", status: str = "") -> int:
        """Toplam indirme sayısını getir."""
        query = "SELECT COUNT(*) FROM downloads WHERE 1=1"
        params = []
        
        if search:
            query += " AND (title LIKE ? OR channel LIKE ? OR url LIKE ?)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        with self._get_connection() as conn:
            return conn.execute(query, params).fetchone()[0]
    
    def delete_download(self, record_id: int) -> bool:
        """İndirme kaydını sil."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM downloads WHERE id = ?", (record_id,))
            return cursor.rowcount > 0
    
    def clear_history(self) -> int:
        """Tüm geçmişi temizle."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM downloads")
            return cursor.rowcount
    
    def get_stats(self) -> Dict[str, Any]:
        """İstatistikleri getir."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
            completed = conn.execute(
                "SELECT COUNT(*) FROM downloads WHERE status = 'completed'"
            ).fetchone()[0]
            failed = conn.execute(
                "SELECT COUNT(*) FROM downloads WHERE status = 'failed'"
            ).fetchone()[0]
            total_size = conn.execute(
                "SELECT COALESCE(SUM(file_size), 0) FROM downloads WHERE status = 'completed'"
            ).fetchone()[0]
            
            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "total_size": total_size,
                "total_size_formatted": self._format_size(total_size),
            }
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Boyutu okunabilir formata çevir."""
        if size_bytes == 0:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if abs(size_bytes) < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
    
    # Settings
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Ayar değerini getir."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]
            return default
    
    def set_setting(self, key: str, value: Any) -> None:
        """Ayar değerini kaydet."""
        with self._get_connection() as conn:
            value_str = json.dumps(value) if not isinstance(value, str) else value
            conn.execute("""
                INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
            """, (key, value_str))
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Tüm ayarları getir."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            settings = {}
            for row in rows:
                try:
                    settings[row[0]] = json.loads(row[1])
                except json.JSONDecodeError:
                    settings[row[0]] = row[1]
            return settings


# Global database instance
db = Database()

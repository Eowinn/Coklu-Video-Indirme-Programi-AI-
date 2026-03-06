"""İndirme kuyruğu yöneticisi."""

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum

from .downloader import Downloader, DownloadOptions
from .utils import truncate_text, has_ffmpeg


class JobStatus(str, Enum):
    """İş durumu."""
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    """İndirme işi."""
    id: str
    url: str
    title: str
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    logs: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Sözlük formatına dönüştür."""
        return {
            "title": self.title,
            "status": self.status.value,
            "progress": self.progress,
            "logs": self.logs[-60:],  # Son 60 log
        }


class JobManager:
    """İndirme işlerini yöneten sınıf."""
    
    def __init__(self, max_log_lines: int = 60):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self._max_log_lines = max_log_lines
        self._downloader = Downloader()
    
    def create_job(self, url: str) -> str:
        """Yeni iş oluştur ve ID döndür."""
        job_id = f"job_{int(time.time() * 1000)}_{len(self._jobs)}"
        short_url = truncate_text(url, 60)
        
        job = Job(
            id=job_id,
            url=url,
            title=short_url,
            logs=[f"Kuyrukta: {url}"]
        )
        
        with self._lock:
            self._jobs[job_id] = job
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """İş bilgilerini getir."""
        with self._lock:
            return self._jobs.get(job_id)
    
    def get_all_jobs(self) -> Dict[str, Dict]:
        """Tüm işleri sözlük olarak getir."""
        with self._lock:
            return {jid: job.to_dict() for jid, job in self._jobs.items()}
    
    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        title: Optional[str] = None,
        log_message: Optional[str] = None,
    ) -> None:
        """İş bilgilerini güncelle."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = progress
            if title is not None:
                job.title = truncate_text(title, 80)
            if log_message is not None:
                job.logs.append(log_message)
                if len(job.logs) > self._max_log_lines:
                    job.logs = job.logs[-self._max_log_lines:]
    
    def clear_finished(self) -> int:
        """Tamamlanan ve hatalı işleri temizle."""
        with self._lock:
            to_delete = [
                jid for jid, job in self._jobs.items()
                if job.status in (JobStatus.DONE, JobStatus.ERROR)
            ]
            for jid in to_delete:
                del self._jobs[jid]
            return len(to_delete)
    
    def start_download(
        self,
        job_id: str,
        quality: str,
        out_dir: str,
        is_playlist: bool = False,
        playlist_start: Optional[str] = None,
        playlist_end: Optional[str] = None,
    ) -> None:
        """İndirmeyi başlat (thread içinde çağrılmalı)."""
        job = self.get_job(job_id)
        if not job:
            return
        
        # Progress callback
        def on_progress(d: Dict) -> None:
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    pct = int(downloaded / total * 100)
                    self.update_job(job_id, progress=pct)
                
                speed = d.get("_speed_str", "")
                eta = d.get("_eta_str", "")
                self.update_job(
                    job_id,
                    log_message=f"[download] {d.get('_percent_str', '?').strip()} | {speed} | ETA {eta}"
                )
            elif d["status"] == "finished":
                self.update_job(job_id, progress=100, log_message="✅ Dosya indirildi…")
        
        # Durumu güncelle
        self.update_job(job_id, status=JobStatus.RUNNING)
        
        ffmpeg = has_ffmpeg()
        self.update_job(job_id, log_message=f"▶ Başladı: {job.url}")
        self.update_job(job_id, log_message=f"FFmpeg: {'var ✓' if ffmpeg else 'yok — muxed stream seçildi'}")
        
        try:
            options = DownloadOptions(
                url=job.url,
                quality=quality,
                out_dir=out_dir,
                is_playlist=is_playlist,
                playlist_start=int(playlist_start) if playlist_start and playlist_start.isdigit() else None,
                playlist_end=int(playlist_end) if playlist_end and playlist_end.isdigit() else None,
            )
            
            fmt, _ = self._downloader.get_format_string(quality)
            self.update_job(job_id, log_message=f"Format: {fmt}")
            
            info = self._downloader.download(options, on_progress)
            
            if info:
                title = info.get("title") or info.get("playlist_title") or ""
                if title:
                    self.update_job(job_id, title=title)
            
            self.update_job(
                job_id,
                status=JobStatus.DONE,
                progress=100,
                log_message="✅ Tamamlandı!"
            )
            
        except Exception as e:
            self.update_job(
                job_id,
                status=JobStatus.ERROR,
                log_message=f"ERROR: {e}"
            )


# Global job manager instance
job_manager = JobManager()

"""yt-dlp wrapper modülü."""

import os
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any, List
import yt_dlp

from .utils import has_ffmpeg


@dataclass
class DownloadOptions:
    """İndirme seçenekleri."""
    url: str
    quality: str = "720"
    out_dir: str = ""
    is_playlist: bool = False
    playlist_start: Optional[int] = None
    playlist_end: Optional[int] = None
    download_subtitles: bool = False
    subtitle_lang: str = "tr,en"  # Virgülle ayrılmış dil kodları


class Downloader:
    """yt-dlp ile video indirme sınıfı."""
    
    QUALITY_MAP = {
        "best": None,
        "1080": 1080,
        "720": 720,
        "480": 480,
        "360": 360,
    }
    
    def __init__(self, ffmpeg_available: Optional[bool] = None):
        self.ffmpeg_available = ffmpeg_available if ffmpeg_available is not None else has_ffmpeg()
    
    def get_format_string(self, quality: str) -> tuple[str, Dict[str, Any]]:
        """Kaliteye göre format string ve ekstra seçenekleri döndür."""
        audio_only = (quality == "audio")
        
        if audio_only:
            return "bestaudio/best", {}
        
        height = self.QUALITY_MAP.get(quality, 720)
        
        if self.ffmpeg_available:
            # FFmpeg varsa ayrı stream'leri birleştirebilir
            if height:
                fmt = f"bestvideo[height<={height}]+bestaudio/best"
            else:
                fmt = "bestvideo+bestaudio/best"
            extra = {"merge_output_format": "mp4"}
        else:
            # FFmpeg yoksa muxed stream kullan
            fmt = "best"
            extra = {}
            if height:
                extra["format_sort"] = [f"res:{height}", "ext:mp4:m4a"]
        
        return fmt, extra
    
    def build_ydl_opts(
        self, 
        options: DownloadOptions,
        progress_callback: Optional[Callable[[Dict], None]] = None
    ) -> Dict[str, Any]:
        """yt-dlp seçeneklerini oluştur."""
        fmt, extra_opts = self.get_format_string(options.quality)
        audio_only = (options.quality == "audio")
        
        # Çıktı şablonu
        if options.is_playlist:
            outtmpl = os.path.join(
                options.out_dir, 
                "%(playlist_title)s",
                "%(playlist_index)s - %(title)s.%(ext)s"
            )
        else:
            outtmpl = os.path.join(options.out_dir, "%(title)s.%(ext)s")
        
        ydl_opts = {
            "format": fmt,
            "outtmpl": outtmpl,
            "noplaylist": not options.is_playlist,
            "ignoreerrors": True,
            "quiet": True,
            "no_warnings": True,
        }
        
        if progress_callback:
            ydl_opts["progress_hooks"] = [progress_callback]
        
        ydl_opts.update(extra_opts)
        
        # Ses çıkarma post-processor
        if audio_only and self.ffmpeg_available:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        
        # Playlist aralığı
        if options.is_playlist:
            if options.playlist_start:
                ydl_opts["playliststart"] = options.playlist_start
            if options.playlist_end:
                ydl_opts["playlistend"] = options.playlist_end
        
        # Altyazı indirme
        if options.download_subtitles:
            langs = [l.strip() for l in options.subtitle_lang.split(",")]
            ydl_opts["writesubtitles"] = True
            ydl_opts["writeautomaticsub"] = True
            ydl_opts["subtitleslangs"] = langs
            ydl_opts["subtitlesformat"] = "srt/best"
        
        return ydl_opts
    
    def download(
        self,
        options: DownloadOptions,
        progress_callback: Optional[Callable[[Dict], None]] = None
    ) -> Optional[Dict[str, Any]]:
        """Video indir ve bilgileri döndür."""
        ydl_opts = self.build_ydl_opts(options, progress_callback)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(options.url, download=True)
            return info
    
    def get_info(self, url: str, flat: bool = True) -> Optional[Dict[str, Any]]:
        """Video bilgilerini indir (video indirmeden)."""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": flat,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    
    def get_video_preview(self, url: str) -> Optional[Dict[str, Any]]:
        """Video önizleme bilgilerini getir."""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None
                
                # Subtitles info
                subtitles = info.get("subtitles", {})
                auto_captions = info.get("automatic_captions", {})
                available_subs = list(subtitles.keys()) + [f"{k} (auto)" for k in auto_captions.keys()]
                
                return {
                    "id": info.get("id", ""),
                    "title": info.get("title", "Başlık alınamadı"),
                    "thumbnail": info.get("thumbnail", ""),
                    "duration": info.get("duration", 0),
                    "duration_string": info.get("duration_string", ""),
                    "channel": info.get("channel", info.get("uploader", "")),
                    "view_count": info.get("view_count", 0),
                    "upload_date": info.get("upload_date", ""),
                    "description": (info.get("description", "") or "")[:200],
                    "subtitles": available_subs[:10],  # İlk 10 dil
                    "has_subtitles": len(subtitles) > 0,
                    "has_auto_captions": len(auto_captions) > 0,
                }
        except Exception as e:
            return {"error": str(e)}

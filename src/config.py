"""Uygulama yapılandırması."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os


@dataclass
class Config:
    """Uygulama yapılandırma sınıfı."""
    
    # Sunucu ayarları
    host: str = "127.0.0.1"
    port: int = 5055
    debug: bool = False
    secret_key: str = "ytstorm2024"
    
    # İndirme ayarları
    download_dir: str = field(default_factory=lambda: str(Path.home() / "Downloads" / "YT_Storm"))
    max_concurrent_downloads: int = 3
    max_log_lines: int = 60
    
    # Pencere ayarları
    window_width: int = 920
    window_height: int = 820
    window_min_width: int = 720
    window_min_height: int = 600
    
    def __post_init__(self):
        """İndirme klasörünü oluştur."""
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_env(cls) -> "Config":
        """Ortam değişkenlerinden yapılandırma oluştur."""
        return cls(
            host=os.getenv("YTSTORM_HOST", "127.0.0.1"),
            port=int(os.getenv("YTSTORM_PORT", "5055")),
            debug=os.getenv("YTSTORM_DEBUG", "").lower() == "true",
            download_dir=os.getenv("YTSTORM_DOWNLOAD_DIR", str(Path.home() / "Downloads" / "YT_Storm")),
        )


# Varsayılan yapılandırma
config = Config()

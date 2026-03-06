"""Yardımcı fonksiyonlar."""

import subprocess
import sys
import os
from pathlib import Path
from typing import List


def auto_install(packages: List[str]) -> None:
    """Eksik paketleri otomatik kur."""
    for pkg in packages:
        module = pkg.split("[")[0].replace("-", "_")
        try:
            __import__(module)
        except ImportError:
            print(f"📦 '{pkg}' kuruluyor...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg, "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT
            )
            print(f"✅ '{pkg}' kuruldu!")


def has_ffmpeg() -> bool:
    """FFmpeg kurulu mu kontrol et."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            timeout=3
        )
        return result.returncode == 0
    except Exception:
        return False


def open_folder(directory: str) -> bool:
    """Klasörü sistem dosya yöneticisinde aç."""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        elif sys.platform == "win32":
            os.startfile(str(path))
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True
    except Exception:
        return False


def truncate_text(text: str, max_length: int = 60) -> str:
    """Metni belirtilen uzunlukta kes."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "…"

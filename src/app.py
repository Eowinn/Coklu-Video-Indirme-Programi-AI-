"""Flask uygulaması ve web arayüzü."""

import os
import sys
import threading
import time
from pathlib import Path

# Otomatik kurulum (geliştirme kolaylığı için)
from .utils import auto_install
auto_install(["flask", "yt_dlp", "pywebview"])

from flask import Flask, request, jsonify, render_template

from .config import config
from .job_manager import job_manager
from .utils import open_folder


def create_app() -> Flask:
    """Flask uygulamasını oluştur."""
    # Template ve static klasörlerini ayarla
    template_dir = Path(__file__).parent.parent / "templates"
    static_dir = Path(__file__).parent.parent / "static"
    
    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )
    app.secret_key = config.secret_key
    
    # Routes
    @app.route("/")
    def index():
        """Ana sayfa."""
        return render_template("index.html")
    
    @app.route("/default_dir")
    def default_dir():
        """Varsayılan indirme klasörünü döndür."""
        return jsonify({"dir": config.download_dir})
    
    @app.route("/jobs")
    def get_jobs():
        """Tüm işleri döndür."""
        return jsonify({"jobs": job_manager.get_all_jobs()})
    
    @app.route("/clear_done", methods=["POST"])
    def clear_done():
        """Tamamlanan işleri temizle."""
        count = job_manager.clear_finished()
        return jsonify({"ok": True, "cleared": count})
    
    @app.route("/open_folder", methods=["POST"])
    def handle_open_folder():
        """Klasörü aç."""
        data = request.get_json()
        directory = data.get("dir", config.download_dir)
        success = open_folder(directory)
        return jsonify({"ok": success})
    
    @app.route("/start", methods=["POST"])
    def start_download():
        """İndirme başlat."""
        data = request.get_json()
        urls = data.get("urls", [])
        quality = data.get("quality", "720")
        out_dir = data.get("out_dir", config.download_dir) or config.download_dir
        is_playlist = data.get("is_playlist", False)
        pl_start = data.get("pl_start", "")
        pl_end = data.get("pl_end", "")
        
        if not urls:
            return jsonify({"ok": False, "error": "URL listesi boş"})
        
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        
        for url in urls:
            job_id = job_manager.create_job(url)
            
            # İndirmeyi ayrı thread'de başlat
            thread = threading.Thread(
                target=job_manager.start_download,
                args=(job_id, quality, out_dir, is_playlist, pl_start, pl_end),
                daemon=True
            )
            thread.start()
        
        return jsonify({"ok": True, "count": len(urls)})
    
    return app


def run_flask(app: Flask) -> None:
    """Flask sunucusunu çalıştır."""
    app.run(
        host=config.host,
        port=config.port,
        debug=config.debug,
        threaded=True,
        use_reloader=False,
    )


def run_desktop() -> None:
    """Masaüstü uygulamasını başlat."""
    import webview
    
    print("""
╔══════════════════════════════════════════════════════╗
║   ⚡  YT STORM — YouTube Toplu Video İndirici        ║
╠══════════════════════════════════════════════════════╣
║   Masaüstü penceresi açılıyor...                     ║
║   Kapatmak için pencereyi kapatın                    ║
╚══════════════════════════════════════════════════════╝
""")
    
    app = create_app()
    
    # Flask'ı arka planda başlat
    flask_thread = threading.Thread(target=run_flask, args=(app,), daemon=True)
    flask_thread.start()
    
    # Flask'ın başlamasını bekle
    time.sleep(1.2)
    
    # Masaüstü penceresi
    window = webview.create_window(
        title="⚡ YT Storm — YouTube İndirici",
        url=f"http://{config.host}:{config.port}",
        width=config.window_width,
        height=config.window_height,
        min_size=(config.window_min_width, config.window_min_height),
        resizable=True,
        text_select=True,
        confirm_close=False,
    )
    
    webview.start(debug=config.debug)


# CLI çalıştırma
if __name__ == "__main__":
    run_desktop()

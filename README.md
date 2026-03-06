# ⚡ YT Storm

**YouTube Toplu Video İndirici** - Modern masaüstü uygulaması

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![yt-dlp](https://img.shields.io/badge/powered%20by-yt--dlp-red.svg)](https://github.com/yt-dlp/yt-dlp)

## ✨ Özellikler

- 🎬 **Tekli video** indirme
- 📦 **Toplu URL** ile çoklu indirme
- 📋 **Playlist / Kanal** desteği
- 🎵 **Yalnızca ses** (MP3) çıkarma
- 📊 **Gerçek zamanlı** ilerleme takibi
- 🎨 **Modern karanlık tema** arayüz
- 💻 **Masaüstü uygulaması** (pywebview)

## 🚀 Kurulum

### Gereksinimler

- Python 3.9+
- FFmpeg (opsiyonel, yüksek kalite için önerilir)

### Pip ile kurulum

```bash
pip install flask yt-dlp pywebview
```

### Çalıştırma

```bash
# Masaüstü uygulaması olarak
python -m src.app

# veya
python run.py
```

## 📁 Proje Yapısı

```
yt-storm/
├── src/
│   ├── __init__.py      # Paket tanımı
│   ├── app.py           # Flask uygulaması & pywebview
│   ├── config.py        # Yapılandırma (dataclass)
│   ├── downloader.py    # yt-dlp wrapper
│   ├── job_manager.py   # İndirme kuyruğu yönetimi
│   └── utils.py         # Yardımcı fonksiyonlar
├── templates/
│   └── index.html       # Ana sayfa şablonu
├── static/
│   ├── css/
│   │   └── style.css    # Stiller
│   └── js/
│       └── app.js       # Frontend JavaScript
├── tests/               # Test dosyaları
├── docs/                # Dokümantasyon
├── requirements.txt     # Bağımlılıklar
├── pyproject.toml       # Proje yapılandırması
└── README.md
```

## 🎯 Kullanım

1. Uygulamayı başlatın
2. **İndirme Modu** seçin (Tekli / Toplu / Playlist)
3. URL'leri girin
4. **Kalite** seçin (En Yüksek, 1080p, 720p, vb.)
5. **İndirmeyi Başlat** butonuna tıklayın

## ⚙️ Yapılandırma

Ortam değişkenleri ile yapılandırılabilir:

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `YTSTORM_HOST` | `127.0.0.1` | Sunucu adresi |
| `YTSTORM_PORT` | `5055` | Sunucu portu |
| `YTSTORM_DOWNLOAD_DIR` | `~/Downloads/YT_Storm` | İndirme klasörü |
| `YTSTORM_DEBUG` | `false` | Debug modu |

## 🔧 Geliştirme

```bash
# Geliştirme bağımlılıklarını kur
pip install -e ".[dev]"

# Linter çalıştır
ruff check src/

# Formatter çalıştır
black src/

# Testleri çalıştır
pytest
```

## 📝 Lisans

MIT License - Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## 🙏 Katkıda Bulunanlar

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video indirme motoru
- [pywebview](https://pywebview.flowrl.com/) - Masaüstü pencere desteği
- [Flask](https://flask.palletsprojects.com/) - Web framework

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/Eowinn">Eowinn</a>
</p>

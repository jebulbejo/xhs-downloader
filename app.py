from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import yt_dlp
import requests

app = Flask(__name__)
CORS(app, origins="*")

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def resolve_short_url(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.20",
            "Referer": "https://www.xiaohongshu.com/",
        }
        response = requests.get(url, allow_redirects=True, timeout=10, headers=headers)
        return response.url
    except:
        return url

def get_video_info(url):
    if "xhslink.com" in url:
        url = resolve_short_url(url)

    # Hapus parameter query yang tidak perlu
    if "?" in url:
        base_url = url.split("?")[0]
        # Pastikan URL valid xiaohongshu
        if "xiaohongshu.com" in base_url:
            url = base_url

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            "Referer": "https://www.xiaohongshu.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
        "extractor_args": {
            "xiaohongshu": {
                "legacy_api": ["1"],
            }
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        formats = []
        if "formats" in info:
            for f in info["formats"]:
                if f.get("vcodec") != "none" and f.get("url"):
                    formats.append({
                        "format_id": f.get("format_id", ""),
                        "ext": f.get("ext", "mp4"),
                        "quality": f.get("format_note", f.get("height", "unknown")),
                        "url": f.get("url", ""),
                        "filesize": f.get("filesize", 0),
                    })

        direct_url = ""
        if formats:
            # Ambil kualitas terbaik
            best = sorted(formats, key=lambda x: x.get("filesize") or 0, reverse=True)
            direct_url = best[0]["url"]
        elif info.get("url"):
            direct_url = info.get("url")

        return {
            "title": info.get("title", "Video"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", "Unknown"),
            "formats": formats,
            "direct_url": direct_url,
        }

@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "XHS Downloader API is running!"})

@app.route("/api/download", methods=["POST", "OPTIONS"])
def download():
    if request.method == "OPTIONS":
        return make_response("", 200)
    try:
        data = request.get_json()
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"error": "URL tidak boleh kosong"}), 400
        if "xiaohongshu.com" not in url and "xhslink.com" not in url:
            return jsonify({"error": "URL harus dari Xiaohongshu atau xhslink.com"}), 400
        info = get_video_info(url)
        direct_url = info.get("direct_url", "")
        if not direct_url:
            return jsonify({"error": "Tidak bisa mendapatkan URL download"}), 500
        return jsonify({
            "success": True,
            "download_url": direct_url,
            "title": info.get("title", "video"),
            "thumbnail": info.get("thumbnail", ""),
        })
    except Exception as e:
        return jsonify({"error": f"Gagal memproses download: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)

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
        response = requests.head(url, allow_redirects=True, timeout=10)
        return response.url
    except:
        return url

def get_video_info(url):
    if "xhslink.com" in url:
        url = resolve_short_url(url)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
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

        return {
            "title": info.get("title", "Video"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", "Unknown"),
            "formats": formats,
            "direct_url": info.get("url", formats[0]["url"] if formats else ""),
        }

@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "XHS Downloader API is running!"})

@app.route("/api/info", methods=["POST", "OPTIONS"])
def get_info():
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
        return jsonify({"success": True, "data": info})
    except Exception as e:
        return jsonify({"error": f"Gagal mengambil info video: {str(e)}"}), 500

@app.route("/api/download", methods=["POST", "OPTIONS"])
def download():
    if request.method == "OPTIONS":
        return make_response("", 200)
    try:
        data = request.get_json()
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"error": "URL tidak boleh kosong"}), 400
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

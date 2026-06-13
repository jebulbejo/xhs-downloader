from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import requests
import re
import json

app = Flask(__name__)
CORS(app, origins="*")

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

def resolve_short_url(url):
    """Resolve xhslink.com ke URL asli."""
    try:
        session = requests.Session()
        session.max_redirects = 10
        resp = session.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        return resp.url
    except Exception as e:
        return url

def extract_note_id(url):
    """Extract note ID dari URL XHS."""
    patterns = [
        r'xiaohongshu\.com/explore/([a-f0-9]+)',
        r'xiaohongshu\.com/discovery/item/([a-f0-9]+)',
        r'xiaohongshu\.com/note/([a-f0-9]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_video_from_page(url):
    """Scrape video URL langsung dari halaman XHS."""
    session = requests.Session()
    
    # Set cookies minimal
    session.cookies.set('a1', 'dummy', domain='.xiaohongshu.com')
    
    resp = session.get(url, headers=HEADERS, timeout=15)
    html = resp.text

    # Cari data video di dalam script tag
    # XHS menyimpan data di window.__INITIAL_STATE__ atau similar
    patterns = [
        r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*;?\s*</script>',
        r'"videoKey"\s*:\s*"([^"]+)"',
        r'"masterUrl"\s*:\s*"([^"]+)"',
        r'"originVideoKey"\s*:\s*"([^"]+)"',
        r'https://sns-video-[^"\']+\.mp4[^"\']*',
        r'https://[^"\']*xhscdn[^"\']*\.mp4[^"\']*',
    ]
    
    # Cari URL video MP4 langsung
    mp4_pattern = r'https://[^\s"\'<>]+\.mp4[^\s"\'<>]*'
    mp4_urls = re.findall(mp4_pattern, html)
    
    if mp4_urls:
        return {
            "success": True,
            "download_url": mp4_urls[0],
            "title": "XHS Video",
            "thumbnail": "",
        }

    # Cari di JSON state
    state_match = re.search(r'window\.__INITIAL_STATE__=(.*?)</script>', html, re.DOTALL)
    if state_match:
        try:
            state_str = state_match.group(1).strip().rstrip(';')
            # Cari URL video di string JSON
            video_urls = re.findall(r'https://[^"]+(?:mp4|video)[^"]*', state_str)
            if video_urls:
                return {
                    "success": True,
                    "download_url": video_urls[0],
                    "title": "XHS Video",
                    "thumbnail": "",
                }
        except:
            pass

    return None

def get_video_info(url):
    """Main function untuk get video info."""
    # Resolve short URL
    if "xhslink.com" in url:
        url = resolve_short_url(url)
    
    # Bersihkan URL dari parameter tracking
    clean_url = url.split("?")[0] if "?" in url else url
    
    # Coba scrape dari halaman
    result = get_video_from_page(clean_url)
    if result:
        return result
    
    # Coba URL dengan parameter xsec_token jika ada
    result = get_video_from_page(url)
    if result:
        return result
        
    return None

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

        result = get_video_info(url)
        
        if not result or not result.get("download_url"):
            return jsonify({"error": "Tidak bisa mengambil video. Pastikan link valid dan video bersifat publik."}), 500

        return jsonify({
            "success": True,
            "download_url": result["download_url"],
            "title": result.get("title", "XHS Video"),
            "thumbnail": result.get("thumbnail", ""),
        })

    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)

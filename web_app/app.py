from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
from datetime import datetime
import threading

app = Flask(__name__)

# Store download progress and use user's Downloads folder
download_status = {}
default_save_path = os.path.join(os.path.expanduser("~"), "Downloads")

def progress_hook(d, download_id):
    if d['status'] == 'downloading':
        try:
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            speed = d.get('speed', 0)
            
            if total:
                percentage = (downloaded / total) * 100
            else:
                percentage = 0
                
            speed_str = f"{speed/1024/1024:.1f} MB/s" if speed else "N/A"
            
            # Include video title in progress message
            title = download_status[download_id].get('title', 'Unknown Title')
            video_id = download_status[download_id].get('video_id', 'Unknown ID')
            
            download_status[download_id] = {
                'status': 'downloading',
                'progress': f"Downloading [{video_id}] {title}: {percentage:.1f}% at {speed_str}",
                'downloaded': downloaded,
                'total': total,
                'speed': speed,
                'title': title,
                'video_id': video_id
            }
            
        except Exception as e:
            download_status[download_id] = {
                'status': 'downloading',
                'progress': "Downloading...",
                'error': str(e)
            }
            
    elif d['status'] == 'finished':
        title = download_status[download_id].get('title', 'Unknown Title')
        video_id = download_status[download_id].get('video_id', 'Unknown ID')
        download_status[download_id] = {
            'status': 'processing',
            'progress': f"Download finished for [{video_id}] {title}, processing file...",
            'title': title,
            'video_id': video_id
        }
    elif d['status'] == 'error':
        download_status[download_id] = {
            'status': 'error',
            'progress': f"Download error: {d.get('error', 'Unknown error')}"
        }



def download_video(url, download_id):
    try:
        download_status[download_id] = {
            'status': 'starting',
            'progress': "Starting download...",
            'title': None
        }

        def hook(d): return progress_hook(d, download_id)

        ydl_opts = {
            'format': 'best',
            'progress_hooks': [hook],
            'outtmpl': os.path.join(default_save_path, '%(title)s.%(ext)s'),
            'nocheckcertificate': True,
            'noplaylist': True,
            'quiet': False,
            'verbose': True,
            'no_warnings': False,
            'extract_flat': False,
            'youtube_include_dash_manifest': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                download_status[download_id]['progress'] = "Extracting video information..."
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    raise Exception("Could not extract video information")
                
                # Store video title and ID
                video_title = info.get('title', 'Unknown Title')
                video_id = info.get('id', 'Unknown ID')
                
                download_status[download_id].update({
                    'title': video_title,
                    'video_id': video_id,
                    'progress': f"Starting download for: {video_title} [{video_id}]"
                })
                
                ydl.download([url])
                
                download_status[download_id] = {
                    'status': 'completed',
                    'progress': f"Successfully downloaded: {video_title} [{video_id}]",
                    'title': video_title,
                    'video_id': video_id
                }
                
            except Exception as e:
                download_status[download_id]['progress'] = f"Download failed: {str(e)}"
                raise

    except Exception as e:
        error_message = str(e)
        download_status[download_id] = {
            'status': 'error',
            'progress': f"Error: {error_message}"
        }


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def start_download():
    url = request.json.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    if not url.startswith(('http://', 'https://')):
        return jsonify({'error': 'Invalid URL format'}), 400
    
    download_id = datetime.now().strftime("%Y%m%d%H%M%S")
    
    if download_id in download_status:
        del download_status[download_id]
    
    thread = threading.Thread(
        target=download_video,
        args=(url, download_id)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'download_id': download_id})

@app.route('/status/<download_id>')
def get_status(download_id):
    return jsonify(download_status.get(download_id, {
        'status': 'not_found',
        'progress': 'Download not found'
    }))

if __name__ == '__main__':
    app.run(debug=True)

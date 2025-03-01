from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import re

app = Flask(__name__)

# Remove cache for now to simplify
# We can add it back later if needed

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def is_valid_youtube_url(url):
    """Validate YouTube URL patterns including Shorts"""
    youtube_regex = (
        r'(https?://)?(www\.)?(youtube\.com/)(shorts/|watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    youtube_regex_match = re.match(youtube_regex, url)
    return bool(youtube_regex_match)

def clean_youtube_url(url):
    """Convert YouTube Shorts URL to standard format"""
    if 'shorts' in url:
        video_id = url.split('shorts/')[-1].split('?')[0]
        return f'https://www.youtube.com/watch?v={video_id}'
    return url

def get_video_info(url):
    # Clean the URL first
    url = clean_youtube_url(url)
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'format': 'bestvideo*+bestaudio/best',
        'youtube_include_dash_manifest': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
            streams = {
                'video': [],
                'audio': []
            }
            
            # Process formats
            video_formats = {}
            best_audio = None
            best_audio_bitrate = 0
            
            for f in formats:
                try:
                    # Video formats
                    if f.get('vcodec') != 'none':
                        height = f.get('height', 0)
                        if height > 0:
                            resolution = f"{height}p"
                            # Keep the highest bitrate for each resolution
                            if resolution not in video_formats or f.get('tbr', 0) > video_formats[resolution].get('tbr', 0):
                                video_formats[resolution] = f
                    
                    # Audio format - keep only the highest quality
                    elif f.get('acodec') != 'none':
                        abr = f.get('abr', 0)
                        if abr > best_audio_bitrate:
                            best_audio_bitrate = abr
                            best_audio = f
                
                except Exception as format_error:
                    print(f"Error processing format: {format_error}")
                    continue

            # Add video formats to streams
            for resolution, format_info in video_formats.items():
                filesize = format_info.get('filesize', 0) or format_info.get('filesize_approx', 0)
                streams['video'].append({
                    'itag': format_info.get('format_id'),
                    'resolution': resolution,
                    'filesize': f"{filesize / 1024 / 1024:.1f} MB" if filesize else 'Unknown size',
                    'ext': 'mp4'
                })

            # Add single high-quality audio option
            if best_audio:
                filesize = best_audio.get('filesize', 0) or best_audio.get('filesize_approx', 0)
                streams['audio'].append({
                    'itag': best_audio.get('format_id'),
                    'abr': '320kbps',  # We'll convert to 320kbps during download
                    'filesize': f"{filesize / 1024 / 1024:.1f} MB" if filesize else 'Unknown size',
                    'ext': 'mp3',
                    'format_note': 'MP3 320kbps'
                })

            # Sort video streams by quality
            streams['video'].sort(key=lambda x: int(x['resolution'].replace('p', '')), reverse=True)

            return {
                'status': 'success',
                'title': info.get('title', ''),
                'thumbnail': info.get('thumbnail', ''),
                'streams': streams,
                'duration': info.get('duration', 0)
            }
            
        except Exception as e:
            print(f"Error in get_video_info: {str(e)}")
            return {'status': 'error', 'message': str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_streams', methods=['POST'])
def get_streams():
    try:
        url = request.form['url'].strip()
        
        if not is_valid_youtube_url(url):
            return jsonify({'status': 'error', 'message': 'Invalid YouTube URL'})
        
        info = get_video_info(url)
        if info['status'] == 'error':
            return jsonify(info)
            
        return jsonify(info)
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/download', methods=['POST'])
def download():
    try:
        url = request.form['url']
        format_id = request.form['itag']
        format_ext = request.form.get('ext', 'mp4')
        
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': 'downloads/%(title)s.%(ext)s'
        }
        
        if format_ext == 'mp3':
            ydl_opts.update({
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }]
            })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if not os.path.exists(filename):
                base_filename = os.path.splitext(filename)[0]
                possible_files = [f for f in os.listdir('downloads') if f.startswith(os.path.basename(base_filename))]
                if possible_files:
                    filename = os.path.join('downloads', possible_files[0])
            
            return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

if __name__ == '__main__':
    import webbrowser
    port = 5000
    url = f"http://127.0.0.1:{port}"
    print(f"Starting server at {url}")
    
    # Create directories if they don't exist
    for directory in ['downloads', 'templates', 'static']:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created {directory} directory")
    
    # Check if template files exist
    required_templates = ['layout.html', 'index.html', 'about.html', 'contact.html', 'privacy.html', 'terms.html']
    missing_templates = [t for t in required_templates if not os.path.exists(f'templates/{t}')]
    
    if missing_templates:
        print(f"Error: Missing template files: {', '.join(missing_templates)}")
        print("Please make sure all template files are in the templates directory")
        exit(1)
    
    try:
        print("Opening browser...")
        webbrowser.open(url)
        print("Starting Flask server...")
        app.run(
            host='127.0.0.1',
            port=port,
            debug=True,
            use_reloader=False
        )
    except Exception as e:
        print(f"Error starting server: {e}") 
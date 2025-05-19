from flask import Flask, request, render_template, jsonify, url_for, send_from_directory
import os
import re
import threading
import sys
import time
import atexit
from urllib.parse import unquote
from faster_whisper import WhisperModel
from mutagen import File as MutagenFile

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/tracks/'
app.config['MAX_CONTENT_PATH'] = 1024 * 1024 * 100  # 100 MB limit for file upload

# Create a persistent WhisperModel instance
whisper_model = WhisperModel("large-v3", device="cuda", compute_type="float16")

# Global variables for thread management
active_threads = []
exit_flag = False

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'mp3'}

@app.route('/')
def index():
    directory = os.path.join(app.static_folder, 'tracks')
    mp3_files = [f.replace('.mp3', '') for f in os.listdir(directory) if f.endswith('.mp3')]
    return render_template('index.html', mp3_files=mp3_files)

@app.route('/static/tracks/<path:filename>')
def uploaded_file(filename):
    # Decode URL-encoded parts
    decoded_filename = unquote(filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], decoded_filename)

    if not os.path.exists(filepath):
        app.logger.error(f"File not found: {filepath}")
        return "File not found", 404

    app.logger.info(f"Serving file: {filepath}")
    return send_from_directory(app.config['UPLOAD_FOLDER'], decoded_filename)

@app.route('/check_file/<path:filename>')
def check_file_exists(filename):
    """Check if a file exists in the tracks directory"""
    try:
        # Decode URL-encoded parts
        decoded_filename = unquote(filename)
        
        # Make sure the path is relative to the upload folder
        if not decoded_filename.startswith('tracks/'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], decoded_filename)
        else:
            # Handle case where 'tracks/' is already in the path
            filepath = os.path.join('static', decoded_filename)
        
        app.logger.info(f"Checking file existence: {filepath}")
        
        if os.path.exists(filepath) and os.path.isfile(filepath):
            app.logger.info(f"File check: {filepath} exists")
            return jsonify({'exists': True}), 200
        else:
            app.logger.info(f"File check: {filepath} does not exist")
            return jsonify({'exists': False}), 404
    except Exception as e:
        app.logger.error(f"Error checking file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)  # Use custom sanitization function
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # Strip the .mp3 extension from filename before appending text labels
        base_filename = filepath.rsplit('.mp3', 1)[0]
        transcription_path_lines = base_filename + '_lines.txt'
        transcription_path_words = base_filename + '_words.txt'

        if os.path.exists(transcription_path_lines) and os.path.exists(transcription_path_words):
            app.logger.info(f"All transcription files already exist for: {filepath}")
            return jsonify({'message': 'File and transcriptions already exist.', 'filename': filename}), 200

        file.save(filepath)
        app.logger.info(f"File uploaded: {filepath}")
        
        # Start a non-daemon thread for transcription to prevent shutdown
        transcription_thread = threading.Thread(target=transcribe_file, args=(filepath,), daemon=False)
        transcription_thread.start()
        
        # Track thread for cleanup
        global active_threads
        active_threads.append(transcription_thread)
        
        return jsonify({'message': 'File uploaded and transcription started!', 'filename': filename})
    else:
        return jsonify({'message': 'No file received or file type not allowed.'}), 400

@app.route('/logs')
def get_logs():
    global log_messages
    messages = log_messages[:]
    log_messages = []  # Clear messages after sending
    return jsonify(messages)

@app.route('/list_mp3s')
def list_mp3s():
    """List all MP3 files in the tracks directory"""
    try:
        mp3_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.mp3')]
        return jsonify(mp3_files)
    except Exception as e:
        app.logger.error(f"Error listing MP3 files: {str(e)}")
        return jsonify([]), 500

@app.route('/check_transcription/<path:filename>')
def check_transcription_complete(filename):
    """Check if all transcription files for a given MP3 file exist"""
    try:
        # Decode URL-encoded parts and remove .mp3 extension if present
        decoded_filename = unquote(filename)
        if decoded_filename.lower().endswith('.mp3'):
            decoded_filename = decoded_filename[:-4]
        
        # Construct paths for all three files
        base_path = os.path.join(app.config['UPLOAD_FOLDER'], decoded_filename)
        lines_path = base_path + '_lines.txt'
        words_path = base_path + '_words.txt'
        lrc_path = base_path + '.lrc'
        
        # Check if all files exist
        lines_exists = os.path.exists(lines_path) and os.path.isfile(lines_path)
        words_exists = os.path.exists(words_path) and os.path.isfile(words_path)
        lrc_exists = os.path.exists(lrc_path) and os.path.isfile(lrc_path)
        
        app.logger.info(f"Transcription check for {decoded_filename}: lines={lines_exists}, words={words_exists}, lrc={lrc_exists}")
        
        # Return the status of all files
        return jsonify({
            'all_complete': lines_exists and words_exists and lrc_exists,
            'lines': lines_exists,
            'words': words_exists,
            'lrc': lrc_exists
        }), 200
    except Exception as e:
        app.logger.error(f"Error checking transcription: {str(e)}")
        return jsonify({'error': str(e)}), 500

def secure_filename(filename):
    # Remove any path information to avoid directory traversal attacks
    filename = filename.split('/')[-1].split('\\')[-1]
    # Allow only certain characters in filenames to prevent issues on the filesystem - Disabled since we're already taking the name from a file, so it should already be fine.
    # filename = re.sub(r'[^a-zA-Z0-9_.()\[\]-]', '', filename)
    return filename

def extract_metadata(filepath):
    """
    Extract title, artist, album metadata from the audio file, falling back to 'Unknown'.
    """
    metadata = {'title': 'Unknown', 'artist': 'Unknown', 'album': 'Unknown'}
    try:
        audio = MutagenFile(filepath, easy=True)
        if audio is not None:
            if 'title' in audio.tags:
                metadata['title'] = audio.tags['title'][0]
            if 'artist' in audio.tags:
                metadata['artist'] = audio.tags['artist'][0]
            if 'album' in audio.tags:
                metadata['album'] = audio.tags['album'][0]
    except Exception as e:
        app.logger.error(f"Error extracting metadata: {str(e)}")
    return metadata


def format_timestamp(seconds):
    """
    Convert float seconds to LRC timestamp format mm:ss.xx
    """
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    return f"{minutes:02d}:{secs:05.2f}"


def write_lrc(segments, metadata, output_path):
    """
    Write .lrc file with metadata and segments list.
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # Metadata headers
            f.write(f"[ti:{metadata['title']}]\n")
            f.write(f"[ar:{metadata['artist']}]\n")
            f.write(f"[al:{metadata['album']}]\n")
            f.write("\n")
            # Lyrics lines
            for seg in segments:
                timestamp = format_timestamp(seg.start)
                text = seg.text.strip()
                f.write(f"[{timestamp}]{text}\n")
        return True
    except Exception as e:
        app.logger.error(f"Error writing LRC file: {str(e)}")
        return False


def transcribe_file(filepath):
    """
    Transcribe an audio file and generate lyrics in various formats.
    This function runs in a background thread and must not crash the server.
    """
    try:
        # Ensure the base filename does not contain '.mp3' for transcription paths
        base_filename = filepath.rsplit('.mp3', 1)[0]
        transcription_path_lines = base_filename + '_lines.txt'
        transcription_path_words = base_filename + '_words.txt'
        lrc_path = base_filename + '.lrc'

        # Check and log file existence
        app.logger.info(f"Checking transcription files: {transcription_path_lines} and {transcription_path_words}")
        transcription_needed = not (os.path.exists(transcription_path_lines) and os.path.exists(transcription_path_words) and os.path.exists(lrc_path))

        if transcription_needed:
            app.logger.info("Transcription started for: " + filepath)
            
            try:
                # Use the global model instance
                segments_generator, info = whisper_model.transcribe(filepath, beam_size=5, word_timestamps=True)
                
                # Convert generator to list to allow multiple iterations
                segments = list(segments_generator)
                
                # Write lines and words files
                with open(transcription_path_lines, 'w', encoding='utf-8') as f_lines, open(transcription_path_words, 'w', encoding='utf-8') as f_words:
                    for segment in segments:
                        f_lines.write(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n")
                        if hasattr(segment, 'words'):
                            for word in segment.words:
                                f_words.write(f"[{word.start:.2f}s -> {word.end:.2f}s] {word.word}\n")
                
                # Extract metadata and generate LRC file
                metadata = extract_metadata(filepath)
                lrc_success = write_lrc(segments, metadata, lrc_path)
                
                # Verify file existence and sizes
                lines_exists = os.path.exists(transcription_path_lines)
                words_exists = os.path.exists(transcription_path_words)
                lrc_exists = os.path.exists(lrc_path)
                
                lines_size = os.path.getsize(transcription_path_lines) if lines_exists else 0
                words_size = os.path.getsize(transcription_path_words) if words_exists else 0
                lrc_size = os.path.getsize(lrc_path) if lrc_exists else 0
                
                app.logger.info(f"File check after transcription:")
                app.logger.info(f"  Lines file: exists={lines_exists}, size={lines_size} bytes")
                app.logger.info(f"  Words file: exists={words_exists}, size={words_size} bytes")
                app.logger.info(f"  LRC file: exists={lrc_exists}, size={lrc_size} bytes")
                
                if lrc_success:
                    app.logger.info(f"Transcription complete for: {filepath} (generated lines, words, and LRC)")
                else:
                    app.logger.info(f"Transcription complete for: {filepath} (generated lines and words, LRC failed)")
                
            except Exception as e:
                app.logger.error(f"Error during transcription processing: {str(e)}")
        else:
            app.logger.info("Transcription files already exist for: " + filepath)
            
    except Exception as e:
        app.logger.error(f"Error during transcription setup: {str(e)}")

# Function to clean up finished threads
def cleanup_threads():
    global active_threads
    # Remove finished threads from the active_threads list
    active_threads = [t for t in active_threads if t.is_alive()]

# Register cleanup function at exit
def cleanup_before_exit():
    global exit_flag
    exit_flag = True
    # Give threads a chance to terminate gracefully
    for thread in active_threads:
        if thread.is_alive():
            thread.join(timeout=1.0)
    app.logger.info("Application exiting, cleaned up threads")

# Register the cleanup function
atexit.register(cleanup_before_exit)

if __name__ == '__main__':
    # Run the Flask app with threaded=True for better concurrency
    app.run(debug=True, host='0.0.0.0', use_reloader=False, threaded=True)
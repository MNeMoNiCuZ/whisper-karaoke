from flask import Flask, request, render_template, jsonify, url_for, send_from_directory
import os
import re
from urllib.parse import unquote
from faster_whisper import WhisperModel

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/tracks/'
app.config['MAX_CONTENT_PATH'] = 1024 * 1024 * 100  # 100 MB limit for file upload

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
        transcribe_file(filepath)
        return jsonify({'message': 'File uploaded and transcription started!', 'filename': filename})
    else:
        return jsonify({'message': 'No file received or file type not allowed.'}), 400

@app.route('/logs')
def get_logs():
    global log_messages
    messages = log_messages[:]
    log_messages = []  # Clear messages after sending
    return jsonify(messages)

def secure_filename(filename):
    # Remove any path information to avoid directory traversal attacks
    filename = filename.split('/')[-1].split('\\')[-1]
    # Allow only certain characters in filenames to prevent issues on the filesystem - Disabled since we're already taking the name from a file, so it should already be fine.
    # filename = re.sub(r'[^a-zA-Z0-9_.()\[\]-]', '', filename)
    return filename

def transcribe_file(filepath):
    model_size = "large-v3"
    model = WhisperModel(model_size, device="cuda", compute_type="float16")
    
    # Ensure the base filename does not contain '.mp3' for transcription paths
    base_filename = filepath.rsplit('.mp3', 1)[0]
    transcription_path_lines = base_filename + '_lines.txt'
    transcription_path_words = base_filename + '_words.txt'

    # Check and log file existence
    app.logger.info(f"Checking transcription files: {transcription_path_lines} and {transcription_path_words}")
    transcription_needed = not (os.path.exists(transcription_path_lines) and os.path.exists(transcription_path_words))

    if transcription_needed:
        app.logger.info("Transcription started for: " + filepath)
        segments, info = model.transcribe(filepath, beam_size=5, word_timestamps=True)
        with open(transcription_path_lines, 'w', encoding='utf-8') as f_lines, open(transcription_path_words, 'w', encoding='utf-8') as f_words:
            for segment in segments:
                f_lines.write(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n")
                if hasattr(segment, 'words'):
                    for word in segment.words:
                        f_words.write(f"[{word.start:.2f}s -> {word.end:.2f}s] {word.word}\n")
        app.logger.info("Transcription complete for: " + filepath)
    else:
        app.logger.info("Transcription files already exist for: " + filepath)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
import os
import shutil
import threading
from queue import Queue
from faster_whisper import WhisperModel
from mutagen import File as MutagenFile

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
    except Exception:
        pass
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


# Initialize the Whisper model with CUDA device
model = WhisperModel("large-v3", device="cuda")


def transcribe_file(filepath, model, output_dir):
    base = os.path.splitext(os.path.basename(filepath))[0]
    lines_path = os.path.join(output_dir, f"{base}_lines.txt")
    words_path = os.path.join(output_dir, f"{base}_words.txt")
    lrc_path = os.path.join(output_dir, f"{base}.lrc")

    if (os.path.exists(lines_path) and os.path.exists(words_path) and os.path.getsize(lines_path) > 0
       and os.path.getsize(words_path) > 0 and os.path.exists(lrc_path)):
        print(f"Skipping, all output exist for: {filepath}")
        return

    print(f"Transcribing: {filepath}")
    segments_generator, info = model.transcribe(filepath, beam_size=5, word_timestamps=True)
    
    # Convert generator to list to allow multiple iterations
    segments = list(segments_generator)
    
    # Write lines and words
    with open(lines_path, 'w', encoding='utf-8') as f_lines, open(words_path, 'w', encoding='utf-8') as f_words:
        for seg in segments:
            f_lines.write(f"[{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}\n")
            if hasattr(seg, 'words'):
                for w in seg.words:
                    f_words.write(f"[{w.start:.2f}s -> {w.end:.2f}s] {w.word}\n")
    # Extract metadata and write LRC
    meta = extract_metadata(filepath)
    write_lrc(segments, meta, lrc_path)
    print(f"Generated: {lines_path}, {words_path}, {lrc_path}")


def process_file(filepath, model, output_dir):
    dest = os.path.join(output_dir, os.path.basename(filepath))
    shutil.copy(filepath, dest)
    print(f"Copied: {dest}")
    transcribe_file(dest, model, output_dir)


def worker():
    while True:
        path = file_queue.get()
        process_file(path, model, 'static/tracks')
        file_queue.task_done()


def handle_drop(event):
    files = root.tk.splitlist(event.data)
    for uri in files:
        path = uri.strip('{}').replace('file:///', '').replace('/', os.sep)
        if path.lower().endswith('.mp3'):
            file_queue.put(path)
            print(f"Queued: {path}")
        else:
            print(f"Skipped (not mp3): {path}")


if __name__ == '__main__':
    import tkinter as tk
    from tkinterdnd2 import DND_FILES, TkinterDnD

    root = TkinterDnD.Tk()
    root.title('Batch MP3 Transcriber')
    root.geometry('400x200')

    file_queue = Queue()
    threading.Thread(target=worker, daemon=True).start()

    label = tk.Label(root, text='Drag and drop MP3 files here', pady=20, padx=20)
    label.pack(expand=True, fill=tk.BOTH)
    label.drop_target_register(DND_FILES)
    label.dnd_bind('<<Drop>>', handle_drop)

    root.mainloop()
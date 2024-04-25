import os
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
import shutil
import threading
from queue import Queue
from faster_whisper import WhisperModel

# Initialize the Whisper model with CUDA device
model = WhisperModel("large-v3", device="cuda")

def transcribe_file(filepath, model, output_dir):
    base_filename = os.path.splitext(os.path.basename(filepath))[0]
    transcription_path_lines = os.path.join(output_dir, f"{base_filename}_lines.txt")
    transcription_path_words = os.path.join(output_dir, f"{base_filename}_words.txt")

    # Log file existence
    if os.path.exists(transcription_path_lines) and os.path.exists(transcription_path_words) and os.path.getsize(transcription_path_lines) > 0 and os.path.getsize(transcription_path_words) > 0:
        if os.path.exists(filepath):
            print(f"All files already exist and skipping: {filepath}, {transcription_path_lines}, {transcription_path_words}")
            return
        else:
            shutil.copy(filepath, filepath)  # This should likely be copying to output_dir
            print(f"Copied missing mp3 for: {filepath}")
            return

    print(f"Starting transcription for: {filepath}")
    segments, info = model.transcribe(filepath, beam_size=5, word_timestamps=True)
    with open(transcription_path_lines, 'w', encoding='utf-8') as f_lines, open(transcription_path_words, 'w', encoding='utf-8') as f_words:
        for segment in segments:
            f_lines.write(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n")
            if hasattr(segment, 'words'):
                for word in segment.words:
                    f_words.write(f"[{word.start:.2f}s -> {word.end:.2f}s] {word.word}\n")
    print(f"Transcription complete for: {filepath}")
    print(f"Output files: {transcription_path_lines}, {transcription_path_words}")

def process_file(filepath, model, output_dir):
    dest_path = os.path.join(output_dir, os.path.basename(filepath))
    shutil.copy(filepath, dest_path)
    print(f"Copied: {dest_path}")
    transcribe_file(dest_path, model, output_dir)

def worker():
    while True:
        filepath = file_queue.get()
        process_file(filepath, model, 'static/tracks')
        file_queue.task_done()

def handle_drop(event):
    files = root.tk.splitlist(event.data)
    for file_uri in files:
        filepath = file_uri.strip('{}').replace('file:///', '').replace('/', os.sep)
        if filepath.lower().endswith('.mp3'):
            file_queue.put(filepath)
            print(f"Queued: {filepath}")
        else:
            print(f"Skipped (not an mp3): {filepath}")

if __name__ == '__main__':
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

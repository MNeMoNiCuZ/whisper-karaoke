# Whisper Karaoke
Whisper Karaoke is a small script that takes mp3-files as input, and uses the [faster-whisper](https://github.com/SYSTRAN/faster-whisper/) library to transcribe the audio file, and also split the transcription into separated words.

This is then used in a small web-player in a Karaoke-like fashion, by highlighting the words as they appear.
![image](https://github.com/MNeMoNiCuZ/whisper-karaoke/assets/60541708/3930f3a0-e46e-4a45-8cda-05fbab531a90)

## Video Examples
https://github.com/MNeMoNiCuZ/whisper-karaoke/assets/60541708/ab030773-e4b5-4e1e-ac65-37c76e8d3e1a

https://github.com/MNeMoNiCuZ/whisper-karaoke/assets/60541708/333e2be4-e34d-4ddd-9ce9-7ffe1aa2f922

https://github.com/MNeMoNiCuZ/whisper-karaoke/assets/60541708/eae45e04-1751-4cad-b6c1-f6a205cddf1c

https://github.com/MNeMoNiCuZ/whisper-karaoke/assets/60541708/955d15d1-63b2-4f26-a350-879cf82cd09c

https://github.com/MNeMoNiCuZ/whisper-karaoke/assets/60541708/7830f598-0d1e-404a-9e57-58f1cc8e3fff

https://github.com/MNeMoNiCuZ/whisper-karaoke/assets/60541708/92bbbcf9-7914-4e79-9a39-5b46c961c5e7

https://github.com/MNeMoNiCuZ/whisper-karaoke/assets/60541708/06ff3d73-3d64-4393-aa1f-c6b545b1a029

https://github.com/MNeMoNiCuZ/whisper-karaoke/assets/60541708/af59895e-d656-4723-9bb6-bddfe2a687a0




## Requirements
The project requires Python 3.8 or greater.
It also requires you to be able to run [faster-whisper](https://github.com/SYSTRAN/faster-whisper/), which in turn requires CUDA 11 or higher.

GPU execution requires the following NVIDIA libraries to be installed:

[cuBLAS for CUDA 11](https://developer.nvidia.com/cublas)

[cuDNN 8 for CUDA 11](https://developer.nvidia.com/cudnn-downloads)

CUDA 12.4 has been tested and runs fine.

## Installation
### Automatic installation
Run `setup.bat` to create a virtual environment and install the requirements.

It will create a `launch.bat` which launches the virtual environment and runs `app.py`.

This launches a window which contains a flask server. In this window you should see a URL, copy that to your web-browser.

### Manual installation
1. Create a virtual environment.
2. Run `pip install -r requirements.txt`
3. Run `py app.py`
4. Open the URL of the launched flask server.

Note: Regarding the libraries, `tkinterdnd2` is only needed for the batch_convert.py script, and `flask` is only needed for the app.py script. `faster_whisper` is required by both.

## How to use
Once you have launched the page successfully, you should see something like this.

![image](https://github.com/MNeMoNiCuZ/whisper-karaoke/assets/60541708/65197d99-1d27-49f8-a035-631de54a9ac1)

In order to transcribe a song or sound file, just drag and drop the mp3-file onto the box and it should start the transcription. The first time this is done, the required models will download to your temporary download folder for models.

It may take a few minutes, and there's no progress bar for this. Look in the flask server console windows for the latest information.

![image](https://github.com/MNeMoNiCuZ/whisper-karaoke/assets/60541708/37d2012d-2349-48d3-af27-2acd80f5c4b8)

The mp3 will be copied to the `/static/tracks/` -folder, and two text-files will be created alongside it. These are the transcriptions as lines and words for your file.

If you are successful, it should also automatically load this file for you in the web interface.

To re-launch this track in the future, you can choose it from the drop-down list, or drag the file onto the interface again. It will not transcribe the file again if both text-files already exist.

## Batch transcribing files
In order to transcribe multiple songs at the same time, you need to launch the `batch_convert.bat` (using automatic setup), or `py batch_convert.py` using the manual setup.

![image](https://github.com/MNeMoNiCuZ/whisper-karaoke/assets/60541708/f43e1313-08b1-42a7-84c6-44b5bb796936)

This should launch a small GUI window where you can drag multiple files onto. Once you do, look in the console for that window to see the progress of the conversion. The GUI window does not update you on the status of the conversion.

![image](https://github.com/MNeMoNiCuZ/whisper-karaoke/assets/60541708/9c01d02b-61f6-4f4c-a66b-095fa4fd9a7a)



## Known bugs
There are bugs. Synchronization isn't perfect, transcription is not perfect, and there are several known bugs with the music player.
Feel free to report issues, and even better, fix them :)

- [x] Sometimes the first words of lines are missing even though they are there in the words file.

- [x] Some tracks get really  messy overlapping text without linebreaks.

- [ ] Words with overlapping timestamps should be pruned
 
- [ ] Model word hallucinations, how can it be improved? Could we rerun with different seeds or models and merge outcome?

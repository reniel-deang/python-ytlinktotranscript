import os
import yt_dlp
import assemblyai as aai
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import json
import wave
import contextlib
import shutil

# Set up AssemblyAI API key
aai.settings.api_key = ""

# Function to create a folder for audio files and transcriptions
def create_folder_for_audio(audio_name):
    folder_name = os.path.splitext(audio_name)[0]
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return folder_name

# Function to load or initialize counters for file naming
def load_counters():
    if not os.path.exists('main_audio_counter.txt'):
        with open('main_audio_counter.txt', 'w') as f:
            f.write('1')
    if not os.path.exists('segment_counter.txt'):
        with open('segment_counter.txt', 'w') as f:
            f.write('1')
    
    with open('main_audio_counter.txt', 'r') as f:
        main_counter = int(f.read())
    
    with open('segment_counter.txt', 'r') as f:
        segment_counter = int(f.read())

    return main_counter, segment_counter

# Function to update the counters
def update_counters(main_counter=None, segment_counter=None):
    if main_counter is not None:
        with open('main_audio_counter.txt', 'w') as f:
            f.write(str(main_counter))
    if segment_counter is not None:
        with open('segment_counter.txt', 'w') as f:
            f.write(str(segment_counter))

# Function to download YouTube audio and process it
def download_youtube_audio(youtube_url, download_output, transcript_output):
    try:
        main_counter, segment_counter = load_counters()

        # Set options for yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'main_audio_file_{main_counter}.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
        }

        # Download audio using yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            enable_command_line(download_output)
            download_output.insert(tk.END, f"Downloading: {youtube_url}\n")
            disable_command_line(download_output)
            ydl.download([youtube_url])

        # Define the downloaded WAV file path
        wav_file = f'main_audio_file_{main_counter}.wav'

        # Create a folder for this audio and its transcription
        folder_name = create_folder_for_audio(wav_file)

        # Move the WAV file into the new folder
        os.rename(wav_file, os.path.join(folder_name, wav_file))

        # Split the audio file and transcribe each segment
        process_wav_file(os.path.join(folder_name, wav_file), folder_name, segment_counter, download_output)

        # Increment and update the main counter
        main_counter += 1
        update_counters(main_counter=main_counter)

    except Exception as e:
        enable_command_line(download_output)
        download_output.insert(tk.END, f"An error occurred: {e}\n")
        disable_command_line(download_output)

# Function to split the WAV file into 20-second segments and transcribe each
def process_wav_file(wav_file, folder_name, segment_counter, download_output):
    try:
        with contextlib.closing(wave.open(wav_file, 'r')) as audio:
            frame_rate = audio.getframerate()
            num_frames = audio.getnframes()
            duration = num_frames / float(frame_rate)
            segment_duration = 20.0
            num_segments = int(duration // segment_duration)

            for i in range(num_segments):
                segment_name = f"audio_segmented_{segment_counter}.wav"
                start_time = i * segment_duration
                end_time = start_time + segment_duration
                save_audio_segment(wav_file, segment_name, start_time, end_time)
                download_output.insert(tk.END, f"Processing segment {i + 1}/{num_segments}\n")

                # Transcribe each segment
                segment_folder = f"audio_segmented_{segment_counter}"
                os.makedirs(segment_folder, exist_ok=True)

                # Move audio segment to its folder
                shutil.move(segment_name, os.path.join(segment_folder, segment_name))

                upload_and_transcribe(os.path.join(segment_folder, segment_name), download_output, segment_folder, segment_counter)

                segment_counter += 1

            # Update segment counter after processing
            update_counters(segment_counter=segment_counter)

            download_output.insert(tk.END, f"Audio split and transcribed into {num_segments} segments.\n")

    except Exception as e:
        download_output.insert(tk.END, f"An error occurred while processing the WAV file: {e}\n")

# Function to save an audio segment
def save_audio_segment(wav_file, segment_name, start_time, end_time):
    with contextlib.closing(wave.open(wav_file, 'r')) as audio:
        frame_rate = audio.getframerate()
        audio.setpos(int(start_time * frame_rate))
        frames = audio.readframes(int((end_time - start_time) * frame_rate))

        with wave.open(segment_name, 'w') as segment:
            segment.setparams(audio.getparams())
            segment.writeframes(frames)

# Function to upload and transcribe using AssemblyAI
def upload_and_transcribe(audio_file, download_output, segment_folder, segment_number):
    try:
        config = aai.TranscriptionConfig(language_code="tl", speech_model=aai.SpeechModel.nano)
        transcriber = aai.Transcriber(config=config)

        enable_command_line(download_output)
        download_output.insert(tk.END, f"Uploading and transcribing segment {segment_number}...\n")
        disable_command_line(download_output)

        transcript = transcriber.transcribe(audio_file)

        # Wait for transcription to complete
        while transcript.status not in [aai.TranscriptStatus.completed, aai.TranscriptStatus.error]:
            transcript = transcriber.get(transcript.id)

        # Check for errors
        if transcript.status == aai.TranscriptStatus.error:
            download_output.insert(tk.END, f"Transcription failed for segment {segment_number}: {transcript.error}\n")
            return

        # Save the transcription in a JSON file
        json_transcript_file = os.path.join(segment_folder, f"audio_segment_{segment_number}.json")
        save_transcript_json(transcript, json_transcript_file)

    except Exception as e:
        download_output.insert(tk.END, f"An error occurred during transcription of segment {segment_number}: {e}\n")

# Function to save transcript as JSON
def save_transcript_json(transcript, json_file_path):
    try:
        transcript_data = {
            "transcript": transcript.text,
            "words": [{"start": word.start, "end": word.end, "text": word.text} for word in transcript.words]
        }

        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(transcript_data, json_file, indent=4)

    except Exception as e:
        print(f"An error occurred while saving JSON: {e}")

# Function to start the process from GUI input
def start_transcription():
    youtube_link = entry.get()
    if 'list=' in youtube_link:
        enable_command_line(download_output)
        download_output.insert(tk.END, "Please provide a direct video link, not a playlist link.\n")
        disable_command_line(download_output)
    else:
        download_youtube_audio(youtube_link, download_output, transcript_output)

# Function to clear the transcription result
def clear_transcription():
    transcript_output.delete(1.0, tk.END)

# Function to show the help note
def show_help():
    messagebox.showinfo("Note", "Enter a valid YouTube link.\nResult of speech corpora may be inaccurate.")

# Helper functions to enable and disable the middle command-line area
def enable_command_line(text_widget):
    text_widget.config(state=tk.NORMAL)

def disable_command_line(text_widget):
    text_widget.config(state=tk.DISABLED)

# Prevent typing or modifying the middle command-line area
def prevent_typing(event):
    return "break"  # Break the default event action, preventing any typing

# Create tkinter GUI
root = tk.Tk()
root.title("YouTube to Transcript")
root.configure(bg="#f0f0f0")
root.geometry("600x500")

# Responsive grid configuration
root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(2, weight=1)
root.grid_rowconfigure(4, weight=1)

# YouTube link input with a question mark button
frame = ttk.Frame(root)
frame.grid(row=0, column=0, padx=20, pady=(10, 5), sticky="ew")

label = ttk.Label(frame, text="Enter YouTube video link:", font=("Arial", 12))
label.grid(row=0, column=0, sticky="w")

entry = ttk.Entry(frame, font=("Arial", 12))
entry.grid(row=0, column=1, sticky="ew")

help_button = ttk.Button(frame, text="?", command=show_help)
help_button.grid(row=0, column=2, padx=(5, 0), sticky="e")

# Transcribe button to start processing
transcribe_button = ttk.Button(root, text="Transcribe", command=start_transcription)
transcribe_button.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

# Output text area for download process (command line style, uneditable)
download_output = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=8, font=("Courier", 10), bg="#333333", fg="#ffffff", insertbackground="white")
download_output.grid(row=3, column=0, padx=20, pady=5, sticky="nsew")
download_output.bind("<Key>", prevent_typing)

# Make the middle section read-only initially
disable_command_line(download_output)

# Output text area for transcription result
transcript_output = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=8, font=("Arial", 10))
transcript_output.grid(row=4, column=0, padx=20, pady=5, sticky="nsew")

# Clear button for the transcription result
clear_button = ttk.Button(root, text="Clear Transcription", command=clear_transcription)
clear_button.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

# Run tkinter main loop
root.mainloop()

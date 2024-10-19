import os
import yt_dlp
import assemblyai as aai
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import json

# Set up AssemblyAI API key
aai.settings.api_key = "d6cc8ff458074f17b04779294f648fb9"

# Function to create directory if it doesn't exist
def create_folder_for_audio(audio_name):
    folder_name = os.path.splitext(audio_name)[0]
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return folder_name

# Function to download YouTube audio in WAV format and generate folder
def download_youtube_audio(youtube_url, download_output, transcript_output):
    try:
        # Fetch video info to get title for folder name
        with yt_dlp.YoutubeDL() as ydl:
            info_dict = ydl.extract_info(youtube_url, download=False)
            video_title = info_dict.get('title', None)

        # Set options for yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{video_title}.%(ext)s',
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
        wav_file = f'{video_title}.wav'
        
        # Create a folder for this audio and its transcription
        folder_name = create_folder_for_audio(video_title)

        # Move the WAV file into the new folder
        os.rename(wav_file, os.path.join(folder_name, wav_file))

        # Upload the WAV file to AssemblyAI and transcribe it
        upload_and_transcribe(os.path.join(folder_name, wav_file), download_output, transcript_output, folder_name)

    except Exception as e:
        enable_command_line(download_output)
        download_output.insert(tk.END, f"An error occurred: {e}\n")
        disable_command_line(download_output)

# Function to upload audio and transcribe using AssemblyAI
def upload_and_transcribe(audio_file, download_output, transcript_output, folder_name):
    try:
        config = aai.TranscriptionConfig(language_code="tl", speech_model=aai.SpeechModel.nano)
        transcriber = aai.Transcriber(config=config)

        enable_command_line(download_output)
        download_output.insert(tk.END, "Uploading audio file...\nTranscripting YouTube video...\n")
        disable_command_line(download_output)
        
        transcript = transcriber.transcribe(audio_file)

        # Wait for transcription to complete
        while transcript.status not in [aai.TranscriptStatus.completed, aai.TranscriptStatus.error]:
            transcript = transcriber.get(transcript.id)

        # Check for errors
        if transcript.status == aai.TranscriptStatus.error:
            transcript_output.insert(tk.END, f"Transcription failed: {transcript.error}\n")
            return

        # Print the transcribed text with spacing
        transcript_output.insert(tk.END, "\n---\n")  # Add separator line and spacing
        transcript_output.insert(tk.END, "Transcription completed:\n")
        transcript_output.insert(tk.END, transcript.text + "\n")

        # Save the transcription in a JSON file with segmentation and metadata
        json_transcript_file = os.path.join(folder_name, "transcript.json")
        generate_segmented_json(transcript, json_transcript_file, download_output)

    except Exception as e:
        enable_command_line(download_output)
        download_output.insert(tk.END, f"An error occurred during transcription: {e}\n")
        disable_command_line(download_output)

# Function to generate a JSON file with 20-second segmented transcription
def generate_segmented_json(transcript, json_file_path, download_output):
    try:
        segments = []
        current_segment = []
        current_start_time = 0.0
        segment_duration = 20.0  # 20 seconds segment
        
        for word in transcript.words:
            start_time = word.start / 1000.0  # Convert ms to seconds
            end_time = word.end / 1000.0

            # If we exceed the segment duration, create a new segment
            if end_time - current_start_time > segment_duration:
                if current_segment:
                    segments.append({
                        "start_time": current_start_time,
                        "end_time": current_segment[-1]["end_time"],
                        "text": " ".join([w["text"] for w in current_segment]),
                        "speaker": "unknown"  # Assuming speaker info is not available in this model
                    })
                current_start_time = start_time
                current_segment = []

            current_segment.append({
                "start_time": start_time,
                "end_time": end_time,
                "text": word.text
            })

        # Add the last segment
        if current_segment:
            segments.append({
                "start_time": current_start_time,
                "end_time": current_segment[-1]["end_time"],
                "text": " ".join([w["text"] for w in current_segment]),
                "speaker": "unknown"
            })

        # Save the segments to a JSON file
        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(segments, json_file, indent=4)
        
        download_output.insert(tk.END, f"Transcription saved in: {json_file_path}\n")

    except Exception as e:
        download_output.insert(tk.END, f"An error occurred while generating JSON: {e}\n")

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
root.geometry("600x500")  # Increased height to accommodate the version label

# Responsive grid configuration
root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(2, weight=1)
root.grid_rowconfigure(4, weight=1)

# YouTube link input with a question mark button
frame = ttk.Frame(root)
frame.grid(row=0, column=0, padx=20, pady=(10, 5), sticky="ew")

label = ttk.Label(frame, text="Enter YouTube video link:", font=("Arial", 12), background="#f0f0f0")
label.pack(side="left")

# Add the question mark button beside the label
help_button = ttk.Button(frame, text="?", width=2, command=show_help)
help_button.pack(side="left", padx=5)

entry = ttk.Entry(root, width=50, font=("Arial", 10))
entry.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

# Transcribe button
button = ttk.Button(root, text="Start Transcription", command=start_transcription)
button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

# Output text area for download process (command line style, uneditable)
download_output = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=8, font=("Courier", 10), bg="#333333", fg="#ffffff", insertbackground="white")
download_output.grid(row=3, column=0, padx=20, pady=5, sticky="nsew")
download_output.bind("<Key>", prevent_typing)  # Bind all key events to prevent typing

# Make the middle section read-only initially
disable_command_line(download_output)

# Output text area for transcription result
transcript_output = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=8, font=("Arial", 10))
transcript_output.grid(row=4, column=0, padx=20, pady=5, sticky="nsew")

# Clear transcription button
clear_button = ttk.Button(root, text="Clear Transcription", command=clear_transcription)
clear_button.grid(row=5, column=0, padx=20, pady=5, sticky="ew")

# Add a version label at the bottom
version_label = ttk.Label(root, text="Version 2.1 - YouTube to Transcript", font=("Arial", 8), background="#f0f0f0")
version_label.grid(row=6, column=0, padx=20, pady=(5, 10), sticky="ew")

root.mainloop()

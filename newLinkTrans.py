import os
import yt_dlp
import assemblyai as aai
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import json
from pydub import AudioSegment

# Set up AssemblyAI API key
aai.settings.api_key = "d6cc8ff458074f17b04779294f648fb9"

# Function to create directory if it doesn't exist
def create_folder_for_audio(audio_name):
    folder_name = os.path.splitext(audio_name)[0]
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return folder_name

# Function to download YouTube audio in WAV format and convert to 16 kHz
def download_youtube_audio(youtube_url, download_output, transcript_output):
    try:
        # Extract video title to create a unique folder
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
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
            info_dict = ydl.extract_info(youtube_url, download=False)
            audio_name = f"{info_dict.get('title', 'audio')}.wav"
            ydl.download([youtube_url])

        # Create a folder for this audio and its transcription
        folder_name = create_folder_for_audio(audio_name)

        # Convert the WAV file to 16 kHz
        convert_to_16kHz(audio_name, folder_name, download_output)

        # Upload the 16 kHz WAV file to AssemblyAI and transcribe it
        upload_and_transcribe(os.path.join(folder_name, 'audio_16kHz.wav'), download_output, transcript_output, folder_name)

    except Exception as e:
        enable_command_line(download_output)
        download_output.insert(tk.END, f"An error occurred: {e}\n")
        disable_command_line(download_output)

# Function to convert WAV file to 16 kHz
def convert_to_16kHz(wav_file, folder_name, download_output):
    try:
        download_output.insert(tk.END, "Converting audio to 16 kHz...\n")
        # Load the audio file
        audio = AudioSegment.from_wav(wav_file)
        
        # Convert the sample rate to 16 kHz
        audio_16kHz = audio.set_frame_rate(16000)
        
        # Save the new 16 kHz WAV file in the folder
        converted_wav_file = os.path.join(folder_name, 'audio_16kHz.wav')
        audio_16kHz.export(converted_wav_file, format="wav")
        
        # Remove the original file if desired
        os.remove(wav_file)

        download_output.insert(tk.END, f"Audio converted to 16 kHz and saved at {converted_wav_file}\n")
    
    except Exception as e:
        download_output.insert(tk.END, f"An error occurred during conversion: {e}\n")

# Function to upload audio and transcribe using AssemblyAI
def upload_and_transcribe(audio_file, download_output, transcript_output, folder_name):
    try:
        config = aai.TranscriptionConfig(language_code="tl", speech_model=aai.SpeechModel.nano)
        transcriber = aai.Transcriber(config=config)

        enable_command_line(download_output)
        download_output.insert(tk.END, "Uploading audio file...\nTranscribing YouTube video...\n")
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


# Function to save transcription and metadata into a JSON file
def generate_segmented_json(transcript, json_file_path, download_output):
    try:
        download_output.insert(tk.END, "Saving transcription with metadata...\n")

        # Extract segments from the transcript
        segments = []
        for word in transcript.words:
            segments.append({
                "word": word.text,
                "start": word.start,
                "end": word.end
            })

        # Create JSON data
        json_data = {
            "transcript_id": transcript.id,
            "status": transcript.status.value,
            "text": transcript.text,
            "segments": segments
        }

        # Write JSON data to file
        with open(json_file_path, "w") as json_file:
            json.dump(json_data, json_file, indent=4)

        download_output.insert(tk.END, f"Transcription saved to {json_file_path}\n")
    
    except Exception as e:
        download_output.insert(tk.END, f"An error occurred while saving the JSON file: {e}\n")


# Other functions remain the same...

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

# Clear button for the transcription result
clear_button = ttk.Button(root, text="Clear Transcription", command=clear_transcription)
clear_button.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

# Run tkinter main loop
root.mainloop()

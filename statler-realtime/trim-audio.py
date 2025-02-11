from pydub import AudioSegment

# Load the audio file
input_file = r"c:\Users\chris\OneDrive - ClearCode .Net Solutions\2025-01-29-16-14-23-gemeenteraad.mp3"
audio = AudioSegment.from_mp3(input_file)

# Calculate start time (25 minutes) in milliseconds
start_minutes = 25
start_ms = start_minutes * 60 * 1000

# Calculate duration (5 minutes) in milliseconds
duration_minutes = 5
duration_ms = duration_minutes * 60 * 1000

# Trim the audio (first trim at 25 min, then take only 5 min)
trimmed_audio = audio[start_ms:start_ms + duration_ms]

# Create output filename by adding "-trimmed-5min" before the extension
output_file = input_file.rsplit('.', 1)[0] + '-trimmed-5min.mp3'

# Export the trimmed audio
trimmed_audio.export(output_file, format="mp3")

print(f"Audio trimmed successfully. Saved as: {output_file}")

import os
import requests
from pydub import AudioSegment
import time

# Constants
ASSEMBLY_API_URL = "https://api.assemblyai.com/v2"
ASSEMBLY_API_KEY = os.getenv("ASSEMBLY_API_KEY")
INPUT_FILE = r"c:\Users\chris\OneDrive - ClearCode .Net Solutions\2025-01-29-16-14-23-gemeenteraad-trimmed-5min.mp3"
DURATION_MS = 5 * 60 * 1000  # 3 minutes in milliseconds

def upload_audio(audio_path):
    """Upload audio file to AssemblyAI"""
    headers = {
        'authorization': ASSEMBLY_API_KEY
    }
    
    with open(audio_path, 'rb') as audio_file:
        response = requests.post(
            f"{ASSEMBLY_API_URL}/upload",
            headers=headers,
            data=audio_file
        )
    return response.json()['upload_url']

def create_transcript(audio_url):
    """Create a transcript using AssemblyAI API"""
    headers = {
        "authorization": ASSEMBLY_API_KEY,
        "content-type": "application/json"
    }
    data = {
        "audio_url": audio_url,
        "language_code": "nl",
        "punctuate": False
    }
    response = requests.post(
        f"{ASSEMBLY_API_URL}/transcript",
        json=data,
        headers=headers
    )
    return response.json()

def get_transcript_result(transcript_id):
    """Get transcript result from AssemblyAI"""
    headers = {
        "authorization": ASSEMBLY_API_KEY
    }
    while True:
        response = requests.get(
            f"{ASSEMBLY_API_URL}/transcript/{transcript_id}",
            headers=headers
        )
        result = response.json()
        
        if result['status'] == 'completed':
            return result
        elif result['status'] == 'error':
            raise Exception(f"Transcription error: {result.get('error')}")
            
        time.sleep(3)

def main():
    if not ASSEMBLY_API_KEY:
        print("Error: ASSEMBLY_API_KEY environment variable not set")
        return
    
    print(f"Processing first {DURATION_MS / 60000} minutes of audio file...")
    
    # Load and trim the audio file
    audio = AudioSegment.from_mp3(INPUT_FILE)
    trimmed_audio = audio[:DURATION_MS]
    
    # Save the trimmed audio to a temporary file

    temp_path = "temp_trimmed_audio.mp3"
    trimmed_audio.export(temp_path, format="mp3")
    
    try:
        # Upload the trimmed audio
        print("Uploading audio...")
        upload_url = upload_audio(temp_path)
        
        # Create transcript
        print("Creating transcript...")
        transcript_response = create_transcript(upload_url)
        transcript_id = transcript_response['id']
        
        # Get results
        print("Waiting for transcription to complete...")
        result = get_transcript_result(transcript_id)
        
        # Save the transcript to a file
        with open("transcript-assembly.txt", "w") as f:
            f.write(result['text'])


        # Print the transcript
        if result.get('text'):


            print("\nTranscript:")
            print(result['text'])
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    main()
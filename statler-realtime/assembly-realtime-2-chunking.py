import asyncio
import base64
import json
import wave
import io
from datetime import datetime
import os
import pyaudio
import requests
import time

# Constants
ASSEMBLY_API_URL = "https://api.assemblyai.com/v2"
ASSEMBLY_API_KEY = os.getenv("ASSEMBLY_API_KEY")

# Audio settings
CHANNELS = 1
FORMAT = pyaudio.paInt16
FRAMES_PER_BUFFER = 3200
SAMPLE_RATE = 16000
CHUNK_DURATION = 15  # Duration in seconds for each audio chunk
CHUNK_OVERLAP = 2  # Overlap duration in seconds

def format_relative_time(seconds):
    """Format seconds into MM:SS format"""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

class AudioChunk:
    def __init__(self, recording_start_time):
        self.frames = []
        self.start_time = time.time()
        self.end_time = None
        self.recording_start_time = recording_start_time
        # Use relative time for chunk_id
        rel_time = format_relative_time(self.start_time - recording_start_time)
        self.chunk_id = f"chunk_{rel_time}"
        self.overlap_frames = []  # Store overlap frames from previous chunk
    
    def add_frame(self, frame):
        self.frames.append(frame)
    
    def set_overlap_frames(self, frames):
        """Set the overlap frames from the previous chunk"""
        self.overlap_frames = frames
        self.frames = self.overlap_frames + self.frames  # Prepend overlap frames
    
    def finalize(self):
        """Call this when chunk is complete to set end time"""
        self.end_time = time.time()
    
    def get_wav_bytes(self):
        with io.BytesIO() as wav_buffer:
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(CHANNELS)
                wav_file.setsampwidth(pyaudio.get_sample_size(FORMAT))
                wav_file.setframerate(SAMPLE_RATE)
                wav_file.writeframes(b''.join(self.frames))
            return wav_buffer.getvalue()

class RecordingState:
    def __init__(self):
        self.is_recording = False
        self.should_stop = False
        self.recording_start_time = None
        self.processing_chunks = []
        self.active_transcriptions = set()
        self.completed_transcriptions = []  # List to maintain order
        self.total_chunks_recorded = 0
        self.chunk_transcriptions = {}
        self.first_chunk_id = None
        self.current_chunk = None
        # Add tracking for failed chunks
        self.failed_chunks = set()
        self.processed_chunks = set()

def upload_audio(audio_bytes):
    """Upload audio bytes to AssemblyAI"""
    headers = {
        'authorization': ASSEMBLY_API_KEY
    }
    response = requests.post(
        f"{ASSEMBLY_API_URL}/upload",
        headers=headers,
        data=audio_bytes
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
        "language_code": "nl",  # Can be made configurable
        "punctuate": False  # Disable automatic punctuation
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
    response = requests.get(
        f"{ASSEMBLY_API_URL}/transcript/{transcript_id}",
        headers=headers
    )
    return response.json()

async def process_audio_chunk(chunk: AudioChunk, recording_state: RecordingState):
    """Process a single audio chunk"""
    try:
        chunk_id = chunk.chunk_id
        
        # Check if we've already processed this chunk
        if chunk_id in recording_state.processed_chunks:
            print(f"\nSkipping already processed chunk {chunk_id}")
            return
            
        # Set first_chunk_id if this is the first chunk
        if recording_state.first_chunk_id is None:
            recording_state.first_chunk_id = chunk_id
            
        duration = round(chunk.end_time - chunk.start_time, 2)
        rel_start = format_relative_time(chunk.start_time - chunk.recording_start_time)
        rel_end = format_relative_time(chunk.end_time - chunk.recording_start_time)
        
        recording_state.active_transcriptions.add(chunk_id)
        backlog = len(recording_state.active_transcriptions)
        print(f"\nProcessing chunk {chunk_id}")
        print(f"Chunk timing: {rel_start} -> {rel_end} (duration: {duration}s)")
        print(f"Status: Total recorded: {recording_state.total_chunks_recorded}, "
              f"Backlog: {backlog}, Completed: {len(recording_state.completed_transcriptions)}, "
              f"Failed: {len(recording_state.failed_chunks)}")
        
        # Upload audio chunk
        audio_bytes = chunk.get_wav_bytes()
        upload_url = upload_audio(audio_bytes)
        
        # Create transcript
        transcript_response = create_transcript(upload_url)
        transcript_id = transcript_response['id']
        
        # Poll for results with timeout and exponential backoff
        retry_count = 0
        max_retries = 10
        base_delay = 0.5
        timeout = 30  # 30 seconds timeout

        async with asyncio.timeout(timeout):
            while True:
                result = get_transcript_result(transcript_id)
                if result['status'] == 'completed':
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    text = result.get('text', '')
                    if text:
                        print(f"\n[{timestamp}] Chunk {chunk_id} completed: {text}")
                        recording_state.chunk_transcriptions[chunk_id] = text
                        recording_state.active_transcriptions.remove(chunk_id)
                        recording_state.processed_chunks.add(chunk_id)
                        if chunk_id not in recording_state.completed_transcriptions:
                            recording_state.completed_transcriptions.append(chunk_id)
                        
                        # Build complete transcription from the start
                        if recording_state.first_chunk_id:
                            try:
                                start_idx = recording_state.completed_transcriptions.index(recording_state.first_chunk_id)
                                current_idx = recording_state.completed_transcriptions.index(chunk_id)
                                chunks_to_show = recording_state.completed_transcriptions[start_idx:current_idx + 1]
                                if all(c in recording_state.chunk_transcriptions for c in chunks_to_show):
                                    full_text = [recording_state.chunk_transcriptions[c] for c in chunks_to_show]
                                    print(f"\n[{timestamp}] Full transcription from start:")
                                    print(" ".join(full_text))
                                    print(f"Chunks used: {chunks_to_show}")  # Debug info
                            except ValueError:
                                print(f"\nWarning: Could not build complete transcription, chunk ordering issue detected")
                    break
                elif result['status'] == 'error':
                    print(f"\nTranscription error for chunk {chunk_id}: {result.get('error')}")
                    recording_state.active_transcriptions.remove(chunk_id)
                    recording_state.failed_chunks.add(chunk_id)
                    break
                
                # Exponential backoff
                delay = min(base_delay * (2 ** retry_count), 5)  # Cap at 5 seconds
                await asyncio.sleep(delay)
                retry_count += 1
                
                if retry_count >= max_retries:
                    print(f"\nTimeout waiting for chunk {chunk_id}")
                    recording_state.active_transcriptions.remove(chunk_id)
                    recording_state.failed_chunks.add(chunk_id)
                    break
            
    except asyncio.TimeoutError:
        print(f"\nTimeout processing chunk {chunk_id}")
        recording_state.failed_chunks.add(chunk_id)
        if chunk_id in recording_state.active_transcriptions:
            recording_state.active_transcriptions.remove(chunk_id)
    except Exception as e:
        print(f"\nError processing chunk {chunk_id}: {e}")
        recording_state.failed_chunks.add(chunk_id)
        if chunk_id in recording_state.active_transcriptions:
            recording_state.active_transcriptions.remove(chunk_id)

async def record_audio():
    """Record audio in chunks"""
    recording_state = RecordingState()
    recording_state.is_recording = True
    recording_state.recording_start_time = time.time()
    # Create first chunk after setting recording_start_time
    recording_state.current_chunk = AudioChunk(recording_state.recording_start_time)
    
    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=FRAMES_PER_BUFFER
    )
    
    print("\nRecording started...")
    print(f"Recording chunk 1 (0:00 -> 0:{CHUNK_DURATION:02d})")
    chunk_start_time = time.time()
    last_progress_time = chunk_start_time
    
    try:
        while recording_state.is_recording:
            frame = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
            current_time = time.time()
            
            recording_state.current_chunk.add_frame(frame)
            
            # Show progress every 3 seconds
            if current_time - last_progress_time >= 3:
                elapsed = int(current_time - chunk_start_time)
                print(f"Recording chunk {recording_state.total_chunks_recorded + 1}: {elapsed}s/{CHUNK_DURATION}s", end='\r')
                last_progress_time = current_time
            
            if current_time - chunk_start_time >= CHUNK_DURATION:
                # Calculate how many frames correspond to CHUNK_OVERLAP seconds
                frames_per_second = SAMPLE_RATE / FRAMES_PER_BUFFER
                overlap_frame_count = int(CHUNK_OVERLAP * frames_per_second)
                
                # Get the last N frames for overlap
                overlap_frames = recording_state.current_chunk.frames[-overlap_frame_count:]
                
                # Finalize current chunk
                recording_state.current_chunk.finalize()
                recording_state.total_chunks_recorded += 1
                
                # Create next chunk with recording start time and overlap frames
                next_chunk = AudioChunk(recording_state.recording_start_time)
                next_chunk.set_overlap_frames(overlap_frames)
                
                chunk_to_process = recording_state.current_chunk
                recording_state.current_chunk = next_chunk
                chunk_start_time = current_time
                
                # Start processing previous chunk
                recording_state.processing_chunks.append(
                    asyncio.create_task(process_audio_chunk(chunk_to_process, recording_state))
                )
                
                # Print status update for new chunk
                backlog = len(recording_state.active_transcriptions)
                chunk_num = recording_state.total_chunks_recorded + 1
                rel_start = int(current_time - recording_state.recording_start_time)
                rel_end = rel_start + CHUNK_DURATION
                print(f"\nStarting chunk {chunk_num} ({format_relative_time(rel_start)} -> {format_relative_time(rel_end)})")
                print(f"Status: Total recorded: {recording_state.total_chunks_recorded}, "
                      f"Backlog: {backlog}, Completed: {len(recording_state.completed_transcriptions)}, "
                      f"Failed: {len(recording_state.failed_chunks)}")
            
            await asyncio.sleep(0.001)
    
    except KeyboardInterrupt:
        print("\nStopping recording...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Process final chunk if it contains data
        if recording_state.current_chunk.frames:
            recording_state.processing_chunks.append(
                asyncio.create_task(process_audio_chunk(recording_state.current_chunk, recording_state))
            )
        
        # Wait for all processing to complete
        if recording_state.processing_chunks:
            print("Processing remaining audio chunks...")
            await asyncio.gather(*recording_state.processing_chunks)
        print("Recording stopped")

async def main():
    if not ASSEMBLY_API_KEY:
        print("Error: ASSEMBLY_API_KEY environment variable not set")
        return
    
    print("Real-Time Transcription Tool")
    print("----------------------------")
    await record_audio()

if __name__ == "__main__":
    asyncio.run(main())
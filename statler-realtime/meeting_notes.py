import asyncio
import websockets
import json
import pyaudio
import base64
import logging
import os
import ssl
import threading
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INSTRUCTIONS = """
You are a professional meeting note-taker. As you listen to the conversation:
1. Capture key points and decisions made
2. Note any action items and who is responsible
3. Summarize important discussions
4. Keep notes clear and concise
5. Format the notes in a professional manner with markdown

Keep your responses focused on documenting the meeting content.

Additionally:
- Identify and list important topics being discussed
- Track key entities (people, organizations, projects) mentioned
- Format any identified topics with #topic and entities with @entity
"""

KEYBOARD_COMMANDS = """
Commands:
q: Quit meeting
t: Type a note manually
a: Start/stop audio recording
s: Save notes to file
"""

class AudioHandler:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.audio_buffer = b''
        self.chunk_size = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 24000
        self.is_recording = False

    def start_audio_stream(self):
        self.stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        logger.info("Started audio recording")

    def stop_audio_stream(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            logger.info("Stopped audio recording")

    def cleanup(self):
        if self.stream:
            self.stop_audio_stream()
        self.p.terminate()

    def start_recording(self):
        self.is_recording = True
        self.audio_buffer = b''
        self.start_audio_stream()

    def stop_recording(self):
        self.is_recording = False
        self.stop_audio_stream()
        return self.audio_buffer

    def record_chunk(self):
        if self.stream and self.is_recording:
            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                self.audio_buffer += data
                return data
            except Exception as e:
                logger.error(f"Error recording audio: {e}")
        return None

class MeetingNotesClient:
    def __init__(self, voice="alloy"):
        self.url = "wss://api.openai.com/v1/realtime"
        self.model = "gpt-4-turbo-preview"
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.ws = None
        self.audio_handler = AudioHandler()
        
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        self.notes = []
        self.topics = set()
        self.entities = set()
        
        self.session_config = {
            "modalities": ["audio", "text"],
            "instructions": INSTRUCTIONS + """
Additionally:
- Identify and list important topics being discussed
- Track key entities (people, organizations, projects) mentioned
- Format any identified topics with #topic and entities with @entity
""",
            "voice": voice,
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "turn_detection": None,
            "input_audio_transcription": {
                "model": "whisper-1"
            },
            "temperature": 0.7
        }
        logger.info("Initializing MeetingNotesClient with voice: %s", voice)
        self.max_retries = 5
        self.retry_delay = 2
        self.connection_timeout = 10

    async def connect(self):
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Waiting {delay} seconds before reconnection attempt...")
                    await asyncio.sleep(delay)
                
                logger.info(f"Connection attempt {attempt + 1}/{self.max_retries}")
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "OpenAI-Beta": "realtime=v1"
                }
                
                async with asyncio.timeout(self.connection_timeout):
                    self.ws = await websockets.connect(
                        f"{self.url}?model={self.model}",
                        additional_headers=headers,
                        ssl=self.ssl_context
                    )
                    
                    try:
                        pong = await self.ws.ping()
                        await asyncio.wait_for(pong, timeout=5.0)
                        logger.info("WebSocket connection verified with ping")
                    except (asyncio.TimeoutError, websockets.ConnectionClosed):
                        raise ConnectionError("Failed to verify WebSocket connection")
                
                await self.send_event({
                    "type": "session.update",
                    "session": self.session_config
                })
                logger.info("Session configuration sent")
                
                try:
                    response = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
                    logger.info(f"Session update response: {response}")
                except asyncio.TimeoutError:
                    logger.error("Timeout waiting for session update response")
                    raise
                
                await self.send_event({"type": "response.create"})
                logger.info("Connected to OpenAI Realtime API and ready for interaction")

                self.receiver_task = asyncio.create_task(self.message_receiver())
                logger.info("Started WebSocket receiver task")
                return
            except asyncio.TimeoutError:
                logger.error(f"Connection attempt {attempt + 1} timed out")
                continue
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Connection failed: {str(e)}. Will retry...")
                else:
                    logger.error(f"Failed to connect after {self.max_retries} attempts: {str(e)}")
                    raise

    async def send_event(self, event):
        for attempt in range(self.max_retries):
            try:
                event_type = event.get("type")
                logger.info(f"Sent event: {event_type}")
                if event_type != "input_audio_buffer.append":  # Don't log audio buffers to avoid spam
                    logger.debug("Sending event: %s", json.dumps(event))
                await self.ws.send(json.dumps(event))
                return
            except websockets.ConnectionClosed:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Connection closed. Attempting to reconnect... ({attempt + 1}/{self.max_retries})")
                    await self.connect()
                else:
                    logger.error("Failed to send event after reconnection attempts")
                    raise
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Failed to send event: {str(e)}. Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Failed to send event after {self.max_retries} attempts")
                    raise

    async def handle_event(self, event):
        event_type = event.get("type")
        logger.info(f"Received event: {event_type}")
        if event_type == "error":
            error_msg = event.get('error', {}).get('message', 'Unknown error')
            session_id = event.get('error', {}).get('session_id')
            logger.error(f"API Error (Session ID: {session_id}): {error_msg}")
            
            if "server_error" in error_msg.lower():
                logger.info("Server error detected, attempting to recover...")
                await self.handle_server_error()
        elif event_type == "session.created":
            logger.info("Session created")
        elif event_type == "session.updated":
            logger.info("Session updated")
        elif event_type == "input_audio_buffer.speech_started":
            logger.info("Speech started")
        elif event_type == "input_audio_buffer.speech_stopped":
            logger.info("Speech stopped")
        elif event_type == "input_audio_buffer.committed":
            logger.info("Audio buffer committed")
        elif event_type == "conversation.item.created":
            logger.info("Conversation item created")
        elif event_type == "response.created":
            logger.info("Response created")
        elif event_type == "response.text.delta":
            text = event["delta"]
            logger.debug("Received text delta: %s", text)
            self.notes.append(text)
            self._extract_topics_entities(text)
            self._display_summary()
        elif event_type == "response.done":
            logger.info("Response completed")
            print("\n")
        else:
            logger.debug(f"Received unhandled event type: {event_type}")

    def _extract_topics_entities(self, text):
        # Extract topics (marked with #)
        topics = set(word.strip() for word in text.split() if word.startswith('#'))
        self.topics.update(topics)
        
        # Extract entities (marked with @)
        entities = set(word.strip() for word in text.split() if word.startswith('@'))
        self.entities.update(entities)

    def _display_summary(self):
        # Clear previous lines (ANSI escape codes)
        print('\033[2J\033[H', end='')
        
        # Display current topics and entities
        if self.topics:
            print("\n=== Current Topics ===")
            for topic in sorted(self.topics):
                print(f"• {topic}")
        
        if self.entities:
            print("\n=== Key Entities ===")
            for entity in sorted(self.entities):
                print(f"• {entity}")
        
        print("\n=== Meeting Notes ===")
        print("".join(self.notes[-1000:]))  # Show last 1000 characters to avoid cluttering
        
        # Add keyboard commands at the bottom
        print(f"\n{KEYBOARD_COMMANDS}")

    async def receive_events(self):
        try:
            async for message in self.ws:
                event = json.loads(message)
                await self.handle_event(event)
        except websockets.ConnectionClosed:
            logger.error("WebSocket connection closed")

    async def send_audio(self):
        logger.info("Starting audio transmission")
        
        self.audio_handler.start_recording()
        logger.info("Recording... Press 'a' again to stop")
        
        async def audio_sender():
            chunks_sent = 0
            try:
                while self.audio_handler.is_recording:
                    chunk = await asyncio.get_event_loop().run_in_executor(
                        None, self.audio_handler.record_chunk
                    )
                    if chunk:
                        base64_chunk = base64.b64encode(chunk).decode('utf-8')
                        await self.send_event({
                            "type": "input_audio_buffer.append",
                            "audio": base64_chunk
                        })
                        chunks_sent += 1
                        if chunks_sent % 100 == 0:  # Log every 100 chunks
                            logger.info(f"Sent {chunks_sent} audio chunks")
                    await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Error in audio sender: {e}")
            finally:
                logger.info(f"Audio sender finished. Total chunks sent: {chunks_sent}")
                self.audio_handler.stop_recording()
                logger.info("Audio recording stopped, committing final buffer")
                await self.send_event({
                    "type": "input_audio_buffer.commit"
                })
                # Add timeout handling for commit response
                try:
                    response = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
                    logger.info(f"Buffer commit response: {response}")
                except asyncio.TimeoutError:
                    logger.error("Timeout waiting for buffer commit response")
                
                await self.send_event({"type": "response.create"})

        # Create and start the audio sender task
        audio_task = asyncio.create_task(audio_sender())
        return audio_task

    def save_notes(self):
        timestamp = asyncio.get_event_loop().time()
        filename = f"meeting_notes_{int(timestamp)}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("".join(self.notes))
        logger.info(f"Notes saved to {filename}")

    async def run(self):
        await self.connect()
        receive_task = asyncio.create_task(self.receive_events())
        audio_task = None

        # Print initial instructions for user
        print("\nMeeting Notes Tool Started!")
        print("Press 'a' to start audio recording and listen to the meeting")
        print(KEYBOARD_COMMANDS)

        try:
            while True:
                command = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input().strip().lower()
                )
                
                if command == 'q':
                    break
                elif command == 'a':
                    if not self.audio_handler.is_recording:
                        audio_task = await self.send_audio()
                    else:
                        self.audio_handler.is_recording = False
                        if audio_task:
                            await audio_task
                            audio_task = None
                
                await asyncio.sleep(0.1)
        finally:
            if audio_task:
                audio_task.cancel()
            receive_task.cancel()
            await self.cleanup()

    async def cleanup(self):
        logger.info("Starting cleanup process")
        self.audio_handler.cleanup()
        if self.ws:
            await self.ws.close()
            logger.info("WebSocket connection closed")

    async def message_receiver(self):
        """Continuously listen for messages from the WebSocket connection"""
        logger.info("Message receiver started")
        while True:
            try:
                message = await self.ws.recv()
                logger.info(f"Received message: {message}")
                
                # Parse and handle the message
                try:
                    msg_data = json.loads(message)
                    msg_type = msg_data.get('type', '')
                    
                    if msg_type == 'error':
                        logger.error(f"API Error: {msg_data.get('message', 'Unknown error')}")
                    elif msg_type == 'transcript':
                        logger.info(f"Transcript: {msg_data.get('text', '')}")
                    else:
                        logger.info(f"Other message type received: {msg_type}")
                        
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse message: {message}")
                    
            except websockets.exceptions.ConnectionClosed:
                logger.error("WebSocket connection closed")
                break
            except Exception as e:
                logger.error(f"Error in message receiver: {e}")
                break
        
        logger.info("Message receiver stopped")

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    async def handle_server_error(self):
        """Handle server errors with exponential backoff retry"""
        for attempt in range(self.max_retries):
            try:
                # Close existing connection and cleanup
                await self.cleanup()
                
                # Wait with exponential backoff
                delay = self.retry_delay * (2 ** attempt)
                logger.info(f"Attempting reconnection in {delay} seconds...")
                await asyncio.sleep(delay)
                
                # Attempt to reconnect
                await self.connect()
                await self.send_event({"type": "response.create"})
                logger.info("Successfully recovered from server error")
                return
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to recover from server error after {self.max_retries} attempts: {e}")
                    raise
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")

async def main():
    client = MeetingNotesClient()
    try:
        await client.run()
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        logger.info("Meeting ended")

if __name__ == "__main__":
    asyncio.run(main()) 
import asyncio
import base64
import json
import sys
from datetime import time, datetime
from typing import Literal, TypedDict, List
import os
import pyaudio
import requests
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
import streamlit as st
from transcript_processor import TranscriptProcessor, TranscriptSegment
import os
from streamlit.runtime.scriptrunner.script_runner import StopException

## Constants
GLADIA_API_URL = "https://api.gladia.io"

# Streamlit UI setup
st.set_page_config(
    page_title="Real-Time Transcription Tool",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("Real-Time Transcription Tool")

# Add a new helper class for state management
class RecordingState:
    def __init__(self):
        self.is_recording = False
        self.should_stop = False

# Update session state initialization
if 'recording_state' not in st.session_state:
    st.session_state.recording_state = RecordingState()
if 'processor' not in st.session_state:
    st.session_state.processor = TranscriptProcessor()
if 'transcripts' not in st.session_state:
    st.session_state.transcripts = []
if 'auto_scroll' not in st.session_state:
    st.session_state.auto_scroll = True

## Type definitions
class InitiateResponse(TypedDict):
    id: str
    url: str

class LanguageConfiguration(TypedDict):
    languages: list[str] | None
    code_switching: bool | None

class StreamingConfiguration(TypedDict):
    # This is a reduced set of options. For a full list, see the API documentation.
    # https://docs.gladia.io/api-reference/v2/live/init
    encoding: Literal["wav/pcm", "wav/alaw", "wav/ulaw"]
    bit_depth: Literal[8, 16, 24, 32]
    sample_rate: Literal[8_000, 16_000, 32_000, 44_100, 48_000]
    channels: int
    language_config: LanguageConfiguration | None


def init_live_session(config: StreamingConfiguration) -> InitiateResponse:
    gladia_key = os.getenv("GLADIA_API_KEY")
    response = requests.post(
        f"{GLADIA_API_URL}/v2/live",
        headers={"X-Gladia-Key": gladia_key},
        json=config,
        timeout=3,
    )
    if not response.ok:
        print(f"{response.status_code}: {response.text or response.reason}")
        exit(response.status_code)
    return response.json()


def format_duration(seconds: float) -> str:
    milliseconds = int(seconds * 1_000)
    return time(
        hour=milliseconds // 3_600_000,
        minute=(milliseconds // 60_000) % 60,
        second=(milliseconds // 1_000) % 60,
        microsecond=milliseconds % 1_000 * 1_000,
    ).isoformat(timespec="milliseconds")



async def print_messages_from_socket(socket: ClientConnection, recording_state: RecordingState) -> None:
    processor = st.session_state.processor

    try:
        async for message in socket:
            #print(message)
            if recording_state.should_stop:
                break
                
            try:
                content = json.loads(message)
                if content["type"] == "transcript" and content["data"]["is_final"]:
                    print(content)
                    start = content["data"]["utterance"]["start"]
                    end = content["data"]["utterance"]["end"]
                    text = content["data"]["utterance"]["text"].strip()
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    transcripts = list(st.session_state.transcripts)
                    transcripts.append({
                        "timestamp": timestamp,
                        "start": start,
                        "end": end,
                        "text": text
                    })
                    st.session_state.transcripts = transcripts
                    segment = TranscriptSegment(start=start, end=end, text=text)
                    processor.add_segment(segment)

                if content["type"] == "post_final_transcript":
                    print("End of session")
                    
            except Exception as e:
                print(f"Error processing message: {e}")
                continue
                
    except (ConnectionClosedError, ConnectionClosedOK) as e:
        print(f"Connection closed: {e}")
    except StopException:
        print("Streamlit stop requested in print_messages_from_socket")
    except Exception as e:
        print(f"Error in print_messages: {e}")
    finally:
        if recording_state.should_stop:
            print("Exiting print_messages_from_socket")


async def stop_recording(websocket: ClientConnection) -> None:
    print(">>>>> Ending the recording…")
    await websocket.send(json.dumps({"type": "stop_recording"}))
    await asyncio.sleep(0)


## Sample code
P = pyaudio.PyAudio()

CHANNELS = 1
FORMAT = pyaudio.paInt16
FRAMES_PER_BUFFER = 3200
SAMPLE_RATE = 16_000

STREAMING_CONFIGURATION: StreamingConfiguration = {
    "encoding": "wav/pcm",
    "sample_rate": SAMPLE_RATE,
    "bit_depth": 16,  # It should match the FORMAT value
    "channels": CHANNELS,
    "language_config": {
        "languages": ["nl"],
        "code_switching": False,
    },
}


async def send_audio(socket: ClientConnection, recording_state: RecordingState) -> None:
    try:
        stream = P.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=FRAMES_PER_BUFFER,
        )

        while recording_state.is_recording and not recording_state.should_stop:
            try:
                data = stream.read(FRAMES_PER_BUFFER)
                data = base64.b64encode(data).decode("utf-8")
                json_data = json.dumps({"type": "audio_chunk", "data": {"chunk": str(data)}})
                await socket.send(json_data)
                await asyncio.sleep(0.1)
            except (ConnectionClosedError, ConnectionClosedOK) as e:
                print(f"Connection closed: {e}")
                break
            except Exception as e:
                print(f"Error in send_audio: {e}")
                break
    except StopException:
        print("Streamlit stop requested in send_audio")
    finally:
        stream.stop_stream()
        stream.close()


async def main():
    # Sidebar settings
    with st.sidebar:
        st.header("Settings")
        st.session_state.auto_scroll = st.toggle("Auto-scroll", value=True)
        language = st.selectbox("Language", ["Dutch", "English", "Auto-detect"])
        update_freq = st.slider("Update frequency (ms)", 100, 1000, 100)
        
        if st.button("Clear Transcripts"):
            st.session_state.transcripts = []
            st.experimental_rerun()

    # Main content area
    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.header("Live Transcription")
        
        # Control buttons in a horizontal layout
        col1, col2 = st.columns(2)
        with col1:
            start_button = st.button(
                "▶️ Start Recording",
                disabled=st.session_state.recording_state.is_recording,
                use_container_width=True
            )
        with col2:
            stop_button = st.button(
                "⏹️ Stop Recording",
                disabled=not st.session_state.recording_state.is_recording,
                use_container_width=True
            )
            
            with st.container():
                st.markdown('<div class="transcript-box">', unsafe_allow_html=True)
                for transcript in reversed(st.session_state.transcripts):
                    with st.expander(
                        f"🎯 {transcript['timestamp']}", 
                        expanded=True
                    ):
                        st.write(transcript['text'])
                st.markdown('</div>', unsafe_allow_html=True)

    with right_col:
        st.header("Analysis")
        
        tab1, tab2 = st.tabs(["Statistics", "Export"])
        
        with tab1:
            st.subheader("Session Stats")
            stats_col1, stats_col2 = st.columns(2)
            with stats_col1:
                st.metric("Duration", "00:00:00")
            with stats_col2:
                st.metric("Word Count", len(st.session_state.transcripts))
        
        with tab2:
            st.subheader("Export Options")
            export_format = st.selectbox(
                "Format",
                ["TXT", "JSON", "SRT"]
            )
            if st.button("Export Transcript"):
                # Add export functionality here
                pass

        # Recording status indicator
        if st.session_state.recording_state.is_recording:
            st.success("🎙️ Recording in progress...")
        else:
            st.info("Ready to record")

    # Handle recording logic
    if start_button:
        st.info("Started")

        try:
            recording_state = st.session_state.recording_state
            recording_state.is_recording = True
            recording_state.should_stop = False
            
            response = init_live_session(STREAMING_CONFIGURATION)
            
            async with connect(
                response["url"],
                ping_interval=20,
                ping_timeout=60,
                close_timeout=5
            ) as websocket:
                send_audio_task = asyncio.create_task(
                    send_audio(websocket, recording_state)
                )
                print_messages_task = asyncio.create_task(
                    print_messages_from_socket(websocket, recording_state)
                )
                
                try:
                    done, pending = await asyncio.wait(
                        [send_audio_task, print_messages_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    recording_state.should_stop = True
                    
                    # Cancel any pending tasks
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except (asyncio.CancelledError, StopException):
                            pass
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                finally:
                    recording_state.is_recording = False
                    recording_state.should_stop = True
                    
                    # Ensure tasks are cleaned up
                    for task in [send_audio_task, print_messages_task]:
                        if not task.done():
                            task.cancel()
                            try:
                                await task
                            except (asyncio.CancelledError, StopException):
                                pass
        
        except Exception as e:
            st.error(f"Connection error: {str(e)}")
            st.session_state.recording_state.is_recording = False
            st.session_state.recording_state.should_stop = True
    
    if stop_button:
        st.session_state.recording_state.should_stop = True
        st.session_state.recording_state.is_recording = False


if __name__ == "__main__":
    os.environ['STREAMLIT_SERVER_PORT'] = '7000'
    asyncio.run(main())
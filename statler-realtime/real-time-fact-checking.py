import openai
import json
import os
from pathlib import Path
import numpy as np
import soundfile as sf
from datetime import datetime
import time
from dotenv import load_dotenv
from colorama import Fore, Style, init

# Initialize colorama for colored console output
init()

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

class RealTimeCouncilAnalyzer:
    def __init__(self, audio_file):
        self.audio_file = audio_file
        self.chunk_duration = 30  # Process 30 seconds at a time
        self.topics = set()
        self.entities = set()
        self.fact_check_questions = []
        self.client = openai.OpenAI()  # Initialize OpenAI client
        
    def load_audio(self):
        """Load and prepare audio file for processing"""
        try:
            data, samplerate = sf.read(self.audio_file)
            return data, samplerate
        except Exception as e:
            print(f"{Fore.RED}Error loading audio file: {e}{Style.RESET_ALL}")
            return None, None

    def process_chunk(self, audio_chunk, samplerate):
        """Process a chunk of audio using OpenAI's Whisper API"""
        # Save temporary audio chunk
        temp_file = "temp_chunk.wav"
        sf.write(temp_file, audio_chunk, samplerate)
        
        try:
            with open(temp_file, "rb") as audio_file:
                # Updated Whisper API call using new client library
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="nl"
                )
            
            # Analyze the transcribed text
            self.analyze_content(transcript.text)
            
        except Exception as e:
            print(f"{Fore.RED}Error processing audio chunk: {e}{Style.RESET_ALL}")
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def analyze_content(self, text):
        """Analyze transcribed text for topics, entities, and fact-checking questions"""
        try:
            # Updated Chat API call using new client library
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": """
                    Analyze the provided text from a Dutch municipal council meeting.
                    Identify:
                    1. Key topics being discussed
                    2. Important entities (people, organizations, locations)
                    3. Generate relevant fact-checking questions
                    Respond in JSON format with these categories.
                    """},
                    {"role": "user", "content": text}
                ]
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            # Update our tracking sets and lists
            self.topics.update(analysis.get("topics", []))
            self.entities.update(analysis.get("entities", []))
            new_questions = analysis.get("fact_checking_questions", [])
            self.fact_check_questions.extend(new_questions)
            
            # Display real-time updates
            self.display_updates(analysis)
            
        except Exception as e:
            print(f"{Fore.RED}Error analyzing content: {e}{Style.RESET_ALL}")

    def display_updates(self, analysis):
        """Display real-time updates to the console"""
        print("\n" + "="*50)
        print(f"{Fore.CYAN}Time: {datetime.now().strftime('%H:%M:%S')}{Style.RESET_ALL}")
        
        if "topics" in analysis:
            print(f"\n{Fore.GREEN}New Topics Detected:{Style.RESET_ALL}")
            for topic in analysis["topics"]:
                print(f"• {topic}")
        
        if "entities" in analysis:
            print(f"\n{Fore.YELLOW}Entities Mentioned:{Style.RESET_ALL}")
            for entity in analysis["entities"]:
                print(f"• {entity}")
        
        if "fact_checking_questions" in analysis:
            print(f"\n{Fore.MAGENTA}Fact-Checking Questions:{Style.RESET_ALL}")
            for question in analysis["fact_checking_questions"]:
                print(f"• {question}")
        
        print("="*50 + "\n")

    def process_audio_file(self):
        """Main method to process the audio file in chunks"""
        data, samplerate = self.load_audio()
        if data is None:
            return
        
        # Calculate chunk size based on duration
        chunk_size = int(samplerate * self.chunk_duration)
        
        # Process audio in chunks
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            print(f"\nProcessing chunk starting at {i//samplerate} seconds...")
            self.process_chunk(chunk, samplerate)
            time.sleep(1)  # Small delay to simulate real-time processing

def main():
    # Audio file path
    audio_file = "real-time-tool/2025-01-29-16-14-23-gemeenteraad.mp3"
    
    if not os.path.exists(audio_file):
        print(f"{Fore.RED}Error: Audio file not found: {audio_file}{Style.RESET_ALL}")
        return
    
    print(f"{Fore.GREEN}Starting real-time analysis of council meeting...{Style.RESET_ALL}")
    analyzer = RealTimeCouncilAnalyzer(audio_file)
    analyzer.process_audio_file()

if __name__ == "__main__":
    main()

import asyncio
import json
from typing import List, TypedDict
import streamlit as st
from google.generativeai import GenerativeModel
from src.milvus import search_documents
from src.perplexity_api import PerplexityAPI
import os
TRANSCRIPT_BUFFER_SIZE = 2  # Number of segments to process together
GEMINI_MODEL = "gemini-1.5-flash-8b"

class TranscriptSegment(TypedDict):
    start: float
    end: float
    text: str

class TranscriptProcessor:
    def __init__(self):
        self.segments: List[TranscriptSegment] = []
        self.genai_model = GenerativeModel(GEMINI_MODEL) 
        self.perplexity_client = PerplexityAPI(api_key=os.getenv("PERPLEXITY_API_KEY"))
        
    async def process_segments(self):
        if len(self.segments) < TRANSCRIPT_BUFFER_SIZE:
            return
            
        # Combine recent segments
        combined_text = "\n".join(seg["text"] for seg in self.segments[-TRANSCRIPT_BUFFER_SIZE:])
        
        st.write("analyzing segments")
        # Initial analysis with more strict JSON formatting instructions
        analysis = self.genai_model.generate_content(f"""
            Analyze this transcript segment from a municipal council meeting and return a JSON object.
            Transcript:
            <transcript>{combined_text}</transcript>
            Identify:
            1. Current topic and speaker positions  in Dutch
            2. Any decisions or proposals in Dutch
            3. Should we search municipal archives? If yes, output 3 semantic search phrases in Dutch for similar discussions
            4. Should we search internet sources? If yes, output search phrase in Dutch for internet search
            Return ONLY a valid JSON object with this exact structure, no other text:
            {{
                "topic": "current topic in Dutch",       
                "decisions_or_proposals": ["decision 1 in Dutch", "decision 2 in Dutch"],
                "search_municipal_archives": ["search phrase 1", "search phrase 2", "search phrase 3"],
                "search_internet": "search phrase for internet search"
            }}
        """)
        
        try:
            # Debug output to see what we're getting
            #st.write("Raw response:", analysis.text)
            
            # Remove any backticks or other non-JSON characters
            cleaned_text = analysis.text.strip().strip('```json ').strip('```')
            
            # Try to parse the JSON
            analysis_dict = json.loads(cleaned_text)
            
        except json.JSONDecodeError as e:
            st.error(f"Failed to parse JSON: {e}")
            st.error(f"Received text: {analysis.text}")
            return
        
        results = []
        
        # Perform searches if needed
        if "search_municipal_archives" in analysis_dict.keys() and len(analysis_dict["search_municipal_archives"]) > 0:    
            st.write("searching municipal archives")
            archive_results = search_documents(analysis_dict["search_municipal_archives"][0], limit=5)                                    
            results.extend(archive_results)            

        if "search_internet" in analysis_dict.keys() and len(analysis_dict["search_internet"]) > 0:
            st.write("searching internet")
            web_results, citations = self.perplexity_client.search(analysis_dict["search_internet"], system_prompt="Je bent een expert adviseur voor gemeentelijke beleidsmakers. Gebruik wetenschappelijke publicaties, nieuwsbronnen en social media bronnen om een accuraat antwoord op de vraag te geven. Gebruik geen markdown in je antwoord. Werk in het Nederlands.")
            results.extend(web_results[0])  # Assuming the first element is the result you need

        # Final summary
        if len(results) > 0:
            st.write("creating summary")
            summary = self.genai_model.generate_content(f"""
                Context: {combined_text}
                Huidige discussie: {analysis_dict["topic"]}
                Vorige relevante besluiten: {results}

                Geef 2-3 bullet points op:
                - Gerelateerde historische besluiten
                - Belangrijkste belanghebbende standpunten
                - Potentiële beleidsimplicaties
                In het Nederlands.
            """)
            with st.container():
                st.subheader("Analysis Update")
                st.write(summary.text)

    def add_segment(self, segment: TranscriptSegment):
        self.segments.append(segment)
        st.session_state.transcripts.append(segment)
        asyncio.create_task(self.process_segments())

import os
import json
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from pathlib import Path
import logging
from typing import Dict, List
from datetime import datetime
import asyncio

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('document_processing.log'),
        logging.StreamHandler()
    ]
)

def setup_gemini_model():
    """Configure and return the Gemini model with proper schema"""
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    
    genai.configure(api_key=GEMINI_API_KEY)

    generation_config = {
        "temperature": 0,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_schema": content.Schema(
            type=content.Type.OBJECT,
            required=["summary", "quality", "missing_context", "document_references", 
                     "language", "status_changes", "dates", "topics", "entity_names"],
            properties={
                "summary": content.Schema(type=content.Type.STRING),
                "quality": content.Schema(type=content.Type.INTEGER),
                "missing_context": content.Schema(
                    type=content.Type.ARRAY,
                    items=content.Schema(type=content.Type.STRING)
                ),
                "document_references": content.Schema(
                    type=content.Type.ARRAY,
                    items=content.Schema(type=content.Type.STRING)
                ),
                "language": content.Schema(type=content.Type.STRING),
                "status_changes": content.Schema(
                    type=content.Type.ARRAY,
                    items=content.Schema(type=content.Type.STRING)
                ),
                "dates": content.Schema(
                    type=content.Type.ARRAY,
                    items=content.Schema(type=content.Type.STRING)
                ),
                "topics": content.Schema(
                    type=content.Type.ARRAY,
                    items=content.Schema(type=content.Type.STRING)
                ),
                "entity_names": content.Schema(
                    type=content.Type.ARRAY,
                    items=content.Schema(type=content.Type.STRING)
                ),
            },
        ),
        "response_mime_type": "application/json",
    }

    return genai.GenerativeModel(
        model_name="gemini-1.5-flash-8b",
        generation_config=generation_config
    )

def create_analysis_prompt(text: str) -> str:
    """Create the analysis prompt for a given text chunk"""
    return f"""<text>
{text}
</text>

Analyze this Dutch policy document text chunk:
* determine language
* determine any other documents that the text refers to
* determine missing context (preceeding or following text or other documents)
* extract its main topics in Dutch, use 1 or 2 word topic names
* extract any entity names (persons, organisations, political parties)
* extract important topic status changes
* determine subjective text quality and usefulness for a policy maker in regards to the topics discussed, from 0 to 100, where 0 is a nonsensical mess and 100 is extremely useful and clearly readable text
* find important dates mentioned, always as YYYY-MM
* give it a short title in Dutch
* write a simple 15-word-max summary in Dutch"""

async def process_chunk(model, chunk: Dict) -> Dict:
    """Process a single text chunk using the Gemini model"""
    try:
        response = await model.generate_content_async(
            create_analysis_prompt(chunk["text"])
        )
        # Parse the response content as JSON
        response_content = json.loads(response.text)
        return {
            "chunk_end": chunk["end"],
            "analysis": response_content
        }
    except Exception as e:
        logging.error(f"Error processing chunk: {str(e)}")
        return None

async def process_file(model, file_path: Path) -> Dict:
    """Process a single JSON file containing document chunks"""
    try:
        logging.info(f"Opening file {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "chunks" not in data:
            logging.error(f"File {file_path} does not contain 'chunks' key")
            return None
        
        processed_chunks = []
        # Process chunks in batches of 5
        for i in range(0, len(data["chunks"]), 5):
            chunk_batch = data["chunks"][i:i+5]
            logging.info(f"Processing chunk batch ending at {[chunk.get('end') for chunk in chunk_batch]}")
            results = await asyncio.gather(
                *(process_chunk(model, chunk) for chunk in chunk_batch)
            )
            processed_chunks.extend(filter(None, results))
        
        output = {
            "source_file": str(file_path),
            "original_metadata": data.get("metadata", {}),
            "processed_chunks": processed_chunks,
            "processed_at": datetime.now().isoformat()
        }
        
        # Save results to output file
        output_path = file_path.parent / f"{file_path.stem}_analyzed.json"
        logging.info(f"Saving results to {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Successfully processed {file_path}")
        return output
        
    except Exception as e:
        logging.error(f"Error processing file {file_path}: {str(e)}")
        return None

async def main():
    """Main function to process all JSON files"""
    model = setup_gemini_model()
    base_path = Path(r"c:\politieke-datasets")
    
    # Find all JSON files
    json_files = list(base_path.rglob("*.json"))[:3]
    logging.info(f"Found {len(json_files)} JSON files to process")
    
    # Process each file
    for file_path in json_files:
        logging.info(f"Processing {file_path}")
        await process_file(model, file_path)

if __name__ == "__main__":
    asyncio.run(main()) 
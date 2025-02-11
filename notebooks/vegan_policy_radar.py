import json
import plotly.graph_objects as go
from anthropic import Anthropic
import pandas as pd
from functools import lru_cache
from queries import search_documents



def create_radar_chart(data_json):
    # Load the JSON data
    data = json.loads(data_json)
    
    # Define a colorful palette
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEEAD', 
              '#D4A5A5', '#9B59B6', '#3498DB', '#E67E22', '#2ECC71']
    
    # Create the radar chart
    fig = go.Figure()
    
    # Add traces for each political party
    categories = list(data['categories'].keys())
    
    # Dutch translations for common category names
    dutch_translations = {
        'Support for plant-based initiatives': 'Steun voor plantaardige initiatieven',
        'Climate consideration in food policy': 'Klimaatoverweging in voedselbeleid',
        'Animal welfare positions': 'Standpunten dierenwelzijn',
        'Economic support for plant-based transition': 'Economische steun voor plantaardige transitie',
        'Public health focus in food policy': 'Focus op volksgezondheid in voedselbeleid'
    }
    
    # Translate categories if they exist in the translation dictionary
    dutch_categories = [dutch_translations.get(cat, cat) for cat in categories]
    
    for i, party in enumerate(data['party_scores']):
        party_name = party['party']
        scores = [party['scores'][cat] for cat in categories]
        
        # Add a trace for this party with a specific color
        fig.add_trace(go.Scatterpolar(
            r=scores,
            theta=dutch_categories,  # Use Dutch categories
            name=party_name,
            fill='toself',
            line=dict(color=colors[i % len(colors)])  # Cycle through colors
        ))
    
    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10]
            )),
        showlegend=True,
        title="Politieke Partijen - Plantaardig en Veganistisch Beleid",
        title_x=0.5,
        font=dict(family="Arial", size=12)
    )
    
    return fig

@lru_cache(maxsize=10)
def analyze_documents_with_claude(query):
    # Get a larger set of documents
    docs_df = search_documents(query, limit=400)
    print(f"Total documents found: {len(docs_df)}")
    
    # Create chunks of 200 documents
    chunk_size = 200
    doc_chunks = [docs_df[i:i + chunk_size] for i in range(0, len(docs_df), chunk_size)]
    print(f"Processing {len(doc_chunks)} chunks of documents")
    
    anthropic = Anthropic()
    all_analyses = []
    
    for chunk_idx, chunk_df in enumerate(doc_chunks):
        docs_text = "\n---\n".join(chunk_df['text'].tolist())
        print(f"Processing chunk {chunk_idx + 1}/{len(doc_chunks)}")
        
        # Define the tool for structured output
        tools = [{
            "name": "create_policy_scores",
            "description": "Create a structured analysis of political parties' positions",
            "input_schema": {
                "type": "object",
                "properties": {
                    "categories": {
                        "type": "object",
                        "description": "Categories for scoring with descriptions",
                        "properties": {
                            "additional_properties": {"type": "string"}
                        }
                    },
                    "party_scores": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "party": {"type": "string"},
                                "scores": {
                                    "type": "object",
                                    "description": "Scores for each category (0-10)"
                                }
                            },
                            "required": ["party", "scores"]
                        }
                    }
                },
                "required": ["categories", "party_scores"]
            }
        }]

        prompt = """Analyze this chunk of Dutch political documents about plant-based and vegan policies. 
        Create a structured analysis showing how different political parties position themselves on these topics.
        
        Score each party from 0-10 on relevant categories like:
        - Support for plant-based initiatives
        - Climate consideration in food policy
        - Animal welfare positions
        - Economic support for plant-based transition
        - Public health focus in food policy
        
        Only include parties that are explicitly mentioned in this chunk of source documents.
        Use the create_policy_scores tool to output the analysis in a structured format."""

        response = anthropic.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=4000,
            temperature=0,
            tools=tools,
            messages=[{
                "role": "user",
                "content": f"Here are the documents to analyze:\n\n<docs>\n{docs_text}\n</docs>\n\n{prompt}"
            }]
        )
        
        # Extract the tool output from the response
        for content in response.content:
            if content.type == 'tool_use':
                all_analyses.append(content.input)
                break
    
    # Aggregate the analyses
    if not all_analyses:
        return None
        
    # Initialize the final structure
    final_analysis = {
        "categories": all_analyses[0]["categories"],  # Use categories from first analysis
        "party_scores": []
    }
    
    # Collect all unique parties
    all_parties = set()
    for analysis in all_analyses:
        for party_data in analysis["party_scores"]:
            all_parties.add(party_data["party"])
    
    # Average the scores for each party across all chunks
    for party in all_parties:
        party_scores = {}
        score_counts = {}
        
        # Collect scores from all analyses
        for analysis in all_analyses:
            for party_data in analysis["party_scores"]:
                if party_data["party"] == party:
                    for category, score in party_data["scores"].items():
                        if category not in party_scores:
                            party_scores[category] = 0
                            score_counts[category] = 0
                        party_scores[category] += score
                        score_counts[category] += 1
        
        # Calculate averages
        averaged_scores = {
            category: party_scores[category] / score_counts[category]
            for category in party_scores
        }
        
        final_analysis["party_scores"].append({
            "party": party,
            "scores": averaged_scores
        })
    
    return final_analysis

def main(): 
    # Analyze with Claude
    analysis_dict = analyze_documents_with_claude("plant-based en vegan beleid partij standpunt voor of tegen")
    print(analysis_dict)
    if analysis_dict:
        try:
            # Convert the dictionary to a JSON string
            analysis_json = json.dumps(analysis_dict)
            # Create and save the radar chart
            fig = create_radar_chart(analysis_json)
            fig.write_html("vegan_policy_radar.html")
            print("Radar chart has been created and saved as vegan_policy_radar.html")
        except Exception as e:
            print(f"Error creating radar chart: {e}")
    else:
        print("Analysis failed to produce valid output")

if __name__ == "__main__":
    main() 
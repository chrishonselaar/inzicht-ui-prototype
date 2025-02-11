import streamlit as st
import time
from openai import OpenAI
from anthropic import Anthropic
from milvus import search_documents
import matplotlib.pyplot as plt
import io
from datetime import datetime
import networkx as nx
import re
import random
import os
import json

# Add page configuration and title
st.set_page_config(page_title="InzichtNL", layout="wide")

# Add sidebar
with st.sidebar:
    # Add logo at the top of sidebar
    st.image("logo.png", width=200)  # Adjust width as needed
    
    # Add additional context info
    st.markdown("---")  # Adds a horizontal line
    st.markdown("""
    ### Over deze applicatie
    Deze AI-assistent helpt u bij het analyseren van documenten en het maken van beslissingen.
    
    ### Hoe te gebruiken
    1. Stel uw vraag in het chat venster
    2. De AI zoekt relevante documenten
    3. U ontvangt een geïnformeerd antwoord
                
Tijdslijn per maand van belangrijke stappen binnen gemeenten Groningen en Amsterdam die zijn gezet om klimaatverandering op de beleidsagenda te krijgen                
    """)

# read ANTHROPIC_API_KEY from .env
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_filename(prompt):
    """Generate a cache filename based on the prompt."""
    # Convert the prompt to a string if it's a dictionary
    if isinstance(prompt, dict):
        prompt_str = json.dumps(prompt, sort_keys=True)
    else:
        prompt_str = prompt
    return os.path.join(CACHE_DIR, f"{hash(prompt_str)}.json")

def real_llm_response(prompt):
    cache_filename = get_cache_filename(prompt)
    
    # Check if the response is already cached
    if os.path.exists(cache_filename):
        with open(cache_filename, 'r') as cache_file:
            cached_response = json.load(cache_file)
            return cached_response["response_content"]
    
    stream = client.messages.create(
        model="claude-3-5-haiku-latest",
        messages=[{
            "role": "user",
            "content": prompt["content"] if isinstance(prompt, dict) else prompt
        }],
        stream=True,
        max_tokens=8000
    )
    citation_count = 0
    response_content = ""
    for chunk in stream:
        if chunk.type == "content_block_delta":
            # Append text if available
            if hasattr(chunk.delta, "text") and chunk.delta.text:
                response_content += chunk.delta.text
            # Append citation details if available
            if hasattr(chunk.delta, "citation") and chunk.delta.citation:
                citation_count += 1
                # Parse the citation for popover content
                popover_content = parse_citation(chunk.delta.citation)
                # Ensure citation is a string and properly formatted
                citation_text = str(popover_content).replace('"', '&quot;').replace('\n', '&#10;')
                citation_tag = f"""
                <sup>
                    <a href="#" title="{citation_text}" style="text-decoration: none;">[{citation_count}]</a>
                </sup>
                """
                # Wrap the citation tag in a span to ensure proper rendering
                response_content += f"<span>{citation_tag}</span>"
    
    # Cache the response to disk
    with open(cache_filename, 'w') as cache_file:
        json.dump({"response_content": response_content}, cache_file)
    
    return response_content

def mock_llm_response(prompt):
    """Simulates LLM response generation with delay"""
    response = f"AI: Processed '{prompt}'"
    for word in response.split():
        yield word + " "
        time.sleep(0.05)

def format_sources(results):
    """Format search results into document content blocks with citations enabled"""
    documents = []
    for result in results:
        # Create a document content block for each search result
        document = {
            "type": "document",
            "source": {
                "type": "text", 
                "media_type": "text/plain",
                "data": result['text']
            },
            # Add metadata as context
            "context": "\n".join(f"{key}: {value}" for key, value in result['metadata'].items() if value),
            # Enable citations for this document
            "citations": {"enabled": True}
        }
        documents.append(document)
    return documents

def parse_citation(citation):
    # Directly access the attributes of the CitationCharLocation object
    cited_text = getattr(citation, 'cited_text', '')
    document_title = getattr(citation, 'document_title', 'Unknown Title')

    # Format the popover content
    popover_content = f"Title: {document_title}\nText: {cited_text}"
    
    return popover_content

def handle_time_events(events):
    """Processes time events from Claude's response."""
    times = [datetime.strptime(event['time'], '%Y-%m-%d %H:%M:%S') for event in events]
    values = [event['value'] for event in events]
    return times, values

def generate_timeseries_plot(times, values):
    """Generates a timeseries plot."""
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(times, values, marker='o')
    ax.set_title('Timeseries Plot of Events')
    ax.set_xlabel('Time')
    ax.set_ylabel('Event Value')
    fig.autofmt_xdate()  # Rotate date labels
    return fig

def generate_document_relations_graph(documents):
    """Generates a graph visualization of document relations."""
    G = nx.Graph()
    
    # Add nodes based on documents
    for i, doc in enumerate(documents):
        # Use the filename from metadata and sanitize it
        raw_label = doc['metadata'].get('filename', f"Document {i}")
        label = re.sub(r'\W+', ' ', raw_label)  # Sanitize to alphanumeric characters
        G.add_node(i, label=label)
    
    # Add edges based on shared council in metadata
    for i, doc1 in enumerate(documents):
        for j, doc2 in enumerate(documents):
            if i != j:
                council1 = doc1['metadata'].get('council')
                council2 = doc2['metadata'].get('council')
                if council1 and council2 and council1 == council2:
                    G.add_edge(i, j)
    
    # Add a few random edges
    num_random_edges = min(5, len(documents) * (len(documents) - 1) // 2)
    for _ in range(num_random_edges):
        a, b = random.sample(range(len(documents)), 2)
        G.add_edge(a, b)
    
    # Draw the graph with improved layout
    pos = nx.spring_layout(G, k=0.1, iterations=100)
    labels = nx.get_node_attributes(G, 'label')
    nx.draw(G, pos, with_labels=True, labels=labels, node_size=3000, node_color='lightblue', font_size=10)
    plt.title('Document Relations Graph')
    st.pyplot(plt)  # Use Streamlit's function to display the plot

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input handling
if prompt := st.chat_input("Type your message..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Search relevant documents
    search_results = search_documents(prompt, limit=10)
    
    # Debugging: Print the structure of search_results
    if search_results:
        print("Sample search result structure:", search_results[0])

    # Create message with documents and user prompt
    message = {
        "role": "user",
        "content": [
            *format_sources(search_results),
            {
                "type": "text",
                "text": prompt
            }
        ]
    }

    # Generate and display AI response
    with st.chat_message("assistant"):
        response_content = real_llm_response(message)
        st.markdown(response_content, unsafe_allow_html=True)
        
        # Generate and display a document relations graph
        generate_document_relations_graph(search_results)
    
    # Add AI response to history 
    st.session_state.messages.append({"role": "assistant", "content": response_content})

import streamlit as st
from milvus import search_documents
from llm import LLMClient
from document import format_sources
from perplexity_api import PerplexityAPI
from ui import init_sidebar, EXAMPLE_QUESTIONS
import os
import random

def click_question(question):    
    submit_question(question)

def input_question():
    prompt = st.session_state.get("chat_input")
    submit_question(prompt)

def submit_question(prompt):    

    # Append the user prompt to the session state messages after displaying
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # read ANTHROPIC_API_KEY from .env
    llm_client = LLMClient(api_key=os.getenv("ANTHROPIC_API_KEY"))
    perplexity_client = PerplexityAPI(api_key=os.getenv("PERPLEXITY_API_KEY"))
    
    infolabel = st.info("Gemeentelijke bronnen zoeken...")
    
    search_results = []

    if os.getenv("USE_DOCUMENTS") == "True":    
        search_results = search_documents(prompt, limit=int(os.getenv("NUM_VECTOR_RESULTS")))

    infolabel.empty()
    
    infolabel = st.info("Online bronnen zoeken...")

    perplexity_citations = []
    if os.getenv("USE_PERPLEXITY") == "True":
        # Add Perplexity search results
        try:
            perplexity_response, perplexity_citations = perplexity_client.search(prompt, system_prompt="Je bent een expert adviseur voor ggemeentelijke beleidsmakers. Gebruik wetenschappelijke publicaties, nieuwsbronnen en social media bronnen om een accuraat antwoord op de vraag te geven. Gebruik geen markdown in je antwoord. Werk in het Nederlands.")
            # Convert Perplexity results to match search_results format
            perplexity_results = [{
                'extended_chunk': perplexity_response,
                'metadata': {
                    'document_type': 'Reliable Perplexity.ai result',
                    'filename': 'Perplexity',
                    'citations': perplexity_citations
                }         
            }]
            
            search_results = perplexity_results + search_results
        except Exception as e:
            st.error(f"Error fetching online results: {str(e)}")
        
    infolabel.empty()

    if len(search_results) > 0:
        st.expander("Gevonden bronnen", expanded=False).write(search_results)    
    else:
        search_results = [{
                'extended_chunk': "Geen specifieke bronnen gevonden bij deze zoekopdracht, maak de vraag specifieker."    
            }]

    message = {
        "role": "user",
        "content": [

            *format_sources(search_results),
            {"type": "text", "text": prompt}
        ],
        "history": [
            {
                "role": m["role"],
                "content": m["content"]
            } for m in st.session_state.messages[-4:]  # Include last 4 messages
        ]
    }
    
    # Display AI response
    #with st.chat_message("assistant"):
    infolabel = st.info("Antwoord aan het genereren...")

    response_content, citations = llm_client.generate_response(message, system="Je bent een expert adviseur voor gemeentelijke beleidsmakers. Gebruik de gevonden RIS/BIS brondocumenten en academische/nieuws/social media bronnen om een accuraat antwoord op de vraag te geven. Gebruik geen markdown in je antwoord. Werk in het Nederlands.", perplexity_citations=perplexity_citations)

    infolabel.empty()
    #st.markdown(response_content, unsafe_allow_html=False)
    
    # Display document relations
    #fig = generate_document_relations_graph(search_results)
    #st.pyplot(fig)
    
    # Append the response to the session state messages after displaying
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_content,
        "citations": citations
    })
    
def main():
    st.set_page_config(page_title="InzichtNL", layout="wide")
    
    # Initialize sidebar
    init_sidebar()

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display example question buttons when chat is empty
    if len(st.session_state.messages) == 0:
        st.markdown("### 👋 Welkom! Stel je vraag onderin:")
        
        # Create columns for better layout
        cols = st.columns(2)
        col_idx = 0
        
        # Display a selection of random questions from different categories
        displayed_categories = random.sample(list(EXAMPLE_QUESTIONS.keys()), 10)
        
        for category in displayed_categories:
            question = random.choice(EXAMPLE_QUESTIONS[category])
            #cols[col_idx].button(f"💡 {question}", use_container_width=True)
            cols[col_idx].button(f"💡 {question}", use_container_width=True, on_click=submit_question, args=(question,))               
            
            col_idx = (col_idx + 1) % 2

    print("rerunning main, displaying all session state messages")
    # Display chat history in the correct order
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "citations" in message and len(message["citations"]) > 0:
                st.expander("Referenties", expanded=False).markdown(message["citations"])
    
    # Handle user input
    st.chat_input("Type je vraag...", on_submit=input_question, key="chat_input")
        
if __name__ == "__main__":
    os.environ['STREAMLIT_SERVER_PORT'] = os.getenv("STREAMLIT_SERVER_PORT")
    main() 
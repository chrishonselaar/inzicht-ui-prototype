from pymilvus import connections, Collection, utility, __version__
import voyageai, os, pandas as pd
import streamlit as st
from functools import lru_cache

def connect_milvus(host='localhost', port='19530'):
    """Setup Milvus connection and collection"""
    # Check if there's an existing connection and disconnect
    if connections.has_connection("default"):
        connections.disconnect("default")
    
    # Try to connect with a timeout
    connections.connect(
        alias="default",
        host=host, 
        port=port,
        timeout=10.0  # Add timeout in seconds
    )
    
    # Verify connection
    if not connections.has_connection("default"):
        raise ConnectionError("Failed to establish connection to Milvus")

    collection_name = "vector_store"
    
    # Check if collection exists
    if not utility.has_collection(collection_name):
        raise ValueError(f"Collection '{collection_name}' does not exist")
        
    # Get existing collection
    collection = Collection(name=collection_name)
    
    # Load the indices explicitly
    collection.load()
    
    return collection

@lru_cache(maxsize=128)  # You can adjust the maxsize as needed
def embed_query(query):
    vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
    vector = vo.embed([query], model="voyage-3-large", input_type="query").embeddings[0]
    return vector

def hybrid_search(collection, query_vector, text_expr=None, metadata_expr=None, timestamp_expr=None, limit=50):
    search_params = {"metric_type": "L2", "params": {"nprobe": 16}}
    
    # Build expression for hybrid filtering
    expr = None
    if text_expr:
        expr = text_expr
    if metadata_expr:
        expr = f"({expr}) && ({metadata_expr})" if expr else metadata_expr
    if timestamp_expr:
        expr = f"({expr}) && ({timestamp_expr})" if expr else timestamp_expr
    
    # results = collection.query(
    #     expr=expr,
    #     output_fields=["text", "metadata", "timestamp"],
    #     limit=limit
    # )
    results = collection.search(
        #data=[],
        data=[query_vector],
        anns_field="embeddings",
        param=search_params,
        limit=limit,

        expr=expr,
        output_fields=["text", "metadata", "timestamp"]
    )
    
    return results

def search_documents(query, limit=3):
    """Search documents using vector similarity"""
    try:
        collection = connect_milvus()
        vector = embed_query(query)
        results = hybrid_search(
            collection,
            query_vector=vector,
            limit=limit
        )
        
        # Convert the Hits object to a list of dictionaries
        formatted_results = []
        for hit in results[0]:
            formatted_results.append({
                "id": hit.id,
                "distance": hit.distance,         
                **{key: hit.entity.get(key) for key in ["text", "metadata", "timestamp"]}            
            })
        
        return pd.DataFrame(formatted_results)
    except Exception as e:
        st.error(f"Error during search: {str(e)}")
        return pd.DataFrame()

# Streamlit UI code
def main():
    st.set_page_config(layout="wide")

    st.title("Semantisch zoeken gemeentelijke archieven Groningen/Amsterdam")
    
    # Search input
    query = st.text_input("Enter your search query:", value="proefdieren voorkeursbeleid")
    limit = st.slider("Number of results", min_value=1, max_value=5000, value=20)
    

    # Search button
    if st.button("Search") and query:
        with st.spinner("Searching..."):
            results_df = search_documents(query, limit=limit)
            st.dataframe(results_df)            

if __name__ == "__main__":    
    os.environ['STREAMLIT_SERVER_PORT'] = '7000'    
    main()
            
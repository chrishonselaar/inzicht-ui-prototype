from pymilvus import connections, Collection, utility, __version__
import voyageai
import os

# Load API key from .env
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")

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

def get_complete_document(filename):
    """Retrieve the complete document using the filename"""
    collection = connect_milvus()
    results = collection.query(
        expr=f'metadata["filename"] == "{filename}"',
        output_fields=["text", "metadata"],  # Removed chunk_index since it doesn't exist
        limit=10000
    )
    
    if not results:
        return None
    
    # Sort chunks by their index and concatenate
    sorted_chunks = sorted(results, key=lambda x: x['metadata']['chunk_position']['end'])
    complete_text = ' '.join(chunk['text'] for chunk in sorted_chunks)


    # Format metadata header
    metadata = results[0]['metadata']
    metadata_text = "\n".join([
        "Document Metadata:",
        f"Council: {metadata.get('council', 'N/A')}",
        f"Document Type: {metadata.get('document_type', 'N/A')}",
        f"Year: {metadata.get('year', 'N/A')}",
        f"Month: {metadata.get('month', 'N/A')}",
        f"Topic: {metadata.get('topic', 'N/A')}",
        f"Filename: {metadata.get('filename', 'N/A')}",
        "\nDocument Content:\n"
    ])
    
    return {
        'text': metadata_text + complete_text,
        'metadata': metadata
    }

def format_search_results(results):
    """Format search results in a more readable way"""
    formatted_results = []
    
    for hit in results[0]:  # results[0] contains the hits for the first query
        filename = hit.entity.metadata.get('filename') if hit.entity.metadata else None
        #complete_doc = get_complete_document(filename) if filename else None
        extended_chunk = get_extended_chunk(filename, 
                                            hit.entity.metadata.get('year') if hit.entity.metadata else None,
                                            hit.entity.metadata.get('month') if hit.entity.metadata else None,
                                            hit.entity.metadata.get('council') if hit.entity.metadata else None,
                                            hit.entity.metadata.get('document_type') if hit.entity.metadata else None,
                                            hit.entity.metadata.get('chunk_position')['start'], 
                                            hit.entity.metadata.get('chunk_position')['end']) if filename else None

        formatted_hit = {
            'id': hit.id,
            'distance': round(hit.distance, 3),
            #'text': hit.entity.text,
            #'complete_document': complete_doc['text'] if complete_doc else None,
            'extended_chunk': extended_chunk['text'] if extended_chunk else None,
            'metadata': {
                'council': hit.entity.metadata.get('council') if hit.entity.metadata else None,

                'document_type': hit.entity.metadata.get('document_type') if hit.entity.metadata else None,
                'year': hit.entity.metadata.get('year') if hit.entity.metadata else None,
                'month': hit.entity.metadata.get('month') if hit.entity.metadata else None,
                'topic': hit.entity.metadata.get('topic') if hit.entity.metadata else None,
                'filename': filename
            }
        }
        formatted_results.append(formatted_hit)
    
    return formatted_results

def search_documents(query, limit=3):
    """Search documents using vector similarity"""
    collection = connect_milvus()
    vo = voyageai.Client(api_key=VOYAGE_API_KEY)
    vector = vo.embed([query], model="voyage-3-large", input_type="query").embeddings[0]
    
    results = hybrid_search(
        collection,
        query_vector=vector,
        limit=limit
    )
    
    return format_search_results(results)

def test_search():
    print(__version__)
    query = "proefdieren voorkeursbeleid"
    collection = connect_milvus()
    vo = voyageai.Client(api_key=VOYAGE_API_KEY)
    vector = vo.embed([query], model="voyage-3-large", input_type="query").embeddings[0]
    
    results = hybrid_search(
        collection,
        query_vector=vector,
        #text_expr='text like "Recreatie"',
        #metadata_expr='metadata["category"] == "A"',
        #metadata_expr='metadata["council"] == "amsterdam" and metadata["document_type"] == "Collegeberichten"',
        #timestamp_expr='timestamp >= 1612137600',
        limit=20
    )
    print(query)
       
    # Format and print results
    formatted_results = format_search_results(results)
    for i, result in enumerate(formatted_results, 1):
        print(f"\nResult {i}:")
        print(f"Distance: {result['distance']}")
        print(f"Text: {result['text']}")
        print("Metadata:")
        for key, value in result['metadata'].items():
            if value:  # Only print if value exists
                print(f"  {key}: {value}")
        if result['complete_document']:
            print("\nComplete Document:")
            print(result['complete_document'])

def get_extended_chunk(filename, year, month, council, document_type, chunk_start, chunk_end, context_size=1):
    """Retrieve the chunk with its preceding and following chunks, removing text overlap
    
    Args:
        filename (str): Name of the file containing the chunk
        chunk_start (int): Start position of the target chunk
        chunk_end (int): End position of the target chunk
        context_size (int): Number of chunks to retrieve before and after (default: 1)
    """
    collection = connect_milvus()
    
    # Query for chunks within the extended range
    results = collection.query(
        expr=f'metadata["filename"] == "{filename}" && metadata["year"] == {year} && metadata["month"] == {month} && metadata["council"] == "{council}" && metadata["document_type"] == "{document_type}"',
        output_fields=["text", "metadata"],
        limit=10000
    )

#    print(results)
    if not results:
        return None
    
    # Sort chunks by their position
    sorted_chunks = sorted(results, key=lambda x: x['id'])
   # print(sorted_chunks)
    # Find the index of our target chunk
    target_idx = next(
        (i for i, chunk in enumerate(sorted_chunks) 
         if chunk['metadata']['chunk_position']['start'] == chunk_start 
         and chunk['metadata']['chunk_position']['end'] == chunk_end),
        None
    )
    #print(target_idx)
    if target_idx is None:
        return None
    
    # Calculate the range of chunks to include
    start_idx = max(0, target_idx - context_size)
    end_idx = min(len(sorted_chunks), target_idx + context_size + 1)
    
    # Get the relevant chunks
    context_chunks = sorted_chunks[start_idx:end_idx]
    
    # Format metadata header
    metadata = context_chunks[0]['metadata']
    metadata_text = "\n".join([
        "Document Metadata:",
        f"Council: {metadata.get('council', 'N/A')}",
        f"Document Type: {metadata.get('document_type', 'N/A')}",
        f"Year: {metadata.get('year', 'N/A')}",
        f"Month: {metadata.get('month', 'N/A')}",
        f"Topic: {metadata.get('topic', 'N/A')}",
        f"Filename: {metadata.get('filename', 'N/A')}",
        "\nDocument Content:\n"
    ])
    
    # Join the chunks with visual separators, removing overlap
    chunks_text = []
    for i, chunk in enumerate(context_chunks):
        if i == target_idx - start_idx:
            chunks_text.append(" ")
        
        current_text = chunk['text']
        if i > 0:
            # Find the overlap with the previous chunk
            prev_text = context_chunks[i-1]['text']
            # Find the longest common suffix/prefix
            min_overlap_len = min(len(prev_text), len(current_text))
            overlap_size = 0
            for j in range(min_overlap_len):
                if prev_text.endswith(current_text[:j+1]):
                    overlap_size = j + 1
            
            # Remove the overlapping part from the beginning of current chunk
            if overlap_size > 0:
                current_text = current_text[overlap_size:]
        
        chunks_text.append(current_text)
        
        if i == target_idx - start_idx:
            chunks_text.append(" ")
    
    return {
        'text': metadata_text + "\n".join(chunks_text),
        'metadata': metadata
    }

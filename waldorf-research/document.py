def format_sources(results):
    """Format search results into document content blocks with citations enabled"""
    documents = []
    for result in results:
        document = {
            "type": "document",
            "source": {
                "type": "text", 
                "media_type": "text/plain",
                #"data": result['text']
                #"data": result['complete_document']
                "data": result['extended_chunk']
            },
            "title": result['metadata']['filename'] if 'metadata' in result else 'Geen titel gevonden',
            #"context": "\n".join(f"{key}: {value}" for key, value in result['metadata'].items() if value),
            "context": result['metadata']['document_type'] if 'metadata' in result else 'Geen document type gevonden',
            "citations": {"enabled": True}



        }
        documents.append(document)
    return documents
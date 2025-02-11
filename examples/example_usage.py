from milvus import search_documents, connect_milvus, hybrid_search
import voyageai

def main():
    # Basic search example
    print("Basic Search Example:")
    results = search_documents(
        #query="What are the policies regarding animal testing?",
        #query="Raadsverslag gemeente Groningen waarin mevrouw Jacobs van VVD mevrouw Bloemhoff aanhaalt over de gepolariseerde samenleving",
        query="stopzetten van gemeentelijke subsidies ouderbijdrage geen belemmering",
        limit=10

    )
    
    # Print results
    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"Distance: {result['distance']}")
        print(f"Text snippet: {result['text']}...")
        print("Metadata:", result['metadata'])

if __name__ == "__main__":
    main() 
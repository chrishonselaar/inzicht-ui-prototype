from pymilvus import MilvusClient
import numpy as np
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
import voyageai
import os

# 1. Connect to Milvus
client = MilvusClient(
    uri="http://localhost:19530",
    token="root:Milvus"
)

query = "dierenrechten"

vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

vector_query = vo.embed([query], model="voyage-3-large", input_type="query").embeddings[0]


# Define Dutch political parties with their variations
dutch_parties = {
    "VVD": ["VVD", "Volkspartij voor Vrijheid en Democratie"],
    "D66": ["D66", "Democraten 66", "D'66"],
    "CDA": ["CDA", "Christen-Democratisch Appèl", "Christen Democratisch Appel"],
    "PvdA": ["PvdA", "Partij van de Arbeid"],
    "SP": ["SP", "Socialistische Partij"],
    "GroenLinks": ["GroenLinks", "Groen Links", "GL"],
    "PVV": ["PVV", "Partij voor de Vrijheid"],
    "ChristenUnie": ["ChristenUnie", "CU"],
    "PvdD": ["PvdD", "Partij voor de Dieren", "partij voor de dieren"],
    "SGP": ["SGP", "Staatkundig Gereformeerde Partij"],
    "DENK": ["DENK"],
    "FVD": ["FVD", "Forum voor Democratie"],
    "BBB": ["BBB", "BoerBurgerBeweging", "Boer Burger Beweging"],
    "Volt": ["Volt", "Volt Nederland"],
    "NSC": ["NSC", "Nieuw Sociaal Contract"],
    "GL-PvdA": ["GL-PvdA", "GroenLinks-PvdA", "Groenlinks-PvdA", "GL/PvdA"]
}

# 2. Filtered search for animal rights documents
results = client.search(
    collection_name="vector_store",
    data=[vector_query],  # Empty for full collection scan
    #filter='topics == "animal_rights"',  # Assuming metadata field 'topics'
    output_fields=["text", "embeddings"],  # Retrieve party affiliation + vectors
    limit=5000  # Max allowed per search
)

# 3. Extract vectors and determine parties from text
vectors = []
parties = []

for hit in results[0]:
    # Initialize as None in case no party is found
    found_party = None
    text = hit['entity']['text'].upper()  # Convert to uppercase for matching
    
    # Find first matching party in text
    for party_key, variations in dutch_parties.items():
        if any(variation.upper() in text for variation in variations):
            found_party = party_key
            vectors.append(hit['entity']['embeddings'])
            parties.append(found_party)
            break

# Check if we have any results
if not vectors:
    print("No search results found. Please check your search query and filters.")
    exit()

print(f"Found {len(vectors)} results with party mentions")

# Convert vectors to numpy array of float64
vectors = np.array(vectors, dtype=np.float64)

# 4. Dimensionality reduction
tsne = TSNE(n_components=2, perplexity=min(30, len(vectors) - 1), random_state=42)
embeddings_2d = tsne.fit_transform(vectors)

# 5. Visualization
plt.figure(figsize=(14, 10))
for party in set(parties):
    mask = np.array(parties) == party
    plt.scatter(embeddings_2d[mask, 0], 
                embeddings_2d[mask, 1], 
                s=10,  # Reduced marker size (default is 100)              
                label=party,
                alpha=0.5)


plt.title("Party Alignment on Animal Rights Policies")
plt.xlabel("t-SNE Dimension 1")
plt.ylabel("t-SNE Dimension 2")
plt.legend(title="Political Parties")
plt.grid(alpha=0.3)
plt.show()

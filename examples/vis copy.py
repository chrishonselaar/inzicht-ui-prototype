from pymilvus import MilvusClient, __version__
import numpy as np
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
import voyageai
import os

# 1. Connect to Milvus and check collection info
client = MilvusClient(
    uri="http://localhost:19530",
    token="root:Milvus"
)

print(__version__)

# Print collection information
collection_info = client.describe_collection("vector_store")
print("Collection info:", collection_info)

query = "partij standpunt dieren PvdD VVD SP"
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

# 2. Query all documents using iterator
target_hits = 20000  # Adjust this number based on your needs

# Convert query vector to correct format
query_vector = [vector_query]  # Wrap in list as required by search_iterator

all_results = []
batch_size = 10000  # Adjust based on your memory constraints

query_iterator = client.query_iterator(
    collection_name="vector_store",
    output_fields=["text", "embeddings"],
    batch_size=batch_size
)

while True:
    try:
        batch = query_iterator.next()
        if not batch:
            break
        all_results.extend(batch)
        print(f"Fetched batch, current total: {len(all_results)}")
        if len(all_results) >= target_hits:
            break
    except StopIteration:
        break

print(f"Total results fetched: {len(all_results)}")

# 3. Extract vectors and determine parties from text
vectors = []
parties = []

for hit in all_results:  # Using accumulated results
    # Initialize as None in case no party is found
    found_party = None
    text = hit['text'].upper()
    
    # Find first matching party in text
    for party_key, variations in dutch_parties.items():
        if any(variation.upper() in text for variation in variations):
            found_party = party_key
            vectors.append(hit['embeddings'])
            parties.append(found_party)
            break

# Check if we have any results
if not vectors:
    print("No search results found with party mentions.")
    exit()

print(f"Found {len(vectors)} results with party mentions")

# Convert vectors to numpy array of float64
vectors = np.array(vectors, dtype=np.float64)

# 4. Define semantic directions and project
# Remove the semantic direction functions and calculations since we'll use t-SNE for both dimensions

# Perform t-SNE for both dimensions
tsne = TSNE(n_components=2, random_state=42)
coords = tsne.fit_transform(vectors)
x_coords = coords[:, 0]
y_coords = coords[:, 1]

# 5. Visualization
plt.figure(figsize=(14, 10))
for party in set(parties):
    mask = np.array(parties) == party
    plt.scatter(x_coords[mask], 
                y_coords[mask], 
                s=20,
                label=party,
                alpha=0.75)

plt.title("Party Alignment")
plt.xlabel("t-SNE dimension 1")
plt.ylabel("t-SNE dimension 2")
plt.legend(title="Political Parties", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

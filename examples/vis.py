import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler

# Simulated Milvus database extraction (replace with actual Milvus connection)
def simulate_milvus_vectors(n_vectors=3000, vector_dim=384):
    np.random.seed(42)
    vectors = np.random.randn(n_vectors, vector_dim)
    
    # Add some artificial clustering to simulate political party differences
    party_centroids = np.random.randn(5, vector_dim) * 2
    for i in range(5):
        mask = np.random.choice(n_vectors, n_vectors // 5, replace=False)
        vectors[mask] += party_centroids[i]
    
    return vectors

# Extract vectors (simulated in this example)
vectors = simulate_milvus_vectors()

# Normalize the vectors
scaler = StandardScaler()
vectors_scaled = scaler.fit_transform(vectors)

# Reduce dimensionality to 2D using t-SNE
tsne = TSNE(n_components=2, random_state=42, perplexity=30)
vectors_2d = tsne.fit_transform(vectors_scaled)

# Visualize the 2D point cloud
plt.figure(figsize=(12, 8))
plt.scatter(vectors_2d[:, 0], vectors_2d[:, 1], alpha=0.5, 
            c=np.random.rand(vectors_2d.shape[0]), cmap='viridis')
plt.title('2D Visualization of Municipality Council Policy Document Embeddings')
plt.xlabel('t-SNE Dimension 1')
plt.ylabel('t-SNE Dimension 2')
plt.colorbar(label='Cluster Gradient')
plt.tight_layout()
plt.savefig('milvus_embeddings_visualization.png')
plt.close()

print("Visualization saved as milvus_embeddings_visualization.png")
print(f"Original vector shape: {vectors.shape}")
print(f"Reduced 2D vector shape: {vectors_2d.shape}")

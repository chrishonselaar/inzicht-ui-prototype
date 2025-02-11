import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import json
from queries import search_documents
import anthropic
import numpy as np
from functools import lru_cache
import networkx as nx

@lru_cache(maxsize=10)
def get_topic_relationship_data(main_topic):
    # Search for relevant documents
    results_df = search_documents(main_topic, limit=200)
    
    # Combine all text for Claude
    combined_text = "\n\n".join(results_df['text'].astype(str).tolist())
    
    # Initialize Claude client
    client = anthropic.Anthropic()
    
    # Define the topic relationship extraction tool
    topic_tool = {
        "name": "extract_topic_relationships",
        "description": "Extract related topics and their relationships to the main topic",
        "input_schema": {
            "type": "object",
            "properties": {
                "main_topic": {
                    "type": "string",
                    "description": "The central topic being analyzed"
                },
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "related_topic": {
                                "type": "string",
                                "description": "Name of the related topic"
                            },
                            "relationship_type": {
                                "type": "string",
                                "description": "Type of relationship (e.g., 'influences', 'depends on', 'part of')"
                            },
                            "strength": {
                                "type": "number",
                                "description": "Strength of relationship (0.0 to 1.0)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of how topics are related"
                            },
                            "secondary_topics": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "object",
                                    "properties": {
                                        "relationship_type": {
                                            "type": "string",
                                            "description": "Type of relationship with the secondary topic"
                                        },
                                        "strength": {
                                            "type": "number",
                                            "description": "Strength of relationship with the secondary topic (0.0 to 1.0)"
                                        }
                                    },
                                    "required": ["relationship_type", "strength"]
                                },
                                "description": "Map of secondary topics and their relationships to this related topic"
                            },
                            "secondary_relationships": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "object",
                                    "properties": {
                                        "relationship_type": {
                                            "type": "string",
                                            "description": "Type of relationship between topics"
                                        },
                                        "strength": {
                                            "type": "number",
                                            "description": "Strength of relationship between topics (0.0 to 1.0)"
                                        }
                                    },
                                    "required": ["relationship_type", "strength"]
                                },
                                "description": "Map of relationships between this topic and other topics at the same level"
                            }
                        },
                        "required": ["related_topic", "relationship_type", "strength", "description"]
                    }
                }
            },
            "required": ["main_topic", "relationships"]
        }
    }

    # Update the prompt to analyze relationships between all topics
    message = client.messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=8000,
        temperature=0,
        tools=[topic_tool],
        messages=[
            {
                "role": "user",
                "content": f"""<sources>
{combined_text}
</sources>

Analyze these sources and identify:
1. Topics and subtopics directly related to '{main_topic}'
2. Secondary topics that are connected to the related topics (up to 2 levels deep from '{main_topic}')
3. Relationships between:
   - '{main_topic}' and directly related topics
   - Between directly related topics themselves
   - Between directly related topics and secondary topics

For each relationship, determine the type and strength. Use Dutch for all output.
"""
            }
        ]
    )

    # Extract the relationship data
    for content in message.content:
        if content.type == 'tool_use':
            return content.input

    return {"main_topic": main_topic, "relationships": []}

def create_topic_map_visualization(topic_data):
    # Create graph
    G = nx.Graph()
    
    # Add main topic node
    main_topic = topic_data['main_topic']
    G.add_node(main_topic, node_type='main')
    
    # Add related topic nodes and edges
    for rel in topic_data['relationships']:
        related_topic = rel['related_topic']
        G.add_node(related_topic, node_type='related')
        G.add_edge(main_topic, related_topic, 
                  weight=rel['strength'],
                  relationship=rel['relationship_type'])
        
        # Add secondary topics if they exist
        if 'secondary_topics' in rel:
            for sec_topic, sec_rel in rel['secondary_topics'].items():
                G.add_node(sec_topic, node_type='secondary')
                G.add_edge(related_topic, sec_topic,
                          weight=sec_rel['strength'],
                          relationship=sec_rel['relationship_type'])
    
    # Add edges between all topics if they exist in the relationships
    for rel1 in topic_data['relationships']:
        topic1 = rel1['related_topic']
        # Look for relationships between topics
        if 'secondary_relationships' in rel1:
            for topic2, sec_rel in rel1['secondary_relationships'].items():
                if G.has_node(topic2):  # Only add edge if both nodes exist
                    G.add_edge(topic1, topic2,
                             weight=sec_rel['strength'],
                             relationship=sec_rel['relationship_type'])
    
    # Create the visualization
    fig, ax = plt.subplots(figsize=(15, 15))
    
    # Try Kamada-Kawai layout instead of spring layout
    # This tends to produce fewer edge crossings
    pos = nx.kamada_kawai_layout(
        G,
        weight='weight',  # Use relationship strength
        scale=2.0,       # Scale up the layout
    )
    
    # If you prefer spring layout, use these enhanced parameters:
    # pos = nx.spring_layout(
    #     G,
    #     k=5,           # Increased repulsion
    #     iterations=100, # More iterations for better convergence
    #     seed=42,
    #     weight='weight',
    #     scale=2.0
    # )
    
    # Draw edges first
    edge_weights = [G[u][v]['weight'] * 3 for u, v in G.edges()]
    nx.draw_networkx_edges(G, pos, width=edge_weights, alpha=0.6, edge_color='#34495e')
    
    # Replace the problematic edge label positioning code with this:
    edge_labels = nx.get_edge_attributes(G, 'relationship')
    edge_label_pos = {}
    for edge in G.edges():
        node1, node2 = edge
        p1 = pos[node1]
        p2 = pos[node2]
        # Calculate midpoint with offset
        edge_label_pos[edge] = (
            (p1[0] + p2[0]) / 2 + 0.03,
            (p1[1] + p2[1]) / 2 + 0.03
        )
    
    # Draw edge labels with background
    for edge, label in edge_labels.items():
        x, y = edge_label_pos[edge]
        plt.text(x, y, label,
                fontsize=8,
                bbox=dict(facecolor='white',
                         edgecolor='none',
                         alpha=0.7,
                         pad=2.0),
                horizontalalignment='center',
                verticalalignment='center')
    
    # Draw nodes
    main_nodes = [n for n, attr in G.nodes(data=True) if attr.get('node_type') == 'main']
    related_nodes = [n for n, attr in G.nodes(data=True) if attr.get('node_type') == 'related']
    secondary_nodes = [n for n, attr in G.nodes(data=True) if attr.get('node_type') == 'secondary']
    
    nx.draw_networkx_nodes(G, pos, nodelist=main_nodes, 
                          node_color='#4a90e2',
                          node_size=3000, 
                          alpha=0.9)
    nx.draw_networkx_nodes(G, pos, nodelist=related_nodes,
                          node_color='#2ecc71',
                          node_size=2500, 
                          alpha=0.8)
    nx.draw_networkx_nodes(G, pos, nodelist=secondary_nodes,
                          node_color='#f1c40f',
                          node_size=2000, 
                          alpha=0.7)
    
    # Add node labels with background
    labels_pos = {node: (coord[0], coord[1] + 0.03) for node, coord in pos.items()}
    for node, (x, y) in labels_pos.items():
        plt.text(x, y, node,
                fontsize=10,
                fontweight='bold',
                horizontalalignment='center',
                bbox=dict(facecolor='white', 
                         edgecolor='none',
                         alpha=0.7,
                         pad=2.0))
    
    plt.title(f'Topic Relationship Map: {main_topic}', pad=20, size=16)
    plt.axis('off')
    ax.margins(0.2)  # Increased margins

    return fig

def main():
    # Get topic relationship data
    topic_data = get_topic_relationship_data("Veehouderij en veeteeltbeleid")
    print("Topic relationships:")
    print(json.dumps(topic_data, indent=2))
    
    # Create visualization
    fig = create_topic_map_visualization(topic_data)
    
    # Save the visualization
    plt.savefig('topic_relationship_map.png', bbox_inches='tight', dpi=300)
    
    # Save the data as JSON
    with open('topic_relationships.json', 'w') as f:
        json.dump(topic_data, f, indent=2)

if __name__ == "__main__":
    main()

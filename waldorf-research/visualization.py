import matplotlib.pyplot as plt
import networkx as nx
import random
import re
from datetime import datetime

def generate_document_relations_graph(documents):
    """Generates a graph visualization of document relations."""
    G = nx.Graph()
    
    # Add nodes
    for i, doc in enumerate(documents):
        raw_label = doc['metadata'].get('filename', f"Document {i}")
        label = re.sub(r'\W+', ' ', raw_label)
        G.add_node(i, label=label)
    
    # Add edges based on shared council
    for i, doc1 in enumerate(documents):
        for j, doc2 in enumerate(documents):
            if i != j:
                council1 = doc1['metadata'].get('council')
                council2 = doc2['metadata'].get('council')
                if council1 and council2 and council1 == council2:
                    G.add_edge(i, j)
    
    # # Add random edges
    # num_random_edges = min(5, len(documents) * (len(documents) - 1) // 2)
    # for _ in range(num_random_edges):
    #     a, b = random.sample(range(len(documents)), 2)
    #     G.add_edge(a, b)
    
    # Draw graph
    pos = nx.spring_layout(G, k=0.1, iterations=100)
    labels = nx.get_node_attributes(G, 'label')
    plt.figure(figsize=(10, 6))
    nx.draw(G, pos, with_labels=True, labels=labels, 
            node_size=3000, node_color='lightblue', font_size=10)
    plt.title('Document Relations Graph')
    return plt.gcf()

def handle_time_events(events):
    """Process time events for visualization."""
    times = [datetime.strptime(event['time'], '%Y-%m-%d %H:%M:%S') for event in events]
    values = [event['value'] for event in events]
    return times, values

def generate_timeseries_plot(times, values):
    """Generate a timeseries plot."""
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(times, values, marker='o')
    ax.set_title('Timeseries Plot of Events')
    ax.set_xlabel('Time')
    ax.set_ylabel('Event Value')
    fig.autofmt_xdate()
    return fig 
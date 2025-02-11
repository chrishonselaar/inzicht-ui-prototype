import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import json
from queries import search_documents
import anthropic
import numpy as np
from functools import lru_cache

@lru_cache(maxsize=10)
def get_policy_timeline_data(phrase):
    # Search for relevant documents
    results_df = search_documents(phrase, limit=200)

    print(results_df)
    # Combine all text for Claude
    combined_text = "\n\n".join(results_df['text'].astype(str).tolist())
    
    # Initialize Claude client
    client = anthropic.Anthropic()
    
    # Define the timeline extraction tool
    timeline_tool = {
        "name": "extract_timeline_events",
        "description": "Extract key events into a structured timeline",
        "input_schema": {
            "type": "object",
            "properties": {
                "events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "Date of the event (YYYY-MM-DD format, use YYYY-01-01 if only year is known)"
                            },
                            "title": {
                                "type": "string",
                                "description": "Short title of the event"
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description of the event"
                            },
                            "category": {
                                "type": "string",                               
                                "description": "Category of the event"
                            }
                        },
                        "required": ["date", "title", "description", "category"]
                    }
                }
            },
            "required": ["events"]
        }
    }

    # Ask Claude to analyze the documents and extract timeline data
    message = client.messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=8000,
        temperature=0,
        tools=[timeline_tool],
        messages=[
            {
                "role": "user",
                "content": f"""<sources>
{combined_text}
</sources>

Analyze these sources and create a structured timeline of key events. Use Dutch.
"""
            }
        ]

    )
    print(message)
    # Extract the timeline data from Claude's response
    for content in message.content:
        if content.type == 'tool_use':
            return content.input['events']
    
    return []

def create_timeline_visualization(events):
    # Convert events to DataFrame
    df = pd.DataFrame(events)
    
    # Handle dates - convert to datetime while handling very old dates
    df['original_date'] = df['date']
    df['date'] = pd.to_datetime(df['date'].apply(lambda x: '1900-01-01' if int(x[:4]) < 1900 else x))
    
    # Sort by date
    df = df.sort_values('date')
    
    # Create the visualization
    fig, ax = plt.subplots(figsize=(12, max(10, len(df) * 0.4)))  # Dynamic height based on number of events
    
    # Create vertical timeline
    categories = df['category'].unique()
    colors = plt.cm.Set3(np.linspace(0, 1, len(categories)))
    category_colors = dict(zip(categories, colors))
    
    # Calculate y-positions with even spacing
    y_positions = np.arange(len(df))
    
    # Draw vertical timeline line
    ax.plot([0, 0], [y_positions[0] - 0.5, y_positions[-1] + 0.5], 
            color='gray', linestyle='-', linewidth=2, zorder=1)
    
    # Plot events
    for idx, (_, row) in enumerate(df.iterrows()):
        # Plot point on timeline
        ax.scatter(0, y_positions[idx], 
                  c=[category_colors[row['category']]], 
                  s=100, zorder=2)
        
        # Use original date string for display if it's before 1900
        year = int(row['original_date'][:4])
        date_str = str(year) if year < 1900 else row['date'].strftime('%Y-%m-%d')
        
        # Add date on the left
        ax.text(-0.1, y_positions[idx], date_str,
                ha='right', va='center', fontsize=10)
        
        # Add title and description on the right
        title_text = f"{row['title']}\n"
        desc_text = f"{row['description']}"
        
        ax.text(0.1, y_positions[idx], title_text,
                ha='left', va='center', fontsize=11, 
                fontweight='bold', color=category_colors[row['category']])
        
        ax.text(0.1, y_positions[idx]-0.2, desc_text,
                ha='left', va='top', fontsize=9,
                wrap=True)
    
    # Customize the plot
    ax.set_ylim(y_positions[0] - 1, y_positions[-1] + 1)
    ax.set_xlim(-2, 8)  # Adjust these values to control text spacing
    
    # Remove axes
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    
    # Add legend
    legend_elements = [plt.Line2D([0], [0], marker='o', color='w',
                                 markerfacecolor=color, label=cat, markersize=10)
                      for cat, color in category_colors.items()]
    ax.legend(handles=legend_elements, loc='center left', 
             bbox_to_anchor=(1.05, 0.5))
    
    # Add title
    plt.title('Timeline of Cattle and Animal Husbandry Policy Developments', 
             pad=20, fontsize=14, fontweight='bold')
    
    # Adjust layout
    plt.tight_layout()
    
    return fig

def main():
    # Get timeline data
    events = get_policy_timeline_data("Belangrijke gebeurtenissen in de ontwikkeling van veehouderij- en veeteeltbeleid met datum, in de afgelopen 5 jaar")
    print("Events:")
    print(events)
    # Create visualization
    fig = create_timeline_visualization(events)
    
    # Save the visualization
    plt.savefig('cattle_policy_timeline.png', bbox_inches='tight', dpi=300)
    
    # Also save the data as JSON for reference
    with open('cattle_policy_timeline.json', 'w') as f:
        json.dump(events, f, indent=2)

if __name__ == "__main__":
    main()

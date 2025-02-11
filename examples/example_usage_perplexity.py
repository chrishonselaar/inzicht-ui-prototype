from perplexity_api import PerplexityAPI
import os
# Initialize the client
api = PerplexityAPI(api_key=os.getenv("PERPLEXITY_API_KEY"))  # or set PERPLEXITY_API_KEY env variable

# Make a search request
response, citations = api.search(
    prompt="Raadsverslag gemeente Amsterdam: Mevrouw SCHIPPER verwijst naar de motie van CDA en VVD voor een evaluatie van de effecten van het stopzetten van gemeentelijke subsidies als zij hun ouderbijdrage hoger houden dan 225 euro",
    #system_prompt="Provide a concise summary with recent developments.",
    temperature=0.2
)

# Print the results
print("Response:", response) 
print("\nCitations:")
for citation in citations:
    print(citation) 
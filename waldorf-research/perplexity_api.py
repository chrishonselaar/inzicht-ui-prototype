import os
from typing import Dict, List, Optional, Tuple
from openai import OpenAI

class PerplexityAPI:
    """Client for making requests to the Perplexity API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Perplexity API client.
        
        Args:
            api_key: Perplexity API key. If not provided, will look for PERPLEXITY_API_KEY env variable.
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided or set as PERPLEXITY_API_KEY environment variable")
            
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.perplexity.ai"
        )

    def search(self, 
               prompt: str,
               system_prompt: str = "Be precise and concise.",
               model: str = "sonar-pro",
               temperature: float = 0.2,
               max_tokens: Optional[int] = None) -> Tuple[str, List[Dict]]:
        """Make a search request to the Perplexity API.
        
        Args:
            prompt: The user's question or prompt
            system_prompt: Instructions for the model's behavior
            model: The model to use for the request
            temperature: Controls randomness in the response (0.0 to 2.0)
            max_tokens: Maximum tokens in the response (optional)
            
        Returns:
            Tuple containing:
            - Response text from the model
            - List of citations (if available)
        """
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]

        # Build request parameters
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens

        # Make the API request
        try:
            response = self.client.chat.completions.create(**params)
          
            # Extract the response text
            response_text = response.choices[0].message.content

            # Extract citations if they exist
            citations = []
            if hasattr(response, 'citations'):
                citations = response.citations
                
            return response_text, citations

        except Exception as e:
            raise Exception(f"Error making request to Perplexity API: {str(e)}") 
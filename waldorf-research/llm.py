from anthropic import Anthropic
import os

class LLMClient:
    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)
    

    def generate_response(self, prompt, system=None, perplexity_citations=[]):
        """Generate response from LLM with caching.
        
        Args:
            prompt: Either a string or dict containing the prompt content
            cache: Cache object for storing/retrieving responses
            system: Optional system prompt to set Claude's role
        """
        # Prepare API call parameters
        messages = []
        
        # Add previous messages if they exist in the prompt dict
        if isinstance(prompt, dict) and "history" in prompt:
            messages.extend(prompt["history"])
        
        # Add current message
        messages.append({
            "role": "user",
            "content": prompt["content"] if isinstance(prompt, dict) else prompt
        })
        
        params = {
            "model": os.getenv("LLM_RESPONSE_MODEL"),
            "messages": messages,
            "stream": True,
            "max_tokens": 8000
        }

        
        # Add system prompt if provided
        if system:
            params["system"] = system
            
        # Generate new response
        stream = self.client.messages.create(**params)
        
        citation_count = 0
        response_content = ""
        citations_content = ""
        citations = []
        

        for chunk in stream:
            if chunk.type == "content_block_delta":
                if hasattr(chunk.delta, "text") and chunk.delta.text:
                    response_content += chunk.delta.text
                if hasattr(chunk.delta, "citation") and chunk.delta.citation:
                    citation_count += 1
                    citation_tag = f'[{citation_count}] '
                    response_content += citation_tag
                    # Clean up cited text and title by removing newlines, extra spaces and HTML tags
                    clean_text = ' '.join(chunk.delta.citation.cited_text.replace('\n', ' ').split())
                    clean_title = ' '.join(chunk.delta.citation.document_title.replace('\n', ' ').split())
                    citations.append(f"[{citation_count}] {clean_text} - {clean_title}")
                    #citations.append(f"[{citation_count}] {clean_title}")
        
        # Add citations below the response if there are any
        if citations:
            citations_content += "\n\n".join(citations)
        
        if len(perplexity_citations) > 0:
            # add perplexity citations
            citations_content += "\n\nOnline referenties:\n\n" + "\n\n".join(perplexity_citations)



        # Cache the response
        #cache.cache_response(prompt, response_content)
        

        return response_content, citations_content
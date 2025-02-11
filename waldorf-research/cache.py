import os
import json

class Cache:
    def __init__(self, cache_dir="cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_cache_filename(self, prompt):
        """Generate a cache filename based on the prompt."""
        if isinstance(prompt, dict):
            prompt_str = json.dumps(prompt, sort_keys=True)
        else:
            prompt_str = prompt
        return os.path.join(self.cache_dir, f"{hash(prompt_str)}.json")
    
    def get_cached_response(self, prompt):
        """Get cached response if it exists."""
        cache_filename = self.get_cache_filename(prompt)
        if os.path.exists(cache_filename):
            with open(cache_filename, 'r') as cache_file:
                cached_response = json.load(cache_file)
                return cached_response["response_content"]
        return None
    
    def cache_response(self, prompt, response_content):
        """Cache a response to disk."""
        cache_filename = self.get_cache_filename(prompt)
        with open(cache_filename, 'w') as cache_file:
            json.dump({"response_content": response_content}, cache_file) 
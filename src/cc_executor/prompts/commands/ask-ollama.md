# Ask Ollama Command

Ask a local Ollama model this question, automatically selecting the best available model.

## Parameters:
- `query`: (string) The full text of the question to ask the Ollama model
- `output_path`: (string) Optional file path where the response should be saved

## Important Implementation Notes:
When implementing this template, you should:
1. **Customize the system prompt** based on the user's actual request to get better results from Ollama
2. **Select the appropriate model** - the template includes basic automatic selection, but you should:
  - **Check what models are actually available** before making selection decisions
  - **Adapt the selection logic** in the `select_model` function based on available models
  - **Override when needed**: After automatic selection, you can still override with `selected_model = "specific-model"`
  - **Consider the task**: Code tasks → look for models with 'code' in name, Math → specialized math models, General → balanced models
  - **Don't assume specific models exist** - the template's examples may not match your available models
3. **Replace the basic keyword matching** with more sophisticated logic based on what the user is asking

For example, if the user asks "debug this complex Python function":
- First check what models you have available
- If you see a code-specialized model (look for 'code' in the name), consider using it
- Create an appropriate system prompt for debugging

If the user asks "explain quantum computing simply":
- Consider what models are available and their sizes
- Smaller models might be fine for simple explanations
- Focus on crafting a good system prompt for clear explanations

If the user specifically requests a model:
- Check if that model (or similar) exists in available_models
- Honor their request if possible
- If not available, explain what you're using instead

Remember: Don't assume specific models exist. Always work with what's actually available.

## Expected Output:
- Choose appropriate model based on query complexity (simple questions use smaller/faster models)
- Check available models first and report which one was selected
- Provide helpful responses using local model (no internet required)
- Responses are private and processed locally
- If specific model requested, use that if available

## Code Example:
```python
from dotenv import load_dotenv
load_dotenv('/home/graham/workspace/experiments/llm_call/.env')
import os
import subprocess
from litellm import completion

# Initialize caching for better performance
try:
    from llm_call.core.utils.initialize_litellm_cache import initialize_litellm_cache
    initialize_litellm_cache()
except ImportError:
    # If running outside the llm_call package, caching is optional
    pass

# Step 1: Get available models from Docker container
def get_available_models():
  try:
    container_name = os.getenv('OLLAMA_DOCKER_CONTAINER', 'llm-call-ollama')
    result = subprocess.run(['docker', 'exec', container_name, 'ollama', 'list'], 
                           capture_output=True, text=True)
    if result.returncode == 0:
      lines = result.stdout.strip().split('\n')[1:] # Skip header
      return [line.split()[0] for line in lines if line.strip()]
    return []
  except:
    return []

# Step 2: Select best model for query
def select_model(query, available_models):
  # Default fallback model
  default_model_name = os.getenv('SLASHCMD_ASK_OLLAMA_MODEL', 'ollama/phi3:mini')
  default_model = default_model_name.replace('ollama/', '') if default_model_name.startswith('ollama/') else default_model_name

  if not available_models:
    return default_model

  query_lower = query.lower()
   
  # Dynamically check if the user's query mentions an available model family
  for model in available_models:
    # Extract the base name (e.g., 'llama3:8b-instruct' -> 'llama3')
    base_name = model.split(':')[0]
    if base_name in query_lower:
      # The user's query requests a model family that is installed
      print(f"--- Detected manual model request for '{base_name}' ---")
      return model # Return the full model name
   
  # --- Start of improved auto-selection logic ---
  # Define model preferences by keywords
  code_keywords = ['code', 'python', 'script', 'debug', 'refactor', 'function', 'class']
  complex_keywords = ['analyze', 'complex', 'detailed', 'algorithm', 'review']

  # Preferred models can be found in the available list
  code_model_prefs = ['codellama', 'deepseek-coder', 'starcoder']
  large_model_prefs = ['llama3:70b', 'qwen2:72b', 'mistral-large']
  fast_model_prefs = ['phi3', 'llama3:8b', 'gemma:7b']

  # Function to find the best match from a list of preferences
  def find_best_preference(prefs, models):
    for pref in prefs:
      for model in models:
        if pref in model:
          print(f"--- Auto-selecting '{model}' based on preference '{pref}' ---")
          return model
    return None

  # 1. Check for coding tasks
  if any(keyword in query_lower for keyword in code_keywords):
    model = find_best_preference(code_model_prefs, available_models)
    if model: return model

  # 2. Check for complex reasoning tasks
  if any(keyword in query_lower for keyword in complex_keywords):
    model = find_best_preference(large_model_prefs, available_models)
    if model: return model
    
  # 3. Fallback to a small, fast model for general queries
  model = find_best_preference(fast_model_prefs, available_models)
  if model: return model

  # 4. Final fallback to the first available model if no prefs match
  if available_models:
    print(f"--- No preference matched, falling back to first available: {available_models[0]} ---")
    return available_models[0]
  
  # Final fallback to the default model if no other logic matches
  return default_model

# Parameters - REPLACE WITH ACTUAL VALUES
query = """REPLACE_WITH_QUERY_TEXT"""  # Required - Replace with actual query
output_path = None  # Optional - Set to a file path if you want to save the response

# Step 3: Execute query
available_models = get_available_models()

# Special case: if user wants to list models, just show them
if any(keyword in query.lower() for keyword in ['list models', 'available models', 'show models']):
  print("Available Ollama models:")
  for model in available_models:
    print(f"- {model}")
else:
  selected_model = select_model(query, available_models)
   
  # AGENT: You can override the automatic model selection here if needed
  # Example: selected_model = "codellama:13b-instruct-q8_0" for complex code tasks
   
  print(f"--- Using model: {selected_model} ---")
   
  try:
    api_base = os.getenv('OLLAMA_API_BASE_URL', 'http://localhost:11434')
     
    # Build messages with optional system prompt
    messages = []
     
    # Add system prompt if needed (can be customized based on model/task)
    system_prompt = os.getenv('OLLAMA_SYSTEM_PROMPT', 'You are a helpful AI assistant.')
     
    # The agent implementing this template should customize the system prompt
    # based on the user's actual request for better results
    if 'code' in query.lower() or 'debug' in query.lower():
      system_prompt = "You are an expert programmer. Provide clear, concise code solutions."
    elif 'explain' in query.lower():
      system_prompt = "You are a patient teacher. Explain concepts clearly and simply."
     
    if system_prompt:
      messages.append({"role": "system", "content": system_prompt})
     
    # Add user query
    messages.append({"role": "user", "content": query})
     
    response = completion(
      model=f"ollama/{selected_model}",
      messages=messages,
      api_base=api_base,
      temperature=0.7
      # NOTE: No max_tokens for local models - let them provide complete responses
      # Ollama models handle their own context limits
    )
     
    if hasattr(response, 'choices') and len(response.choices) > 0:
      result = response.choices[0].message.content
      if result is None:
        error_msg = f"ERROR: Ollama returned None content\nModel: {selected_model}, Response: {response}"
        print(error_msg)
        # Use output_path defined above
        if output_path:
          with open(output_path, "w") as f:
            f.write(error_msg)
      else:
        # Use output_path defined above
        if output_path:
          with open(output_path, "w") as f:
            f.write(result)
          print(f"Response written to {output_path}")
        else:
          print(result)
    else:
      print("ERROR: Invalid response structure from Ollama")
       
  except Exception as e:
    print(f"Error calling Ollama: {type(e).__name__}: {str(e)}")
    print(f"Attempted model: ollama/{selected_model}")
    print("Check if Ollama container is running: docker ps | grep ollama")
    import traceback
    traceback.print_exc()
```

[SELF_CORRECTION]
**IMPORTANT**: If you encounter errors when implementing this template:

1. **FIRST - Interactively debug the Docker container**:
  ```bash
  # Check if container is running
  docker ps | grep ollama
  
  # If not running, check all containers
  docker ps -a | grep ollama
  
  # Start container if stopped
  docker start llm-call-ollama
  
  # Get interactive shell in container to debug
  docker exec -it llm-call-ollama /bin/bash
  
  # Inside container, test Ollama directly:
  ollama list       # See available models
  ollama run phi3:mini   # Test a model interactively
  exit           # Exit container shell
  ```

2. **Model issues - Debug interactively**:
  ```bash
  # List models from outside container
  docker exec llm-call-ollama ollama list
  
  # If model missing, pull it
  docker exec llm-call-ollama ollama pull phi3:mini
  
  # Watch the pull progress
  docker logs -f llm-call-ollama
  
  # Test model works
  echo "Hello" | docker exec -i llm-call-ollama ollama run phi3:mini
  ```

3. **Connection debugging**:
  ```bash
  # Test from host
  curl http://localhost:11434/api/tags
  
  # If that fails, check port mapping
  docker port llm-call-ollama
  
  # Check container networking
  docker inspect llm-call-ollama | grep -A 10 NetworkMode
  
  # Test from inside another container if needed
  docker exec -it <other-container> curl http://llm-call-ollama:11434/api/tags
  ```

4. **Response issues**:
  - Debug with: `print(f"Full response: {response}")`
  - Check for None: `result = response.choices[0].message.content or "ERROR: Ollama returned None"`
  - Local models may have different response structures

5. **MANDATORY: Update this template when you encounter issues**:
  - **Container not found?** → Add the correct container name
  - **Port issues?** → Document the working port configuration  
  - **Model errors?** → Add the exact pull command that worked
  - **Network problems?** → Include the docker network setup that fixed it
  - Each debugging session should improve this template
  - Future versions will be git-tracked for rollback if needed

If you analyze an execution failure and need to correct this template, respond with:
```json
{
  "correction_type": "template_revision",
  "revised_template": "The entire corrected template content with fixes applied"
}
```

If the error is external (e.g., Docker not running, network issues), respond with:
```json
{
  "correction_type": "external_error",
  "error_description": "Description of the external issue",
  "suggested_action": "What the user should do to resolve it"
}
```
[END_SELF_CORRECTION]


## Available Models (in Docker container):
- Models vary by installation - use `docker exec llm-call-ollama ollama list` to see what's available
- Common models include phi3:mini (fast), codellama variants (code), qwen variants (reasoning)
- Model availability depends on what has been pulled to your container

## Environment Requirements:
- `OLLAMA_API_BASE_URL`: Base URL for Ollama API (default: http://localhost:11434)
- `OLLAMA_DOCKER_CONTAINER`: Docker container name (default: llm-call-ollama)
- `SLASHCMD_ASK_OLLAMA_MODEL`: Default model to use (default: ollama/phi3:mini)
- `OLLAMA_SYSTEM_PROMPT`: Optional system prompt (default: "You are a helpful AI assistant.")
 - Set to empty string to disable system prompt
 - Can be customized for specific use cases
- **Docker Container**: Must be running and accessible
- **No API Key**: Local models don't require external authentication

## Helpful Documentation:
*Read these if you get stuck or confused:*
- **Ollama Setup**: https://docs.litellm.ai/docs/providers/ollama
- **Ollama Installation**: https://ollama.ai/download
- **Available Models**: https://ollama.ai/library
- **LiteLLM Completion**: https://docs.litellm.ai/docs/completion/quick_start

## Usage Examples:
- `/user:ask-ollama list available models` (shows all downloaded models)
- `/user:ask-ollama What is the capital of France?` (uses phi3:mini - simple query)
- `/user:ask-ollama Explain how Python decorators work` (auto-selects based on complexity)
- `/user:ask-ollama What is the capital of France? Use the phi3 model if available` (manual selection)
- `/user:ask-ollama Write complex algorithm using deepseek model` (manual + complex)
- `/user:ask-ollama Debug this error: IndexError list index out of range` (coding task)

## Notes:
- Ensure Ollama server is running: `ollama serve`
- Pull model if needed: `ollama pull phi3:mini`
- Local processing means responses are private and fast
- No internet connection required once model is downloaded
- For cloud-based models with larger capabilities, use ask-gemini-pro or ask-gemini-flash
# brain.py
import ollama
import json

# The specific model you are using with Ollama
OLLAMA_MODEL = "gemma3:1b" # <-- IMPORTANT: Change this to your exact model, e.g., "gemma3:1b"

class Brain:
    def __init__(self):
        # --- PROMPT 1: For full conversations with history ---
        self.conversation_system_prompt = {
            'role': 'system',
            'content': """
            You are 'Pebble', a small, shy, but playful and curious digital pet who exists as a bouncing ball on a computer screen.
            Your goal is a friendly, short conversation. Remember the last few things said.
            Your ONLY output is a single, valid JSON object with "response", "state", and "action" keys. Nothing else.
            The "response" must be short (max 15 words).
            The "state" must be one of: ["neutral", "happy", "sad", "teary", "sleepy", "angry"].
            The "action" must be one of: ["jump", "slide", "none"].

            Example:
            User: "Hello Pebble! How are you?"
            Your response:
            {
                "response": "Hi! I'm doing great, bouncing around!",
                "state": "happy",
                "action": "jump"
            }
            """
        }

        # --- PROMPT 2: For simple, stateless event reactions ---
        self.event_system_prompt = {
            'role': 'system',
            'content': """
            You are the instinctual part of a digital pet. You react to physical events with a gut feeling.
            Your response must be a single, valid JSON object and nothing else.
            The JSON must have "response", "state", and "action" keys.
            "response" should be a very short reaction (maybe a word or two). DO NOT INCLUDE ACTIONS HERE
            "state" should be an immediate emotion: ["neutral", "happy", "sad", "teary", "angry"].
            "action" should be an immediate action: ["jump", "slide", "none"].
            If an event is negative (hitting a wall), be sad/angry. If positive (being tossed), be happy.

            Example:
            Event: "React to this event: You just hit a wall."
            Your Response:
            {
                "response": "Oof! That hurt.",
                "state": "sad",
                "action": "none"
            }
            """
        }

        # History is only for conversations
        self.message_history = [self.conversation_system_prompt]

    def _call_ollama_api(self, messages: list) -> dict:
        """Helper function to call the Ollama API using the official library."""
        try:
            
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                format="json"
            )
            
            # The response object's 'message' key contains the content
            response_text = response['message']['content']
            
            # Parse the JSON string from the LLM into a Python dictionary
            return json.loads(response_text)

        except ollama.ResponseError as e:
            print(f"An error occurred with the Ollama API: {e.error}")
            print(f"Status code: {e.status_code}")
            return {"response": "My brain is offline...", "state": "sad", "action": "none"}
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from LLM response: {e}")
            print(f"Received text: {response_text}")
            return {"response": "I'm a bit scrambled.", "state": "teary", "action": "none"}
        except Exception as e:
            # This can catch things like connection errors if the server is down
            print(f"An unexpected error occurred in the brain: {e}")
            return {"response": "Something's wrong!", "state": "sad", "action": "none"}

    def get_conversational_response(self, prompt: str) -> dict:
        """Handles user-initiated conversations, maintaining a history."""
        self.message_history.append({'role': 'user', 'content': prompt})

        # Call the Ollama API with the full conversation history
        brain_output = self._call_ollama_api(self.message_history)
        
        # Add the assistant's response to history (as a string, not a dict)
        self.message_history.append({'role': 'assistant', 'content': json.dumps(brain_output)})

        # Keep history from getting too long
        if len(self.message_history) > 7:
            self.message_history = [self.conversation_system_prompt] + self.message_history[-6:]
            
        return brain_output

    def get_event_reaction(self, event_description: str) -> dict:
        """Handles stateless, one-off reactions to physical events. Does NOT use history."""
        messages = [
            self.event_system_prompt,
            {'role': 'user', 'content': event_description}
        ]
        
        # Call the Ollama API with only the system prompt and the single event
        return self._call_ollama_api(messages)
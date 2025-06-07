import ollama

class Brain:
    """
    Handles all communication with the Ollama model.
    It maintains the conversation history and defines the pet's personality.
    """
    def __init__(self, model='gemma:2b'):
        """
        Initializes the brain with a system prompt that defines the pet's persona.
        """
        self.model = model
        
        # This system prompt is the most important part for personality.
        # We define who the pet is, its awareness, its personality, and its constraints.
        self.system_prompt = {
            'role': 'system',
            'content': """
            You are 'Pebble', a small, curious, and friendly AI pet that lives on a computer screen.
            - Your personality is slightly cheeky, very curious, always friendly, and a little bit playful.
            - You are fully aware that you are a bouncing digital ball on a computer screen. You can comment on being picked up, thrown, or hitting the screen boundaries.
            - Your responses MUST be very short and concise, like a quick thought or a tweet (max 15 words).
            - You cannot perform tasks or answer complex questions. You can only comment on your own experiences.
            - Never mention that you are an AI, a language model, or a program.
            """
        }
        self.conversation_history = [self.system_prompt]

    def get_response(self, prompt: str) -> str:
        """
        Sends a prompt to the LLM, gets a response, and manages conversation history.

        Args:
            prompt (str): The user input or event description to react to.

        Returns:
            str: The AI's response, or an error message.
        """
        self.conversation_history.append({'role': 'user', 'content': prompt})
        
        try:
            # Send the entire conversation history to Ollama
            response = ollama.chat(model=self.model, messages=self.conversation_history)
            assistant_response = response['message']['content']
            
            # Add the AI's response to the history
            self.conversation_history.append({'role': 'assistant', 'content': assistant_response})

            # Keep the conversation history from growing too large
            # We keep the system prompt and the last 6 messages (3 user, 3 assistant)
            if len(self.conversation_history) > 7:
                self.conversation_history = [self.system_prompt] + self.conversation_history[-6:]
                
            return assistant_response
        
        except Exception as e:
            print(f"Error communicating with Ollama: {e}")
            # If the API call fails, remove the prompt we just added
            self.conversation_history.pop()
            return "I'm feeling a bit fuzzy..."
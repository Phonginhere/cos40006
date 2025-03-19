import openai

def load_api_key():
    """Loads the OpenAI API key from a separate text file."""
    try:
        with open("openai_api_key.txt", "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError("API key file not found. Please create 'openai_api_key.txt' and add your API key.")

# Set OpenAI API key
api_key = load_api_key()
openai.api_key = api_key

def get_gpt_4o_mini_response(prompt):
    """
    Calls GPT-4o-mini and returns the generated response.
    
    :param prompt: The input prompt for the LLM.
    :return: The model's response as a string.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert in system requirements engineering."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=8192,
            temperature=0.7,
            n=1
        )
        return response.choices[0].message.content.strip()
    
    except openai.OpenAIError as e:
        print(f"❌ OpenAI API Error: {e}")
        return None

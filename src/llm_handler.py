import os
import openai

from transformers import GPTNeoForCausalLM, GPT2Tokenizer
import torch

# Global variable to specify which LLM is being used in the pipeline
CURRENT_LLM = "gpt-4o-mini"

# ======================================================================================================================================================================
# OPENAI
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

def get_openai_response(prompt, model):
    """Uses OpenAI's API to generate a response."""
    try:
        response = openai.chat.completions.create(
            model=model,
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
    
# ======================================================================================================================================================================
# GPT-NEO
# GPT-Neo loading (only once)
_neo_model = None
_neo_tokenizer = None

def _load_gpt_neo():
    global _neo_model, _neo_tokenizer
    if _neo_model is None or _neo_tokenizer is None:
        print("🔄 Loading GPT-Neo model and tokenizer...")
        _neo_model = GPTNeoForCausalLM.from_pretrained("EleutherAI/gpt-neo-1.3B")
        _neo_tokenizer = GPT2Tokenizer.from_pretrained("EleutherAI/gpt-neo-1.3B")
    return _neo_model, _neo_tokenizer

# GPT-Neo handler
def get_gpt_neo_response(prompt: str) -> str:
    model, tokenizer = _load_gpt_neo()
    input_ids = tokenizer(prompt, return_tensors="pt").input_ids

    with torch.no_grad():
        gen_tokens = model.generate(
            input_ids,
            do_sample=True,
            temperature=0.8,
            max_length=600,
            pad_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(gen_tokens[0], skip_special_tokens=True)

# ======================================================================================================================================================================
# LLM DISPATCHER
def get_llm_response(prompt: str) -> str:
    if CURRENT_LLM.startswith("gpt-4"):
        return get_openai_response(prompt, model=CURRENT_LLM)
    elif CURRENT_LLM.startswith("gpt-neo"):
        return get_gpt_neo_response(prompt)
    else:
        raise NotImplementedError(f"LLM '{CURRENT_LLM}' is not supported yet.")

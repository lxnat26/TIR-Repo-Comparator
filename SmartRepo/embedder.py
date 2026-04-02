import requests
from config import OLLAMA_URL, EMBED_MODEL

def convert_to_vector(text):
    response = requests.post(OLLAMA_URL, json={"model": EMBED_MODEL, "prompt": text})
    data = response.json()
    vector = data["embedding"]

    return vector

if __name__ == "__main__":
    result = convert_to_vector("Drug X completed Phase 2 enrollment")
    print(len(result))
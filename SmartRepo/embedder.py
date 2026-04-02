import ollama
from config import EMBED_MODEL

def convert_to_vector(text):
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    vector = response["embedding"]

    return vector

if __name__ == "__main__":
    result = convert_to_vector("Drug X completed Phase 2 enrollment")
    print(len(result))
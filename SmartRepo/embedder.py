import ollama

def convert_to_vector(text: str) -> list[float]:
    if not isinstance(text, str):
        raise TypeError(f"text must be a str, got {type(text).__name__}")

    try:
        response = ollama.embeddings(model="nomic-embed-text", prompt=text)
    except ollama.ResponseError as e:
        raise RuntimeError(f"Ollama API error: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to reach Ollama service: {e}") from e

    embedding = response.get("embedding")
    if not embedding:
        raise ValueError("Ollama returned an empty or missing embedding")

    return embedding


if __name__ == "__main__":
    result = convert_to_vector("Drug X completed Phase 2 enrollment")
    print(len(result))
from llama_cpp import Llama

llm = Llama(
    model_path="model.gguf",
    n_ctx=512,
    n_threads=6 
)

def generate_answer(prompt: str) -> str:
    full_prompt = f"User: {prompt}\nAssistant:"

    result = llm(
        full_prompt,
        max_tokens=200,
        stream=False
    )

    return result["choices"][0]["text"].strip()
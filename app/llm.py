import ollama


# ---------------------------
# Normal (existing) call
# ---------------------------
def ask_llm(prompt: str):
    response = ollama.chat(
        model="llama3",
        messages=[
            {
                "role": "system",
                "content": "You are a precise RCA assistant. Keep answers short, factual, and to the point."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "num_predict": 80,
            "temperature": 0.2,
            "top_p": 0.9,
            "repeat_penalty": 1.1
        }
    )

    return response["message"]["content"]


# ---------------------------
# 🔥 Streaming call (NEW)
# ---------------------------
def stream_llm(prompt: str):
    stream = ollama.chat(
        model="llama3",
        messages=[
            {
                "role": "system",
                "content": "You are a strict RCA extraction engine. Be concise."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        stream=True,   # 🔥 KEY
        options={
            "num_predict": 80,
            "temperature": 0.2,
            "top_p": 0.9
        }
    )

    for chunk in stream:
        if "message" in chunk and "content" in chunk["message"]:
            yield chunk["message"]["content"]
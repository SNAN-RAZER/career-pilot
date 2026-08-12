from app.llm.lmstudio_client import LMStudioClient


def test_embedding():

    client = LMStudioClient()

    vector = client.embed(
        "VxWorks real time operating system"
    )

    print(
        f"\nEmbedding dimensions: {len(vector)}"
    )

    assert isinstance(vector, list)
    assert len(vector) > 0

def test_llm():

    client = LMStudioClient()

    response = client.chat(
        [
            {
                "role": "system",
                "content": (
                    "You are a career analysis assistant. "
                    "Answer concisely."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Is VxWorks relevant to an "
                    "embedded software engineer?"
                ),
            },
        ]
    )

    print("\nLLM response:")
    print(response)

    assert response
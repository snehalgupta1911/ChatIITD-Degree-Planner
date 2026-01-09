from transformers import pipeline
from huggingface_hub import login
import os

login(token=os.getenv("HF_TOKEN"))

generator = pipeline("text-generation", model="gpt2")
output = generator("Hello, world!", max_length=50)
print(output[0]["generated_text"])


import os
import requests

try:
    with open(".env", "r") as f:
        env = f.read()
    key = None
    for line in env.splitlines():
        if line.startswith("OPENAI_API_KEY="):
            key = line.split("=", 1)[1].strip()
            
    r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}")
    data = r.json()
    for m in data.get("models", []):
        if "gemini" in m["name"]:
            print(m["name"])
except Exception as e:
    print(e)

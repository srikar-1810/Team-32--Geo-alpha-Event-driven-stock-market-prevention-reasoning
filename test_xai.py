import os
import requests

key = "xai_key_goes_here"
try:
    r = requests.get("https://api.x.ai/v1/models", headers={"Authorization": f"Bearer {key}"})
    print(r.json())
except Exception as e:
    print(e)

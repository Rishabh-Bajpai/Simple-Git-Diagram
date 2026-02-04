import httpx
import os
from openai import OpenAI
import sys

base_url = "http://[IP_ADDRESS]/v1"
api_key = "dummy"

print(f"Testing URL: {base_url}")

print("\n--- 1. Testing with httpx directly ---")
try:
    with httpx.Client(base_url=base_url) as client:
        resp = client.get("/models")
        print(f"Status: {resp.status_code}")
        print(f"Preview: {resp.text[:100]}")
except Exception as e:
    print(f"HTTPX Error: {e}")
    # print(e.__class__.__name__)

print("\n--- 2. Testing with OpenAI Client ---")
try:
    client = OpenAI(base_url=base_url, api_key=api_key)
    # List models to test connection
    models = client.models.list()
    print(f"Successfully connected. Found {len(list(models))} models.")
except Exception as e:
    print(f"OpenAI Error: {e}")

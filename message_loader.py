import yaml
import os

def load_messages(filepath="messages/messages.yaml"):
    with open(filepath, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data.get(data)

MESSAGES = load_messages()

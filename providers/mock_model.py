"""A deliberately unreliable stand-in for an AI model.

It classifies support tickets with simple rules, then gets the answer wrong
some of the time (MOCK_ERROR_RATE, default 0.05). That is the point: real
models also vary between identical runs, so the gate measures a pass rate
over repeated runs instead of expecting one perfect result.
"""

import json
import os
import random
import re

CATEGORIES = ["billing", "technical", "account", "other"]


def _ticket(prompt):
    m = re.search(r'"""\s*(.*?)\s*"""', prompt, re.S)
    return (m.group(1) if m else prompt).lower()


def _classify(ticket):
    if re.search(r"charge|refund|invoice|payment|card|declined", ticket):
        category = "billing"
    elif re.search(r"password|log ?in to my account|reset", ticket):
        category = "account"
    elif re.search(r"error|502|down|crash|log in|bug", ticket):
        category = "technical"
    else:
        category = "other"
    if re.search(r"nobody|every user|all users|outage", ticket):
        priority = "high"
    elif re.search(r"no rush|curious", ticket):
        priority = "low"
    else:
        priority = "medium"
    return category, priority


def call_api(prompt, options, context):
    category, priority = _classify(_ticket(prompt))
    error_rate = float(os.environ.get("MOCK_ERROR_RATE", "0.05"))
    if random.random() < error_rate:
        category = random.choice([c for c in CATEGORIES if c != category])
    if random.random() < error_rate:
        priority = random.choice(["low", "medium", "high"])
    return {"output": json.dumps({"category": category, "priority": priority})}

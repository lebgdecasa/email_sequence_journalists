import os
import textwrap

import requests

_ENDPOINT = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/projects/PROJECT/locations/us-central1/publishers/google/"
    "models/gemini-pro:generateContent"
)

_KEY = os.environ["GEMINI_KEY"]


def summarise_article(url: str) -> dict:
    # minimal implementation; expand later
    prompt = textwrap.dedent(
        f"""
        Summarise this article in one sentence and ask one probing question.
        URL: {url}
    """
    )
    res = requests.post(
        _ENDPOINT,
        params={"key": _KEY},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=15,
    )
    return res.json()  # you'll parse .candidates[0]....

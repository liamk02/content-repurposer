"""Content Repurposer - one piece of long-form content in, several
repurposed formats out (summary, social posts, email blurb), via Claude.

Usage:
    python app.py
    (then open http://127.0.0.1:5000)

Deployment (Render): set ANTHROPIC_API_KEY as a server-side environment
variable and run with gunicorn (see Procfile).
"""

import json
import os
import re

import anthropic
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

MODEL = "claude-sonnet-5"
MAX_CONTENT_CHARS = 8000

SYSTEM_PROMPT = """You repurpose long-form content (blog posts, video/podcast
transcripts, articles) into a few other formats, keeping the original's key
points and voice as much as possible.

Respond with ONLY a JSON object, no other text, in exactly this shape:
{"summary": "<one paragraph, 2-4 sentences>", "social_posts": ["<post 1>", "<post 2>", "<post 3>"], "email_blurb": "<3-5 sentences, teases the content and invites the reader to check it out>"}

Rules:
- social_posts: exactly 3 posts, each a genuinely different angle on the
  source content (not three phrasings of the same point), each under 280
  characters, no hashtags unless the source content uses them itself
- Do not invent facts, numbers, or claims not present in the source content
- Match the source's tone (casual stays casual, technical stays technical)
- Plain text only in every field - no markdown formatting"""


def extract_json(text: str) -> dict:
    """Parse the model's JSON reply, tolerating stray text around it."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("No JSON object found in model response")


load_dotenv()
app = Flask(__name__, static_folder="static", static_url_path="")
client = anthropic.Anthropic()
limiter = Limiter(get_remote_address, app=app, default_limits=[])


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    # No Claude API call here - a liveness check should never cost money.
    response = jsonify({"status": "ok", "service": "content-repurposer"})
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/api/repurpose", methods=["POST"])
@limiter.limit("10 per hour")
def repurpose():
    data = request.get_json(force=True, silent=True) or {}
    content = (data.get("content") or "").strip()

    if not content:
        return jsonify({"error": "Paste in some content first."}), 400
    if len(content) > MAX_CONTENT_CHARS:
        return jsonify({"error": f"Content too long (max {MAX_CONTENT_CHARS} characters for this demo)."}), 400

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Source content:\n\n{content}"}],
        )
        raw = next((b.text for b in response.content if b.type == "text"), "")
        result = extract_json(raw)

        if (
            not isinstance(result.get("summary"), str)
            or not isinstance(result.get("social_posts"), list)
            or len(result["social_posts"]) != 3
            or not isinstance(result.get("email_blurb"), str)
        ):
            raise ValueError(f"Model returned unexpected shape: {result}")

    except anthropic.RateLimitError:
        return jsonify({"error": "Busy right now - try again shortly."}), 429
    except anthropic.APIStatusError as e:
        return jsonify({"error": f"API error: {e.message}"}), 502
    except (ValueError, json.JSONDecodeError):
        return jsonify({"error": "Could not repurpose that content - try again."}), 502

    return jsonify(result)


@app.errorhandler(429)
def rate_limited(_e):
    return jsonify({"error": "Rate limit reached - try again in a bit."}), 429


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1", port=int(os.environ.get("PORT", 5000)))

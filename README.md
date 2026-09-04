# Content Repurposer

Paste in long-form content (a blog post, a video/podcast transcript, an
article) and get back a summary, 3 distinct social posts, and an email
blurb — one Claude call, several output formats.

## Why this exists

My other two projects read and react: `doc-qa-tool` retrieves and answers,
`lead-triage` classifies. This one *generates* - the first project in the
portfolio that produces new content instead of extracting or scoring
existing content. That's a different, complementary pitch: less "AI saves
you time reading," more "AI multiplies what you get out of one piece of
content."

## How it works

1. Paste content into the textarea, click **Repurpose**
2. One request to Claude (Sonnet 5 - generating decent marketing copy
   benefits from more capability than simple classification does) returns
   JSON: `summary`, `social_posts` (exactly 3, each a different angle),
   `email_blurb`
3. Each output renders in its own card with a **Copy** button

## Guardrails (public endpoint)

- **Rate limited** - 10 requests/hour per visitor (`flask-limiter`)
- **Input capped** - 8,000 characters, enforced both client-side
  (`maxlength`) and server-side
- Single Claude call per request (not one call per output format) keeps
  cost per use low

## Local setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# edit .env, paste in your Anthropic API key
python app.py
# open http://127.0.0.1:5000
```

## Deploy to Render (free tier)

1. Push this repo to GitHub
2. New Web Service on [render.com](https://render.com), pointed at this repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT` (set this
   explicitly in the dashboard - a Procfile alone isn't enough if the
   dashboard has its own Start Command field, which overrides it)
5. Environment variables: `ANTHROPIC_API_KEY`

Set a monthly spend cap in the Anthropic Console regardless - same
reasoning as the other two projects: rate limiting bounds normal traffic,
but a cap is the real safety net for a public endpoint.

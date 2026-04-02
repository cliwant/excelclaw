"""ExcelClaw WhatsApp Bot — FastAPI application."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.whatsapp.webhook import router as webhook_router
from app.agent.sessions import active_session_count

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger(__name__).info("ExcelClaw WhatsApp Bot starting up")
    yield
    logging.getLogger(__name__).info("ExcelClaw WhatsApp Bot shutting down")


app = FastAPI(
    title="ExcelClaw WhatsApp Bot",
    description="Turn your Excel into an AI agent via WhatsApp",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(webhook_router)


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    return """<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ExcelClaw - Privacy Policy</title>
<style>body{font-family:sans-serif;max-width:700px;margin:40px auto;padding:0 20px;line-height:1.6;color:#333}h1{border-bottom:2px solid #eee;padding-bottom:10px}</style>
</head><body>
<h1>Privacy Policy</h1>
<p><strong>Last updated:</strong> April 2, 2026</p>

<h2>1. Overview</h2>
<p>ExcelClaw ("we", "our") is a WhatsApp-based assistant that helps users manage Excel files through chat. We are committed to protecting your privacy.</p>

<h2>2. Data We Collect</h2>
<ul>
<li><strong>WhatsApp messages:</strong> Text messages and files you send to our bot, used solely to process your requests.</li>
<li><strong>Phone number:</strong> Your WhatsApp phone number, used to identify your session.</li>
<li><strong>Uploaded files:</strong> Excel files you share, processed temporarily to fulfill your requests.</li>
</ul>

<h2>3. How We Use Your Data</h2>
<p>Your data is used exclusively to provide the ExcelClaw service. We do not sell, share, or use your data for advertising purposes.</p>

<h2>4. Data Retention</h2>
<p>Uploaded files and session data are stored temporarily and deleted after your session ends or within 24 hours, whichever comes first.</p>

<h2>5. Third-Party Services</h2>
<p>We use the following third-party services:</p>
<ul>
<li><strong>Meta (WhatsApp Business API):</strong> For messaging. Subject to <a href="https://www.whatsapp.com/legal/privacy-policy">WhatsApp's Privacy Policy</a>.</li>
<li><strong>Anthropic (Claude API):</strong> For AI processing. No personal data is retained by Anthropic.</li>
</ul>

<h2>6. Contact</h2>
<p>For privacy-related inquiries, please contact us via WhatsApp.</p>
</body></html>"""


@app.get("/terms", response_class=HTMLResponse)
async def terms_of_service():
    return """<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ExcelClaw - Terms of Service</title>
<style>body{font-family:sans-serif;max-width:700px;margin:40px auto;padding:0 20px;line-height:1.6;color:#333}h1{border-bottom:2px solid #eee;padding-bottom:10px}</style>
</head><body>
<h1>Terms of Service</h1>
<p><strong>Last updated:</strong> April 2, 2026</p>

<h2>1. Acceptance of Terms</h2>
<p>By using ExcelClaw ("the Service"), you agree to these Terms of Service. If you do not agree, please stop using the Service.</p>

<h2>2. Description of Service</h2>
<p>ExcelClaw is a WhatsApp-based AI assistant that helps users manage and analyze Excel files through chat messages.</p>

<h2>3. User Responsibilities</h2>
<ul>
<li>You must not use the Service for any illegal or unauthorized purpose.</li>
<li>You are responsible for the content of the files you upload.</li>
<li>You must not attempt to disrupt or abuse the Service.</li>
</ul>

<h2>4. Limitation of Liability</h2>
<p>The Service is provided "as is" without warranties of any kind. We are not liable for any data loss, errors in file processing, or damages arising from the use of the Service.</p>

<h2>5. Modifications</h2>
<p>We reserve the right to modify or discontinue the Service at any time without prior notice.</p>

<h2>6. Termination</h2>
<p>We may terminate or suspend access to the Service at our discretion, without notice, for conduct that we believe violates these Terms.</p>

<h2>7. Contact</h2>
<p>For questions about these Terms, please contact us via WhatsApp.</p>
</body></html>"""


@app.get("/datadeletion", response_class=HTMLResponse)
async def data_deletion():
    return """<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ExcelClaw - Data Deletion</title>
<style>body{font-family:sans-serif;max-width:700px;margin:40px auto;padding:0 20px;line-height:1.6;color:#333}h1{border-bottom:2px solid #eee;padding-bottom:10px}.btn{display:inline-block;background:#25D366;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;margin-top:10px}</style>
</head><body>
<h1>Data Deletion Request</h1>
<p><strong>Last updated:</strong> April 2, 2026</p>

<h2>Your Data</h2>
<p>ExcelClaw stores the following data temporarily:</p>
<ul>
<li>WhatsApp phone number (session identifier)</li>
<li>Conversation history (in-memory, auto-deleted within 24 hours)</li>
<li>Uploaded Excel files (auto-deleted within 24 hours)</li>
</ul>

<h2>Automatic Deletion</h2>
<p>All user data is automatically deleted within 24 hours of your last interaction. No long-term storage of personal data is maintained.</p>

<h2>Request Manual Deletion</h2>
<p>If you would like your data deleted immediately, send the message <strong>"delete my data"</strong> to our WhatsApp bot, and all your session data and files will be removed instantly.</p>

<h2>Contact</h2>
<p>For additional data deletion requests, please contact us via WhatsApp.</p>
</body></html>"""


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "active_sessions": active_session_count(),
    }

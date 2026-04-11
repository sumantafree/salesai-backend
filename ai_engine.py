"""
AI Message Generation Engine
- Uses OpenAI GPT if API key is set in config.env
- Falls back to smart templates if no API key
"""

import os
import random

# Try to load OpenAI (optional)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def _use_openai() -> bool:
    return OPENAI_AVAILABLE and bool(OPENAI_API_KEY)


def _openai_generate(prompt: str) -> str:
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400
    )
    return response.choices[0].message.content.strip()


# ─── EMAIL GENERATION ──────────────────────────────────────────────────────────

EMAIL_SUBJECTS = [
    "Quick idea to get more leads for {business}",
    "I noticed something about {business}'s online presence",
    "3X more leads without increasing ad spend — for {business}?",
    "Free website audit for {business}",
    "{business} — quick growth opportunity I spotted",
]

EMAIL_TEMPLATES = [
    """Hi {owner},

I came across {business} online and noticed your digital presence has some untapped potential.

Specifically, I spotted a few areas where businesses in the {industry} space typically see quick wins:
• Conversion optimization on the landing page
• Retargeting setup for visitors who don't convert
• Local SEO that your competitors may not be using

We recently helped a {industry} business in {location} increase their qualified leads by 3X — without increasing their ad budget.

Would you be open to a free 10-minute audit call this week? I'll share exactly what I found and what I'd do differently.

No pressure, no pitch — just value.

Best,
[Your Name]
[Agency Name]
[Phone]""",

    """Hi {owner},

Quick question — are you happy with the ROI you're getting from your current digital marketing?

I looked at {business} and noticed a few missed opportunities that could significantly improve your lead flow.

We specialize in helping {industry} businesses:
✅ Get more qualified leads from Google & Meta Ads
✅ Improve website conversion rates
✅ Automate follow-ups so no lead goes cold

I'd love to share a quick audit report (no cost, no commitment).

Would Thursday or Friday work for a 15-minute call?

Regards,
[Your Name]""",

    """Dear {owner},

I hope this finds you well. I'm reaching out because I work with several {industry} businesses in {location} and noticed that {business} could benefit from a stronger digital strategy.

After a quick review of your online presence, I identified 3 specific improvements that typically generate 40-60% more leads within 60 days.

I'd like to share these insights with you at no charge. We believe in leading with value.

Could I schedule a brief 10-minute call this week?

Looking forward to connecting,
[Your Name]
[Agency Name]"""
]


def generate_email(lead) -> dict:
    business = lead.business_name or "your business"
    owner = lead.owner_name or "there"
    industry = lead.industry or "your industry"
    location = lead.location or "your area"

    if _use_openai():
        prompt = f"""Write a professional cold sales email for a digital marketing agency.

Lead details:
- Business: {business}
- Owner: {owner}
- Industry: {industry}
- Location: {location}

Requirements:
- Subject line (high open rate, personalized)
- Professional but friendly tone
- Mention specific pain points for {industry}
- Offer a free audit or strategy call
- Keep under 200 words
- End with clear CTA

Format:
SUBJECT: [subject line]
BODY:
[email body]"""
        try:
            result = _openai_generate(prompt)
            lines = result.split("\n")
            subject = ""
            body_lines = []
            in_body = False
            for line in lines:
                if line.startswith("SUBJECT:"):
                    subject = line.replace("SUBJECT:", "").strip()
                elif line.startswith("BODY:"):
                    in_body = True
                elif in_body:
                    body_lines.append(line)
            return {
                "subject": subject or f"Quick idea for {business}",
                "body": "\n".join(body_lines).strip()
            }
        except Exception:
            pass  # Fall through to template

    # Template-based fallback
    subject = random.choice(EMAIL_SUBJECTS).format(business=business)
    body = random.choice(EMAIL_TEMPLATES).format(
        business=business,
        owner=owner,
        industry=industry,
        location=location
    )
    return {"subject": subject, "body": body}


# ─── WHATSAPP GENERATION ───────────────────────────────────────────────────────

WA_TEMPLATES = [
    "Hi {owner}! 👋\n\nI checked {business} online — noticed a few quick wins in your ads & website that could improve lead flow.\n\nCan I share a free audit? Just 5 mins of your time. 🙏",

    "Hey {owner}, I came across {business} and spotted some growth opportunities in your digital marketing.\n\nWe helped a similar {industry} business get 3X more leads last month.\n\nWould love to share what worked for them — free of charge! 📈\n\nInterested?",

    "Hi {owner}! Quick message — I noticed {business} has strong potential online but a few gaps that are probably costing you leads.\n\nI do free 10-min audits for {industry} businesses. Want me to send you what I found? No obligation at all. 😊",
]


def generate_whatsapp(lead) -> dict:
    business = lead.business_name or "your business"
    owner = lead.owner_name or "there"
    industry = lead.industry or "your industry"

    if _use_openai():
        prompt = f"""Write a short WhatsApp message for digital marketing agency outreach.

Business: {business}
Owner: {owner}
Industry: {industry}

Requirements:
- Very short (under 80 words)
- Conversational, non-spammy tone
- Personalized with business name
- Clear value proposition
- Soft CTA
- Can include 1-2 relevant emojis

Write only the message text, nothing else."""
        try:
            return {"body": _openai_generate(prompt)}
        except Exception:
            pass

    body = random.choice(WA_TEMPLATES).format(
        business=business,
        owner=owner,
        industry=industry
    )
    return {"body": body}


# ─── LINKEDIN GENERATION ──────────────────────────────────────────────────────

LI_TEMPLATES = [
    "Hi {owner}, I work with {industry} businesses to improve ROI from digital marketing. I noticed {business} and would love to connect and share some insights that could be relevant for you.",

    "Hi {owner}, I came across {business} and was impressed. I specialize in helping {industry} companies get more leads from Meta and Google Ads. Would love to connect!",

    "Hello {owner}, I help businesses like {business} generate more qualified leads without increasing ad spend. Would love to connect and share what's been working in the {industry} space.",
]


def generate_linkedin(lead) -> dict:
    business = lead.business_name or "your business"
    owner = lead.owner_name or "there"
    industry = lead.industry or "your industry"

    if _use_openai():
        prompt = f"""Write a short LinkedIn connection request message.

Business: {business}
Owner: {owner}
Industry: {industry}

Requirements:
- Under 300 characters (LinkedIn limit)
- Professional tone
- Mention their industry
- No hard selling
- Feel genuinely interested

Write only the message, nothing else."""
        try:
            return {"body": _openai_generate(prompt)}
        except Exception:
            pass

    body = random.choice(LI_TEMPLATES).format(
        business=business,
        owner=owner,
        industry=industry
    )
    return {"body": body}


# ─── FOLLOW-UP SEQUENCE ───────────────────────────────────────────────────────

FOLLOWUP_SEQUENCES = {
    1: "Hi {owner}, just following up on my earlier message about {business}. Did you get a chance to look at it? Would love to share those insights.",
    3: "Hey {owner}! Quick reminder — I have a free audit ready for {business}. Businesses in {industry} are seeing great results right now. Want to take a look?",
    5: "Hi {owner}, I thought you might find this relevant: we recently helped a {industry} business increase leads by 2.5X in 45 days. Happy to walk you through the same approach for {business}.",
    7: "Hi {owner}, last nudge from me! If you ever want to explore how {business} can get more leads digitally, I'm here. Feel free to reach out anytime. 😊",
}


def generate_followup(lead, day: int) -> dict:
    business = lead.business_name or "your business"
    owner = lead.owner_name or "there"
    industry = lead.industry or "your industry"

    template = FOLLOWUP_SEQUENCES.get(day, FOLLOWUP_SEQUENCES[7])
    body = template.format(business=business, owner=owner, industry=industry)
    return {"body": body, "day": day}

"""
AI Sales Assistant - FastAPI Backend
Run with: uvicorn main:app --reload
"""

import os
from dotenv import load_dotenv

# Load config.env from parent directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "config.env"))

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import sqlalchemy.orm as orm

from database import engine, SessionLocal, Base, User, Lead, Message, Campaign
from auth import create_token, verify_token, hash_password, verify_password
from ai_engine import generate_email, generate_whatsapp, generate_linkedin, generate_followup
from scraper import scrape_leads
from email_service import send_email

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Sales Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "https://sales.digitalsumanta.com",
]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


# ─── DATABASE DEPENDENCY ──────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── AUTH DEPENDENCY ──────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: orm.Session = Depends(get_db)
):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ─── SCHEMAS ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class LeadCreate(BaseModel):
    business_name: str
    owner_name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    website: Optional[str] = ""
    industry: str
    location: Optional[str] = ""
    social_links: Optional[str] = ""
    notes: Optional[str] = ""

class LeadUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    score: Optional[int] = None
    tag: Optional[str] = None

class MessageRequest(BaseModel):
    lead_id: int
    message_type: str  # email / whatsapp / linkedin

class SendEmailRequest(BaseModel):
    lead_id: int
    subject: str
    body: str

class ScrapeRequest(BaseModel):
    keyword: str
    location: str
    limit: Optional[int] = 10

class CampaignCreate(BaseModel):
    name: str
    industry: Optional[str] = ""
    location: Optional[str] = ""
    tone: Optional[str] = "friendly"
    offer: Optional[str] = "free audit"
    daily_limit: Optional[int] = 20


# ─── HELPER: LEAD SCORING ─────────────────────────────────────────────────────

def score_lead(lead: LeadCreate) -> int:
    score = 0
    if lead.website:
        score += 25
    if lead.email and "gmail.com" not in lead.email.lower() and "yahoo.com" not in lead.email.lower():
        score += 20
    elif lead.email:
        score += 8
    if lead.phone:
        score += 15
    if lead.social_links:
        score += 15
    hot_industries = ["real estate", "healthcare", "coaching", "ecommerce", "restaurant", "interior", "gym", "salon", "education"]
    if any(ind in lead.industry.lower() for ind in hot_industries):
        score += 25
    return min(score, 100)


def tag_from_score(score: int) -> str:
    if score >= 70:
        return "HOT"
    elif score >= 40:
        return "WARM"
    return "COLD"


def lead_to_dict(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "business_name": lead.business_name,
        "owner_name": lead.owner_name,
        "email": lead.email,
        "phone": lead.phone,
        "website": lead.website,
        "industry": lead.industry,
        "location": lead.location,
        "social_links": lead.social_links,
        "notes": lead.notes,
        "score": lead.score,
        "tag": lead.tag,
        "status": lead.status,
        "created_at": lead.created_at.isoformat() if lead.created_at else "",
    }


# ─── AUTH ROUTES ──────────────────────────────────────────────────────────────

@app.post("/register")
def register(req: RegisterRequest, db: orm.Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(name=req.name, email=req.email, password=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user.id)
    return {"token": token, "user": {"id": user.id, "name": user.name, "email": user.email}}


@app.post("/login")
def login(req: LoginRequest, db: orm.Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user.id)
    return {"token": token, "user": {"id": user.id, "name": user.name, "email": user.email}}


# ─── LEAD ROUTES ──────────────────────────────────────────────────────────────

@app.get("/leads")
def get_leads(
    tag: Optional[str] = None,
    status: Optional[str] = None,
    db: orm.Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Lead).filter(Lead.user_id == current_user.id)
    if tag:
        query = query.filter(Lead.tag == tag.upper())
    if status:
        query = query.filter(Lead.status == status.upper())
    leads = query.order_by(Lead.score.desc()).all()
    return [lead_to_dict(l) for l in leads]


@app.post("/leads")
def create_lead(
    lead: LeadCreate,
    db: orm.Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sc = score_lead(lead)
    new_lead = Lead(
        user_id=current_user.id,
        business_name=lead.business_name,
        owner_name=lead.owner_name,
        email=lead.email,
        phone=lead.phone,
        website=lead.website,
        industry=lead.industry,
        location=lead.location,
        social_links=lead.social_links,
        notes=lead.notes,
        score=sc,
        tag=tag_from_score(sc),
        status="NEW"
    )
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    return lead_to_dict(new_lead)


@app.put("/leads/{lead_id}")
def update_lead(
    lead_id: int,
    update: LeadUpdate,
    db: orm.Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.user_id == current_user.id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if update.status is not None:
        lead.status = update.status
    if update.notes is not None:
        lead.notes = update.notes
    if update.score is not None:
        lead.score = update.score
        lead.tag = tag_from_score(update.score)
    if update.tag is not None:
        lead.tag = update.tag
    db.commit()
    db.refresh(lead)
    return lead_to_dict(lead)


@app.delete("/leads/{lead_id}")
def delete_lead(
    lead_id: int,
    db: orm.Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.user_id == current_user.id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()
    return {"message": "Lead deleted"}


# ─── MESSAGE GENERATION ───────────────────────────────────────────────────────

@app.post("/generate-message")
def generate_message_route(
    req: MessageRequest,
    db: orm.Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lead = db.query(Lead).filter(Lead.id == req.lead_id, Lead.user_id == current_user.id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if req.message_type == "email":
        result = generate_email(lead)
    elif req.message_type == "whatsapp":
        result = generate_whatsapp(lead)
    elif req.message_type == "linkedin":
        result = generate_linkedin(lead)
    else:
        raise HTTPException(status_code=400, detail="Invalid message type. Use: email, whatsapp, linkedin")

    # Save as draft
    msg = Message(
        user_id=current_user.id,
        lead_id=lead.id,
        message_type=req.message_type,
        subject=result.get("subject", ""),
        body=result.get("body", ""),
        status="DRAFT"
    )
    db.add(msg)
    db.commit()

    return result


@app.post("/generate-followup/{lead_id}")
def generate_followup_route(
    lead_id: int,
    day: int = 1,
    db: orm.Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.user_id == current_user.id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return generate_followup(lead, day)


# ─── EMAIL SENDING ────────────────────────────────────────────────────────────

@app.post("/send-email")
def send_email_route(
    req: SendEmailRequest,
    db: orm.Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lead = db.query(Lead).filter(Lead.id == req.lead_id, Lead.user_id == current_user.id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.email:
        raise HTTPException(status_code=400, detail="Lead has no email address")

    result = send_email(lead.email, req.subject, req.body)

    if result["success"]:
        lead.status = "CONTACTED"
        msg = Message(
            user_id=current_user.id,
            lead_id=lead.id,
            message_type="email",
            subject=req.subject,
            body=req.body,
            status="SENT"
        )
        db.add(msg)
        db.commit()

    return result


# ─── SCRAPER ──────────────────────────────────────────────────────────────────

@app.post("/scrape")
def scrape_route(
    req: ScrapeRequest,
    db: orm.Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    results = scrape_leads(req.keyword, req.location, req.limit)
    saved_count = 0
    for r in results:
        lead = Lead(
            user_id=current_user.id,
            business_name=r["business"],
            website=r.get("website", ""),
            industry=req.keyword,
            location=req.location,
            score=30,
            tag="COLD",
            status="NEW"
        )
        db.add(lead)
        saved_count += 1
    db.commit()
    return {"scraped": saved_count, "leads": results}


# ─── MESSAGES HISTORY ─────────────────────────────────────────────────────────

@app.get("/messages/{lead_id}")
def get_messages(
    lead_id: int,
    db: orm.Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    msgs = db.query(Message).filter(
        Message.lead_id == lead_id,
        Message.user_id == current_user.id
    ).order_by(Message.created_at.desc()).all()
    return [
        {
            "id": m.id,
            "type": m.message_type,
            "subject": m.subject,
            "body": m.body,
            "status": m.status,
            "created_at": m.created_at.isoformat() if m.created_at else ""
        }
        for m in msgs
    ]


# ─── CAMPAIGNS ────────────────────────────────────────────────────────────────

@app.get("/campaigns")
def get_campaigns(db: orm.Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    campaigns = db.query(Campaign).filter(Campaign.user_id == current_user.id).all()
    return [
        {
            "id": c.id, "name": c.name, "industry": c.industry,
            "location": c.location, "tone": c.tone, "offer": c.offer,
            "daily_limit": c.daily_limit, "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else ""
        }
        for c in campaigns
    ]


@app.post("/campaigns")
def create_campaign(
    req: CampaignCreate,
    db: orm.Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    campaign = Campaign(
        user_id=current_user.id,
        name=req.name,
        industry=req.industry,
        location=req.location,
        tone=req.tone,
        offer=req.offer,
        daily_limit=req.daily_limit,
        status="ACTIVE"
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return {"id": campaign.id, "name": campaign.name, "status": campaign.status}


# ─── ANALYTICS ────────────────────────────────────────────────────────────────

@app.get("/analytics")
def get_analytics(db: orm.Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    leads = db.query(Lead).filter(Lead.user_id == current_user.id).all()
    total = len(leads)

    by_tag = {"HOT": 0, "WARM": 0, "COLD": 0}
    by_status = {}
    by_industry = {}

    for lead in leads:
        by_tag[lead.tag] = by_tag.get(lead.tag, 0) + 1
        by_status[lead.status] = by_status.get(lead.status, 0) + 1
        if lead.industry:
            by_industry[lead.industry] = by_industry.get(lead.industry, 0) + 1

    messages = db.query(Message).filter(Message.user_id == current_user.id).all()
    sent = len([m for m in messages if m.status == "SENT"])

    return {
        "total_leads": total,
        "hot_leads": by_tag.get("HOT", 0),
        "warm_leads": by_tag.get("WARM", 0),
        "cold_leads": by_tag.get("COLD", 0),
        "by_status": by_status,
        "by_industry": by_industry,
        "total_messages": len(messages),
        "emails_sent": sent,
        "conversion_rate": round((by_status.get("CLOSED", 0) / total * 100) if total > 0 else 0, 1),
        "calls_booked": by_status.get("CALL_BOOKED", 0),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

TRACKID=PS01
# Triage Assistant — Track PS01

A hackathon-ready rule-grounded triage assistant. It accepts a patient's free-text description, evaluates it against the supplied triage rules, asks follow-up questions when the rules do not provide enough information, and escalates high-risk/uncertain cases to human review.

## Features
- Rule-grounded recommendations
- Explicit Rule ID citations
- Follow-up questions for missing information
- Human escalation for high-risk/uncertain cases
- Demo scenarios
- Simple responsive web UI
- Gemini integration with a safe local fallback rule engine

## Run

1. Create a virtual environment:
   `python -m venv .venv`
2. Activate it.
3. Install:
   `pip install -r requirements.txt`
4. Create `.env` from `.env.example` and add your Gemini API key.
5. Run:
   `python app.py`
6. Open:
   `http://localhost:8000`

## Demo
Use the three buttons in the UI:
- Chest Pain
- Abdominal Pain
- Breathing Emergency

## Safety
This is a hackathon prototype, not a medical diagnostic system. It does not diagnose conditions. High-risk or uncertain cases should be escalated to qualified human clinicians/emergency services.

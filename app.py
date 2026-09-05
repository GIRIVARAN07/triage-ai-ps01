import json
import os
import re

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

with open("data/triage_rules.json", "r", encoding="utf-8") as f:
    RULES = json.load(f)

SYSTEM_PROMPT = """
You are a Triage Assistant for a hackathon prototype.

Safety rules:
1. Do NOT diagnose diseases.
2. Use ONLY the supplied triage rules.
3. Cite the Rule ID for every recommendation.
4. If the supplied rules do not support a recommendation, ask focused follow-up questions.
5. If a case appears high-risk or uncertain, recommend human escalation.
6. Never invent a department or urgency not supported by the rules.
7. Return valid JSON with exactly these keys:
   urgency, department, reasoning, rule_id, knowns, unknowns, follow_up_questions, action.
"""

def load_gemini():
    """Create the Gemini model when an API key is configured."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception:
        return None

MODEL = load_gemini()

def fallback_triage(text):
    """Deterministic fallback so the demo still works without an API key."""
    t = text.lower()

    # R04
    breathing = [
        "gasping", "can't breathe", "cannot breathe",
        "barely speak", "short sentences", "short sentence",
        "struggling to breathe", "difficulty breathing"
    ]
    if any(x in t for x in breathing):
        return {
            "urgency": "EMERGENCY",
            "department": "Respiratory",
            "reasoning": "The description indicates gasping or severe breathing difficulty, matching Rule R04.",
            "rule_id": "R04",
            "knowns": extract_knowns(t, ["gasping", "barely speak", "short sentences", "difficulty breathing"]),
            "unknowns": ["Age", "Medical history", "Duration", "Oxygen level"],
            "follow_up_questions": [],
            "action": "Immediate human/emergency medical escalation is recommended."
        }

    # R01
    chest = [
        "crushing chest pain", "crushing pain",
        "left arm", "left jaw", "jaw and arm"
    ]
    if ("chest pain" in t and ("crushing" in t or "left arm" in t or "left jaw" in t)) or \
       ("crushing pain" in t and ("arm" in t or "jaw" in t)):
        return {
            "urgency": "URGENT",
            "department": "Cardiology",
            "reasoning": "The description reports crushing chest pain and/or radiation to the left arm/jaw, matching Rule R01.",
            "rule_id": "R01",
            "knowns": extract_knowns(t, ["crushing chest pain", "chest pain", "left arm", "left jaw"]),
            "unknowns": ["Age", "Medical history", "Current medications", "Other symptoms"],
            "follow_up_questions": [],
            "action": "Escalate for prompt human clinical review."
        }

    # R02
    fever_match = re.search(r"(\d+(?:\.\d+)?)\s*°?\s*f", t)
    high_fever = bool(fever_match and float(fever_match.group(1)) > 103)
    stiff_neck = "stiff neck" in t
    if high_fever or stiff_neck:
        return {
            "urgency": "URGENT",
            "department": "General Medicine",
            "reasoning": "The description meets the high-fever/stiff-neck condition in Rule R02.",
            "rule_id": "R02",
            "knowns": ["High fever above 103°F" if high_fever else "Stiff neck"],
            "unknowns": ["Age", "Duration of fever", "Other symptoms", "Medical history"],
            "follow_up_questions": [],
            "action": "Escalate for prompt human clinical review."
        }

    # R03
    injury_words = ["injury", "twisted", "sprain", "fracture", "fell", "ankle"]
    unable_weight = any(x in t for x in ["cannot put any weight", "can't put any weight", "cannot bear weight", "can't bear weight"])
    deformity = any(x in t for x in ["visible deformity", "deformity", "bone looks"])
    if (any(x in t for x in injury_words) and (unable_weight or deformity)):
        return {
            "urgency": "NON-URGENT",
            "department": "Orthopedics",
            "reasoning": "The injury description indicates inability to bear weight or visible deformity, matching Rule R03.",
            "rule_id": "R03",
            "knowns": ["Injury reported"] + (["Unable to bear weight"] if unable_weight else []) + (["Visible deformity"] if deformity else []),
            "unknowns": ["Pain severity", "Swelling", "Exact mechanism of injury", "Medical history"],
            "follow_up_questions": [],
            "action": "Orthopedic evaluation is recommended according to Rule R03."
        }

    # No matching rule: ask for more information.
    return {
        "urgency": "NEEDS MORE INFORMATION",
        "department": "UNDETERMINED",
        "reasoning": "The supplied rules do not support a specific triage recommendation for this description.",
        "rule_id": "NONE",
        "knowns": [text.strip()],
        "unknowns": [
            "Exact location and severity",
            "Duration and progression",
            "Associated symptoms",
            "Relevant medical history"
        ],
        "follow_up_questions": [
            "Where exactly is the problem?",
            "How severe is it from 0–10?",
            "When did it begin?",
            "Has it become worse?",
            "Are there any other symptoms such as fever, breathing difficulty, vomiting, or injury?"
        ],
        "action": "Do not guess. Collect more information and escalate to a human if symptoms are severe or concerning."
    }

def extract_knowns(text, terms):
    found = []
    for term in terms:
        if term in text:
            found.append(term)
    return found or ["Relevant symptom reported"]

def gemini_triage(text):
    rules_text = json.dumps(RULES, indent=2)
    prompt = (
        SYSTEM_PROMPT
        + "\n\nTRIAGE RULES:\n"
        + rules_text
        + "\n\nPATIENT DESCRIPTION:\n"
        + text
        + "\n\nReturn JSON only."
    )
    try:
        response = MODEL.generate_content(prompt)
        raw = response.text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        required = [
            "urgency", "department", "reasoning", "rule_id",
            "knowns", "unknowns", "follow_up_questions", "action"
        ]
        if not all(k in data for k in required):
            raise ValueError("Missing required JSON fields")
        return data
    except Exception:
        # Safe deterministic fallback if Gemini fails or returns malformed output.
        return fallback_triage(text)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "gemini_configured": MODEL is not None
    })

@app.route("/rules", methods=["GET"])
def rules():
    return jsonify(RULES)

@app.route("/scenarios", methods=["GET"])
def scenarios():
    with open("data/patient_history.json", "r", encoding="utf-8") as f:
        return jsonify(json.load(f))

@app.route("/triage", methods=["POST"])
def triage():
    body = request.get_json(silent=True) or {}
    patient_input = str(body.get("text", "")).strip()

    if not patient_input:
        return jsonify({"error": "Please enter a patient description."}), 400
    if len(patient_input) > 5000:
        return jsonify({"error": "Input is too long. Please keep it under 5000 characters."}), 400

    result = gemini_triage(patient_input)
    return jsonify({
        "patient_input": patient_input,
        "result": result
    })


   
    if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)

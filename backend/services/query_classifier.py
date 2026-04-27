"""
Pre-retrieval query classification.

Classifies user queries into urgency categories BEFORE the expensive
hybrid-search pipeline runs.  Intentionally rule-based (no LLM call)
so it adds <1 ms of latency.

Categories
----------
RED_FLAG  — emergency symptoms that need urgent-care guidance first.
VAGUE     — too little symptom detail to retrieve meaningfully;
            the assistant should ask follow-up questions instead.
MODERATE  — enough symptom information for retrieval + generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QueryUrgency(str, Enum):
    RED_FLAG = "red_flag"
    VAGUE = "vague"
    MODERATE = "moderate"


@dataclass
class QueryClassification:
    urgency: QueryUrgency
    red_flags: list[str] = field(default_factory=list)
    symptom_count: int = 0


# ── red-flag patterns ──
# If ANY of these appear the query is classified as RED_FLAG.

RED_FLAG_PHRASES: list[str] = [
    "chest pain", "chest tightness", "chest pressure",
    "can't breathe", "cannot breathe", "can not breathe",
    "difficulty breathing", "trouble breathing",
    "shortness of breath", "hard to breathe", "struggling to breathe",
    "heart attack", "stroke",
    "fainting", "fainted", "passed out", "lost consciousness", "unconscious",
    "seizure", "convulsion",
    "severe bleeding", "won't stop bleeding",
    "suicidal", "kill myself", "want to die", "self harm", "self-harm",
    "overdose", "poisoning",
    "anaphylaxis", "severe allergic", "throat closing", "throat swelling",
    "can't move", "paralysis", "paralyzed",
    "choking",
    "worst headache", "thunderclap headache",
    "coughing blood", "vomiting blood", "blood in stool",
]

# ── symptom vocabulary ──
# Used to measure how specific a query is.

SYMPTOM_TERMS: list[str] = [
    "headache", "fever", "cough", "nausea", "vomiting",
    "diarrhea", "fatigue", "tired", "dizzy", "dizziness",
    "pain", "ache", "sore", "rash", "itching", "swelling",
    "numbness", "tingling", "weakness", "chills", "sweating",
    "congestion", "runny nose", "sneezing", "wheezing",
    "cramps", "bloating", "constipation", "burning",
    "stiffness", "blurred vision", "loss of appetite",
    "weight loss", "weight gain", "insomnia",
    "palpitations", "tremor", "bleeding", "bruising",
    "joint pain", "muscle pain", "back pain",
    "abdominal pain", "stomach pain", "throat", "earache",
    "hot", "cold", "temperature",
    # informal / colloquial symptom language
    "hurts", "hurt", "hurting",
    "head", "stomach", "belly", "chest", "arm", "leg",
    "throw up", "throwing up",
    "stuffy", "achy", "shaky", "shaking",
    "swollen", "lump", "bump",
    "can't sleep", "can't eat",
    "blood", "pus", "discharge",
]

# ── vague-query patterns ──
# Queries that match these AND have very few symptom terms → VAGUE.

VAGUE_PHRASES: list[str] = [
    "don't feel well", "do not feel well",
    "feel sick", "feeling sick",
    "not feeling good", "not feeling well",
    "something is wrong", "something wrong",
    "feel bad", "feeling bad",
    "feel unwell", "feeling unwell",
    "feel off", "feeling off",
    "feel terrible", "feeling terrible",
    "feel awful", "feeling awful",
    "not okay", "not ok",
    "feel weird", "feeling weird",
    "feel strange", "feeling strange",
    "i'm sick", "i am sick",
    "what's wrong with me", "what is wrong with me",
    "help me", "i need help",
]


def classify_query(query: str) -> QueryClassification:
    """Classify *query* by urgency and symptom specificity."""
    q = query.lower().strip()

    symptom_count = _count_symptoms(q)

    matched_flags = [p for p in RED_FLAG_PHRASES if p in q]
    if matched_flags:
        return QueryClassification(
            urgency=QueryUrgency.RED_FLAG,
            red_flags=matched_flags,
            symptom_count=symptom_count,
        )

    is_vague_phrase = any(p in q for p in VAGUE_PHRASES)
    if is_vague_phrase and symptom_count <= 1:
        return QueryClassification(urgency=QueryUrgency.VAGUE, symptom_count=symptom_count)

    if len(q.split()) <= 5 and symptom_count == 0:
        return QueryClassification(urgency=QueryUrgency.VAGUE, symptom_count=0)

    return QueryClassification(urgency=QueryUrgency.MODERATE, symptom_count=symptom_count)


def _count_symptoms(text: str) -> int:
    return sum(1 for t in SYMPTOM_TERMS if t in text)

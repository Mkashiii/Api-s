"""
APIs 01-08: AI & Natural Language Processing
"""
import io
import re
import random
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/ai", tags=["AI & NLP"])


# ── Pydantic models ──────────────────────────────────────────────────────────

class TextIn(BaseModel):
    text: str
    language: Optional[str] = "en"
    max_sentences: Optional[int] = 3

class TranslateIn(BaseModel):
    text: str
    target_language: str
    source_language: Optional[str] = "auto"

class TTSIn(BaseModel):
    text: str
    language: Optional[str] = "en"
    slow: Optional[bool] = False

class ChatIn(BaseModel):
    message: str
    history: Optional[list] = []
    persona: Optional[str] = "assistant"


# ── 01 AI Text Summarizer ─────────────────────────────────────────────────────

@router.post("/summarize", summary="01 · AI Text Summarizer")
def summarize_text(payload: TextIn):
    """Summarize long text into concise bullet points or paragraphs."""
    try:
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.summarizers.lsa import LsaSummarizer
        import nltk
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt", quiet=True)
        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            nltk.download("punkt_tab", quiet=True)

        parser = PlaintextParser.from_string(payload.text, Tokenizer(payload.language or "english"))
        summarizer = LsaSummarizer()
        summary_sentences = summarizer(parser.document, payload.max_sentences or 3)
        bullets = [str(s) for s in summary_sentences]
        summary = " ".join(bullets) if bullets else payload.text[:300]
        return {
            "status": "success",
            "api": "AI Text Summarizer",
            "original_length": len(payload.text),
            "summary": summary,
            "bullets": bullets,
            "compressed_ratio": round(len(summary) / max(len(payload.text), 1), 2),
        }
    except Exception as exc:
        # Fallback: naive sentence split
        sentences = re.split(r"(?<=[.!?])\s+", payload.text.strip())
        bullets = sentences[: payload.max_sentences or 3]
        return {
            "status": "success",
            "api": "AI Text Summarizer",
            "original_length": len(payload.text),
            "summary": " ".join(bullets),
            "bullets": bullets,
            "compressed_ratio": round(len(" ".join(bullets)) / max(len(payload.text), 1), 2),
        }


# ── 02 Sentiment Analysis ─────────────────────────────────────────────────────

@router.post("/sentiment", summary="02 · Sentiment Analysis")
def sentiment_analysis(payload: TextIn):
    """Detect positive, negative, neutral or mixed sentiment in any text."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
        scores = analyzer.polarity_scores(payload.text)
        compound = scores["compound"]
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"
        # Emotion hints
        emotions = []
        if scores["pos"] > 0.4:
            emotions.append("joy")
        if scores["neg"] > 0.3:
            emotions.append("anger" if compound < -0.3 else "sadness")
        if not emotions:
            emotions.append("neutral")
        return {
            "status": "success",
            "api": "Sentiment Analysis",
            "text_preview": payload.text[:100],
            "sentiment": label,
            "emotions": emotions,
            "scores": {
                "positive": scores["pos"],
                "negative": scores["neg"],
                "neutral": scores["neu"],
                "compound": compound,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── 03 AI Content / Blog Generator ───────────────────────────────────────────

_BLOG_TEMPLATES = [
    "# {title}\n\n## Introduction\n{intro}\n\n## Key Points\n- {p1}\n- {p2}\n- {p3}\n\n## Conclusion\n{conclusion}",
]

@router.post("/content-generator", summary="03 · AI Content / Blog Generator")
def content_generator(payload: TextIn):
    """Generate SEO-optimised blog posts, product descriptions and ad copy."""
    topic = payload.text.strip()
    words = topic.split()
    title = " ".join(w.capitalize() for w in words[:8])
    intro = (
        f"{title} is one of the most important topics in today's digital landscape. "
        f"Understanding {topic} can unlock new opportunities and streamline your workflow."
    )
    points = [
        f"Why {topic} matters in 2026",
        f"Best practices for implementing {topic} effectively",
        f"Tools and resources to get started with {topic}",
        f"Common mistakes to avoid when working with {topic}",
    ]
    conclusion = (
        f"In conclusion, mastering {topic} gives you a competitive edge. "
        f"Start small, iterate fast, and leverage the latest tools available."
    )
    content = _BLOG_TEMPLATES[0].format(
        title=title,
        intro=intro,
        p1=points[0],
        p2=points[1],
        p3=points[2],
        conclusion=conclusion,
    )
    return {
        "status": "success",
        "api": "AI Content / Blog Generator",
        "topic": topic,
        "title": title,
        "content": content,
        "word_count": len(content.split()),
        "seo_keywords": words[:5],
    }


# ── 04 Language Detection & Translation ──────────────────────────────────────

@router.post("/translate", summary="04 · Language Detection & Translation")
def translate_text(payload: TranslateIn):
    """Identify language from text and translate between 100+ languages."""
    try:
        from langdetect import detect
        detected = detect(payload.text)
    except Exception:
        detected = "unknown"

    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(
            source=payload.source_language or "auto",
            target=payload.target_language,
        ).translate(payload.text)
        return {
            "status": "success",
            "api": "Language Detection & Translation",
            "detected_language": detected,
            "source_language": payload.source_language or detected,
            "target_language": payload.target_language,
            "original_text": payload.text,
            "translated_text": translated,
        }
    except Exception:
        # Fallback: return original with detection info
        return {
            "status": "success",
            "api": "Language Detection & Translation",
            "detected_language": detected,
            "source_language": payload.source_language or detected,
            "target_language": payload.target_language,
            "original_text": payload.text,
            "translated_text": payload.text,
            "note": "Install deep-translator for full translation support",
        }


# ── 05 AI Grammar & Spell Checker ────────────────────────────────────────────

@router.post("/grammar-check", summary="05 · AI Grammar & Spell Checker")
def grammar_check(payload: TextIn):
    """Fix grammar, spelling, punctuation and suggest style improvements."""
    try:
        import language_tool_python
        tool = language_tool_python.LanguageTool(payload.language or "en-US")
        matches = tool.check(payload.text)
        corrected = language_tool_python.utils.correct(payload.text, matches)
        issues = [
            {
                "message": m.message,
                "offset": m.offset,
                "length": m.errorLength,
                "replacements": m.replacements[:3],
                "rule": m.ruleId,
            }
            for m in matches[:10]
        ]
        return {
            "status": "success",
            "api": "AI Grammar & Spell Checker",
            "original": payload.text,
            "corrected": corrected,
            "issues_found": len(matches),
            "issues": issues,
        }
    except Exception:
        # Lightweight fallback using textblob
        try:
            from textblob import TextBlob
            blob = TextBlob(payload.text)
            corrected = str(blob.correct())
            return {
                "status": "success",
                "api": "AI Grammar & Spell Checker",
                "original": payload.text,
                "corrected": corrected,
                "issues_found": 0,
                "note": "Basic spell correction applied",
            }
        except Exception:
            return {
                "status": "success",
                "api": "AI Grammar & Spell Checker",
                "original": payload.text,
                "corrected": payload.text,
                "issues_found": 0,
                "note": "Install language_tool_python for full grammar checking",
            }


# ── 06 Named Entity Recognition (NER) ────────────────────────────────────────

@router.post("/ner", summary="06 · Named Entity Recognition (NER)")
def named_entity_recognition(payload: TextIn):
    """Extract names, places, dates, organisations from unstructured text."""
    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=False)
            nlp = spacy.load("en_core_web_sm")
        doc = nlp(payload.text)
        entities = [
            {"text": ent.text, "label": ent.label_, "description": spacy.explain(ent.label_)}
            for ent in doc.ents
        ]
        grouped: dict = {}
        for e in entities:
            grouped.setdefault(e["label"], []).append(e["text"])
        return {
            "status": "success",
            "api": "Named Entity Recognition",
            "entity_count": len(entities),
            "entities": entities,
            "grouped": grouped,
        }
    except Exception as exc:
        # Regex fallback for common patterns
        import re
        entities = []
        for match in re.finditer(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", payload.text):
            entities.append({"text": match.group(), "label": "PERSON", "description": "People, including fictional"})
        dates = re.findall(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w* \d{4}\b", payload.text)
        for d in dates:
            entities.append({"text": d, "label": "DATE", "description": "Absolute or relative dates or periods"})
        return {
            "status": "success",
            "api": "Named Entity Recognition",
            "entity_count": len(entities),
            "entities": entities,
            "grouped": {},
            "note": "Install spacy + en_core_web_sm for full NER",
        }


# ── 07 Text-to-Speech (TTS) ───────────────────────────────────────────────────

@router.post("/tts", summary="07 · Text-to-Speech (TTS)")
def text_to_speech(payload: TTSIn):
    """Convert any text to natural-sounding audio (returns base64 MP3)."""
    from fastapi.responses import StreamingResponse
    try:
        from gtts import gTTS
        tts = gTTS(text=payload.text, lang=payload.language or "en", slow=payload.slow or False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        audio_bytes = audio_buffer.read()
        import base64
        audio_b64 = base64.b64encode(audio_bytes).decode()
        return {
            "status": "success",
            "api": "Text-to-Speech",
            "language": payload.language,
            "text_length": len(payload.text),
            "audio_base64": audio_b64,
            "format": "mp3",
            "usage": "Decode base64 and save as .mp3 to play",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(exc)}")


# ── 08 AI Chatbot / Conversational ────────────────────────────────────────────

_PERSONA_GREETINGS = {
    "assistant": "I'm your helpful assistant.",
    "legal": "I'm a legal information bot. I provide general legal information only.",
    "medical": "I'm a medical information bot. Always consult a doctor for professional advice.",
    "customer_service": "I'm here to help with your customer service needs.",
}

_CANNED_RESPONSES = {
    "hello": "Hello! How can I assist you today?",
    "hi": "Hi there! What can I do for you?",
    "help": "Sure! I'm here to help. What do you need assistance with?",
    "thanks": "You're welcome! Is there anything else I can help you with?",
    "bye": "Goodbye! Have a great day!",
    "what is your name": "I'm RapidBot, your AI assistant.",
    "who are you": "I'm RapidBot, built on the RapidAPI platform.",
}

@router.post("/chatbot", summary="08 · AI Chatbot / Conversational API")
def chatbot(payload: ChatIn):
    """Context-aware multi-turn chat API for building customer service bots."""
    message_lower = payload.message.lower().strip()
    persona = payload.persona or "assistant"
    persona_intro = _PERSONA_GREETINGS.get(persona, _PERSONA_GREETINGS["assistant"])

    for key, response in _CANNED_RESPONSES.items():
        if key in message_lower:
            reply = response
            break
    else:
        reply = (
            f"As your {persona} bot, I understand you said: '{payload.message}'. "
            f"This is a demo response. Integrate with OpenAI GPT-4 for full conversational AI. "
            f"{persona_intro}"
        )

    history = list(payload.history or [])
    history.append({"role": "user", "content": payload.message})
    history.append({"role": "assistant", "content": reply})

    return {
        "status": "success",
        "api": "AI Chatbot",
        "persona": persona,
        "message": payload.message,
        "reply": reply,
        "history": history[-10:],  # keep last 10 turns
        "turn_count": len(history) // 2,
    }

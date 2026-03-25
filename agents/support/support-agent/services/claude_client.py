import json
import os
from typing import Any, Dict, List, Optional

import httpx

from ..logging_config import get_logger

logger = get_logger("services.claude_client")


class ClaudeClient:
    """Client for Claude API."""

    BASE_URL = "https://api.anthropic.com/v1/messages"
    MODEL = "claude-3-sonnet-20240229"
    MAX_TOKENS = 4096
    TEMPERATURE = 0.3

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.Client(
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=30.0,
        )

    def classify_intent_and_risk(
        self,
        ticket_text: str,
        identity: Dict[str, Any],
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Classify intent category and risk flags in a single call."""
        try:
            prompt = f"""
            Classify the following support ticket:
            
            Message: {ticket_text}
            
            Customer Identity: {identity}
            
            Return JSON with two separate classifications:
            
            1. intent_classification:
               - category: technical | billing | general | license
               - confidence: 0-1
               - extracted_keywords: [list of keywords]
               
            2. risk_flags:
               - flags: [billing_dispute, legal_threat, churn_risk, account_issue]
               - risk_level: low | medium | high | critical
               - reason: brief reason
            """

            response = self.client.post(
                self.BASE_URL,
                json={
                    "model": self.MODEL,
                    "max_tokens": self.MAX_TOKENS,
                    "temperature": self.TEMPERATURE,
                    "system": "You are a customer support classifier. Return ONLY valid JSON.",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()

            data = response.json()
            content = data["content"][0]["text"]

            # Parse JSON response
            import json

            result = json.loads(content)

            intent = result.get("intent_classification", {})
            risk = result.get("risk_flags", {})

            return intent, risk

        except httpx.HTTPStatusError as e:
            logger.error(f"Error classifying intent and risk: {e}")
            return {
                "category": "general",
                "confidence": 0.5,
                "extracted_keywords": [],
            }, {"flags": [], "risk_level": "low"}
        except Exception as e:
            logger.error(f"Error in classify_intent_and_risk: {e}")
            return {
                "category": "general",
                "confidence": 0.5,
                "extracted_keywords": [],
            }, {"flags": [], "risk_level": "low"}

    def generate_answer(
        self,
        ticket: Dict[str, Any],
        retrieval_results: List[Dict[str, Any]],
        identity: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate support answer with disclaimer."""
        try:
            # Build retrieval context
            sources = []
            context_text = "Knowledge base results:\n\n"

            for result in retrieval_results[:3]:  # Use top 3 results
                context_text += (
                    f"Source: {result.get('metadata', {}).get('source', 'Unknown')}\n"
                )
                context_text += f"Content: {result.get('text', '')}\n\n"
                sources.append(result.get("metadata", {}).get("source", "Unknown"))

            prompt = f"""
            Generate a helpful answer for this support ticket:
            
            Ticket Message: {ticket.get("message", "")}
            Subject: {ticket.get("subject", "")}
            Customer Identity: {identity}
            
            Knowledge Base Results:
            {context_text}
            
            Requirements:
            1. Use ONLY the knowledge base results above
            2. Be helpful and specific
            3. Use sources from knowledge base
            4. Start with: "هذا رد آلي — إن لم يحل مشكلتك، سيتولى فريقنا الأمر"
            5. Provide 2-3 bullet points
            6. End with: "هل لديك أي استفسار إضافي؟"
            
            Return JSON with:
            - answer: the actual answer text
            - disclaimer: the required disclaimer
            - sources: [list of source identifiers]
            """

            response = self.client.post(
                self.BASE_URL,
                json={
                    "model": self.MODEL,
                    "max_tokens": self.MAX_TOKENS,
                    "temperature": self.TEMPERATURE,
                    "system": "You are a helpful customer support agent. Return ONLY valid JSON.",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()

            data = response.json()
            content = data["content"][0]["text"]

            # Parse JSON response
            import json

            result = json.loads(content)

            answer = result.get("answer", "")
            disclaimer = result.get(
                "disclaimer", "هذا رد آلي — إن لم يحل مشكلتك، سيتولى فريقنا الأمر"
            )
            sources = result.get("sources", [])

            # Add default disclaimer if missing
            if not disclaimer:
                disclaimer = "هذا رد آلي — إن لم يحل مشكلتك، سيتولى فريقنا الأمر"

            return {
                "answer": answer,
                "disclaimer": disclaimer,
                "sources": sources,
                "confidence": 0.85,  # Default confidence
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Error generating answer: {e}")
            return {
                "answer": "شكراً لتواصلك معنا. نحن نحاول المساعدة عبر القاعدة المعرفية، لكن يبدو أننا لم نجد حلولاً مناسبة في الوقت الحالي. يرجى الانتظار بينما يقوم فريق الدعم المعني بالرد عليك.",
                "disclaimer": "هذا رد آلي — إن لم يحل مشكلتك، سيتولى فريقنا الأمر",
                "sources": [],
                "confidence": 0.2,
            }
        except Exception as e:
            logger.error(f"Error in generate_answer: {e}")
            return {
                "answer": "شكراً لتواصلك معنا. يبدو أن هناك مشكلة تقنية في المعالجة الآلية. سيقوم فريق الدعم بالرد عليك قريباً.",
                "disclaimer": "هذا رد آلي — إن لم يحل مشكلتك، سيتولى فريقنا الأمر",
                "sources": [],
                "confidence": 0.1,
            }

    def validate_answer(
        self,
        answer: str,
        retrieval_results: List[Dict[str, Any]],
    ) -> tuple[float, List[str]]:
        """Validate answer and provide confidence score and issues."""
        try:
            prompt = f"""
            Evaluate the following answer based on the knowledge base sources:
            
            Answer: {answer}
            
            Knowledge Base Sources:
            {[r.get("text", "") for r in retrieval_results[:2]]}
            
            Return JSON with:
            - confidence_score: 0-1
            - issues: [list of potential issues or factual discrepancies]
            
            """
            import json

            response = self.client.post(
                self.BASE_URL,
                json={
                    "model": self.MODEL,
                    "max_tokens": 1024,
                    "temperature": 0.2,
                    "system": "You are an answer validator. Return ONLY valid JSON.",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()

            data = response.json()
            content = data["content"][0]["text"]
            result = json.loads(content)

            return result.get("confidence_score", 0.5), result.get("issues", [])

        except Exception as e:
            logger.error(f"Error validating answer: {e}")
            return 0.5, []


    def classify_risk(
        self,
        ticket: Dict[str, Any],
        intent: Dict[str, Any],
        answer: Dict[str, Any],
    ) -> tuple[List[str], str]:
        """Classify escalation risk after a draft answer is prepared."""
        try:
            prompt = f"""
            Assess the support risk of the following ticket and draft answer.

            Ticket: {ticket}
            Intent: {intent}
            Draft Answer: {answer}

            Return JSON with:
            - flags: [billing_dispute, legal_threat, churn_risk, account_issue]
            - risk_level: low | medium | high | critical
            """

            response = self.client.post(
                self.BASE_URL,
                json={
                    "model": self.MODEL,
                    "max_tokens": 1024,
                    "temperature": 0.2,
                    "system": "You are a support risk classifier. Return ONLY valid JSON.",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()

            data = response.json()
            content = data["content"][0]["text"]
            result = json.loads(content)

            flags = result.get("flags", [])
            risk_level = result.get("risk_level", "low")
            if not isinstance(flags, list):
                flags = []
            if risk_level not in {"low", "medium", "high", "critical"}:
                risk_level = "low"

            return flags, risk_level

        except Exception as e:
            logger.error(f"Error classifying risk: {e}")
            return [], "low"


def get_claude_client(api_key: Optional[str] = None) -> ClaudeClient:
    """Get Claude client instance."""
    return ClaudeClient(
        api_key
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("CLAUDE_API_KEY", "")
    )

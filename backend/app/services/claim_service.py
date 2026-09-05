from app.models.claim import Claim
from app.models.analysis import Analysis
from sqlalchemy.orm import Session
from app.models.analysis import VerdictEnum

class ClaimService:
    def extract_claims(self, text: str):
        claims = [
            frase.strip()
            for frase in text.split(".")
            if frase.strip()
        ]

        return claims

    def create_claims(self, db: Session,  analysis: Analysis, claims:list[str]):
        created_claims = []
        for claim_text in claims:
            claim = Claim(
                analysis_id=analysis.id,
                text=claim_text
            )
            db.add(claim)
            created_claims.append(claim)

        db.commit()
        return created_claims

    def calculate_confidence(self, evidences):
        if not evidences:
            return 0.0

        relevances = [evidence.relevance for evidence in evidences]

        total = sum(relevances)
        media = total / len(relevances)
        return media

    def generate_verdict(self, confidence: float):
        if confidence < 0.20:
            return VerdictEnum.FALSA
        elif confidence < 0.40:
            return VerdictEnum.PROVAVELMENTE_FALSA
        elif confidence < 0.70:
            return VerdictEnum.INCONCLUSIVA
        elif confidence < 0.90:
            return VerdictEnum.PROVAVELMENTE_VERDADEIRA
        else:
            return VerdictEnum.VERDADEIRA





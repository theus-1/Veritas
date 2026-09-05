from app.models.claim import Claim
from app.models.analysis import Analysis
from sqlalchemy.orm import Session

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



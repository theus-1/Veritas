from app.core.database import Base, engine
from app.models.analysis import Analysis
from app.models.claim import Claim
from app.models.evidence import Evidence

Base.metadata.create_all(bind=engine)

print("Banco de dados inicializado!")

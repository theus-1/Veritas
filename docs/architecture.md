# Arquitetura atual do Veritas

## Fluxo implementado

1. React envia título, texto e URL opcional ao endpoint POST /analysis/.
2. FastAPI valida entrada e limites de requisição.
3. ClaimService extrai afirmações e enriquece o contexto de busca.
4. SearchService consulta GNews; EvidenceService ordena e limita resultados.
5. AnalysisService interpreta microbatches: Gemini primário → Groq fallback → heurística local nos erros recuperáveis previstos.
6. EvidenceService persiste relações específicas entre fontes e afirmações. AnalysisService calcula vereditos e força das evidências.
7. SQLAlchemy persiste análises, claims e evidências em SQLite.
8. O frontend agrupa artigos na lista geral e mantém as avaliações individuais acessíveis.

## Limites de responsabilidade

O backend controla a classificação. O agrupamento visual não altera dados persistidos, votos ou resposta da API. Uma URL pode apoiar uma afirmação e contradizer outra.

A calibração é aplicada às novas relevâncias persistidas, inclusive vindas de IA. O consenso e a diversidade continuam calculados localmente. Sem evidências direcionais, o resultado permanece inconclusivo.

O cliente OpenAI legado permanece no repositório, mas não participa da cadeia ativa Gemini → Groq → local. Docker, autenticação, histórico navegável e deploy público não são capacidades declaradas deste MVP.

## Validação e privacidade

Os testes isolam configuração e banco antes da importação da aplicação. Chamadas externas são simuladas. O modo validation do Vite desabilita arquivos de ambiente. Logs da Groq contêm status e códigos controlados, sem corpo de erro do provedor.

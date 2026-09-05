# Veritas

Verificação de notícias por afirmação, com fontes consultáveis e explicações de apoio, contradição ou insuficiência de evidências.

**MVP de portfólio validado localmente.** O sistema ajuda a consultar fontes; seus índices são estimativas heurísticas, não probabilidades estatísticas de verdade. **Sem evidência ≠ falso.**

![Fontes agrupadas por artigo](docs/screenshots/fontes.png)

*A demonstração usa dados simulados, não representa uma checagem real.*

## Funcionalidades

- Extração de até 10 afirmações e busca contextualizada via GNews.
- Até 5 evidências por afirmação, ordenadas e deduplicadas.
- Gemini como provedor primário, Groq como fallback e heurística local quando o fallback não está disponível ou retorna resposta inválida.
- Interpretação em microbatches de até 3 afirmações, com validação de índices e citações.
- Vereditos verdadeira, provavelmente verdadeira, inconclusiva, provavelmente falsa e falsa.
- Uma fonte por cartão na lista geral, com contagem de afirmações distintas e avaliações específicas preservadas, inclusive quando discordam.
- Interface responsiva, validação de entrada e mensagens estruturadas de erro.

## Arquitetura

React + TypeScript + Vite → FastAPI → serviços de claims, busca e evidências → SQLAlchemy + SQLite.

A IA interpreta as evidências retornadas pela busca. O veredito e a confiança são calculados pelos serviços locais. Não há mudança de esquema ou de contrato da API neste acabamento.

Veja [arquitetura atual](docs/architecture.md) e [QA final](docs/QA-final.md).

## Executar localmente

Requisitos: Python com suporte às dependências de `backend/requirements.txt` e Node.js 22.18+ para os testes TypeScript. A validação registrada utilizou Python 3.14.6.

Backend, a partir de `backend`:

```powershell
python -m venv venv
./venv/Scripts/python.exe -m pip install -r requirements.txt
# Configure as variáveis de processo antes de iniciar:
$env:APP_NAME = "Veritas"
$env:APP_ENV = "development"
$env:DATABASE_URL = "sqlite:///./veritas.db"
$env:GNEWS_BASE_URL = "https://gnews.io/api/v4"
$env:GNEWS_ENABLED = "false"
$env:GEMINI_ENABLED = "false"
./venv/Scripts/python.exe -m app.init_db
./venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Para consulta real, configure as credenciais de GNews, Gemini e Groq pelo ambiente privado do processo, habilite GNews/Gemini e selecione os modelos disponíveis na conta. Não coloque credenciais no frontend, repositório ou screenshots. Sem busca habilitada, a demonstração local não verifica notícias atuais.

Frontend, em outro terminal a partir de `frontend`:

```powershell
npm ci
npm run dev -- --mode validation
```

Abra `http://localhost:5173`. A interface usa a API em `http://localhost:8000`; a API permite essa origem local. Swagger: `http://localhost:8000/docs`.

## Testes e build sem arquivos de ambiente

```powershell
# Em backend: o conftest desabilita dotenv e usa banco temporário e mocks.
./venv/Scripts/python.exe -m pytest -q --cov=app --cov-report=term

# Em frontend: validation desabilita o carregamento de arquivos de ambiente do Vite.
npm test
npm run build:validation
```

Resultado em 05/09/2026: **214 testes backend, 6 testes frontend, build aprovado e QA de navegador desktop/mobile**. Cobertura backend: **81%**; cliente Groq: **95%**. Dois avisos de depreciação das dependências de teste permanecem documentados.

## Interpretação dos índices

Relevância até 90% é preservada; a faixa acima de 90% é comprimida até 92%, tanto para a avaliação local quanto para a IA. A confiança combina relevância, consenso e diversidade de fontes com retornos decrescentes. Duplicatas do mesmo veículo não somam votos na mesma direção. A ausência de evidências direcionais mantém classificação inconclusiva e confiança nula.

A lista visual agrupa a URL do artigo ignorando fragmentos e parâmetros conhecidos de rastreamento; preserva parâmetros que identificam artigos. Artigos diferentes do mesmo domínio permanecem separados. Avaliações por afirmação não são substituídas por um único veredito da fonte.

## Limitações e próximos passos

- A calibração é conservadora e heurística; requer um conjunto rotulado para validação estatística.
- Nome do veículo é uma aproximação de diversidade: republicações entre veículos podem não ser independentes.
- A busca depende da cobertura das fontes, da atualidade dos resultados e de cotas externas.
- A confiança geral atual é a média dos índices disponíveis; não mede a cobertura de todas as afirmações.
- As mudanças valem para novas análises; registros antigos não são recalculados.
- APIs externas reais não foram chamadas neste QA. Deploy público, autenticação e endurecimento de infraestrutura ficam fora deste fechamento local.

![Interface mobile](docs/screenshots/mobile.png)

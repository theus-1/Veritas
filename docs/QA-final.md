# QA de fechamento — 05/09/2026

## Resultado

- Backend: 214 testes aprovados; cobertura global 81%.
- AnalysisService: 92%; EvidenceService: 82%; GroqClient: 95%.
- Frontend: 6 testes aprovados; TypeScript e build Vite aprovados.
- Edge headless: validação em 1440 × 1000 e 390 × 844, sem erros de execução e sem overflow horizontal no celular.
- Nenhum arquivo de ambiente foi acessado ou alterado. Testes com banco temporário, configuração isolada e provedores simulados.

## Cenários verificados

- Agrupamento de URL com rastreamento/fragmento e contagem de claims distintas.
- Artigos distintos do mesmo domínio e parâmetros de identificação preservados.
- Avaliações de apoio, contradição e neutralidade preservadas por claim.
- Ausência de evidências, conflito equilibrado, relevância baixa e simetria verdadeiro/falso.
- Relevância extrema comprimida; confiança cresce com diversidade sem duplicatas inflacionarem o resultado.
- Gemini primário; Groq inválida permite fallback local.
- Groq: respostas em objeto/array, índices incompletos, citação inventada, schema inválido, autenticação, cota, falha de transporte e retries.
- Entrada e limites da API, persistência e fluxo completo cobertos pela suíte existente.
- Navegador: envio do formulário, abertura do resultado, dedupe geral e por claim, fechamento via Escape e layout responsivo.

## Correções complementares

Removido código duplicado inalcançável do cliente Groq. Logs de erros externos não registram mais mensagem/tipo arbitrários do provedor, evitando dados sensíveis e erro de parsing de corpos inesperados.

## Limitações do QA

Chamadas reais aos provedores não foram executadas; cotas, credenciais e qualidade factual em produção não foram verificadas. Screenshots usam dados simulados. A suíte informa duas depreciações preexistentes de Starlette/httpx e AnyIO, sem falhas. A cobertura global inclui cliente OpenAI legado inativo sem testes.

Consulte o README para repetir testes e build com isolamento dos arquivos de ambiente.

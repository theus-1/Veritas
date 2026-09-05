# Deploy do Veritas

Arquitetura preparada: Vercel (frontend), Render Free (API), Neon Free (PostgreSQL).
Render Free pode suspender a API por inatividade. PostgreSQL gratuito do Render expira em 30 dias; por isso usamos Neon.

## Backend

Importe o repositório no Render como Blueprint usando `render.yaml`.
Configure somente no painel da plataforma:

- `DATABASE_URL`: conexão PostgreSQL do Neon com TLS (`sslmode=require`).
- `CORS_ORIGINS`: URL HTTPS final do frontend, sem caminhos. Separe múltiplas origens por vírgula.
- `GNEWS_API_KEYS`: chaves de notícias separadas por vírgula.
- `GEMINI_API_KEY`, `GEMINI_MODEL`: chave e modelo habilitado na conta.
- `GROQ_API_KEY`: chave Groq; o modelo continua `openai/gpt-oss-20b`.

O Blueprint define `APP_ENV=production`, desativa dotenv e ativa Gemini. A cadeia Gemini → Groq → heurística local não foi alterada.
O comando de inicialização cria as tabelas em um banco vazio e inicia um único worker (rate limiter em memória).
`create_all` não migra tabelas preexistentes. Use banco de produção novo; nenhum histórico SQLite local foi transferido.

## Frontend

Importe o mesmo repositório na Vercel, com Root Directory `frontend`.
Defina `VITE_API_BASE_URL` para a URL HTTPS do Render e faça deploy.
O build de produção não carrega arquivos dotenv. Nunca coloque chaves em variáveis `VITE_*`.
Após obter o domínio definitivo Vercel, configure `CORS_ORIGINS` no Render com esse domínio.

## Verificação final

Verifique `/health`, carregamento do frontend, preflight CORS e uma análise ponta a ponta.
Confirme persistência da análise após reiniciar a API. Esses passos dependem de serviços provisionados e credenciais configuradas.

## Desenvolvimento

SQLite continua suportado no ambiente de desenvolvimento. Para executar sem ler dotenv, defina `VERITAS_DISABLE_DOTENV=1` no processo; forneça as variáveis no ambiente.
Testes backend já desativam dotenv e usam SQLite temporário. Frontend: `npm test` e `npm run build:validation`.

# STACK do projeto

## Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- SQLite inicialmente
- PostgreSQL posteriormente
- Pytest

Responsável por receber requisições, validar dados, auth, chamar serviços, retornar respostas, guardar dados e testes automatizados

## Frontend

- React
- Vite
- TypeScript
- CSS/Tailwind

Responsável pela interface, entrada de notícia, exbição do resultado e histórico

## Inteligência

- API de LLM para análise semântica
- APIs/busca de notícias para encontrar evidências

Responsável pela orquestração da análise, encontrar e organizar evidências e interpretação de informações

## Infra

- Git + GitHub
- Docker
- Render/Vercel no deploy

Responsável por toda parte de infraestrutura base da aplicação.


# Arquitetura Geral
```
                    ┌─────────────────┐
                    │    FRONTEND     │
                    │ React/TypeScript│
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │       API       │
                    │     FastAPI     │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ Analysis │   │ Evidence │   │ History  │
        │ Service  │   │ Service  │   │ Service  │
        └──────────┘   └─────┬────┘   └──────────┘
                             │
                     ┌───────┴────────┐
                     ▼                ▼
                ┌─────────┐      ┌─────────┐
                │ Search  │      │   AI    │
                │  APIs   │      │ Provider│
                └─────────┘      └─────────┘
```

# Fluxo de análise

Abaixo um fluxo de como seria a análise inteligente de conferência de uma notícia.

```
Usuário
   ↓
Envia notícia
   ↓
API recebe
   ↓
Extrai claims
   ↓
Busca evidências
   ↓
Analisa fontes
   ↓
IA interpreta evidências
   ↓
Calcula classificação
   ↓
Salva resultado
   ↓
Retorna para usuário
```

# IA

A IA não será a fonte da verdade e sim um facilitador para entendimento da notícia.

Não é:
```
Notícia
   ↓
ChatGPT
   ↓
"É fake"
```

E sim:
```
Notícia
   ↓
Claims
   ↓
Fontes
   ↓
Evidências
   ↓
IA interpreta
   ↓
Classificação
```

# Dependências Externas

Abaixo algumas API's não listadas, mas que são utilizadas no projeto.

- API de busca de notícias
- API de LLM
- Serviço de busca/web

1. E o que acontece caso a API caia?

Avisa o usuário que o serviço está temporariamente indisponível.

# Processamento

Análise síncrona:

```
POST /analysis
       ↓
espera
       ↓
resultado
```

# Diagrama de estrutura do projeto

```mermaid
flowchart TD
    A[Usuário]-->B[FrontEnd]-->C[FastAPI]-->D[Analysis Service]
    D -- | --> E[Claim Extraction]
    D -- | --> F[Evidence Service]
    D -- | --> G[AI Provider]
    D -- | --> H[(DataBase)]
    F -- | --> I[Search API]

# Veritas

Sistema de verificação de notícias baseado em evidências e fontes externas.

O Veritas recebe uma notícia ou URL e realiza uma análise buscando identificar as principais afirmações presentes no conteúdo, encontrar evidências e apresentar uma classificação baseada nas fontes encontradas.

## 🎯 Objetivo

O projeto tem como objetivo incentivar a verificação de informações e facilitar a consulta de fontes antes de considerar uma notícia como verdadeira ou falsa.

O Veritas não tem como objetivo substituir a pesquisa do usuário, mas apresentar evidências e fontes que auxiliem na análise.

## 🔎 Como funciona

Notícia → Extração das afirmações → Busca por fontes → Coleta de evidências → Análise das evidências → Classificação → Resultado + fontes

## 📊 Classificações

O sistema pode retornar:

- `VERDADEIRA`
- `PROVAVELMENTE_VERDADEIRA`
- `INCONCLUSIVA`
- `PROVAVELMENTE_FALSA`
- `FALSA`

## 🛠️ Tecnologias

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- SQLite
- Pytest

### Frontend

- React
- TypeScript
- Vite

### Integrações

- APIs de busca/notícias
- Provedor de IA para interpretação das evidências

## 🏗️ Arquitetura

O projeto utiliza uma arquitetura separando frontend, API, serviços de análise, evidências e persistência de dados.

A documentação detalhada da arquitetura está disponível em:

`docs/architecture.md`

## 🚧 Status

Projeto em desenvolvimento.

### Sprint atual

Sprint 1 — Definição e arquitetura

- [x] Requisitos
- [x] Arquitetura
- [x] Estrutura inicial do projeto
- [x] Banco de dados
- [ ] Backend API
- [ ] Motor de análise
- [ ] Busca de evidências
- [ ] Interface web
- [ ] Deploy

## 📄 Licença

Este projeto está licenciado sob a licença MIT.

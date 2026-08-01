---
title: MoodScript Backend
emoji: 🧠
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# MoodScript Backend

FastAPI backend for MoodScript — text + face emotion analysis, fused emotion detection,
persistent per-user auth, and an LLM-driven therapist companion ("Aria") that remembers
patterns across conversations.

## Endpoints

- `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` — account auth (JWT bearer tokens).
- `POST /chat` — send `{ message, image_base64?, conversation_id? }` (auth required). Returns
  emotion analysis, Aria's reply, crisis info, and an updated overall rating.
- `GET /conversations`, `GET /conversations/{id}/messages` — past conversations.
- `GET /history`, `GET /rating`, `GET /reflection` — mood log, wellbeing score, weekly reflection.
- `GET /export` — download your full journal as text.
- `DELETE /account` — delete your account and all associated data.
- `GET /health` — health check.

## Required secrets

Set these in this Space's settings (Settings → Repository secrets):

- `GROQ_API_KEY` — Groq API key for the LLM.
- `JWT_SECRET` — signing secret for auth tokens (any long random string; must stay stable
  across restarts or existing sessions are invalidated).
- `DATABASE_URL` — Postgres connection string (Neon). Storage is persistent — data survives
  Space restarts/rebuilds.

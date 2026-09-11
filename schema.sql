-- Referência: este arquivo NÃO é executado pelo app.
-- Rode manualmente no SQL Editor do Neon (já foi executado no provisionamento).
CREATE TABLE IF NOT EXISTS tarefas (
  id     SERIAL PRIMARY KEY,
  titulo TEXT NOT NULL,
  feita  BOOLEAN NOT NULL DEFAULT FALSE
);

# webapp-aula123

API de Tarefas com FastAPI + Neon Postgres, deploy contínuo via GitHub Actions → Vercel (Docker via `Dockerfile.vercel`).

---

## Equivalência Azure → Vercel

| Azure | Vercel / Neon |
|---|---|
| Resource Group | Conta pessoal Hobby (não criar team) |
| PostgreSQL Flexible Server | Neon via Vercel Marketplace |
| Networking → Add client IP | Não existe — acesso por TLS + credencial |
| Database `appdb` | Igual (`appdb` no Neon) |
| Container Registry | Não existe — build direto do repositório Git |
| App Service + Docker | Vercel Function (runtime Python serverless) |
| `WEBSITES_PORT` | Não existe — variável equivalente a configurar é `DATABASE_URL` |
| Service Principal + `AZURE_CREDENTIALS` | `VERCEL_TOKEN` + `VERCEL_ORG_ID` + `VERCEL_PROJECT_ID` |

---

## Criar o projeto webapp-aula123

1. Criar o repositório GitHub `webapp-aula123` (público ou privado) e dar push desta pasta para a branch `main`:
   ```bash
   git init
   git add .
   git commit -m "chore: initial commit"
   git branch -M main
   git remote add origin https://github.com/<seu-usuario>/webapp-aula123.git
   git push -u origin main
   ```

2. Na Vercel: **Add New → Project** → selecionar o repositório `webapp-aula123` → **Import**.

3. Framework Preset: deixar o detectado automaticamente (Python/FastAPI). Não configurar Build Command nem Output Directory.

4. Clicar em **Deploy** — o primeiro deploy pode falhar por falta de `DATABASE_URL`. É normal nesse ponto.

5. Ir em **Storage** → abrir a integração Neon `postgres-aula123` → **Connect to Project** → selecionar `webapp-aula123` → marcar os três ambientes (Production, Preview, Development) → confirmar prefixo `DATABASE` (isso gera `DATABASE_URL`).

6. Em **Settings → Environment Variables**, confirmar que `DATABASE_URL` aponta para o database `appdb` (não `neondb`) nos três ambientes. Editar a URL se necessário:
   ```
   postgresql://usuario:senha@ep-xxxx-pooler.us-east-1.aws.neon.tech/appdb?sslmode=require
   ```

7. **Deployments → ⋯ → Redeploy** para aplicar a variável de ambiente.

---

## Configurar o GitHub Actions

1. Gerar token em `vercel.com/account/settings/tokens` (scope: Full Account).

2. Rodar localmente para obter os IDs do projeto:
   ```bash
   npm i -g vercel
   vercel login
   vercel link --yes   # selecionar webapp-aula123 quando perguntado
   cat .vercel/project.json
   ```
   O JSON retorna `orgId` e `projectId`.

3. Cadastrar em **Settings → Secrets and variables → Actions** do repositório GitHub:
   - `VERCEL_TOKEN`
   - `VERCEL_ORG_ID` (valor de `orgId`)
   - `VERCEL_PROJECT_ID` (valor de `projectId`)

4. Commitar `.github/workflows/deploy.yml` e `vercel.json` (já estão no repositório).

---

## Testar

1. Fazer qualquer alteração (ex: mudar o `<h1>` da página), commit, push na `main`:
   ```bash
   git add .
   git commit -m "test: primeiro deploy via Actions"
   git push
   ```

2. Conferir a aba **Actions** do repositório no GitHub — o workflow deve ficar verde.

3. Abrir `https://webapp-aula123.vercel.app`.

4. Validar os endpoints:
   - `https://webapp-aula123.vercel.app/api/health` → `{"status":"ok","postgres":"..."}`
   - `https://webapp-aula123.vercel.app/docs` → Swagger UI

---

## Rodar localmente

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Editar .env com a DATABASE_URL real do Neon (connection string pooled, database appdb)

uvicorn api.index:app --reload
```

Abrir `http://localhost:8000`.

---

## Armadilhas

- **Cold start do Neon**: o banco tem scale-to-zero. A primeira request após inatividade demora ~1–3 s enquanto o servidor acorda.
- **Redeploy obrigatório após variável de ambiente**: alterar `DATABASE_URL` na Vercel não se propaga automaticamente ao deployment ativo — é necessário fazer redeploy.
- **Deploy duplicado**: sem `"deploymentEnabled": {"main": false}` no `vercel.json`, a Vercel dispara seu próprio deploy além do GitHub Actions, gerando dois deploys por push.
- **`.vercel` no `.gitignore`**: a pasta `.vercel/` contém IDs locais do projeto e não deve ser commitada.
- **Esgotamento de conexões**: usar a connection string sem `-pooler` no host abre conexões diretas ao Postgres, que têm limite baixo no plano gratuito do Neon. Sempre usar a string pooled.
- **Database `neondb` vs `appdb`**: o Neon cria o database `neondb` por padrão. O `appdb` precisa ser criado manualmente no SQL Editor do Neon, e a `DATABASE_URL` gerada pela integração Vercel precisa ser editada para apontar para `appdb`.

---

## Deploy via Docker

A partir de junho de 2026, a Vercel suporta `Dockerfile.vercel` nativamente: ela builda a imagem, armazena no Vercel Container Registry e roda em Fluid compute. O projeto `webapp-aula123` migrou para esse modo — **mesmo projeto, mesma URL, mesmo banco** — só o modo de build mudou.

**Por que migrar**: runtime Python nativo da Vercel tem limitações de dependências nativas (como `psycopg[binary]`). Docker resolve isso e dá controle total do ambiente.

**Testar localmente antes do push:**

```bash
# build
docker build -f Dockerfile.vercel -t webapp-aula123 .

# rodar (substituir <url> pela DATABASE_URL real do Neon)
docker run -e DATABASE_URL="<url>" -e PORT=8080 -p 8080:8080 webapp-aula123
```

Abrir `http://localhost:8080/api/health` para confirmar.

**Notas importantes:**
- `PORT` é injetada automaticamente pela Vercel em produção — não fixar valor no código nem no `CMD` do Dockerfile.
- A `DATABASE_URL` continua injetada pela integração Neon, sem nenhuma mudança de configuração no projeto Vercel.
- O workflow do GitHub Actions (`deploy.yml`) detecta o `Dockerfile.vercel` automaticamente — nenhuma flag adicional é necessária nos comandos `vercel build` / `vercel deploy`.

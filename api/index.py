import os

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator

app = FastAPI(title="Tarefas API")


def _db_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL não configurada")
    return url


def _connect():
    return psycopg.connect(_db_url(), connect_timeout=10)


HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Tarefas</title>
  <style>
    body { font-family: sans-serif; max-width: 600px; margin: 2rem auto; padding: 0 1rem; }
    h1 { margin-bottom: 1rem; }
    #form { display: flex; gap: .5rem; }
    #form input { flex: 1; padding: .4rem .6rem; font-size: 1rem; }
    button { padding: .4rem .8rem; cursor: pointer; font-size: 1rem; }
    ul { list-style: none; padding: 0; margin-top: 1rem; }
    li { display: flex; align-items: center; gap: .5rem; padding: .35rem 0;
         border-bottom: 1px solid #eee; }
    li.feita span { text-decoration: line-through; color: #999; }
    li span { flex: 1; }
    #erro { color: #c00; min-height: 1.2rem; margin: .4rem 0; }
  </style>
</head>
<body>
  <h1>Lista de Tarefas!</h1>
  <div id="form">
    <input id="novo" type="text" placeholder="Nova tarefa…" />
    <button onclick="criar()">Adicionar</button>
  </div>
  <p id="erro"></p>
  <ul id="lista"></ul>
  <script>
    const $erro = document.getElementById('erro');
    const $lista = document.getElementById('lista');

    async function carregar() {
      const tarefas = await fetch('/api/tarefas').then(r => r.json());
      $lista.innerHTML = '';
      tarefas.forEach(t => {
        const li = document.createElement('li');
        li.className = t.feita ? 'feita' : '';
        li.innerHTML =
          `<input type="checkbox" ${t.feita ? 'checked' : ''} onchange="toggle(${t.id})">` +
          `<span>${t.titulo}</span>` +
          `<button onclick="remover(${t.id})">✕</button>`;
        $lista.appendChild(li);
      });
    }

    async function criar() {
      const input = document.getElementById('novo');
      const titulo = input.value.trim();
      $erro.textContent = '';
      if (!titulo) { $erro.textContent = 'Título não pode ser vazio.'; return; }
      const res = await fetch('/api/tarefas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ titulo }),
      });
      if (!res.ok) {
        const d = await res.json();
        $erro.textContent = d.detail || 'Erro ao criar tarefa.';
        return;
      }
      input.value = '';
      carregar();
    }

    async function toggle(id) {
      await fetch('/api/tarefas/' + id, { method: 'PATCH' });
      carregar();
    }

    async function remover(id) {
      await fetch('/api/tarefas/' + id, { method: 'DELETE' });
      carregar();
    }

    carregar();
  </script>
</body>
</html>"""


class TarefaIn(BaseModel):
    titulo: str

    @field_validator("titulo")
    @classmethod
    def nao_vazio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("título não pode ser vazio ou só espaços")
        return v.strip()


@app.get("/", response_class=HTMLResponse)
def pagina():
    return HTML


@app.get("/api/health")
def health():
    try:
        with _connect() as conn:
            row = conn.execute("SELECT version()").fetchone()
        return {"status": "ok", "postgres": row[0]}
    except Exception:
        raise HTTPException(status_code=503, detail="Banco indisponível")


@app.get("/api/tarefas")
def listar():
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, titulo, feita FROM tarefas ORDER BY id DESC"
        ).fetchall()
    return [{"id": r[0], "titulo": r[1], "feita": r[2]} for r in rows]


@app.post("/api/tarefas", status_code=201)
def criar(tarefa: TarefaIn):
    with _connect() as conn:
        row = conn.execute(
            "INSERT INTO tarefas (titulo) VALUES (%s) RETURNING id, titulo, feita",
            (tarefa.titulo,),
        ).fetchone()
    return {"id": row[0], "titulo": row[1], "feita": row[2]}


@app.patch("/api/tarefas/{tarefa_id}")
def toggle(tarefa_id: int):
    with _connect() as conn:
        row = conn.execute(
            "UPDATE tarefas SET feita = NOT feita WHERE id = %s RETURNING id, titulo, feita",
            (tarefa_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Tarefa {tarefa_id} não encontrada")
    return {"id": row[0], "titulo": row[1], "feita": row[2]}


@app.delete("/api/tarefas/{tarefa_id}", status_code=204)
def remover(tarefa_id: int):
    with _connect() as conn:
        row = conn.execute(
            "DELETE FROM tarefas WHERE id = %s RETURNING id",
            (tarefa_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Tarefa {tarefa_id} não encontrada")

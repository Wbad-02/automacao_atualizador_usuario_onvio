"""
Gestta Automation v1.2 — API Server
Expoe endpoints REST para o dashboard web.

Endpoints:
  GET  /status                  - stats de todas as listas em execucao
  GET  /logs/{lista_index}      - stream SSE de logs da lista
  GET  /logs/{lista_index}/poll - polling de logs (fallback SSE)
  POST /emails/add              - adiciona email na lista com menos entradas

Uso:
  uvicorn src.api_server:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# APP
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Gestta Automation API",
    version="1.2.0",
    description="Dashboard API para monitoramento de automacoes Gestta",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # dev — restringir em producao
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
BASE_DIR   = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
LOGS_DIR   = BASE_DIR / "logs"

# ---------------------------------------------------------------------------
# IN-MEMORY STATE  (substituir por integracao real com automation_executor)
# ---------------------------------------------------------------------------
# Formato de cada lista:
#   {
#     "index":   int,
#     "name":    str,
#     "emails":  list[str],        # emails atribuidos
#     "status":  dict[str, str],   # email -> "success" | "failed" | "running"
#     "log_file": Path | None,
#   }

_state_lock = Lock()
_lists: list[dict[str, Any]] = []
_log_buffers: dict[int, list[str]] = {}  # listIndex -> linhas em memoria


def _load_initial_state() -> None:
    """
    Carrega estado inicial a partir dos arquivos de configuracao e logs.
    Em producao, este estado deve ser alimentado pelo automation_executor.
    """
    global _lists, _log_buffers

    # Descobre arquivos de emails (emails_list.txt, emails_list_2.txt, etc.)
    email_files = sorted(CONFIG_DIR.glob("emails_list*.txt"))
    if not email_files:
        # Fallback: cria lista demo para a UI nao ficar vazia
        email_files = []

    with _state_lock:
        _lists = []
        _log_buffers = {}

        for idx, ef in enumerate(email_files):
            emails = _read_email_file(ef)
            _lists.append({
                "index":    idx,
                "name":     ef.stem.replace("_", " ").title(),
                "emails":   emails,
                "status":   {},         # preenchido em tempo de execucao
                "log_file": None,       # sera ligado ao executor externo
            })
            _log_buffers[idx] = []

        # Se nenhum arquivo encontrado, cria lista padrao
        if not _lists:
            _lists.append({
                "index":    0,
                "name":     "Lista Principal",
                "emails":   [],
                "status":   {},
                "log_file": None,
            })
            _log_buffers[0] = []

        # Carrega logs do dia atual em memoria
        today = datetime.now().strftime("%Y%m%d")
        log_file = LOGS_DIR / f"automation_{today}.log"
        if log_file.exists():
            lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
            # Distribui linhas no buffer da lista 0 (sem separacao real por lista)
            _log_buffers[0] = lines[-500:]  # ultimas 500 linhas


def _read_email_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    emails = []
    for line in text.splitlines():
        line = line.strip()
        if line and "@" in line and not line.startswith("#"):
            emails.append(line)
    return emails


def _write_email_file(list_index: int, email: str) -> None:
    """Persiste email no arquivo de configuracao da lista correspondente."""
    email_files = sorted(CONFIG_DIR.glob("emails_list*.txt"))

    if list_index < len(email_files):
        target = email_files[list_index]
    elif email_files:
        target = email_files[0]
    else:
        # Cria arquivo se nao existir
        CONFIG_DIR.mkdir(exist_ok=True)
        target = CONFIG_DIR / "emails_list.txt"

    with open(target, "a", encoding="utf-8") as f:
        f.write(f"\n{email}")


# Carrega ao iniciar
_load_initial_state()

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _aggregate_stats(lst: dict) -> dict:
    statuses = lst["status"]
    success  = sum(1 for s in statuses.values() if s == "success")
    failed   = sum(1 for s in statuses.values() if s == "failed")
    running  = sum(1 for s in statuses.values() if s == "running")
    total    = len(lst["emails"])
    return {
        "index":   lst["index"],
        "name":    lst["name"],
        "total":   total,
        "success": success,
        "failed":  failed,
        "running": running,
    }


def _all_emails_flat() -> list[dict]:
    """Retorna todos os emails de todas as listas com seu status."""
    result = []
    with _state_lock:
        for lst in _lists:
            for email in lst["emails"]:
                result.append({
                    "email":      email,
                    "status":     lst["status"].get(email, "running"),
                    "list_index": lst["index"],
                })
    return result


# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def serve_dashboard():
    """Serve o dashboard.html na raiz."""
    html_file = BASE_DIR / "dashboard.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="dashboard.html não encontrado")
    return FileResponse(html_file, media_type="text/html")


@app.get("/status", summary="Stats de todas as listas")
async def get_status() -> dict:
    """
    Retorna estatisticas de todas as listas em execucao.

    Response:
      {
        "lists": [
          {
            "index": 0,
            "name": "Lista Principal",
            "total": 120,
            "success": 80,
            "failed": 5,
            "running": 35
          }
        ],
        "emails": [
          { "email": "...", "status": "success|failed|running", "list_index": 0 }
        ]
      }
    """
    with _state_lock:
        lists_stats = [_aggregate_stats(lst) for lst in _lists]

    return {
        "lists":  lists_stats,
        "emails": _all_emails_flat(),
    }


@app.get("/logs/{lista_index}", summary="SSE stream de logs de uma lista")
async def get_logs_sse(lista_index: int):
    """
    Abre um stream SSE (Server-Sent Events) com os logs em tempo real
    de uma lista especifica.

    O cliente recebe eventos no formato:
      data: <linha de log>\\n\\n

    Fallback: se SSE nao for suportado, use GET /logs/{lista_index}/poll
    """
    with _state_lock:
        exists = any(lst["index"] == lista_index for lst in _lists)

    if not exists:
        raise HTTPException(status_code=404, detail=f"Lista {lista_index} nao encontrada")

    async def event_generator():
        # 1. Envia buffer atual (historico)
        with _state_lock:
            history = list(_log_buffers.get(lista_index, []))

        for line in history:
            yield f"data: {line}\n\n"

        # 2. Monitora arquivo de log do dia em busca de novas linhas
        today = datetime.now().strftime("%Y%m%d")
        log_file = LOGS_DIR / f"automation_{today}.log"
        last_size = log_file.stat().st_size if log_file.exists() else 0
        last_pos = last_size  # começa do final (apenas novas linhas)

        while True:
            await asyncio.sleep(0.8)
            try:
                if not log_file.exists():
                    continue
                current_size = log_file.stat().st_size
                if current_size > last_pos:
                    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(last_pos)
                        new_content = f.read()
                    last_pos = current_size
                    for line in new_content.splitlines():
                        if line.strip():
                            with _state_lock:
                                _log_buffers.setdefault(lista_index, []).append(line)
                            yield f"data: {line}\n\n"
            except OSError:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/logs/{lista_index}/poll", summary="Polling de logs (fallback SSE)")
async def get_logs_poll(lista_index: int, offset: int = 0) -> dict:
    """
    Retorna linhas de log a partir do offset informado.
    Usar quando SSE nao estiver disponivel.

    Query params:
      offset  (int): indice da ultima linha ja recebida (default: 0)

    Response:
      { "lines": ["linha1", "linha2", ...], "total": 120 }
    """
    with _state_lock:
        exists = any(lst["index"] == lista_index for lst in _lists)
        buffer = list(_log_buffers.get(lista_index, []))

    if not exists:
        raise HTTPException(status_code=404, detail=f"Lista {lista_index} nao encontrada")

    # Atualiza buffer a partir do arquivo de hoje
    today = datetime.now().strftime("%Y%m%d")
    log_file = LOGS_DIR / f"automation_{today}.log"
    if log_file.exists():
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        with _state_lock:
            _log_buffers[lista_index] = lines
        buffer = lines

    new_lines = buffer[offset:]
    return {"lines": new_lines, "total": len(buffer)}


class AddEmailRequest(BaseModel):
    email: str


@app.post("/emails/add", summary="Adiciona email na lista com menos entradas")
async def add_email(body: AddEmailRequest) -> dict:
    """
    Adiciona o email informado na lista com menos emails.
    Em caso de empate, adiciona na primeira lista (menor indice).

    Body:
      { "email": "usuario@dominio.com" }

    Response:
      { "ok": true, "list_index": 0, "message": "..." }
    """
    email = body.email.strip().lower()

    # Validacao basica
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=422, detail="Email invalido")

    with _state_lock:
        if not _lists:
            raise HTTPException(status_code=503, detail="Nenhuma lista disponivel")

        # Encontra lista com menos emails (empate = menor indice)
        target = min(_lists, key=lambda lst: len(lst["emails"]))
        target_index = target["index"]

        # Evita duplicata na mesma lista
        if email in target["emails"]:
            return {
                "ok":         False,
                "list_index": target_index,
                "message":    f"Email ja existe na Lista {target_index + 1}",
            }

        target["emails"].append(email)
        target["status"][email] = "running"

    # Persiste em disco (fora do lock para nao bloquear)
    try:
        _write_email_file(target_index, email)
    except OSError as exc:
        # Nao falha a requisicao, apenas loga
        print(f"[WARN] Nao foi possivel persistir email em disco: {exc}")

    return {
        "ok":         True,
        "list_index": target_index,
        "message":    f"Adicionado na Lista {target_index + 1}",
    }


# ---------------------------------------------------------------------------
# HOOKS DE INTEGRACAO (chamados pelo automation_executor em tempo de execucao)
# ---------------------------------------------------------------------------

def update_email_status(list_index: int, email: str, status: str) -> None:
    """
    Hook para o automation_executor atualizar o status de cada email.
    status: "success" | "failed" | "running"
    Chamar via importacao: from src.api_server import update_email_status
    """
    with _state_lock:
        for lst in _lists:
            if lst["index"] == list_index:
                lst["status"][email] = status
                break


def append_log_line(list_index: int, line: str) -> None:
    """
    Hook para o automation_executor injetar linhas de log em tempo real.
    Chamar via importacao: from src.api_server import append_log_line
    """
    with _state_lock:
        _log_buffers.setdefault(list_index, []).append(line)
        # Mantém limite de 2000 linhas por lista em memoria
        if len(_log_buffers[list_index]) > 2000:
            _log_buffers[list_index] = _log_buffers[list_index][-2000:]


# ---------------------------------------------------------------------------
# ENTRY POINT (dev)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api_server:app", host="0.0.0.0", port=59871, reload=True)

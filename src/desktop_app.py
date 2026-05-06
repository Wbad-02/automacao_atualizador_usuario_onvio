"""
Gestta Automation v1.2 — Interface Desktop
"""

import asyncio
import logging
import queue
import re
import sys
import threading
from pathlib import Path

import customtkinter as ctk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

_BG       = "#0f2218"
_BG2      = "#162e21"
_BG3      = "#1e4030"
_GOLD     = "#C9A84C"
_GOLD_H   = "#dfc472"
_GOLD_DIM = "#5a4a20"
_WHITE    = "#FFFFFF"
_GRAY     = "#7a9488"
_RED      = "#dc2626"
_GREEN_OK = "#16a34a"

BASE_DIR   = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"


# ---------------------------------------------------------------------------
# Helpers de arquivo
# ---------------------------------------------------------------------------

def _list_email_files() -> list[Path]:
    files = sorted(CONFIG_DIR.glob("emails_list*.txt"))
    if not files:
        CONFIG_DIR.mkdir(exist_ok=True)
        default = CONFIG_DIR / "emails_list.txt"
        default.touch()
        files = [default]
    return files


def _count_emails(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(
        1 for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def _append_email_to_file(path: Path, email: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n{email}")


# ---------------------------------------------------------------------------
# Log handler — intercepta logs da automação e roteia para a fila de UI
# ---------------------------------------------------------------------------

class _QueueLogHandler(logging.Handler):
    def __init__(self, q: queue.Queue):
        super().__init__()
        self._q = q
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record):
        try:
            msg = self.format(record)
            m = re.search(r'\[Lista (\d+)', msg)
            list_idx = (int(m.group(1)) - 1) if m else 0
            self._q.put(("log", list_idx, {"line": msg}))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# TerminalCard — painel de log + indicadores por lista
# ---------------------------------------------------------------------------

class TerminalCard(ctk.CTkFrame):
    def __init__(self, parent, list_index: int, list_name: str, **kwargs):
        super().__init__(
            parent,
            fg_color=_BG2,
            corner_radius=8,
            border_width=1,
            border_color=_BG3,
            **kwargs,
        )
        self.list_index = list_index
        self.list_name  = list_name
        self._email_rows: dict[str, ctk.CTkLabel] = {}
        self._total = self._success = self._failed = 0
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        # Cabeçalho do card
        hdr = ctk.CTkFrame(self, fg_color=_BG3, corner_radius=0, height=36)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)
        hdr.grid_propagate(False)

        ctk.CTkLabel(
            hdr,
            text=f"  {self.list_name}",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=_GOLD,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=8)

        self.stats_label = ctk.CTkLabel(
            hdr,
            text="0/0 | 0 ok | 0 falhas",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=_GRAY,
            anchor="e",
        )
        self.stats_label.grid(row=0, column=1, padx=12)

        # Terminal de log
        self.log_box = ctk.CTkTextbox(
            self,
            height=160,
            fg_color="#0a1a10",
            text_color="#a8c5b0",
            font=ctk.CTkFont(family="Cascadia Code", size=10),
            corner_radius=0,
            border_width=0,
            state="disabled",
            wrap="word",
        )
        self.log_box.grid(row=1, column=0, sticky="ew")

        # Grade de emails (scrollable)
        self.email_frame = ctk.CTkScrollableFrame(
            self,
            height=130,
            fg_color=_BG2,
            corner_radius=0,
            border_width=0,
        )
        self.email_frame.grid(row=2, column=0, sticky="ew", padx=4, pady=(4, 8))
        self.email_frame.grid_columnconfigure(0, weight=1)

    def append_log(self, line: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def set_email_status(self, email: str, status: str) -> None:
        """status: 'running' | 'success' | 'failed'"""
        if status == "running":
            self._total += 1

        if email not in self._email_rows:
            row_idx = len(self._email_rows)
            lbl = ctk.CTkLabel(
                self.email_frame,
                text="",
                font=ctk.CTkFont(family="Consolas", size=10),
                anchor="w",
            )
            lbl.grid(row=row_idx, column=0, sticky="ew", padx=4, pady=1)
            self._email_rows[email] = lbl

        lbl = self._email_rows[email]

        if status == "success":
            self._success += 1
            lbl.configure(text=f"  {email}", text_color=_GREEN_OK)
        elif status == "failed":
            self._failed += 1
            lbl.configure(text=f"  {email}", text_color=_RED)
        else:
            lbl.configure(text=f"  {email}", text_color=_GOLD)

        processed = self._success + self._failed
        self.stats_label.configure(
            text=f"{processed}/{self._total} | {self._success} ok | {self._failed} falhas"
        )


# ---------------------------------------------------------------------------
# Modal — Adicionar Email
# ---------------------------------------------------------------------------

class AddEmailModal(ctk.CTkToplevel):
    def __init__(self, parent, on_confirm):
        super().__init__(parent)
        self.title("Adicionar Email")
        self.geometry("400x200")
        self.resizable(False, False)
        self.configure(fg_color=_BG2)
        self.grab_set()
        self._on_confirm = on_confirm
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Novo Email",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=_GOLD,
        ).grid(row=0, column=0, pady=(20, 4))

        self.entry = ctk.CTkEntry(
            self,
            placeholder_text="usuario@exemplo.com",
            width=340,
            height=38,
            fg_color=_BG3,
            text_color=_WHITE,
            border_color=_GOLD_DIM,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.entry.grid(row=1, column=0, padx=20, pady=8)
        self.entry.bind("<Return>", lambda _: self._confirm())
        self.entry.focus()

        self.feedback = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=_GRAY,
        )
        self.feedback.grid(row=2, column=0)

        ctk.CTkButton(
            self,
            text="Adicionar",
            width=160,
            height=36,
            fg_color=_GOLD,
            hover_color=_GOLD_H,
            text_color=_BG,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            corner_radius=6,
            command=self._confirm,
        ).grid(row=3, column=0, pady=12)

    def _confirm(self):
        email = self.entry.get().strip().lower()
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            self.feedback.configure(text="Email inválido", text_color=_RED)
            return
        self._on_confirm(email, self)


# ---------------------------------------------------------------------------
# Janela principal
# ---------------------------------------------------------------------------

class GesttaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gestta Automation v1.2")
        self.geometry("960x720")
        self.minsize(720, 520)
        self.configure(fg_color=_BG)

        self._queue: queue.Queue = queue.Queue()
        self._running   = False
        self._cards: list[TerminalCard] = []
        self._log_handler: _QueueLogHandler | None = None

        self._email_files = _list_email_files()
        self._build_ui()
        self._poll_queue()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, fg_color=_BG2, corner_radius=0, height=64)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)

        # Marca
        brand = ctk.CTkFrame(hdr, fg_color="transparent")
        brand.grid(row=0, column=0, padx=20, sticky="w")

        ctk.CTkLabel(
            brand,
            text="G",
            width=36, height=36,
            fg_color=_GOLD,
            text_color=_BG,
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            corner_radius=6,
        ).grid(row=0, column=0, padx=(0, 10))

        ctk.CTkLabel(
            brand,
            text="GESTTA AUTOMATION",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=_WHITE,
        ).grid(row=0, column=1)

        ctk.CTkLabel(
            brand,
            text="v1.2",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=_GRAY,
        ).grid(row=0, column=2, padx=(6, 0))

        # Botões
        btns = ctk.CTkFrame(hdr, fg_color="transparent")
        btns.grid(row=0, column=2, padx=20, sticky="e")

        ctk.CTkButton(
            btns,
            text="+ Email",
            width=100, height=34,
            fg_color=_BG3,
            hover_color=_GOLD_DIM,
            text_color=_GOLD,
            border_color=_GOLD_DIM,
            border_width=1,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            corner_radius=6,
            command=self._open_add_email,
        ).grid(row=0, column=0, padx=(0, 10))

        self.start_btn = ctk.CTkButton(
            btns,
            text="▶  Iniciar",
            width=120, height=34,
            fg_color=_GOLD,
            hover_color=_GOLD_H,
            text_color=_BG,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            corner_radius=6,
            command=self._start_automation,
        )
        self.start_btn.grid(row=0, column=1)

        # Separador
        ctk.CTkFrame(self, fg_color=_GOLD_DIM, height=1, corner_radius=0).grid(
            row=1, column=0, sticky="ew"
        )

        # Área scrollable de terminais
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=_BG, corner_radius=0)
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=16)
        self._scroll.grid_columnconfigure(0, weight=1)

        self._build_terminals()

        # Rodapé
        ctk.CTkFrame(self, fg_color=_GOLD_DIM, height=1, corner_radius=0).grid(
            row=3, column=0, sticky="ew"
        )
        ctk.CTkLabel(
            self,
            text="© Wbad-02",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=_GOLD_DIM,
        ).grid(row=4, column=0, pady=5)

    def _build_terminals(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        self._cards.clear()
        for i, fp in enumerate(self._email_files):
            card = TerminalCard(
                self._scroll,
                list_index=i,
                list_name=f"Lista {i + 1} — {fp.name}",
            )
            card.grid(row=i, column=0, sticky="ew", pady=(0, 12))
            self._cards.append(card)

    # --------------------------------------------------------------- Actions -

    def _start_automation(self):
        if self._running:
            return

        self._email_files = _list_email_files()
        if len(self._email_files) != len(self._cards):
            self._build_terminals()

        self._running = True
        self.start_btn.configure(
            state="disabled",
            text="⏳  Executando...",
            fg_color=_BG3,
            text_color=_GRAY,
        )

        # Instala handler de log
        self._log_handler = _QueueLogHandler(self._queue)
        logging.getLogger().addHandler(self._log_handler)

        def run():
            try:
                from src.automation_executor import AutomationExecutor
                executor = AutomationExecutor(
                    emails_files=[str(f) for f in self._email_files],
                    headless=True,
                    ui_callback=self._ui_callback,
                )
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(executor.run())
                loop.close()
            except Exception as exc:
                self._queue.put(("log", 0, {"line": f"ERRO CRÍTICO: {exc}"}))
            finally:
                self._queue.put(("done", None, None))

        threading.Thread(target=run, daemon=True).start()

    def _ui_callback(self, event_type: str, list_index: int, **kwargs):
        self._queue.put((event_type, list_index, kwargs))

    def _poll_queue(self):
        try:
            while True:
                event_type, list_index, data = self._queue.get_nowait()

                if event_type == "done":
                    self._running = False
                    if self._log_handler:
                        logging.getLogger().removeHandler(self._log_handler)
                        self._log_handler = None
                    self.start_btn.configure(
                        state="normal",
                        text="▶  Iniciar",
                        fg_color=_GOLD,
                        text_color=_BG,
                    )

                elif event_type == "log":
                    line = data.get("line", "") if isinstance(data, dict) else str(data)
                    if 0 <= list_index < len(self._cards):
                        self._cards[list_index].append_log(line)

                elif event_type == "email_start":
                    email = data.get("email", "")
                    if 0 <= list_index < len(self._cards):
                        self._cards[list_index].set_email_status(email, "running")

                elif event_type == "email_done":
                    email   = data.get("email", "")
                    success = data.get("success", False)
                    if 0 <= list_index < len(self._cards):
                        self._cards[list_index].set_email_status(
                            email, "success" if success else "failed"
                        )
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _open_add_email(self):
        def on_confirm(email: str, modal: AddEmailModal):
            files = _list_email_files()
            if not files:
                modal.feedback.configure(text="Nenhuma lista encontrada", text_color=_RED)
                return

            # Lista com menos emails; empate = menor índice (min() é estável)
            target = min(files, key=_count_emails)

            _append_email_to_file(target, email)
            modal.feedback.configure(
                text=f"Adicionado em {target.name}",
                text_color=_GREEN_OK,
            )
            modal.after(1500, modal.destroy)

        AddEmailModal(self, on_confirm)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    app = GesttaApp()
    app.mainloop()


if __name__ == "__main__":
    main()

"""
© 2024 Wbad-02 - Todos os direitos reservados
Executor Principal da Automação Gestta V1.2

Orquestra o fluxo completo (Email Search):
1. Carrega emails de uma ou mais listas
2. Inicializa browser
3. Realiza login
4. Para cada lista em sua aba: busca + abre usuário + clica Salvar
5. Trata erros e continua (skip & continue policy)
6. Gera relatório final consolidado
"""

import asyncio
import time
from pathlib import Path
from typing import List, Dict
from playwright.async_api import Page
from src.browser_manager import BrowserManager
from src.credential_manager import get_credentials
from src.logger_handler import AutomationLogger


class AutomationExecutor:
    """
    Executa automação V1.2: Email Search no Gestta com suporte a múltiplas listas.

    Fluxo:
    1. Carrega emails de N arquivos (um por lista)
    2. Inicializa browser e realiza login
    3. Cria uma tab por lista (tab 0 já existe do initialize)
    4. Processa cada lista em sua tab via asyncio.gather()
    5. Gera relatório consolidado
    """

    def __init__(
        self,
        emails_files,
        login_url: str = "https://onvio.com.br/login/#/",
        headless: bool = True,
        verbose: bool = False,
        ui_callback=None,
    ):
        """
        Args:
            emails_files: Arquivo único (str) ou lista de arquivos com emails
            login_url: URL de login do Gestta
            headless: Executar em modo headless
            verbose: Output detalhado
            ui_callback: Callable(event_type, list_index, **kwargs) para atualizar UI
        """
        if isinstance(emails_files, str):
            emails_files = [emails_files]
        self.emails_files = [Path(f) for f in emails_files]
        self.login_url = login_url
        self.headless = headless
        self.verbose = verbose
        self.ui_callback = ui_callback

        self.logger = AutomationLogger(__name__)
        self.browser_manager = None

        # Stats por arquivo: {filename: {total, successful, failed, start_time, end_time}}
        self.stats: Dict[str, dict] = {}

        self.logger.logger.info(
            "🎯 Automação GESTTA V1.2 (Email Search)\n"
            "© 2024 Wbad-02 - RH & Folha\n"
        )

    async def _load_emails_from_file(self, file_path: Path) -> List[str]:
        """
        Carrega lista de emails de um arquivo.

        Returns:
            Lista de emails (strings), vazia em caso de erro
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            emails = [
                email.strip().lower()
                for email in lines
                if email.strip() and not email.strip().startswith("#")
            ]

            self.logger.logger.info(f"✓ {len(emails)} emails carregados de {file_path.name}")
            return emails

        except Exception as e:
            self.logger.log_error_safe(f"Erro ao carregar {file_path}: {str(e)}")
            return []

    async def validate_config(self) -> bool:
        """
        Valida todos os arquivos de email e credenciais antes de iniciar.

        Returns:
            bool: True se tudo validado
        """
        self.logger.logger.info("🔍 Validando configuração...")

        for file_path in self.emails_files:
            if not file_path.exists():
                self.logger.log_error_safe(f"Arquivo não encontrado: {file_path}")
                return False

        try:
            get_credentials()
        except Exception as e:
            self.logger.log_error_safe(f"Credenciais inválidas: {str(e)}")
            return False

        self.logger.logger.info("✓ Configuração validada\n")
        return True

    async def perform_login(self, username: str, password: str) -> bool:
        """Realiza login no Onvio e aguarda redirecionamento para o Gestta."""
        self.logger.logger.info("=== REALIZANDO LOGIN ===")

        if not await self.browser_manager.navigate(self.login_url, wait_time=20):
            self.logger.log_error_safe("Falha ao navegar para login")
            return False

        if not await self.browser_manager.submit_form(username, password):
            self.logger.log_error_safe("Falha ao fazer login")
            return False

        self.logger.logger.info("Login realizado com sucesso\n")
        return True

    async def _navigate_with_retry(
        self,
        url: str,
        page: Page,
        max_retries: int = 3,
        base_wait: int = 30
    ) -> bool:
        """Navega para URL com retry e espera crescente em caso de falha."""
        for attempt in range(1, max_retries + 1):
            if await self.browser_manager.navigate(url, wait_time=20, page=page):
                return True
            if attempt < max_retries:
                wait_time = base_wait * attempt
                self.logger.logger.warning(
                    f"⚠️ Navegação falhou (tentativa {attempt}/{max_retries}). "
                    f"Aguardando {wait_time}s antes de tentar novamente..."
                )
                await asyncio.sleep(wait_time)
        self.logger.log_error_safe(f"Navegação falhou após {max_retries} tentativas: {url}")
        return False

    async def _click_result_with_retry(
        self,
        result_selector: str,
        page: Page,
        email: str = "",
        max_retries: int = 3,
        base_wait: int = 30
    ) -> bool:
        """Clica no resultado com retry. Após reload, re-pesquisa o email antes de tentar clicar."""
        for attempt in range(1, max_retries + 1):
            if await self.browser_manager.click_search_result(result_selector, page=page):
                return True
            if attempt < max_retries:
                wait_time = base_wait * attempt
                self.logger.logger.warning(
                    f"⚠️ Clique no link falhou (tentativa {attempt}/{max_retries}). "
                    f"Aguardando {wait_time}s antes de tentar novamente..."
                )
                self.logger.logger.info("Recarregando pagina antes de nova tentativa...")
                await self.browser_manager.reload(page=page)
                await asyncio.sleep(wait_time)

                # Após reload o campo de busca fica vazio — re-pesquisa o email
                if email:
                    if not await self.browser_manager.search_email(
                        email=email,
                        search_field_selector='input[placeholder="Pesquisar por nome"]',
                        wait_time=15,
                        page=page
                    ):
                        continue
                    await asyncio.sleep(5)
                    await self.browser_manager.wait_for_search_results(
                        result_selector=result_selector,
                        wait_time=15,
                        page=page
                    )

        self.logger.log_error_safe(f"Clique no resultado falhou após {max_retries} tentativas")
        return False

    async def _process_list_on_tab(self, list_index: int, file_path: Path, page: Page) -> dict:
        """
        Processa todos os emails de uma lista em uma tab específica.

        Args:
            list_index: Índice da lista (para logging)
            file_path: Caminho do arquivo de emails
            page: Tab do browser onde esta lista será processada

        Returns:
            dict: Estatísticas da lista processada
        """
        emails = await self._load_emails_from_file(file_path)

        stats = {
            "total_emails": len(emails),
            "successful_emails": 0,
            "failed_emails": [],
            "start_time": time.time(),
            "end_time": None
        }

        if not emails:
            self.logger.log_error_safe(f"[Lista {list_index+1}] Nenhum email em {file_path.name}")
            stats["end_time"] = time.time()
            return stats

        customer_list_url = "https://app.gestta.com.br/admin/#/sidebar/customer-user/list"
        label = f"[Lista {list_index+1}/{len(self.emails_files)} - {file_path.name}]"

        self.logger.logger.info(f"\n🚀 {label} Iniciando processamento de {len(emails)} emails...\n")

        def _notify(event_type, **kwargs):
            if self.ui_callback:
                self.ui_callback(event_type, list_index, **kwargs)

        for step_num, email in enumerate(emails, 1):
            try:
                self.logger.logger.info(f"\n{'='*60}")
                self.logger.logger.info(f"{label} Step {step_num}/{len(emails)}: {email}")
                self.logger.logger.info(f"{'='*60}")
                _notify("email_start", email=email)

                if not await self._navigate_with_retry(customer_list_url, page=page):
                    self.logger.log_step(step_num, email, "NAVEGACAO FALHOU")
                    stats["failed_emails"].append(email)
                    _notify("email_done", email=email, success=False)
                    continue

                if not await self.browser_manager.search_email(
                    email=email,
                    search_field_selector='input[placeholder="Pesquisar por nome"]',
                    wait_time=15,
                    page=page
                ):
                    self.logger.log_step(step_num, email, "FALHA AO PREENCHER EMAIL")
                    stats["failed_emails"].append(email)
                    _notify("email_done", email=email, success=False)
                    continue

                await asyncio.sleep(5)

                if not await self.browser_manager.wait_for_search_results(
                    result_selector="a.link-to-edit",
                    wait_time=15,
                    page=page
                ):
                    self.logger.log_step(step_num, email, "NENHUM RESULTADO ENCONTRADO")
                    stats["failed_emails"].append(email)
                    _notify("email_done", email=email, success=False)
                    continue

                if not await self._click_result_with_retry(
                    result_selector="a.link-to-edit",
                    page=page,
                    email=email
                ):
                    self.logger.log_step(step_num, email, "FALHA AO CLICAR RESULTADO")
                    stats["failed_emails"].append(email)
                    _notify("email_done", email=email, success=False)
                    continue

                await asyncio.sleep(5)

                success = await self.browser_manager.click_save_button(step_num=step_num, page=page)

                if success:
                    stats["successful_emails"] += 1
                    self.logger.log_step(step_num, email, "SUCESSO")
                    _notify("email_done", email=email, success=True)
                    self.logger.logger.info("Aguardando 10s antes do proximo email...")
                    await asyncio.sleep(10)
                else:
                    stats["failed_emails"].append(email)
                    self.logger.log_step(step_num, email, "FALHA AO SALVAR")
                    _notify("email_done", email=email, success=False)

                if step_num % 5 == 0:
                    self.logger.logger.info(
                        f"{label} Progresso: {step_num}/{len(emails)} "
                        f"({stats['successful_emails']} ok, "
                        f"{len(stats['failed_emails'])} falhos)"
                    )

            except Exception as e:
                self.logger.log_error_safe(
                    f"{label} Step {step_num}: Erro inesperado: {str(e)}",
                    exc_info=True
                )
                stats["failed_emails"].append(email)

        stats["end_time"] = time.time()
        return stats

    def generate_report(self) -> str:
        """
        Gera relatório final consolidado de todas as listas.

        Returns:
            str: Relatório formatado
        """
        total_emails = sum(s["total_emails"] for s in self.stats.values())
        total_success = sum(s["successful_emails"] for s in self.stats.values())
        total_failed = sum(len(s["failed_emails"]) for s in self.stats.values())

        report = [
            "\n" + "="*60,
            "📊 RELATÓRIO FINAL - AUTOMAÇÃO GESTTA V1.2",
            "="*60,
            f"\n📋 Listas processadas: {len(self.stats)}",
            f"📧 Total de emails: {total_emails}",
            f"✓ Emails processados: {total_success}",
            f"✗ Emails falhados: {total_failed}",
        ]

        if total_emails > 0:
            report.append(f"📈 Taxa de sucesso: {total_success/total_emails*100:.1f}%")

        for filename, s in self.stats.items():
            elapsed = (s["end_time"] or time.time()) - s["start_time"]
            report.append(f"\n  [{filename}] — {s['successful_emails']}/{s['total_emails']} ok, {elapsed:.1f}s")
            if s["failed_emails"]:
                for email in s["failed_emails"]:
                    report.append(f"    ✗ {email}")

        report.append("\n" + "="*60)
        report.append("✨ Automação concluída!")
        report.append("="*60 + "\n")

        return "\n".join(report)

    async def run(self) -> bool:
        """
        Executa fluxo completo de automação.

        Returns:
            bool: True se tudo executado
        """
        try:
            if not await self.validate_config():
                return False

            self.browser_manager = BrowserManager(headless=self.headless)
            if not await self.browser_manager.initialize():
                self.logger.log_error_safe("Falha ao inicializar browser")
                return False

            creds = get_credentials()
            if "error" in creds:
                self.logger.log_error_safe(f"Credenciais invalidas: {creds['error']}")
                return False
            username, password = creds["username"], creds["password"]

            if not await self.perform_login(username, password):
                return False

            # Cria tabs adicionais para cada lista extra (tab 0 já existe)
            for i in range(1, len(self.emails_files)):
                tab = await self.browser_manager.create_tab()
                if not tab:
                    self.logger.log_error_safe(f"Falha ao criar tab para lista {i+1}")
                    return False

            # Processa todas as listas em paralelo, cada uma em sua tab
            tasks = [
                self._process_list_on_tab(i, file_path, self.browser_manager.pages[i])
                for i, file_path in enumerate(self.emails_files)
            ]
            results = await asyncio.gather(*tasks)

            for file_path, stats in zip(self.emails_files, results):
                self.stats[file_path.name] = stats

            report = self.generate_report()
            self.logger.logger.info(report)

            report_file = Path("logs") / "automation_report.txt"
            report_file.parent.mkdir(exist_ok=True)
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(report)

            return True

        except Exception as e:
            self.logger.log_error_safe(f"Erro crítico: {str(e)}", exc_info=True)
            return False

        finally:
            if self.browser_manager:
                await self.browser_manager.cleanup()

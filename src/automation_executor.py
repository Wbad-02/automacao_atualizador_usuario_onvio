"""
© 2024 Wbad-02 - Todos os direitos reservados
Executor Principal da Automação Gestta V1.2

Orquestra o fluxo completo (Email Search):
1. Carrega emails da lista
2. Inicializa browser
3. Realiza login
4. Para cada email: busca + abre usuário + TAB 16x + ENTER
5. Trata erros e continua (skip & continue policy)
6. Gera relatório final com emails falhados
"""

import asyncio
import time
from pathlib import Path
from typing import List
from src.browser_manager import BrowserManager
from src.credential_manager import get_credentials
from src.logger_handler import AutomationLogger


class AutomationExecutor:
    """
    Executa automação V1.2: Email Search no Gestta.
    
    Fluxo:
    1. Carrega emails do arquivo config/emails_list.txt
    2. Inicializa browser e realiza login
    3. Para cada email:
       ├─ Navega para /admin/#/sidebar/customer-user/list
       ├─ Preenche campo de busca com EMAIL
       ├─ Aguarda resultado aparecer
       ├─ Clica no link do usuário
       ├─ TAB 16x com 1s de intervalo
       ├─ ENTER 1x
       └─ Se falhar: registra e continua
    4. Gera relatório final com emails falhados
    """
    
    def __init__(
        self,
        emails_file: str = "config/emails_list.txt",
        login_url: str = "https://onvio.com.br/login/#/",
        headless: bool = True,
        verbose: bool = False
    ):
        """
        Inicializa executor de automação V1.2 (Email Search).
        
        Args:
            emails_file: Arquivo com lista de emails (um por linha)
            login_url: URL de login do Gestta
            headless: Executar em modo headless
            verbose: Output detalhado
        """
        self.emails_file = Path(emails_file)
        self.login_url = login_url
        self.headless = headless
        
        self.logger = AutomationLogger(__name__)
        self.browser_manager = None
        
        # Emails para processamento
        self.emails = []
        
        # Estatísticas
        self.stats = {
            "total_emails": 0,
            "successful_emails": 0,
            "failed_emails": [],
            "start_time": None,
            "end_time": None
        }
        
        self.logger.logger.info(
            "🎯 Automação GESTTA V1.2 (Email Search)\n"
            "© 2024 Wbad-02 - RH & Folha\n"
        )
    
    async def load_emails(self) -> bool:
        """
        Carrega lista de emails do arquivo config/emails_list.txt
        
        Returns:
            bool: True se emails foram carregados com sucesso
        """
        try:
            if not self.emails_file.exists():
                self.logger.log_error_safe(f"Arquivo não encontrado: {self.emails_file}")
                return False
            
            with open(self.emails_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Filtra linhas vazias e comentários
            self.emails = [
                email.strip().lower()
                for email in lines
                if email.strip() and not email.strip().startswith("#")
            ]
            
            self.stats["total_emails"] = len(self.emails)
            
            self.logger.logger.info(f"✓ {self.stats['total_emails']} emails carregados")
            return True
        
        except Exception as e:
            self.logger.log_error_safe(f"Erro ao carregar emails: {str(e)}")
            return False
    
    async def validate_config(self) -> bool:
        """
        Valida configuração antes de iniciar automação.
        
        Verifica:
        - Arquivo de emails existe
        - Emails foram carregados
        - Credenciais existem
        
        Returns:
            bool: True se tudo validado
        """
        self.logger.logger.info("🔍 Validando configuração...")
        
        # Valida arquivo
        if not self.emails_file.exists():
            self.logger.log_error_safe(f"Arquivo não encontrado: {self.emails_file}")
            return False
        
        # Carrega emails
        if not await self.load_emails():
            self.logger.log_error_safe("Falha ao carregar emails")
            return False
        
        if self.stats["total_emails"] == 0:
            self.logger.log_error_safe("Nenhum email na lista")
            return False
        
        # Valida credenciais
        try:
            get_credentials()
        except Exception as e:
            self.logger.log_error_safe(f"Credenciais inválidas: {str(e)}")
            return False
        
        self.logger.logger.info("✓ Configuração validada\n")
        return True
    
    async def perform_login(self, username: str, password: str) -> bool:
        """
        Realiza login no Onvio e aguarda redirecionamento para o Gestta.

        Fluxo:
        1. Navega para onvio.com.br/login
        2. Preenche usuário e senha
        3. Aguarda redirect para app.gestta.com.br
        """
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
        max_retries: int = 3,
        base_wait: int = 30
    ) -> bool:
        """Navega para URL com retry e espera crescente em caso de falha."""
        for attempt in range(1, max_retries + 1):
            if await self.browser_manager.navigate(url, wait_time=20):
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
        max_retries: int = 3,
        base_wait: int = 30
    ) -> bool:
        """Clica no resultado com retry e espera crescente em caso de falha."""
        for attempt in range(1, max_retries + 1):
            if await self.browser_manager.click_search_result(result_selector):
                return True
            if attempt < max_retries:
                wait_time = base_wait * attempt
                self.logger.logger.warning(
                    f"⚠️ Clique no link falhou (tentativa {attempt}/{max_retries}). "
                    f"Aguardando {wait_time}s antes de tentar novamente..."
                )
                await asyncio.sleep(wait_time)
        self.logger.log_error_safe(f"Clique no resultado falhou após {max_retries} tentativas")
        return False

    async def execute_automation(self) -> bool:
        """
        Executa automação V1.2: Busca emails e realiza TAB 16x + ENTER.
        
        Fluxo por EMAIL:
        1. Navega para /admin/#/sidebar/customer-user/list
        2. Preenche campo de busca com EMAIL
        3. Aguarda elemento de resultado aparecer
        4. Clica no link do resultado
        5. Aguarda página carregar
        6. TAB 16x com 1s de intervalo
        7. ENTER 1x
        8. Volta para lista
        9. Repete com próximo EMAIL
        
        Returns:
            bool: True se execução completou
        """
        self.logger.logger.info("🚀 Iniciando automação EMAIL SEARCH...\n")
        
        self.stats["start_time"] = time.time()
        
        # URL base da lista de clientes
        customer_list_url = "https://app.gestta.com.br/admin/#/sidebar/customer-user/list"
        
        for step_num, email in enumerate(self.emails, 1):
            try:
                self.logger.logger.info(f"\n{'='*60}")
                self.logger.logger.info(f"Step {step_num}/{self.stats['total_emails']}: {email}")
                self.logger.logger.info(f"{'='*60}")

                # Navega para lista de clientes com retry (espera 30s, 60s, 90s entre tentativas)
                if not await self._navigate_with_retry(customer_list_url):
                    self.logger.log_step(step_num, email, "NAVEGACAO FALHOU")
                    self.stats["failed_emails"].append(email)
                    continue
                await asyncio.sleep(5)

                # Preenche campo de busca com EMAIL (5s de espera)
                if not await self.browser_manager.search_email(
                    email=email,
                    search_field_selector='input[placeholder="Pesquisar por nome"]',
                    wait_time=10
                ):
                    self.logger.log_step(step_num, email, "FALHA AO PREENCHER EMAIL")
                    self.stats["failed_emails"].append(email)
                    continue
                await asyncio.sleep(5)

                # Aguarda e clica no resultado
                if not await self.browser_manager.wait_for_search_results(
                    result_selector="a.link-to-edit",
                    wait_time=10
                ):
                    self.logger.log_step(step_num, email, "NENHUM RESULTADO ENCONTRADO")
                    self.stats["failed_emails"].append(email)
                    continue

                # Clica no link do resultado com retry (espera 30s, 60s, 90s entre tentativas)
                if not await self._click_result_with_retry(result_selector="a.link-to-edit"):
                    self.logger.log_step(step_num, email, "FALHA AO CLICAR RESULTADO")
                    self.stats["failed_emails"].append(email)
                    continue

                # Aguarda página de edição carregar (5s)
                await asyncio.sleep(5)

                # Encontra botão Salvar → 3s → clica
                success = await self.browser_manager.click_save_button(step_num=step_num)

                if success:
                    self.stats["successful_emails"] += 1
                    self.logger.log_step(step_num, email, "SUCESSO")
                    self.logger.logger.info("Aguardando 10s antes do proximo email...")
                    await asyncio.sleep(10)
                else:
                    self.stats["failed_emails"].append(email)
                    self.logger.log_step(step_num, email, "FALHA AO SALVAR")

                if step_num % 5 == 0:
                    self.logger.logger.info(
                        f"Progresso: {step_num}/{self.stats['total_emails']} "
                        f"({self.stats['successful_emails']} ok, "
                        f"{len(self.stats['failed_emails'])} falhos)"
                    )
            
            except Exception as e:
                self.logger.log_error_safe(
                    f"Step {step_num}: Erro inesperado: {str(e)}",
                    exc_info=True
                )
                self.stats["failed_emails"].append(email)
        
        self.stats["end_time"] = time.time()
        return True
    
    def generate_report(self) -> str:
        """
        Gera relatório final com estatísticas e emails falhados.
        
        Returns:
            str: Relatório formatado
        """
        elapsed_time = self.stats["end_time"] - self.stats["start_time"]
        
        report = [
            "\n" + "="*60,
            "📊 RELATÓRIO FINAL - AUTOMAÇÃO GESTTA V1.2",
            "="*60,
            f"\n⏱️ Tempo total: {elapsed_time:.1f}s",
            f"📧 Total de emails: {self.stats['total_emails']}",
            f"✓ Emails processados: {self.stats['successful_emails']}",
            f"✗ Emails falhados: {len(self.stats['failed_emails'])}",
            f"📈 Taxa de sucesso: {self.stats['successful_emails']/self.stats['total_emails']*100:.1f}%",
        ]
        
        # Se houve emails falhados
        if self.stats["failed_emails"]:
            report.append("\n" + "-"*60)
            report.append("⚠️ EMAILS QUE NÃO RETORNARAM RESULTADOS:")
            report.append("-"*60)
            for idx, email in enumerate(self.stats["failed_emails"], 1):
                report.append(f"{idx}. {email}")
        
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
            # Valida configuração
            if not await self.validate_config():
                return False
            
            # Inicializa browser
            self.browser_manager = BrowserManager(headless=self.headless)
            if not await self.browser_manager.initialize():
                self.logger.log_error_safe("Falha ao inicializar browser")
                return False

            # Obtém credenciais
            creds = get_credentials()
            if "error" in creds:
                self.logger.log_error_safe(f"Credenciais invalidas: {creds['error']}")
                return False
            username, password = creds["username"], creds["password"]
            
            # Realiza login
            if not await self.perform_login(username, password):
                return False
            
            # Executa automação
            if not await self.execute_automation():
                return False
            
            # Gera relatório
            report = self.generate_report()
            self.logger.logger.info(report)
            
            # Salva relatório em arquivo
            report_file = Path("logs") / "automation_report.txt"
            report_file.parent.mkdir(exist_ok=True)
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(report)
            
            return True
        
        except Exception as e:
            self.logger.log_error_safe(f"Erro crítico: {str(e)}", exc_info=True)
            return False
        
        finally:
            # Fecha browser
            if self.browser_manager:
                await self.browser_manager.cleanup()

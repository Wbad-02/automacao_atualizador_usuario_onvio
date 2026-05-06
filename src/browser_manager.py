"""
© 2024 Wbad-02 - Todos os direitos reservados
Módulo de Gerenciamento de Browser com Playwright

Implementa:
- Inicialização robusta do Chromium/Edge
- Wait inteligentes (elemento, timeout)
- Retry automático em falhas transitórias
- Screenshots para debugging
- Limpeza segura de recursos
- Suporte a múltiplas tabs (pages)
"""

import asyncio
from pathlib import Path
from typing import Optional, List
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from src.logger_handler import AutomationLogger
import logging


class BrowserManager:
    """
    Gerencia ciclo de vida do browser Playwright.

    Responsabilidades:
    - Inicializar browser e context
    - Navegar entre URLs
    - Executar cliques com retry
    - Capturar screenshots para debugging
    - Fechar recursos adequadamente
    - Gerenciar múltiplas tabs
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.pages: List[Page] = []
        self.logger = AutomationLogger(__name__)

        # Diretório para screenshots
        self.screenshots_dir = Path("screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)

    @property
    def page(self) -> Optional[Page]:
        """Retorna a primeira tab (compatibilidade com código existente)."""
        return self.pages[0] if self.pages else None

    async def initialize(self) -> bool:
        """
        Inicializa browser e primeira página.

        Returns:
            bool: True se sucesso, False caso contrário
        """
        try:
            playwright = await async_playwright().start()

            # Tenta Chromium primeiro, fallback para Edge se disponível
            try:
                self.browser = await playwright.chromium.launch(headless=self.headless)
            except Exception as e:
                self.logger.logger.warning(f"Chromium não disponível: {e}. Tentando Edge...")
                self.browser = await playwright.edge.launch(headless=self.headless)

            # Cria context com viewport padrão
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720}
            )

            first_page = await self.context.new_page()
            self.pages.append(first_page)

            self.logger.logger.info("✓ Browser inicializado com sucesso")
            return True

        except Exception as e:
            self.logger.log_error_safe(f"Falha ao inicializar browser: {str(e)}", exc_info=True)
            return False

    async def create_tab(self) -> Optional[Page]:
        """
        Cria uma nova aba no browser e a registra na lista de pages.

        Returns:
            Page: Nova page criada, ou None em caso de falha
        """
        if not self.context:
            self.logger.log_error_safe("Context não inicializado")
            return None
        try:
            new_page = await self.context.new_page()
            self.pages.append(new_page)
            self.logger.logger.info(f"✓ Nova tab criada (total: {len(self.pages)})")
            return new_page
        except Exception as e:
            self.logger.log_error_safe(f"Falha ao criar nova tab: {str(e)}")
            return None

    async def navigate(self, url: str, wait_time: int = 20, page: Optional[Page] = None) -> bool:
        """
        Navega até URL e aguarda carregamento.

        Args:
            url: URL a navegar
            wait_time: Timeout em segundos
            page: Tab a usar (padrão: primeira tab)

        Returns:
            bool: True se sucesso
        """
        _page = page or self.page
        if not _page:
            self.logger.log_error_safe("Browser não inicializado")
            return False

        try:
            await _page.goto(url, wait_until="networkidle", timeout=wait_time * 1000)
            self.logger.logger.debug(f"✓ Navegado para: {url[:50]}...")
            return True

        except asyncio.TimeoutError:
            self.logger.log_error_safe(f"Timeout ao navegar para URL (wait_time={wait_time}s)")
            return False

        except Exception as e:
            self.logger.log_error_safe(f"Erro ao navegar: {str(e)}")
            return False

    async def get_current_url(self, page: Optional[Page] = None) -> str:
        """Retorna a URL atual da página."""
        _page = page or self.page
        if not _page:
            return ""
        return _page.url

    async def search_email(self, email: str, search_field_selector: str = "input[type='text']", wait_time: int = 15, page: Optional[Page] = None) -> bool:
        """
        Pesquisa email no campo de busca.

        Args:
            email: Email a pesquisar
            search_field_selector: Seletor CSS do campo de busca
            wait_time: Timeout em segundos
            page: Tab a usar (padrão: primeira tab)

        Returns:
            bool: True se email foi preenchido com sucesso
        """
        _page = page or self.page
        if not _page:
            self.logger.log_error_safe("Browser não inicializado")
            return False

        try:
            self.logger.logger.info(f"🔍 Buscando email: {email}")

            # Preenche campo de busca
            await _page.fill(search_field_selector, email, timeout=wait_time * 1000)

            self.logger.logger.info(f"✓ Email preenchido: {email}")
            return True

        except Exception as e:
            self.logger.log_error_safe(f"Timeout ({wait_time}s) ao preencher email '{email}': {str(e)}")
            return False

    async def wait_for_search_results(self, result_selector: str = "a.link-to-edit", wait_time: int = 15, page: Optional[Page] = None) -> bool:
        """
        Aguarda elemento de resultado aparecer.

        Args:
            result_selector: Seletor CSS do link de resultado
            wait_time: Timeout em segundos
            page: Tab a usar (padrão: primeira tab)

        Returns:
            bool: True se elemento apareceu
        """
        _page = page or self.page
        if not _page:
            self.logger.log_error_safe("Browser não inicializado")
            return False

        try:
            self.logger.logger.info(f"⏳ Aguardando resultados ({wait_time}s)...")

            await _page.wait_for_selector(
                result_selector,
                state="attached",
                timeout=wait_time * 1000
            )

            self.logger.logger.info(f"✓ Resultado encontrado!")
            return True

        except Exception as e:
            self.logger.log_error_safe(f"Timeout ({wait_time}s) aguardando resultados '{result_selector}': {str(e)}")
            return False

    async def reload(self, wait_time: int = 15, page: Optional[Page] = None) -> bool:
        """Recarrega a página atual e aguarda networkidle."""
        _page = page or self.page
        if not _page:
            return False
        try:
            await _page.reload(wait_until="networkidle", timeout=wait_time * 1000)
            self.logger.logger.info("Pagina recarregada")
            return True
        except Exception as e:
            self.logger.log_error_safe(f"Erro ao recarregar pagina: {str(e)}")
            return False

    async def click_search_result(self, result_selector: str = "a.link-to-edit", page: Optional[Page] = None) -> bool:
        """
        Clica no primeiro resultado de busca (segue link).

        Args:
            result_selector: Seletor CSS do link
            page: Tab a usar (padrão: primeira tab)

        Returns:
            bool: True se clique foi bem-sucedido
        """
        _page = page or self.page
        if not _page:
            self.logger.log_error_safe("Browser não inicializado")
            return False

        try:
            self.logger.logger.info(f"🔗 Clicando no resultado...")

            await _page.click(result_selector, force=True)
            await _page.wait_for_load_state("networkidle", timeout=15000)

            self.logger.logger.info(f"✓ Resultado clicado!")
            return True

        except Exception as e:
            self.logger.log_error_safe(f"Erro ao clicar resultado: {str(e)}")
            return False

    async def click_save_button(self, step_num: int = 0, page: Optional[Page] = None) -> bool:
        """
        Encontra o botão Salvar, aguarda 3s e clica.
        """
        _page = page or self.page
        if not _page:
            self.logger.log_error_safe("Browser não inicializado")
            return False

        try:
            self.logger.logger.info("Procurando botao Salvar...")
            await _page.wait_for_selector('button.submit.btn-primary span.ladda-label', state="visible", timeout=15000)
            await _page.click('button.submit.btn-primary')
            self.logger.logger.info("Botao Salvar clicado")
            return True

        except Exception as e:
            self.logger.log_error_safe(f"Erro ao clicar Salvar: {str(e)}")
            await self._capture_screenshot(f"step_{step_num}_save_failed", page=_page)
            return False

    async def press_tab_with_interval(
        self,
        tab_presses: int = 16,
        interval: float = 1.0,
        step_num: int = 0,
        page: Optional[Page] = None
    ) -> bool:
        """
        Pressiona TAB N vezes COM intervalo entre cada pressão + ENTER 1 vez.
        """
        _page = page or self.page
        if not _page:
            self.logger.log_error_safe("Browser não inicializado")
            return False

        try:
            self.logger.logger.info(f"⌨️ Pressionando TAB {tab_presses}x (intervalo: {interval}s)...")

            for i in range(tab_presses):
                await _page.keyboard.press('Tab')
                self.logger.logger.debug(f"  TAB {i+1}/{tab_presses}")
                await asyncio.sleep(interval)

            self.logger.logger.info(f"✓ TABs pressionados ({tab_presses}x)")

            self.logger.logger.info("Pressionando ENTER...")
            await _page.keyboard.press('Enter')
            await asyncio.sleep(1)

            self.logger.logger.info("ENTER pressionado")
            return True

        except Exception as e:
            self.logger.log_error_safe(f"Erro ao pressionar TAB+ENTER: {str(e)}")
            await self._capture_screenshot(f"step_{step_num}_failed", page=_page)
            return False

    async def submit_form(self, username: str, password: str) -> bool:
        """
        Preenche e submete formulário de login Onvio (Auth0, dois passos).

        Fluxo:
        1. Preenche username e clica Continue
        2. Aguarda campo de senha aparecer
        3. Preenche senha e submete
        """
        _page = self.page
        if not _page:
            return False

        try:
            self.logger.logger.info("Preenchendo formulário de login (Onvio)...")

            await _page.wait_for_load_state("networkidle", timeout=30000)

            await _page.keyboard.press("Enter")
            await _page.wait_for_timeout(15000)

            await _page.keyboard.type(username)
            self.logger.logger.info("Usuario digitado")

            await _page.keyboard.press("Enter")
            await _page.wait_for_selector('input[type="password"]', timeout=20000)

            await _page.keyboard.type(password)
            self.logger.logger.info("Senha digitada")

            await _page.keyboard.press("Enter")
            self.logger.logger.info("Credenciais submetidas")
            await asyncio.sleep(20)

            await _page.keyboard.press("Tab")
            await _page.keyboard.press("Tab")
            await asyncio.sleep(2)

            await _page.keyboard.press("Enter")
            await asyncio.sleep(2)

            await _page.keyboard.press("Tab")
            await asyncio.sleep(2)

            await _page.keyboard.press("Enter")
            self.logger.logger.info("Login concluido, aguardando Gestta...")
            await asyncio.sleep(10)
            return True

        except Exception as e:
            self.logger.log_error_safe(f"Erro ao preencher formulario: {str(e)}", exc_info=True)
            await self._capture_screenshot("login_form_failed")
            return False

    async def _capture_screenshot(self, name: str, page: Optional[Page] = None):
        """Captura screenshot para debugging."""
        _page = page or self.page
        if not _page:
            return

        try:
            path = self.screenshots_dir / f"{name}.png"
            await _page.screenshot(path=str(path))
            self.logger.logger.debug(f"📸 Screenshot salvo: {path}")
        except Exception as e:
            self.logger.logger.warning(f"Não foi possível capturar screenshot: {e}")

    async def cleanup(self):
        """Fecha todas as tabs, context e browser, liberando recursos."""
        try:
            for p in self.pages:
                try:
                    await p.close()
                except Exception:
                    pass
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()

            self.logger.logger.info("✓ Browser fechado com segurança")
        except Exception as e:
            self.logger.log_error_safe(f"Erro ao fechar browser: {str(e)}")

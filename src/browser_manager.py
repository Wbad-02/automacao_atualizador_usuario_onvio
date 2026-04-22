"""
© 2024 Wbad-02 - Todos os direitos reservados
Módulo de Gerenciamento de Browser com Playwright

Implementa:
- Inicialização robusta do Chromium/Edge
- Wait inteligentes (elemento, timeout)
- Retry automático em falhas transitórias
- Screenshots para debugging
- Limpeza segura de recursos
"""

import asyncio
from pathlib import Path
from typing import Optional, Tuple
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
    """
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.logger = AutomationLogger(__name__)
        
        # Diretório para screenshots
        self.screenshots_dir = Path("screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
    
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
            
            self.page = await self.context.new_page()
            
            self.logger.logger.info("✓ Browser inicializado com sucesso")
            return True
        
        except Exception as e:
            self.logger.log_error_safe(f"Falha ao inicializar browser: {str(e)}", exc_info=True)
            return False
    
    async def navigate(self, url: str, wait_time: int = 20) -> bool:
        """
        Navega até URL e aguarda carregamento.
        
        Args:
            url: URL a navegar
            wait_time: Timeout em segundos
        
        Returns:
            bool: True se sucesso
        """
        if not self.page:
            self.logger.log_error_safe("Browser não inicializado")
            return False
        
        try:
            await self.page.goto(url, wait_until="networkidle", timeout=wait_time * 1000)
            self.logger.logger.debug(f"✓ Navegado para: {url[:50]}...")
            return True
        
        except asyncio.TimeoutError:
            self.logger.log_error_safe(f"Timeout ao navegar para URL (wait_time={wait_time}s)")
            return False
        
        except Exception as e:
            self.logger.log_error_safe(f"Erro ao navegar: {str(e)}")
            return False
    
    async def get_current_url(self) -> str:
        """Retorna a URL atual da página."""
        if not self.page:
            return ""
        return self.page.url

    async def search_email(self, email: str, search_field_selector: str = "input[type='text']", wait_time: int = 10) -> bool:
        """
        Pesquisa email no campo de busca.
        
        Args:
            email: Email a pesquisar
            search_field_selector: Seletor CSS do campo de busca
            wait_time: Timeout em segundos
        
        Returns:
            bool: True se email foi preenchido com sucesso
        """
        if not self.page:
            self.logger.log_error_safe("Browser não inicializado")
            return False
        
        try:
            self.logger.logger.info(f"🔍 Buscando email: {email}")
            
            # Preenche campo de busca
            await self.page.fill(search_field_selector, email, timeout=wait_time * 1000)
            
            self.logger.logger.info(f"✓ Email preenchido: {email}")
            return True
        
        except Exception as e:
            self.logger.log_error_safe(f"Erro ao preencher email: {str(e)}")
            return False
    
    async def wait_for_search_results(self, result_selector: str = "a.link-to-edit", wait_time: int = 10) -> bool:
        """
        Aguarda elemento de resultado aparecer.
        
        Args:
            result_selector: Seletor CSS do link de resultado
            wait_time: Timeout em segundos
        
        Returns:
            bool: True se elemento apareceu
        """
        if not self.page:
            self.logger.log_error_safe("Browser não inicializado")
            return False
        
        try:
            self.logger.logger.info(f"⏳ Aguardando resultados ({wait_time}s)...")

            # Aguarda elemento no DOM (attached), mesmo que ainda esteja hidden.
            # O AngularJS injeta o <a class="link-to-edit"> antes de torná-lo visível,
            # então state="visible" dá timeout mesmo o elemento existindo.
            await self.page.wait_for_selector(
                result_selector,
                state="attached",
                timeout=wait_time * 1000
            )

            self.logger.logger.info(f"✓ Resultado encontrado!")
            return True

        except Exception as e:
            self.logger.log_error_safe(f"Timeout aguardando resultados: {str(e)}")
            return False
    
    async def click_search_result(self, result_selector: str = "a.link-to-edit") -> bool:
        """
        Clica no primeiro resultado de busca (segue link).
        
        Args:
            result_selector: Seletor CSS do link
        
        Returns:
            bool: True se clique foi bem-sucedido
        """
        if not self.page:
            self.logger.log_error_safe("Browser não inicializado")
            return False
        
        try:
            self.logger.logger.info(f"🔗 Clicando no resultado...")
            
            # force=True permite clicar mesmo que o elemento esteja hidden/obscured
            await self.page.click(result_selector, force=True)

            # Aguarda navegação
            await asyncio.sleep(2)
            
            self.logger.logger.info(f"✓ Resultado clicado!")
            return True
        
        except Exception as e:
            self.logger.log_error_safe(f"Erro ao clicar resultado: {str(e)}")
            return False
    
    async def click_save_button(self, step_num: int = 0) -> bool:
        """
        Encontra o botão Salvar, aguarda 3s e clica.
        """
        if not self.page:
            self.logger.log_error_safe("Browser não inicializado")
            return False

        try:
            self.logger.logger.info("Procurando botao Salvar...")
            await self.page.wait_for_selector('button.submit.btn-primary span.ladda-label', timeout=15000)
            await asyncio.sleep(3)
            await self.page.click('button.submit.btn-primary')
            self.logger.logger.info("Botao Salvar clicado")
            return True

        except Exception as e:
            self.logger.log_error_safe(f"Erro ao clicar Salvar: {str(e)}")
            await self._capture_screenshot(f"step_{step_num}_save_failed")
            return False

    async def press_tab_with_interval(
        self,
        tab_presses: int = 16,
        interval: float = 1.0,
        step_num: int = 0
    ) -> bool:
        """
        Pressiona TAB N vezes COM intervalo entre cada pressão + ENTER 1 vez.
        
        Args:
            tab_presses: Número de vezes para pressionar TAB (padrão: 16)
            interval: Intervalo em segundos entre cada TAB (padrão: 1.0)
            step_num: Número da etapa (para logging)
        
        Returns:
            bool: True se bem-sucedido
        
        Fluxo V1.2:
        1. Pressiona TAB 16 vezes (com 1s de intervalo)
        2. Pressiona ENTER 1 vez
        """
        if not self.page:
            self.logger.log_error_safe("Browser não inicializado")
            return False
        
        try:
            self.logger.logger.info(f"⌨️ Pressionando TAB {tab_presses}x (intervalo: {interval}s)...")
            
            # Pressiona TAB N vezes COM intervalo
            for i in range(tab_presses):
                await self.page.keyboard.press('Tab')
                self.logger.logger.debug(f"  TAB {i+1}/{tab_presses}")
                await asyncio.sleep(interval)
            
            self.logger.logger.info(f"✓ TABs pressionados ({tab_presses}x)")
            
            # Pressiona ENTER + aguarda 1s
            self.logger.logger.info("Pressionando ENTER...")
            await self.page.keyboard.press('Enter')
            await asyncio.sleep(1)

            self.logger.logger.info("ENTER pressionado")
            return True
        
        except Exception as e:
            self.logger.log_error_safe(f"Erro ao pressionar TAB+ENTER: {str(e)}")
            
            # Captura screenshot para debugging
            await self._capture_screenshot(f"step_{step_num}_failed")
            return False
    
    async def submit_form(self, username: str, password: str, timeout: int = 15) -> bool:
        """
        Preenche e submete formulário de login Onvio (Auth0, dois passos).

        Fluxo:
        1. Preenche username e clica Continue
        2. Aguarda campo de senha aparecer
        3. Preenche senha e submete
        """
        if not self.page:
            return False

        try:
            self.logger.logger.info("Preenchendo formulário de login (Onvio)...")

            # Aguarda página renderizar completamente
            await asyncio.sleep(5)

            # ENTER → 7s
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(7)

            # Digita email → 7s
            await self.page.keyboard.type(username)
            self.logger.logger.info("Usuario digitado")
            await asyncio.sleep(7)

            # ENTER → 7s
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(7)

            # Digita senha → 7s
            await self.page.keyboard.type(password)
            self.logger.logger.info("Senha digitada")
            await asyncio.sleep(7)

            # ENTER → 20s
            await self.page.keyboard.press("Enter")
            self.logger.logger.info("Credenciais submetidas")
            await asyncio.sleep(20)

            # TAB TAB → 2s
            await self.page.keyboard.press("Tab")
            await self.page.keyboard.press("Tab")
            await asyncio.sleep(2)

            # ENTER → 2s
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(2)

            # TAB → 2s
            await self.page.keyboard.press("Tab")
            await asyncio.sleep(2)

            # ENTER → 10s (aguarda Gestta carregar)
            await self.page.keyboard.press("Enter")
            self.logger.logger.info("Login concluido, aguardando Gestta...")
            await asyncio.sleep(10)
            return True

        except Exception as e:
            self.logger.log_error_safe(f"Erro ao preencher formulario: {str(e)}", exc_info=True)
            await self._capture_screenshot("login_form_failed")
            return False
    
    async def _capture_screenshot(self, name: str):
        """Captura screenshot para debugging."""
        if not self.page:
            return
        
        try:
            path = self.screenshots_dir / f"{name}.png"
            await self.page.screenshot(path=str(path))
            self.logger.logger.debug(f"📸 Screenshot salvo: {path}")
        except Exception as e:
            self.logger.logger.warning(f"Não foi possível capturar screenshot: {e}")
    
    async def cleanup(self):
        """Fecha browser e libera recursos."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            
            self.logger.logger.info("✓ Browser fechado com segurança")
        except Exception as e:
            self.logger.log_error_safe(f"Erro ao fechar browser: {str(e)}")

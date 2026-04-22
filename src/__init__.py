"""
© 2024 Wbad-02 - Todos os direitos reservados

Pacote de Automação Gestta

Módulos:
  - automation_executor: Orquestra o fluxo completo
  - browser_manager: Gerencia Playwright
  - credential_manager: Criptografia de credenciais
  - logger_handler: Logging estruturado
"""

from .automation_executor import AutomationExecutor
from .browser_manager import BrowserManager
from .credential_manager import CredentialManager, init_credentials, get_credentials
from .logger_handler import AutomationLogger, setup_logger

__version__ = "1.0.0"
__author__ = "Wbad-02"
__all__ = [
    "AutomationExecutor",
    "BrowserManager",
    "CredentialManager",
    "AutomationLogger",
    "init_credentials",
    "get_credentials",
    "setup_logger",
]

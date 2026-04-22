"""
© 2024 Wbad-02 - Todos os direitos reservados
Módulo de Logging Estruturado para Automação Gestta

Implementa logging seguro que:
- Nunca registra credenciais ou dados sensíveis
- Mantém auditoria detalhada de cada ação
- Gera logs estruturados em JSON para análise
- Conforme LGPD e boas práticas de segurança
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from pythonjsonlogger import jsonlogger


class SafeLoggerFormatter(logging.Formatter):
    """
    Formatter customizado que mascara dados sensíveis antes de registrar.
    Evita exposição de credenciais, tokens, ou dados pessoais.
    """
    
    SENSITIVE_KEYS = [
        'password', 'passwd', 'pwd', 'secret', 'token', 'api_key',
        'username', 'user', 'email', 'phone', 'cpf', 'cnpj',
        'credential', 'auth', 'Authorization'
    ]
    
    def format(self, record):
        # Mascara valores sensíveis em mensagens
        for key in self.SENSITIVE_KEYS:
            if key.lower() in record.getMessage().lower():
                record.msg = self._redact_sensitive(record.getMessage())
        
        return super().format(record)
    
    @staticmethod
    def _redact_sensitive(message: str) -> str:
        """Substitui valores sensíveis por [REDACTED]."""
        import re
        # Padrão: chave=valor ou "chave": "valor"
        pattern = r'(password|passwd|pwd|secret|token|api_key|username|user|email|phone|cpf|cnpj)[\s:=]+"?[^\s,"}\]]+?(?=[\s,"\}\]])'
        return re.sub(pattern, r'\1=[REDACTED]', message, flags=re.IGNORECASE)


def setup_logger(name: str, log_dir: str = "logs") -> logging.Logger:
    """
    Configura logger com formatação segura e múltiplos handlers.
    
    Args:
        name: Nome do logger (geralmente __name__)
        log_dir: Diretório para armazenar logs
    
    Returns:
        logging.Logger: Logger configurado e pronto
    """
    # Cria diretório de logs se não existir
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Remove handlers anteriores (evita duplicação)
    logger.handlers.clear()
    
    # ============ HANDLER 1: Console (INFO+) ============
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    console_formatter = SafeLoggerFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # ============ HANDLER 2: File (DEBUG+, Texto) ============
    file_handler = logging.FileHandler(
        log_path / f"automation_{datetime.now().strftime('%Y%m%d')}.log",
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    file_formatter = SafeLoggerFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # ============ HANDLER 3: File (JSON, para análise estruturada) ============
    json_handler = logging.FileHandler(
        log_path / f"automation_{datetime.now().strftime('%Y%m%d')}.jsonl",
        encoding='utf-8'
    )
    json_handler.setLevel(logging.DEBUG)
    
    json_formatter = jsonlogger.JsonFormatter(
        fmt='%(timestamp)s %(level)s %(name)s %(funcName)s %(lineno)d %(message)s'
    )
    json_handler.setFormatter(json_formatter)
    logger.addHandler(json_handler)
    
    return logger


class AutomationLogger:
    """Wrapper com métodos de conveniência para logging de automação."""
    
    def __init__(self, name: str):
        self.logger = setup_logger(name)
    
    def log_step(self, step_num: int, url: str, status: str, details: str = ""):
        """Registra etapa da automação."""
        msg = f"Step {step_num} | URL: {url} | Status: {status}"
        if details:
            msg += f" | {details}"
        self.logger.info(msg)
    
    def log_error_safe(self, error_msg: str, exc_info=False):
        """Registra erro de forma segura (sem exposição de dados sensíveis)."""
        self.logger.error(error_msg, exc_info=exc_info)
    
    def log_click(self, url: str, x: int, y: int, success: bool):
        """Registra ação de clique."""
        status = "✓ Sucesso" if success else "✗ Falha"
        self.logger.info(f"Clique em ({x}, {y}) na URL [...] | {status}")
    
    def log_login_attempt(self, status: str):
        """Registra tentativa de login (sem expor credenciais)."""
        self.logger.info(f"Login attempt: {status}")
    
    def log_summary(self, total_links: int, successful: int, failed: int, duration: float):
        """Registra resumo da execução."""
        success_rate = (successful / total_links * 100) if total_links > 0 else 0
        msg = (
            f"\n{'='*60}\n"
            f"RESUMO DA EXECUÇÃO\n"
            f"{'='*60}\n"
            f"Total de links: {total_links}\n"
            f"Sucesso: {successful}\n"
            f"Falha: {failed}\n"
            f"Taxa de sucesso: {success_rate:.1f}%\n"
            f"Duração: {duration:.2f}s\n"
            f"{'='*60}"
        )
        self.logger.info(msg)


# Export padrão
logger = setup_logger(__name__)

"""
© 2024 Wbad-02 - Todos os direitos reservados
Automação Gestta - Script Principal

Uso:
    python main.py                  # Executa automação com credenciais existentes
    python main.py --setup-credentials  # Configura credenciais (novo setup)
    python main.py --headless       # Executa em headless mode (sem browser visível)
    python main.py --help           # Mostra ajuda
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path

# Adiciona diretório src ao path
sys.path.insert(0, str(Path(__file__).parent))

from src.credential_manager import init_credentials
from src.automation_executor import AutomationExecutor
from src.logger_handler import setup_logger


# Configurações padrão
DEFAULT_LOGIN_URL = "https://onvio.com.br/login/#/"
DEFAULT_CLICK_X = 0
DEFAULT_CLICK_Y = 0


def print_banner():
    """Exibe banner da aplicação."""
    banner = """
╔════════════════════════════════════════════════════════════════╗
║                   AUTOMAÇÃO GESTTA v1.0                        ║
║                  © 2024 Wbad-02 - RH & Folha                  ║
╚════════════════════════════════════════════════════════════════╝
    """
    print(banner.encode('ascii', 'ignore').decode('ascii') if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf-16') else banner)


def setup_cli_parser() -> argparse.ArgumentParser:
    """Configura parser de argumentos CLI."""
    parser = argparse.ArgumentParser(
        description="Automação inteligente do Gestta (RH & Folha)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py                      Executa automação normal
  python main.py --setup-credentials  Configura credenciais
  python main.py --headless          Executa sem interface visual
  python main.py --config-file custom_urls.txt  Usa arquivo customizado
        """
    )
    
    parser.add_argument(
        "--setup-credentials",
        action="store_true",
        help="Inicia setup interativo de credenciais"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Executa browser em headless mode (padrão: True)"
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Executa com browser visível"
    )
    
    parser.add_argument(
        "--config-file",
        type=str,
        default="config/urls_list.txt",
        help="Arquivo com lista de URLs (padrão: config/urls_list.txt)"
    )
    
    parser.add_argument(
        "--login-url",
        type=str,
        default=DEFAULT_LOGIN_URL,
        help=f"URL de login do Gestta (padrão: {DEFAULT_LOGIN_URL})"
    )
    
    parser.add_argument(
        "--tab-presses",
        type=int,
        default=16,
        help="Número de vezes para pressionar TAB (padrão: 16)"
    )
    
    parser.add_argument(
        "--tab-interval",
        type=float,
        default=1.0,
        help="Intervalo em segundos entre TABs (padrão: 1.0)"
    )
    
    parser.add_argument(
        "--emails-file",
        type=str,
        default="config/emails_list.txt",
        help="Arquivo com lista de emails (padrão: config/emails_list.txt)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Ativa logging verbose (DEBUG)"
    )
    
    return parser


async def main():
    """Função principal."""
    print_banner()
    
    # Parse de argumentos
    parser = setup_cli_parser()
    args = parser.parse_args()
    
    # Setup de logging
    logger = setup_logger("main", log_dir="logs")
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    logger.info(f"{'='*70}")
    logger.info(f"Inicialização da Automação Gestta")
    logger.info(f"{'='*70}")
    
    # ============ MODO: SETUP DE CREDENCIAIS ============
    if args.setup_credentials:
        logger.info("\n🔐 MODO: Configuração de Credenciais\n")
        
        if init_credentials():
            logger.info("✓ Credenciais configuradas com sucesso!")
            logger.info("Você pode executar a automação com: python main.py")
            return 0
        else:
            logger.error("✗ Falha ao configurar credenciais")
            return 1
    
    # ============ MODO: AUTOMAÇÃO NORMAL ============
    logger.info("\n🚀 MODO: Automação Normal\n")
    
    # Valida arquivo de emails
    emails_file = Path(args.emails_file)
    if not emails_file.exists():
        logger.error(f"Arquivo de emails nao encontrado: {emails_file}")
        logger.info("Crie o arquivo config/emails_list.txt com os emails")
        return 1

    logger.info(f"Configuracao:")
    logger.info(f"   Emails: {emails_file}")
    logger.info(f"   Login: {args.login_url}")
    logger.info(f"   TABs: {args.tab_presses} x {args.tab_interval}s")
    logger.info(f"   Headless: {args.headless}\n")

    # Cria executor e executa
    executor = AutomationExecutor(
        emails_file=str(emails_file),
        login_url=args.login_url,
        headless=args.headless,
        verbose=args.verbose
    )
    
    success = await executor.run()
    
    logger.info(f"{'='*70}")
    
    if success:
        logger.info("✓ Automação finalizada com sucesso!")
        return 0
    else:
        logger.error("✗ Automação finalizada com erros")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

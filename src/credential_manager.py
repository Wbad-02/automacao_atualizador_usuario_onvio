"""
© 2024 Wbad-02 - Todos os direitos reservados
Módulo de Gerenciamento Seguro de Credenciais para Automação Gestta

Este módulo implementa criptografia Fernet (simétrica) para armazenar
credenciais de forma segura, evitando exposição de dados sensíveis.
Conforme LGPD, credenciais nunca são logadas ou expostas em plain text.
"""

import os
import json
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv, set_key
import logging


class CredentialManager:
    """
    Gerencia credenciais do Gestta de forma segura.
    
    Fluxo:
    1. Gera/carrega chave de criptografia
    2. Criptografa credenciais ao armazenar
    3. Descriptografa credenciais ao usar
    4. Nunca expõe dados em logs ou outputs
    """
    
    def __init__(self, env_path: str = ".env"):
        self.env_path = Path(env_path)
        self.logger = logging.getLogger(__name__)
        
        # Garante que .env existe
        if not self.env_path.exists():
            self.env_path.touch()
            self.logger.info("✓ Arquivo .env criado")
        
        load_dotenv(self.env_path)
        
        # Carrega ou gera chave de criptografia
        self._cipher_key = self._get_or_create_cipher_key()
        self.cipher = Fernet(self._cipher_key)
    
    def _get_or_create_cipher_key(self) -> bytes:
        """
        Carrega chave de criptografia ou gera nova.
        
        A chave é armazenada em .env como CIPHER_KEY (apenas para inicialização).
        Em produção, deveria estar em um vault seguro (Vault, AWS Secrets Manager, etc).
        
        Returns:
            bytes: Chave Fernet válida
        """
        cipher_key = os.getenv("CIPHER_KEY")
        
        if not cipher_key:
            # Gera nova chave
            cipher_key = Fernet.generate_key().decode()
            set_key(self.env_path, "CIPHER_KEY", cipher_key)
            self.logger.info("⚠️ Nova chave de criptografia gerada. Guarde em local seguro!")
        
        return cipher_key.encode()
    
    def encrypt_credentials(self, username: str, password: str) -> dict:
        """
        Criptografa credenciais e as armazena em .env.
        
        Args:
            username: Usuário Gestta
            password: Senha Gestta
            
        Returns:
            dict: Status da operação
        """
        try:
            encrypted_user = self.cipher.encrypt(username.encode()).decode()
            encrypted_pass = self.cipher.encrypt(password.encode()).decode()
            
            set_key(self.env_path, "GESTTA_USER_ENC", encrypted_user)
            set_key(self.env_path, "GESTTA_PASS_ENC", encrypted_pass)
            
            self.logger.info("✓ Credenciais armazenadas de forma criptografada")
            return {"success": True, "message": "Credenciais salvas com segurança"}
        
        except Exception as e:
            self.logger.error(f"✗ Erro ao criptografar credenciais: {str(e)}")
            return {"success": False, "message": f"Erro: {str(e)}"}
    
    def decrypt_credentials(self) -> dict:
        """
        Descriptografa credenciais do .env.
        
        Returns:
            dict: {"username": str, "password": str} ou {"error": str}
        """
        try:
            encrypted_user = os.getenv("GESTTA_USER_ENC")
            encrypted_pass = os.getenv("GESTTA_PASS_ENC")
            
            if not encrypted_user or not encrypted_pass:
                self.logger.warning("⚠️ Credenciais não encontradas. Execute setup_credentials() primeiro")
                return {"error": "Credenciais não configuradas"}
            
            username = self.cipher.decrypt(encrypted_user.encode()).decode()
            password = self.cipher.decrypt(encrypted_pass.encode()).decode()
            
            return {"username": username, "password": password}
        
        except Exception as e:
            self.logger.error(f"✗ Erro ao descriptografar credenciais: {str(e)}")
            return {"error": f"Falha na descriptografia: {str(e)}"}
    
    def setup_credentials_interactive(self) -> bool:
        """
        Fluxo interativo para configurar credenciais.
        Solicita usuário e senha via input (seguro - não aparece no terminal).
        
        Returns:
            bool: True se configurado com sucesso
        """
        from getpass import getpass
        
        print("\n🔐 === CONFIGURAÇÃO DE CREDENCIAIS GESTTA ===")
        print("As credenciais serão criptografadas e armazenadas com segurança.\n")
        
        username = input("👤 Usuário Gestta: ").strip()
        if not username:
            self.logger.error("✗ Usuário não pode estar vazio")
            return False
        
        password = getpass("🔑 Senha Gestta (não será exibida): ")
        if not password:
            self.logger.error("✗ Senha não pode estar vazia")
            return False
        
        result = self.encrypt_credentials(username, password)
        
        if result["success"]:
            print(f"\n✓ {result['message']}")
            return True
        else:
            print(f"\n✗ {result['message']}")
            return False


# Funções auxiliares
def init_credentials() -> bool:
    """Inicializa credenciais de forma interativa."""
    manager = CredentialManager()
    return manager.setup_credentials_interactive()


def get_credentials() -> dict:
    """Obtém credenciais descriptografadas."""
    manager = CredentialManager()
    return manager.decrypt_credentials()

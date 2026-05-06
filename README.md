© 2024 Wbad-02 - Todos os direitos reservados

# Automação Gestta v1.2 — RH & Folha

Automação web para o Gestta (Onvio). Faz login único, busca usuários por e-mail e executa a ação de salvar em lote. Suporta múltiplas listas de e-mails processadas em paralelo, cada uma em sua própria aba do browser.

---

## Características

- Login seguro com credenciais criptografadas (Fernet)
- Busca de usuários por e-mail (`input[placeholder="Pesquisar por nome"]`)
- Processamento em lote com política skip & continue
- Múltiplas listas de e-mails em abas paralelas do browser
- Interface desktop com customtkinter (terminais por lista, indicadores visuais)
- Logging estruturado + screenshots automáticos em falha
- Relatório final consolidado por lista

---

## Pré-Requisitos

- Python 3.9+
- pip

---

## Instalação

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

---

## Configurar Credenciais

Na primeira execução, configure as credenciais do Onvio:

```bat
python -m src.main --setup-credentials
```

As credenciais são criptografadas e salvas em `.env`. Nunca commitar esse arquivo.

---

## Listas de E-mails

Crie um ou mais arquivos em `config/` com um e-mail por linha:

```
# config/emails_list.txt
usuario1@empresa.com
usuario2@empresa.com
# linhas com # são ignoradas
```

Para múltiplas listas, crie arquivos adicionais:

```
config/emails_list.txt    → Lista 1
config/emails_list2.txt   → Lista 2
config/emails_list3.txt   → Lista 3
```

Cada lista será processada em uma aba separada do browser, em paralelo.

---

## Uso

### Interface Desktop (recomendado)

Execute `start.bat` e escolha a opção **[1] Interface Desktop**.

Ou diretamente:

```bat
python -m src.desktop_app
```

A interface exibe:
- Um terminal por lista com os logs em tempo real
- Indicador visual por e-mail: verde (sucesso), vermelho (falha), dourado (em andamento)
- Botão **+ Email** para adicionar um e-mail diretamente pela interface

### CLI

```bat
# Uma lista (comportamento padrão)
python -m src.main --emails-file config/emails_list.txt

# Múltiplas listas — cada uma em sua própria aba
python -m src.main --emails-file config/emails_list.txt config/emails_list2.txt

# Com browser visível (debug)
python -m src.main --no-headless --emails-file config/emails_list.txt

# Verbose
python -m src.main --verbose --emails-file config/emails_list.txt
```

---

## Múltiplas Listas em Paralelo

Quando mais de um arquivo é passado, o sistema:

1. Faz login uma única vez na primeira aba
2. Abre uma aba adicional para cada lista extra
3. Processa todas as listas simultaneamente via `asyncio.gather()`
4. Gera relatório consolidado ao final

**Exemplo com 3 listas:**

```bat
python -m src.main ^
  --emails-file config/lista_rh.txt config/lista_folha.txt config/lista_socios.txt
```

### Adicionar e-mail pela interface

O botão **+ Email** na interface desktop adiciona o e-mail à lista que tiver **menos entradas**. Em caso de empate, adiciona na primeira lista.

---

## Relatório Final

Gerado em `logs/automation_report.txt` ao fim de cada execução:

```
[emails_list.txt]  — 48/50 ok, 12.3s
  ✗ usuario_problema@empresa.com
[emails_list2.txt] — 30/30 ok, 8.1s
```

---

## Estrutura do Projeto

```
gestta-automation-v1.2/
├── src/
│   ├── __init__.py
│   ├── main.py                  # Entry point CLI
│   ├── desktop_app.py           # Interface desktop (customtkinter)
│   ├── automation_executor.py   # Orquestra o fluxo completo
│   ├── browser_manager.py       # Gerencia Playwright (multi-tab)
│   ├── credential_manager.py    # Criptografia de credenciais
│   ├── logger_handler.py        # Logging estruturado
│   └── api_server.py            # API REST opcional (porta 59871)
├── config/
│   └── emails_list.txt          # Lista(s) de e-mails
├── logs/                        # Logs e relatórios (gerado em runtime)
├── screenshots/                 # Screenshots de debug (gerado em runtime)
├── .env                         # Credenciais criptografadas (não commitar)
├── .gitignore
├── requirements.txt
├── start.bat
└── README.md
```

---

## Segurança

- Credenciais nunca aparecem em logs
- Dados criptografados com Fernet (AES-128)
- `.env` está no `.gitignore`

---

## Troubleshooting

**"Arquivo de emails não encontrado"**
Crie `config/emails_list.txt` com pelo menos um e-mail.

**"Credenciais não configuradas"**
Execute `python -m src.main --setup-credentials`.

**"Browser initialization failed"**
Execute `playwright install chromium`.

**E-mail não encontrado na busca**
O usuário pode não existir no Gestta ou o e-mail pode estar incorreto. O sistema registra o e-mail em `failed_emails` e continua.

**Timeout após reload**
O sistema re-pesquisa o e-mail automaticamente após cada reload antes de tentar clicar novamente.

---

## API Opcional

Para uso externo ou integrações, suba o servidor:

```bat
uvicorn src.api_server:app --host 0.0.0.0 --port 59871
```

Endpoints disponíveis: `GET /status`, `GET /logs/{index}`, `POST /emails/add`.

---

© 2024 Wbad-02 - Todos os direitos reservados  
**Versão:** 1.2.0 | **Atualizado:** 06/05/2026

# CashFlow

Aplicação web responsiva para organização financeira de empreendedores, pequenos negócios e uso pessoal. O projeto utiliza Flask, SQLAlchemy, SQLite e uma interface mobile-first.

## Funcionalidades

- Cadastro de receitas e despesas;
- Saldo e histórico com filtros por período;
- Relatórios financeiros e exportação em PDF;
- Registros fixos e geração mensal de despesas recorrentes;
- Categorias e produtos reutilizáveis;
- Autenticação de usuários e perfis administrativos;
- Backup e restauração do banco de dados;
- Interface responsiva com suporte a tema claro e escuro.

## Tecnologias

- Python 3.11+
- Flask
- Flask-Login
- Flask-SQLAlchemy
- SQLite para desenvolvimento
- ReportLab para relatórios em PDF
- HTML, CSS e JavaScript

## Execução local

### 1. Clonar e entrar no projeto

```bash
git clone https://github.com/AdrianKoll/CashFlow.git
cd CashFlow
```

### 2. Criar e ativar um ambiente virtual

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Instalar dependências

```bash
python -m pip install -r requirements.txt
```

### 4. Configurar o ambiente

Copie `.env.example` para `.env` ou exporte as variáveis diretamente no shell. O projeto não contém chave secreta nem credencial de acesso no código-fonte.

Para criar o primeiro administrador, configure temporariamente:

```bash
export CASHFLOW_SECRET_KEY="gere-uma-chave-aleatoria-forte"
export CASHFLOW_ADMIN_NAME="Administrador"
export CASHFLOW_ADMIN_USERNAME="seu-usuario"
export CASHFLOW_ADMIN_PASSWORD="sua-senha-com-pelo-menos-12-caracteres"
```

No Windows PowerShell:

```powershell
$env:CASHFLOW_SECRET_KEY = "gere-uma-chave-aleatoria-forte"
$env:CASHFLOW_ADMIN_NAME = "Administrador"
$env:CASHFLOW_ADMIN_USERNAME = "seu-usuario"
$env:CASHFLOW_ADMIN_PASSWORD = "sua-senha-com-pelo-menos-12-caracteres"
```

A aplicação cria o usuário somente quando as três variáveis de administrador estão preenchidas. A senha nunca é armazenada em texto puro. Depois do primeiro acesso, remova as variáveis de criação do administrador do ambiente.

### 5. Executar

```bash
python run.py
```

O servidor local fica disponível em <http://127.0.0.1:5000>. O debug permanece desativado por padrão. Para desenvolvimento local, ele pode ser habilitado conscientemente com `CASHFLOW_DEBUG=true`.

## Configuração de produção

Em produção, defina `CASHFLOW_ENV=production` e uma `CASHFLOW_SECRET_KEY` forte e exclusiva. Use HTTPS e configure `CASHFLOW_SESSION_COOKIE_SECURE=true`. Também é recomendado executar a aplicação por um servidor WSGI, como Gunicorn, atrás de um proxy reverso.

Nunca versionar arquivos `.env`, chaves, senhas, bancos de dados locais ou cópias de backup. O arquivo `.gitignore` deve permanecer ativo para esses artefatos.

## Estrutura

```text
CashFlow/
├── app/
│   ├── database.py
│   ├── models.py
│   └── routes/
├── docs/presentation/
├── static/
├── templates/
├── .env.example
├── requirements.txt
└── run.py
```

## Participação no projeto

Adrian Koll: arquitetura, desenvolvimento backend e frontend, estruturação do banco de dados e engenharia do sistema.

Adrielle Meneses: análise de negócio, levantamento de requisitos, validação do produto, planejamento e estruturação dos fluxos de usuário.

## Status

Projeto de portfólio em evolução. Antes de uso público, recomenda-se adicionar testes automatizados, pipeline de integração contínua, migrações versionadas e revisão de segurança das rotas administrativas.

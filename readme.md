# CashFlow

Aplicação web responsiva para organização financeira de empreendedores, pequenos negócios e uso pessoal. O projeto utiliza Flask, SQLAlchemy, SQLite e uma interface mobile-first.

## Funcionalidades

- Cadastro de receitas e despesas;
- Saldo e histórico com filtros por período;
- Relatórios financeiros e exportação em PDF;
- Registros fixos e geração mensal de despesas recorrentes;
- Categorias e produtos reutilizáveis;
- Autenticação de usuários com senha armazenada em hash;
- Troca de senha e edição de perfil com confirmação da senha atual;
- Cópia de segurança do banco SQLite (criar e baixar) e reset de dados com confirmação de senha;
- Registro de auditoria das ações (login, criação, edição e remoção de dados);
- Proteção CSRF e limite de tentativas de login;
- Interface responsiva com suporte a tema claro e escuro.

## Tecnologias

- Python 3.11+
- Flask
- Flask-Login
- Flask-SQLAlchemy
- Flask-WTF (proteção CSRF)
- Flask-Limiter (limite de tentativas de login)
- SQLite
- ReportLab para relatórios em PDF
- HTML, CSS e JavaScript (sem frameworks)
- pytest e GitHub Actions para testes e integração contínua

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

A aplicação cria o usuário somente quando `CASHFLOW_ADMIN_USERNAME` e `CASHFLOW_ADMIN_PASSWORD` estão preenchidas (o nome é opcional). A senha nunca é armazenada em texto puro. Depois do primeiro acesso, remova as variáveis de criação do administrador do ambiente.

### 5. Executar

```bash
python run.py
```

O servidor local fica disponível em <http://127.0.0.1:5000>. O debug permanece desativado por padrão. Para desenvolvimento local, ele pode ser habilitado conscientemente com `CASHFLOW_DEBUG=true`.

## Testes

```bash
python -m pip install -r requirements-dev.txt
pytest
```

A suíte usa um banco SQLite temporário, sem tocar em dados reais, e cobre:

- configuração de segurança (chave secreta, cookies de sessão, criação do administrador);
- login, logout e proteção das rotas;
- API de movimentações, produtos e registros fixos, incluindo a geração mensal sem duplicar lançamentos;
- resumo financeiro, páginas e relatório em PDF;
- perfil, troca de senha, cópia de segurança e reset de dados;
- proteção CSRF e limite de tentativas de login.

O workflow `.github/workflows/ci.yml` executa os testes em Python 3.11, 3.12 e 3.13 a cada push e pull request para a `main`.

## Configuração de produção

Em produção, defina `CASHFLOW_ENV=production` e uma `CASHFLOW_SECRET_KEY` forte e exclusiva. Use HTTPS e configure `CASHFLOW_SESSION_COOKIE_SECURE=true`. Também é recomendado executar a aplicação por um servidor WSGI, como Gunicorn, atrás de um proxy reverso.

Atrás de um proxy reverso (como Nginx), defina `CASHFLOW_TRUSTED_PROXIES` com o número de proxies confiáveis. Sem isso, o limite de tentativas de login enxerga o IP do proxy e não o do cliente. Deixe `0` quando a aplicação recebe conexões diretas, porque o cabeçalho `X-Forwarded-For` pode ser forjado por qualquer cliente.

Os contadores do limite de login ficam em memória (um por processo). Com vários workers do Gunicorn, aponte `CASHFLOW_RATELIMIT_STORAGE_URI` para um armazenamento compartilhado, como Redis (exige o pacote `redis`).

Nunca versionar arquivos `.env`, chaves, senhas, bancos de dados locais ou cópias de backup. O arquivo `.gitignore` deve permanecer ativo para esses artefatos.

## Segurança

- Senhas armazenadas apenas como hash (Werkzeug); o administrador inicial exige pelo menos 12 caracteres.
- Chave secreta e credenciais vêm do ambiente, nunca do código; em produção a aplicação recusa iniciar sem `CASHFLOW_SECRET_KEY`.
- Cookies de sessão com `HttpOnly` e `SameSite=Lax`, e `Secure` configurável.
- Proteção CSRF em todos os formulários e chamadas da API (token no campo do formulário ou no cabeçalho `X-CSRFToken`).
- Limite de tentativas de login: 5 falhas por usuário e 10 por IP a cada 15 minutos. Só tentativas que falham consomem o limite.
- Reset de dados exige a senha do usuário e cria uma cópia de segurança antes de apagar.

### Limitações conhecidas

- O modelo de usuário tem o campo `role`, mas ainda não há controle de acesso por perfil: qualquer usuário autenticado acessa todas as funções. A aplicação foi pensada para uso individual.
- O logout aceita requisição `GET`.
- Não há migrações versionadas: a compatibilidade com bancos antigos é feita por `ensure_database_columns()`.
- Não há função de restaurar uma cópia de segurança dentro da aplicação; a cópia pode ser baixada.
- Os dados ficam em um único arquivo SQLite, adequado a uso individual ou de pequeno porte.

## Estrutura

```text
CashFlow/
├── .github/workflows/ci.yml   # testes automáticos
├── app/
│   ├── __init__.py            # fábrica da aplicação e extensões
│   ├── database.py
│   ├── helpers.py
│   ├── models.py
│   ├── pdf.py
│   └── routes/                # páginas, autenticação, cópias e API
├── docs/presentation/
├── static/
├── templates/
├── tests/                     # suíte pytest
├── .env.example
├── .gitattributes
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
└── run.py
```

## Participação no projeto

Adrian Koll: arquitetura, desenvolvimento backend e frontend, estruturação do banco de dados e engenharia do sistema.

Adrielle Meneses: análise de negócio, levantamento de requisitos, validação do produto, planejamento e estruturação dos fluxos de usuário.

## Status

Testes automatizados, integração contínua, proteção CSRF e limite de tentativas de login já estão implementados. Os próximos passos são migrações versionadas (Alembic), controle de acesso por perfil e uma revisão de segurança antes de exposição pública ampla.

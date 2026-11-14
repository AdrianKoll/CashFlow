# CashFlow

Aplicação web responsiva para organização financeira de empreendedores, pequenos negócios e uso pessoal. O projeto utiliza Flask, SQLAlchemy, SQLite (desenvolvimento) ou PostgreSQL (produção/Docker) e uma interface mobile-first.

## Funcionalidades

- Cadastro de receitas e despesas;
- Saldo e histórico com filtros por período;
- Relatórios financeiros e exportação em PDF;
- Registros fixos e geração mensal de despesas recorrentes;
- Categorias e produtos reutilizáveis;
- Autenticação de usuários com senha armazenada em hash;
- Troca de senha e edição de perfil com confirmação da senha atual;
- Cópia de segurança do banco (arquivo SQLite ou `pg_dump` no PostgreSQL; criar e baixar) e reset de dados com confirmação de senha;
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
- SQLite (padrão local) e PostgreSQL 17 via psycopg 3
- Gunicorn e Docker Compose
- ReportLab para relatórios em PDF
- HTML, CSS e JavaScript (sem frameworks)
- `pyproject.toml` para metadados e configuração do pytest
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

Alternativa, usando o `pyproject.toml` (instala as mesmas dependências; `.[dev]` inclui o pytest):

```bash
python -m pip install ".[dev]"
```

Os arquivos `requirements*.txt` e o `pyproject.toml` precisam listar as mesmas dependências; um teste (`tests/test_project_metadata.py`) falha se divergirem.

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

## Docker e PostgreSQL

O `docker-compose.yml` sobe a aplicação (Gunicorn) e um PostgreSQL 17 com volume persistente:

```bash
cp .env.example .env     # preencha POSTGRES_PASSWORD, CASHFLOW_SECRET_KEY e o administrador inicial
docker compose up --build
```

A aplicação fica em <http://127.0.0.1:8000> (a porta é publicada só na própria máquina; para expor na internet, use um proxy reverso com HTTPS). O endpoint `/healthz` responde `200` quando a aplicação e o banco funcionam e é usado pelo `HEALTHCHECK` da imagem. As cópias de segurança ficam no volume `backups`.

Para usar PostgreSQL fora do Docker, defina `CASHFLOW_DATABASE_URI`, por exemplo `postgresql://usuario:senha@localhost:5432/cashflow` (os prefixos `postgres://` e `postgresql://` são convertidos para o driver psycopg 3). Para criar cópias de segurança é preciso ter o `pg_dump` instalado, com versão igual ou mais nova que a do servidor.

O Gunicorn roda com 1 worker e 4 threads de propósito: o limite de tentativas de login fica em memória, e vários workers teriam contadores separados (veja "Configuração de produção").

## Testes

```bash
python -m pip install -r requirements-dev.txt
pytest
```

Por padrão a suíte usa um banco SQLite temporário, sem tocar em dados reais. Para rodá-la também no PostgreSQL, aponte para um banco **de teste** (cada teste cria e remove um schema próprio):

```bash
TEST_DATABASE_URL="postgresql+psycopg://usuario:senha@localhost:5432/cashflow_test" pytest
```

A suíte cobre:

- configuração de segurança (chave secreta, cookies de sessão, criação do administrador);
- login, logout e proteção das rotas;
- API de movimentações, produtos e registros fixos, incluindo a geração mensal sem duplicar lançamentos;
- resumo financeiro, páginas e relatório em PDF;
- perfil, troca de senha, cópia de segurança e reset de dados (o reset é cancelado se a cópia falhar);
- endpoint `/healthz`, normalização da URL do banco e migração de bancos antigos;
- proteção CSRF e limite de tentativas de login.

O workflow `.github/workflows/ci.yml` executa os testes em Python 3.11, 3.12 e 3.13 (SQLite), em PostgreSQL 17 e valida a construção da imagem Docker com `/healthz`, a cada push e pull request para a `main`.

## Configuração de produção

Em produção, defina `CASHFLOW_ENV=production` e uma `CASHFLOW_SECRET_KEY` forte e exclusiva. Use HTTPS e configure `CASHFLOW_SESSION_COOKIE_SECURE=true`. Execute a aplicação por um servidor WSGI (a imagem Docker já usa Gunicorn) atrás de um proxy reverso.

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
- Sem `CASHFLOW_DATABASE_URI`, os dados ficam em um único arquivo SQLite, adequado a uso individual ou de pequeno porte; para mais que isso, use PostgreSQL.
- As cópias do PostgreSQL (`.dump`, formato custom do `pg_dump`) só podem ser restauradas fora da aplicação, com `pg_restore`.
- Com mais de um worker, o limite de login precisa de armazenamento compartilhado (Redis).

## Estrutura

```text
CashFlow/
├── .github/workflows/ci.yml   # testes (SQLite e PostgreSQL) e build do Docker
├── app/
│   ├── __init__.py            # fábrica da aplicação e extensões
│   ├── database.py
│   ├── helpers.py
│   ├── models.py
│   ├── pdf.py
│   └── routes/                # páginas, autenticação, cópias, saúde e API
├── docs/presentation/
├── static/
├── templates/
├── tests/                     # suíte pytest
├── .env.example
├── .gitattributes
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml             # metadados e configuração do pytest
├── requirements.txt
├── requirements-dev.txt
└── run.py
```

## Participação no projeto

Adrian Koll: arquitetura, desenvolvimento backend e frontend, estruturação do banco de dados e engenharia do sistema.

Adrielle Meneses: análise de negócio, levantamento de requisitos, validação do produto, planejamento e estruturação dos fluxos de usuário.

## Status

Testes automatizados (SQLite e PostgreSQL), integração contínua, Docker, proteção CSRF e limite de tentativas de login já estão implementados. Os próximos passos são migrações versionadas (Alembic), controle de acesso por perfil e uma revisão de segurança antes de exposição pública ampla.

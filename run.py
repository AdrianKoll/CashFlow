"""
Ponto de entrada da aplicação CashFlow.

Execute com: python run.py
As opções de execução podem ser definidas pelas variáveis CASHFLOW_HOST,
CASHFLOW_PORT e CASHFLOW_DEBUG.
"""

import os

from app import create_app

app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("CASHFLOW_HOST", "127.0.0.1"),
        port=int(os.getenv("CASHFLOW_PORT", "5000")),
        debug=os.getenv("CASHFLOW_DEBUG", "false").strip().lower() == "true",
    )

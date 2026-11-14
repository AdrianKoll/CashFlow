"""Garante que pyproject.toml e os arquivos requirements*.txt não divergem."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _normalize(spec: str) -> str:
    return "".join(spec.split()).lower()


def _requirements(filename: str) -> set[str]:
    lines = (ROOT / filename).read_text(encoding="utf-8").splitlines()
    return {
        _normalize(line)
        for line in lines
        if line.strip() and not line.lstrip().startswith(("#", "-r"))
    }


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_dependencias_do_pyproject_coincidem_com_requirements_txt():
    declared = {_normalize(d) for d in _pyproject()["project"]["dependencies"]}
    assert declared == _requirements("requirements.txt")


def test_dependencias_de_desenvolvimento_coincidem_com_requirements_dev():
    declared = {_normalize(d) for d in _pyproject()["project"]["optional-dependencies"]["dev"]}
    assert declared == _requirements("requirements-dev.txt")


def test_requirements_dev_inclui_as_dependencias_de_producao():
    text = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "-r requirements.txt" in text


def test_versao_minima_do_python_bate_com_o_ci():
    project = _pyproject()["project"]
    assert project["requires-python"] == ">=3.11"
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert '"3.11"' in workflow

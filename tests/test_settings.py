"""Configurações da conta: perfil e troca de senha."""
from werkzeug.security import check_password_hash

from app import db
from app.models import AuditLog, User
from tests.conftest import TEST_PASSWORD, TEST_USERNAME


def _user(app, user_id):
    with app.app_context():
        return db.session.get(User, user_id)


def test_atualiza_perfil_com_senha_correta(app, auth_client, user_id):
    response = auth_client.post(
        "/configuracoes/perfil",
        data={"name": "Novo Nome", "username": "novo_login", "password": TEST_PASSWORD},
        follow_redirects=True,
    )
    assert "Perfil atualizado com sucesso." in response.get_data(as_text=True)
    with app.app_context():
        user = db.session.get(User, user_id)
        assert (user.name, user.username) == ("Novo Nome", "novo_login")
        assert AuditLog.query.filter_by(action="atualizou perfil").count() == 1


def test_perfil_com_senha_errada_nao_altera_nada(app, auth_client, user_id):
    response = auth_client.post(
        "/configuracoes/perfil",
        data={"name": "Invasor", "username": "invasor", "password": "errada"},
        follow_redirects=True,
    )
    assert "Senha atual incorreta" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(User, user_id).username == TEST_USERNAME


def test_perfil_rejeita_usuario_ja_existente(app, auth_client, user_id):
    with app.app_context():
        db.session.add(User(name="Outro", username="ocupado", password_hash="x"))
        db.session.commit()
    response = auth_client.post(
        "/configuracoes/perfil",
        data={"name": "Teste", "username": "ocupado", "password": TEST_PASSWORD},
        follow_redirects=True,
    )
    assert "já está em uso" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(User, user_id).username == TEST_USERNAME


def test_perfil_exige_nome_e_usuario(auth_client):
    response = auth_client.post(
        "/configuracoes/perfil",
        data={"name": " ", "username": "x", "password": TEST_PASSWORD},
        follow_redirects=True,
    )
    assert "obrigatórios" in response.get_data(as_text=True)


def test_troca_de_senha_permite_login_com_a_nova(app, auth_client, user_id):
    response = auth_client.post(
        "/configuracoes/senha",
        data={
            "current_password": TEST_PASSWORD,
            "new_password": "outra-senha-forte-456",
            "confirm_password": "outra-senha-forte-456",
        },
        follow_redirects=True,
    )
    assert "Senha alterada com sucesso." in response.get_data(as_text=True)
    with app.app_context():
        user = db.session.get(User, user_id)
        assert check_password_hash(user.password_hash, "outra-senha-forte-456")
    # Clientes separados: quem já está autenticado é redirecionado em /login.
    new_login = app.test_client().post(
        "/login", data={"username": TEST_USERNAME, "password": "outra-senha-forte-456"}
    )
    assert new_login.status_code == 302
    old_login = app.test_client().post(
        "/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    assert old_login.status_code == 200
    assert "Usuário ou senha inválidos." in old_login.get_data(as_text=True)


def test_troca_de_senha_valida_senha_atual_confirmacao_e_tamanho(app, auth_client, user_id):
    cases = [
        ({"current_password": "errada", "new_password": "novasenha-forte1", "confirm_password": "novasenha-forte1"},
         "Senha atual incorreta"),
        ({"current_password": TEST_PASSWORD, "new_password": "curta", "confirm_password": "curta"},
         "pelo menos 12 caracteres"),
        ({"current_password": TEST_PASSWORD, "new_password": "novasenha-forte1", "confirm_password": "diferente"},
         "confirmação da senha não confere"),
    ]
    for form, expected in cases:
        response = auth_client.post("/configuracoes/senha", data=form, follow_redirects=True)
        assert expected in response.get_data(as_text=True), form
    with app.app_context():
        assert check_password_hash(db.session.get(User, user_id).password_hash, TEST_PASSWORD)

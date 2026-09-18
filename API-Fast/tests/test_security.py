from src.security.passwords import generate_temp_password


def test_temp_password_is_not_1234():
    password = generate_temp_password()
    assert password != "1234"
    assert len(password) >= 8


def test_secret_rejects_default(monkeypatch):
    import src.config.settings as settings_mod
    from src.security.jwt import assert_secret_configured

    monkeypatch.setattr(settings_mod.settings, "AUTH_FAIL_FAST", True)
    monkeypatch.setattr(settings_mod.settings, "SECRET_KEY", "change-me-in-production")
    try:
        assert_secret_configured()
        raised = False
    except RuntimeError:
        raised = True
    assert raised

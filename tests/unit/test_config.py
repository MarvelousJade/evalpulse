from evalpulse.config import Settings


def test_render_postgres_url_selects_psycopg_driver() -> None:
    settings = Settings(database_url="postgresql://user:password@database/evalpulse")
    assert settings.database_url == "postgresql+psycopg://user:password@database/evalpulse"

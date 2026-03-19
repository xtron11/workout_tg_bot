from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Данные для подключения к БД
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    # Токен телеграм бота
    BOT_TOKEN: str

    # ID администратора
    ADMIN_ID: int

    @property
    def DATABASE_URL_asyncpg(self): 
        # URL для асинхронного подключения к PostgreSQL
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Берём переменные из .env файла
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
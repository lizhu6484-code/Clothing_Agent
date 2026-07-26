from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # SenseNova (VLM + LLM)
    SENSENOVA_API_KEY: str = ""
    SENSENOVA_BASE_URL: str = "https://token.sensenova.cn/v1"
    SENSENOVA_VLM_MODEL: str = "sensenova-6.7-flash-lite"
    SENSENOVA_LLM_MODEL: str = "deepseek-v4-flash"

    # QWeather
    QWEATHER_API_KEY: str = ""
    QWEATHER_BASE_URL: str = "https://devapi.qweather.com"

    # DashScope (optional, imagesearch AI fallback)
    DASHSCOPE_API_KEY: str = ""

    # Baidu Map (optional, offline shopping nearby stores)
    BAIDU_MAP_AK: str = ""

    # Pinduoduo DDK (online purchase product search)
    PDD_CLIENT_ID: str = ""
    PDD_CLIENT_SECRET: str = ""
    PDD_PID: str = ""

    # App
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8080
    DB_PATH: str = "./data.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

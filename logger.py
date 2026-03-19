import logging

# Настраиваем логгер
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),  # пишем в файл
        logging.StreamHandler()  # и в консоль
    ]
)

logger = logging.getLogger(__name__)
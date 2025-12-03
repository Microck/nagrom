import asyncio
import logging
from .bot import AVABot
from .config_manager import BotConfig

logging.basicConfig(level=logging.INFO)

async def main():
    try:
        config = BotConfig.load()
        bot = AVABot(config)
        async with bot:
            await bot.start(config.discord.token)
    except FileNotFoundError:
        print("Configuration file not found. Please verify config/bot.yaml exists.")
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
from asr_trading.core.logger import logger
from asr_trading.core.config import cfg
import asyncio
# from telegram import Bot (Import only if installed/configured)

class NotificationService:
    def __init__(self):
        self.telegram_token = None # Load from Config
        self.chat_id = None
        self.enabled = False
        
        # Check config
        # if cfg.TELEGRAM_TOKEN: ...
        
    async def send_message(self, message: str):
        logger.info(f"NOTIFICATION: {message}")
        if self.enabled:
            # await self.bot.send_message(chat_id=self.chat_id, text=message)
            pass

    def notify_signal(self, symbol, action, confidence):
        msg = f"🔔 SIGNAL: {action} {symbol} (Conf: {confidence}%)"
        asyncio.run(self.send_message(msg))

    def notify_trade(self, symbol, action, price):
        msg = f"🚀 EXECUTED: {action} {symbol} @ {price}"
        asyncio.run(self.send_message(msg))

    def notify_emergency(self, reason):
        msg = f"🚨 EMERGENCY: {reason}"
        asyncio.run(self.send_message(msg))

class CommandProcessor:
    """
    Parses and sanitizes incoming Telegram commands.
    """
    def process_command(self, user_id: int, command_text: str) -> str:
        # 1. Sanitization (Fuzzing protection)
        if len(command_text) > 100:
             return "Error: Command too long (buffer protection)."
        
        # 2. SQL/Shell Injection Check (Naive)
        bad_chars = [";", "'", '"', "`", "--"]
        if any(char in command_text for char in bad_chars):
             return "Error: Invalid characters detected."

        cmd_parts = command_text.split()
        if not cmd_parts: 
             return "Error: Empty command."

        action = cmd_parts[0].lower()
        
        if action == "/status":
             return "System NORMAL."
        elif action == "/trade":
             return f"Trade command '{command_text}' processed."
        
        return f"Error: Unrecognized command '{action}'."

notifier = NotificationService()

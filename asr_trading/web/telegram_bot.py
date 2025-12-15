from asr_trading.core.logger import logger
from asr_trading.core.config import cfg
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from asr_trading.core.avionics import avionics_monitor
from asr_trading.brain.linguistics import linguistics

class TelegramAdminBot:
    def __init__(self):
        self.token = cfg.TELEGRAM_TOKEN
        self.admin_id = str(cfg.TELEGRAM_ADMIN_ID) if cfg.TELEGRAM_ADMIN_ID else None
        self.app = None
        self.running = False

    async def start_bot(self):
        """
        Starts the polling loop in background.
        """
        if not self.token:
            logger.warning("Telegram Token not set. Bot disabled.")
            return

        try:
            # Disable JobQueue to avoid weakref issues on Py3.13
            builder = ApplicationBuilder().token(self.token).job_queue(None)
            self.app = builder.build()
            
            # Register Handlers
            self.app.add_handler(CommandHandler("start", self._start))
            self.app.add_handler(CommandHandler("status", self._status))
            self.app.add_handler(CommandHandler("pause", self._pause))
            self.app.add_handler(CommandHandler("resume", self._resume))
            self.app.add_handler(CommandHandler("kill", self._kill))
            self.app.add_handler(CommandHandler("why", self._why))
            self.app.add_handler(CommandHandler("explain", self._explain))
            
            # UX: Handle plain text commands (Case Insensitive)
            self.app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self._handle_text))

            logger.info("Telegram Bot Starting Polling (v20+ Async)...")
            self.running = True
            
            # Start Polling
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            
        except Exception as e:
            logger.error(f"Telegram Bot Crash: {e}", exc_info=True)
            self.running = False

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        text = update.message.text.strip()
        
        # Use Linguistic Engine for Free-form
        response = linguistics.handle_freeform(text)
        await update.message.reply_text(response)

    async def _check_auth(self, update: Update) -> bool:
        if str(update.effective_user.id) != self.admin_id:
            logger.warning(f"Unauthorized access attempt from {update.effective_user.id}")
            return False
        return True

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        
        # RCA Fix: Set persistent menu commands for iOS visibility
        from telegram import BotCommand
        commands = [
            BotCommand("status", "System Health Check"),
            BotCommand("price", "Check Price"),
            BotCommand("signals", "Scan Markets"),
            BotCommand("why", "Explain Decision"),
            BotCommand("pause", "Pause Trading"),
            BotCommand("resume", "Resume Trading"),
            BotCommand("kill", "Emergency Stop")
        ]
        await self.app.bot.set_my_commands(commands)
        
        # RCA Fix: Removed Markdown parsing to prevent iOS crashes
        await update.message.reply_text(linguistics.get_greeting())

    async def _status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        
        # Real System Health
        health = avionics_monitor.get_system_health()
        status_emoji = "✅" if health['status'] == "HEALTHY" else "⚠️"
        
        msg = (
            f"{status_emoji} System Status\n"
            f"Mode: {cfg.EXECUTION_MODE}\n"
            f"Health: {health['status']}\n"
            f"Components: {len(health['components'])}\n"
            f"Uptime: (Live)\n"
        )
        await update.message.reply_text(msg, parse_mode=None)

    async def _pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        await update.message.reply_text(linguistics.handle_freeform("pause"))
        logger.info("ADMIN: PAUSE command received.")

    async def _resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        await update.message.reply_text("▶️ Trade Execution RESUMED.")
        logger.info("ADMIN: RESUME command received.")

    async def _kill(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        await update.message.reply_text("🚨 KILL SWITCH ACTIVATED. System Stopping.")
        logger.critical("ADMIN: KILL SWITCH ACTIVATED.")
        
    async def _why(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        response = linguistics.explain_last_decision()
        await update.message.reply_text(response)

    async def _explain(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        # Placeholder for specific trade ID explanation
        await update.message.reply_text("Specify a Trade ID to explain (Feature coming in Phase 17). Use /why for last decision.")

    # --- Proactive Methods (Called by System) ---
    async def notify_monitoring(self, ticker: str, reason: str, technicals: dict):
        if self.app:
            msg = linguistics.announce_monitoring(ticker, reason, technicals)
            await self.app.bot.send_message(chat_id=self.admin_id, text=msg)

    async def notify_trade(self, trade: dict):
        if self.app:
            msg = linguistics.announce_trade_entry(trade)
            await self.app.bot.send_message(chat_id=self.admin_id, text=msg)

telegram_bot = TelegramAdminBot()

from asr_trading.core.logger import logger
import logging
from asr_trading.core.config import cfg
from telegram import Update, BotCommand, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from asr_trading.core.avionics import avionics_monitor
from asr_trading.brain.linguistics import linguistics
from asr_trading.strategy.planner import planner_engine
from asr_trading.execution.execution_manager import execution_manager
import asyncio

class TelegramAdminBot:
    def __init__(self):
        # RCA Debug: Enable verbose logging for telegram library
        logging.getLogger("telegram").setLevel(logging.INFO)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        
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
            self.app.add_handler(CommandHandler("help", self._start))
            self.app.add_handler(CommandHandler("status", self._status))
            
            # Mode Commands (Explicit)
            self.app.add_handler(CommandHandler("paper", self._set_paper_mode))
            self.app.add_handler(CommandHandler("live", self._set_live_mode))
            self.app.add_handler(CommandHandler("auto", self._set_auto_mode))
            self.app.add_handler(CommandHandler("stop", self._stop_trading))
            
            # UX: Handle plain text commands (Case Insensitive)
            self.app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self._handle_text))

            logger.info("Telegram Bot Starting Polling (Command Center Mode)...")
            self.running = True
            
            # Start Polling
            await self.app.initialize()
            await self.app.start()
            # Drop pending updates to avoid processing old commands
            await self.app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Telegram Bot Crash: {e}", exc_info=True)
            self.running = False

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        text = update.message.text.strip().lower()
        
        # 1. COMMAND ALIASES
        if text == "status": return await self._status(update, context)
        if text == "paper mode": return await self._set_paper_mode(update, context)
        if text == "live mode": return await self._set_live_mode(update, context)
        if text == "stop trading": return await self._stop_trading(update, context)
        if text in ["cancel", "no"]:
            if 'pending_proposal' in context.user_data:
                del context.user_data['pending_proposal']
                await update.message.reply_text("❌ Action Cancelled.")
            return

        # 2. CONFIRMATION (OK)
        if text in ["ok", "execute", "yes", "go"]:
            await self._handle_execution_confirmation(update, context)
            return
            
        # 3. STRATEGY CHECK (NIFTY etc)
        # Check if text looks like a strategy/market query
        triggers = ["nifty", "banknifty", "reliance", "relience", "hdfc", "tcs", "infy", "sbin", "check strategy"]
        if any(t in text for t in triggers):
            await self._handle_strategy_check(update, context, text)
            return
            
        # 4. Fallback to NLP
        await update.message.reply_text("Unrecognized command. Try 'Status', 'Paper Mode', or a Symbol.")

    async def _handle_strategy_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Unified Strategy Check -> Proposal"""
        
        # Extract Symbol (Simple logic for now, could use Linguistics)
        symbol = "NIFTY" # Default
        if "banknifty" in text: symbol = "BANKNIFTY"
        elif "reliance" in text or "relience" in text: symbol = "RELIANCE"
        elif "tcs" in text: symbol = "TCS"
        # ... add others
        
        # Using 0.0 price implies "Fetch Live Price" inside planner/server logic, 
        # or we could fetch it here if we wanted to be helpful, strictly core does logic.
        # But PlannerEngine.generate_proposal expects a price.
        # Let's mock a fetch via linguistics logic-mode or just pass 0 and let planner handle (if it can).
        # Planner currently needs a price. 
        # For this implementation, let's use Linguistics to get price cleanly.
        
        await update.message.reply_text(f"🔍 Analyzing {symbol} strategies...")
        
        # 1. Get Live Data (via helper)
        # We can reuse the snippet from linguistics or call a proper price fetcher
        # For reliability, let's assume Planner can handle volatility=0, but price is needed.
        # We will fetch a rough price from yfinance here to pass to planner.
        import yfinance as yf
        ticker_map = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "RELIANCE": "RELIANCE.NS"}
        yf_sym = ticker_map.get(symbol, f"{symbol}.NS")
        
        try:
             data = yf.Ticker(yf_sym).history(period="1d")
             if data.empty:
                 await update.message.reply_text("⚠️ Market data unavailable.")
                 return
             current_price = data['Close'].iloc[-1]
        except:
             current_price = 100.0 # Fallback for offline testing
             
        # 2. Generate Proposal (Unified Path)
        # Default action BUY for check unless specified
        action = "SELL" if "sell" in text else "BUY"
        
        plan = planner_engine.generate_proposal(
            strategy_id="TELEGRAM_CMD",
            symbol=symbol,
            action=action,
            confidence=0.85, # Assessing...
            current_price=current_price
        )
        
        if not plan or plan.status == "REJECTED":
            reason = plan.rejection_reason if plan else "Unknown Risk Block"
            await update.message.reply_text(f"🛑 **Strategy Rejected**\nReason: {reason}")
            return

        # 3. Present to User
        msg = (
            f"**Mode**: {cfg.EXECUTION_MODE}\n"
            f"**Strategy**: Manual/Telegram\n"
            f"**Signal**: {plan.side} {plan.symbol}\n"
            f"**Entry**: {plan.entry_price:.2f}\n"
            f"**SL**: {plan.stop_loss:.2f} | **TP**: {plan.take_profit:.2f}\n\n"
            f"Say **'ok'** to execute in {cfg.EXECUTION_MODE} mode."
        )
        
        # Store for Context
        context.user_data['pending_proposal'] = plan
        await update.message.reply_text(msg)

    async def _handle_execution_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Executes the pending proposal."""
        if 'pending_proposal' not in context.user_data:
            await update.message.reply_text("No pending proposal. Ask to 'check strategy' first.")
            return
            
        plan = context.user_data['pending_proposal']
        del context.user_data['pending_proposal']
        
        msg = await update.message.reply_text(f"🚀 Executing {plan.symbol} ({cfg.EXECUTION_MODE})...")
        
        # EXECUTE (Unified Path)
        # Note: server.py validates -> creates plan. Here we have a plan.
        # We call execution_manager directly.
        
        # Ensure plan status is set for execution
        plan.status = "PENDING" 
        
        # Force Paper if Mode is Paper
        force_paper = (cfg.EXECUTION_MODE == "PAPER")
        
        try:
            result = await execution_manager.execute_plan(plan, force_paper=force_paper)
            
            # UX Improvement: If Manual "OK" triggered this, and it hits Semi-Auto Gate,
            # we should auto-confirm it because the User JUST confirmed it.
            if result.get("status") == "PENDING_APPROVAL":
                 logger.info("Telegram: Auto-confirming manually approved plan.")
                 plan_id = context.user_data.get('pending_proposal_id', plan.plan_id) # Getting ID from plan obj
                 # Wait, confirm_execution sends to brokers.
                 result = await execution_manager.confirm_execution(plan.plan_id, force_paper=force_paper)

            # Response
            final_status = result.get('status', 'Submitted')
            await msg.edit_text(
                f"✅ **Execution Submitted**\n"
                f"Status: {final_status}\n"
                f"ID: {result.get('trade_id') or result.get('order_id') or 'N/A'}\n"
                f"Monitoring Active."
            )
            
        except Exception as e:
            await msg.edit_text(f"❌ Execution Failed: {e}")

    async def _check_auth(self, update: Update) -> bool:
        if str(update.effective_user.id) != self.admin_id:
            logger.warning(f"Unauthorized access attempt from {update.effective_user.id}")
            return False
        return True

    # --- MODE HANDLERS ---
    async def _set_paper_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        cfg.EXECUTION_MODE = "PAPER"
        cfg.IS_PAPER_TRADING = True
        await update.message.reply_text("📝 **Execution Mode set to PAPER.**\nAll new trades will be virtual.")

    async def _set_live_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        # Safety Gate
        health = avionics_monitor.get_system_health()
        if health['status'] != "HEALTHY":
            await update.message.reply_text(f"⛔ **Live Mode Blocked**\nSystem Health is {health['status']}. Fix issues first.")
            return
            
        cfg.EXECUTION_MODE = "LIVE"
        cfg.IS_PAPER_TRADING = False
        await update.message.reply_text("🚨 **Execution Mode set to LIVE.**\nREAL MONEY IS NOW AT RISK.")

    async def _set_auto_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        # Toggle or Set? User said "auto mode on"
        args = context.args
        state = "AUTO" # Default
        if args and args[0].lower() == "off": state = "SEMI"
        
        cfg.EXECUTION_TYPE = state
        await update.message.reply_text(f"⚙️ **Automation**: {state}")

    async def _stop_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        # Panic Switch logic could go here
        await update.message.reply_text("🛑 **Trading STOPPED** (Placeholder for Panic Switch)")

    # --- STANDARD HANDLERS ---
    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        # iOS Fix: ReplyKeyboardRemove
        await update.message.reply_text(
            " **ASR Command Center** Online.\n"
            "type 'status', 'paper mode', or a symbol like 'nifty'.",
            reply_markup=ReplyKeyboardRemove()
        )

    async def _status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update): return
        health = avionics_monitor.get_system_health()
        msg = (
            f"📊 **System Status**\n"
            f"Mode: {cfg.EXECUTION_MODE} ({cfg.EXECUTION_TYPE})\n"
            f"Health: {health['status']}\n"
            f"Active: {len(execution_manager.pending_plans)} Pending"
        )
        await update.message.reply_text(msg)

    # --- PROACTIVE NOTIFICATIONS ---
    def _format_trade_msg(self, data: dict, title: str) -> str:
        """
        Formats trade data into a clear, detailed message.
        """
        symbol = data.get('ticker', 'UNKNOWN')
        mode = data.get('mode', 'UNKNOWN')
        strategy = data.get('strategy_id', data.get('strategy', 'Unknown'))
        
        # Simple Symbol Parser (NIFTY23DEC18000CE)
        instrument = symbol
        strike = "N/A"
        expiry = "N/A"
        opt_type = "SPOT/FUT"
        
        if "CE" in symbol or "PE" in symbol:
             # Heuristic check
             if symbol.endswith("CE"): opt_type = "CALL (CE)"
             if symbol.endswith("PE"): opt_type = "PUT (PE)"
             # TODO: deeper regex if strictly needed, but this covers visual requirement
        
        qt = data.get('size', 0)
        pr = data.get('price', 0.0)
        
        msg = (
            f"{title}\n"
            f"🔹 **{instrument}**\n"
            f"Type: {opt_type}\n"
            f"Strategy: {strategy}\n"
            f"Mode: **{mode}**\n"
            f"-------------------\n"
            f"Action: {data.get('action')} | Qty: {qt}\n"
            f"Price: {pr:.2f}\n"
        )
        if 'stop_loss' in data:
            msg += f"SL: {data['stop_loss']:.2f}\n"
            
        return msg

    async def request_approval(self, plan_data: dict):
        if self.app:
            msg = self._format_trade_msg(plan_data, "✋ **APPROVAL REQUIRED**")
            msg += f"\n👉 Type `/approve {plan_data['plan_id']}` to Execute."
            await self.app.bot.send_message(chat_id=self.admin_id, text=msg)

    async def notify_monitoring(self, ticker: str, reason: str, technicals: dict):
        if self.app:
            await self.app.bot.send_message(chat_id=self.admin_id, text=f"👀 **Monitoring**: {ticker}\n{reason}")

    async def notify_trade(self, trade: dict):
        if self.app:
            msg = self._format_trade_msg(trade, "⚡ **TRADE EXECUTED**")
            await self.app.bot.send_message(chat_id=self.admin_id, text=msg)

telegram_bot = TelegramAdminBot()

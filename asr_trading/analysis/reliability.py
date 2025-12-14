from asr_trading.core.logger import logger

import numpy as np

class ReliabilityTracker:
    def __init__(self):
        self.stats = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0
        }
        self.returns = [] # List of percentage returns per trade
        self.peak_balance = 10000.0 # Standard assumption or passed in
        self.current_balance = 10000.0

    def calculate_score(self) -> float:
        """Calculates Reliability Score (0-100)"""
        # Simple Logic: Win Rate * 50 + Consistency
        if self.stats["total_trades"] == 0:
            return 50.0 # Neural start
            
        win_rate = self.stats["wins"] / self.stats["total_trades"]
        score = win_rate * 100
        return max(0, min(100, score))

    def get_maturity_level(self):
        score = self.calculate_score()
        if score < 40: return "Newbie"
        if score < 60: return "Growing"
        if score < 75: return "Stable"
        return "Expert"

    def log_trade_result(self, pnl: float):
        self.stats["total_trades"] += 1
        self.stats["total_pnl"] += pnl
        
        # Returns calculation
        pct_return = pnl / self.current_balance
        self.returns.append(pct_return)
        
        # Balance update
        self.current_balance += pnl
        self.peak_balance = max(self.peak_balance, self.current_balance)
        
        # Drawdown calculation
        dd = (self.peak_balance - self.current_balance) / self.peak_balance
        self.stats["max_drawdown"] = max(self.stats["max_drawdown"], dd)

        if pnl > 0:
            self.stats["wins"] += 1
        else:
            self.stats["losses"] += 1
            
        logger.info(f"Reliability Updated: Score={self.calculate_score():.2f}, Level={self.get_maturity_level()}")
        self.log_pro_metrics()

    def log_pro_metrics(self):
        if not self.returns: return
        
        arr = np.array(self.returns)
        std_dev = np.std(arr)
        avg_ret = np.mean(arr)
        
        # Sharpe (Simplified annualized, assuming daily trades)
        sharpe = (avg_ret / std_dev) * np.sqrt(252) if std_dev > 0 else 0
        
        # Sortino (Downside deviation only)
        downside = arr[arr < 0]
        downside_std = np.std(downside) if len(downside) > 0 else 1.0
        sortino = (avg_ret / downside_std) * np.sqrt(252) if len(downside) > 0 else 0
        
        logger.info(f"[PRO METRICS] Sharpe: {sharpe:.2f} | Sortino: {sortino:.2f} | MaxDD: {self.stats['max_drawdown']*100:.2f}%")

reliability_engine = ReliabilityTracker()

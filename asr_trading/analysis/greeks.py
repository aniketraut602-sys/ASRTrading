import numpy as np
from scipy.stats import norm
from asr_trading.core.logger import logger

class BlackScholes:
    """
    Professional-grade Black-Scholes-Merton model for European Options.
    """
    
    @staticmethod
    def d1(S, K, T, r, sigma):
        return (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))

    @staticmethod
    def d2(S, K, T, r, sigma):
        return BlackScholes.d1(S, K, T, r, sigma) - sigma * np.sqrt(T)

    @staticmethod
    def calculate_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"):
        """
        S: Spot Price
        K: Strike Price
        T: Time to Expiry (in years)
        r: Risk-free rate (decimal)
        sigma: Volatility (decimal)
        option_type: 'call' or 'put'
        """
        if T <= 0 or sigma <= 0 or S <= 0:
            return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0}

        d1 = BlackScholes.d1(S, K, T, r, sigma)
        d2 = BlackScholes.d2(S, K, T, r, sigma)
        
        N_prime = norm.pdf(d1)
        
        if option_type == "call":
            delta = norm.cdf(d1)
            gamma = N_prime / (S * sigma * np.sqrt(T))
            theta = (- (S * N_prime * sigma) / (2 * np.sqrt(T)) 
                     - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365.0
            vega = (S * np.sqrt(T) * N_prime) / 100.0
            rho = (K * T * np.exp(-r * T) * norm.cdf(d2)) / 100.0
        else: # put
            delta = norm.cdf(d1) - 1
            gamma = N_prime / (S * sigma * np.sqrt(T))
            theta = (- (S * N_prime * sigma) / (2 * np.sqrt(T)) 
                     + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365.0
            vega = (S * np.sqrt(T) * N_prime) / 100.0
            rho = (-K * T * np.exp(-r * T) * norm.cdf(-d2)) / 100.0

        return {
            "delta": round(delta, 4),
            "gamma": round(gamma, 4),
            "theta": round(theta, 4),
            "vega": round(vega, 4),
            "rho": round(rho, 4)
        }

greeks_engine = BlackScholes()

from datetime import datetime, timedelta
import math

class OptionMapper:
    """
    Maps Spot Price -> Option Symbol (Indian Market Standard).
    Example: NIFTY 21000 -> NIFTY23DEC21000CE
    """
    
    @staticmethod
    def get_atm_strike(spot_price: float, step: int = 50) -> int:
        return int(round(spot_price / step) * step)

    @staticmethod
    def get_symbol(underlying: str, spot_price: float, side: str, expiry_date: datetime = None) -> str:
        """
        Generates a standardized option symbol.
        In a real system, this would query the broker's instrument master.
        Here we generate a semantic string for the Command Center.
        """
        if "NIFTY" not in underlying and "BANK" not in underlying:
             return underlying # Equity, no mapping needed yet

        step = 100 if "BANK" in underlying else 50
        strike = OptionMapper.get_atm_strike(spot_price, step)
        
        # Adjust for OTM?
        # If BUY CALL -> ATM or OTM? Scalping usually prefers ATM or ITM.
        # Let's stick to ATM for now.
        
        type_suffix = "CE" if side == "BUY" else "PE" # Assuming Long Call / Long Put for "BUY" signal
        # Note: If Strategy says "SELL", does it mean Short Selling Spot or Buying Put?
        # ASR 'Scalping' usually implies Directional Long.
        # BUY = Long Call, SELL = Long Put (Hedging/Reversal) or Short Call?
        # Let's assume BUY = CALL, SELL (if signal is short) = PUT.
        
        if side == "SELL":
            type_suffix = "PE"
            # logic: Bearish signal -> Buy Put
        
        # Expiry Format (e.g., 21DEC)
        if not expiry_date:
            expiry_date = datetime.now() # Mock: Today/Next Thursday
            
        exp_str = expiry_date.strftime("%d%b").upper()
        
        # Example: NIFTY23DEC21000CE
        # Simplify for prototype:
        return f"{underlying}_{exp_str}_{strike}_{type_suffix}"

options_mapper = OptionMapper()

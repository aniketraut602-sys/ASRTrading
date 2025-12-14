import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os

# Create dummy DF
df = pd.DataFrame({
    'Close': [100.0, 101.0, 102.0, 101.5, 103.0] * 20, # 100 rows
    'High': [104.0] * 100,
    'Low': [99.0] * 100,
    'Open': [100.0] * 100,
    'Volume': [1000] * 100
})

print("Original DF shape:", df.shape)

try:
    df['RSI'] = ta.rsi(df['Close'], length=14)
    print("RSI Calculated. Shape:", df.shape)
    print(df.tail())
except Exception as e:
    print(f"RSI Failed: {e}")

try:
    st = ta.supertrend(df['High'], df['Low'], df['Close'], length=7, multiplier=3.0)
    print("SuperTrend Calculated.")
    print(st.head())
    df = pd.concat([df, st], axis=1)
except Exception as e:
    print(f"SuperTrend Failed: {e}")

# Check data na
print("NaNs before drop:")
print(df.isna().sum())

df.dropna(inplace=True)
print("Shape after drop:", df.shape)

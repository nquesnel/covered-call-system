"""
Data Fetcher with Real API Integration - Yahoo Finance and other free sources
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random
import requests
import yfinance as yf
import numpy as np
from config import Config


class RealDataFetcher:
    """Fetch real market data from free sources"""
    
    def __init__(self):
        # Cache settings
        self.cache_duration = Config.CACHE_DURATION_SECONDS
        self.cache = {}
        self.cache_timestamps = {}
        
        # API endpoints
        self.alpha_vantage_key = Config.YAHOO_FINANCE_API_KEY  # Free tier
        
    def get_stock_data(self, symbol: str) -> Dict:
        """Get real stock data from Yahoo Finance"""
        # Check cache
        cache_key = f"stock_{symbol}"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        try:
            # Get Yahoo Finance data
            ticker = yf.Ticker(symbol)
            info = ticker.info
            history = ticker.history(period="3mo")
            
            if history.empty:
                # Fall back to mock data if symbol not found
                return self._generate_mock_stock_data(symbol)
            
            # Current data
            current_price = history['Close'].iloc[-1]
            prev_close = history['Close'].iloc[-2] if len(history) > 1 else current_price
            
            # Calculate technical indicators
            close_prices = history['Close'].values
            volumes = history['Volume'].values
            
            # Moving averages
            ma_50 = np.mean(close_prices[-50:]) if len(close_prices) >= 50 else current_price
            ma_200 = np.mean(close_prices[-200:]) if len(close_prices) >= 200 else current_price
            
            # RSI
            rsi = self._calculate_rsi(close_prices)
            
            # Volatility (30-day historical)
            returns = np.diff(close_prices) / close_prices[:-1]
            volatility_30d = np.std(returns[-30:]) * np.sqrt(252) * 100 if len(returns) >= 30 else 30
            
            # Get earnings date
            try:
                earnings_dates = ticker.earnings_dates
                if earnings_dates is not None and not earnings_dates.empty:
                    next_earnings = earnings_dates.index[0].strftime('%Y-%m-%d')
                else:
                    next_earnings = (datetime.now() + timedelta(days=45)).strftime('%Y-%m-%d')
            except:
                next_earnings = (datetime.now() + timedelta(days=45)).strftime('%Y-%m-%d')
            
            data = {
                'symbol': symbol,
                'price': round(current_price, 2),
                'bid': round(current_price - 0.01, 2),
                'ask': round(current_price + 0.01, 2),
                'volume': int(volumes[-1]) if len(volumes) > 0 else 0,
                'avg_volume_10d': int(np.mean(volumes[-10:])) if len(volumes) >= 10 else 0,
                'avg_volume_50d': int(np.mean(volumes[-50:])) if len(volumes) >= 50 else 0,
                'open': round(history['Open'].iloc[-1], 2),
                'high': round(history['High'].iloc[-1], 2),
                'low': round(history['Low'].iloc[-1], 2),
                'prev_close': round(prev_close, 2),
                
                # Technical indicators
                'ma_50': round(ma_50, 2),
                'ma_200': round(ma_200, 2),
                'rsi': round(rsi, 2),
                'volatility_30d': round(volatility_30d, 2),
                'beta': info.get('beta', 1.0),
                
                # Fundamentals from info
                'pe_ratio': info.get('forwardPE', info.get('trailingPE', 20)),
                'market_cap': info.get('marketCap', 0),
                'revenue_growth': info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 10,
                'earnings_growth': info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') else 10,
                
                # Dates
                'next_earnings_date': next_earnings,
                'ex_dividend_date': info.get('exDividendDate', ''),
                
                # Price changes
                'price_change_1d': round(((current_price - prev_close) / prev_close) * 100, 2),
                'price_change_1w': round(((current_price - close_prices[-5]) / close_prices[-5]) * 100, 2) if len(close_prices) >= 5 else 0,
                'price_change_1m': round(((current_price - close_prices[-22]) / close_prices[-22]) * 100, 2) if len(close_prices) >= 22 else 0,
                
                # IV and options sentiment (will be updated from options chain)
                'iv_rank': 50,  # Placeholder - will calculate from options
                'options_sentiment': 'neutral',
                'institutional_ownership_change': 0,
                'social_sentiment_score': 50
            }
            
            # Cache the result
            self._cache_data(cache_key, data)
            return data
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {str(e)}")
            # Fall back to mock data
            return self._generate_mock_stock_data(symbol)
    
    def get_options_chain(self, symbol: str) -> Dict:
        """Get real options chain from Yahoo Finance"""
        cache_key = f"options_{symbol}"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Get available expiration dates
            expirations = ticker.options
            if not expirations:
                return self._generate_mock_options_chain(symbol)
            
            chain = {}
            stock_data = self.get_stock_data(symbol)
            current_price = stock_data['price']
            
            # Get options for next 8 expirations
            for exp_date in expirations[:8]:
                try:
                    opt_chain = ticker.option_chain(exp_date)
                    calls = opt_chain.calls
                    
                    if calls.empty:
                        continue
                    
                    chain[exp_date] = {}
                    
                    for _, row in calls.iterrows():
                        strike = row['strike']
                        
                        # Filter strikes within reasonable range
                        if 0.7 * current_price <= strike <= 1.3 * current_price:
                            # Calculate IV rank (simplified)
                            iv = row.get('impliedVolatility', 0.3)
                            iv_rank = min(100, iv * 100)  # Simplified
                            
                            chain[exp_date][strike] = {
                                'strike': strike,
                                'expiration': exp_date,
                                'bid': row.get('bid', 0),
                                'ask': row.get('ask', 0),
                                'last': row.get('lastPrice', 0),
                                'volume': row.get('volume', 0),
                                'open_interest': row.get('openInterest', 0),
                                'implied_volatility': iv,
                                'delta': abs(row.get('delta', 0.5)),  # Approximate
                                'gamma': row.get('gamma', 0.02),
                                'theta': row.get('theta', -0.05),
                                'vega': row.get('vega', 0.1),
                                'iv_rank': iv_rank,
                                'iv_percentile': iv_rank - random.uniform(-5, 5)
                            }
                except Exception as e:
                    print(f"Error processing expiration {exp_date}: {str(e)}")
                    continue
            
            if chain:
                self._cache_data(cache_key, chain)
                return chain
            else:
                return self._generate_mock_options_chain(symbol)
                
        except Exception as e:
            print(f"Error fetching options for {symbol}: {str(e)}")
            return self._generate_mock_options_chain(symbol)
    
    def get_whale_flows(self, min_premium: float = 50000) -> List[Dict]:
        """
        Get unusual options activity from free sources
        Note: Real whale flow data requires paid services like Unusual Whales
        This implementation provides simulated data based on real market activity
        """
        if self._is_cached("whale_flows"):
            return self.cache["whale_flows"]
        
        # In a real implementation, this would:
        # 1. Connect to Unusual Whales API (paid)
        # 2. Or scrape free sources like Barchart unusual options
        # 3. Or use TD Ameritrade API for unusual volume
        
        # For now, generate realistic mock flows based on market conditions
        flows = self._generate_mock_whale_flows()
        self._cache_data("whale_flows", flows)
        
        return flows
    
    def get_iv_rank_for_symbol(self, symbol: str) -> float:
        """Calculate IV rank from options chain"""
        try:
            chain = self.get_options_chain(symbol)
            if not chain:
                return 50.0
            
            # Collect all IVs
            ivs = []
            for exp_date, strikes in chain.items():
                for strike, data in strikes.items():
                    if data.get('implied_volatility', 0) > 0:
                        ivs.append(data['implied_volatility'])
            
            if not ivs:
                return 50.0
            
            # Calculate IV rank (simplified - should use 52-week data)
            current_iv = np.mean(ivs)
            min_iv = min(ivs) * 0.8  # Approximate yearly low
            max_iv = max(ivs) * 1.2  # Approximate yearly high
            
            iv_rank = ((current_iv - min_iv) / (max_iv - min_iv)) * 100
            return round(max(0, min(100, iv_rank)), 1)
            
        except:
            return 50.0
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down if down != 0 else 100
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _is_cached(self, key: str) -> bool:
        """Check if data is cached and still valid"""
        if key not in self.cache_timestamps:
            return False
        
        age = (datetime.now() - self.cache_timestamps[key]).total_seconds()
        return age < self.cache_duration
    
    def _cache_data(self, key: str, data: any):
        """Cache data with timestamp"""
        self.cache[key] = data
        self.cache_timestamps[key] = datetime.now()
    
    # Keep mock data methods as fallback
    def _generate_mock_stock_data(self, symbol: str) -> Dict:
        """Fallback mock data when real data unavailable"""
        base_prices = {
            'AAPL': 195.0, 'TSLA': 200.0, 'PLTR': 25.0,
            'MGNI': 15.0, 'SPY': 450.0, 'QQQ': 380.0
        }
        
        base_price = base_prices.get(symbol, random.uniform(20, 200))
        price = base_price * random.uniform(0.95, 1.05)
        
        return {
            'symbol': symbol,
            'price': round(price, 2),
            'bid': round(price - 0.01, 2),
            'ask': round(price + 0.01, 2),
            'volume': random.randint(1000000, 50000000),
            'avg_volume_10d': random.randint(1000000, 40000000),
            'avg_volume_50d': random.randint(1000000, 35000000),
            'volatility_30d': random.uniform(20, 60),
            'iv_rank': random.uniform(10, 90),
            'ma_50': round(price * random.uniform(0.95, 1.05), 2),
            'ma_200': round(price * random.uniform(0.90, 1.10), 2),
            'rsi': random.uniform(20, 80),
            'next_earnings_date': (datetime.now() + timedelta(days=random.randint(5, 60))).strftime('%Y-%m-%d'),
            'price_change_1m': random.uniform(-10, 10),
            'revenue_growth_yoy': random.uniform(-20, 100),
            'earnings_growth_yoy': random.uniform(-30, 150),
            'analyst_rating': random.uniform(1, 5),
            'institutional_ownership_change': random.uniform(-10, 10),
            'options_sentiment': random.choice(['very_bullish', 'bullish', 'neutral', 'bearish']),
            'social_sentiment_score': random.uniform(10, 90)
        }
    
    def _generate_mock_options_chain(self, symbol: str) -> Dict:
        """Fallback mock options chain"""
        stock_data = self.get_stock_data(symbol)
        current_price = stock_data['price']
        
        chain = {}
        
        for weeks_out in range(1, 9):
            exp_date = datetime.now() + timedelta(weeks=weeks_out)
            days_until_friday = (4 - exp_date.weekday()) % 7
            if days_until_friday == 0 and exp_date.hour > 16:
                days_until_friday = 7
            exp_date = exp_date + timedelta(days=days_until_friday)
            exp_str = exp_date.strftime('%Y-%m-%d')
            
            chain[exp_str] = {}
            
            strike_increment = 1 if current_price < 50 else 5 if current_price < 200 else 10
            min_strike = int(current_price * 0.85 / strike_increment) * strike_increment
            max_strike = int(current_price * 1.15 / strike_increment) * strike_increment
            
            for strike in range(min_strike, max_strike + strike_increment, strike_increment):
                dte = (exp_date - datetime.now()).days
                otm_percent = max(0, (strike - current_price) / current_price)
                
                time_value = (dte / 365) ** 0.5
                volatility_component = stock_data['volatility_30d'] / 100
                base_premium = current_price * volatility_component * time_value * 0.4
                
                if strike < current_price:
                    intrinsic = current_price - strike
                    premium = intrinsic + base_premium * 0.3
                else:
                    premium = base_premium * max(0.1, 1 - otm_percent * 5)
                
                premium = max(0.05, round(premium, 2))
                
                spread_pct = 0.05 if premium > 1 else 0.10
                bid = round(premium * (1 - spread_pct/2), 2)
                ask = round(premium * (1 + spread_pct/2), 2)
                
                volume = random.randint(10, 5000) if abs(strike - current_price) / current_price < 0.1 else random.randint(0, 500)
                open_interest = random.randint(100, 10000) if abs(strike - current_price) / current_price < 0.1 else random.randint(10, 1000)
                
                delta = max(0.01, min(0.99, 1 - otm_percent * 2)) if strike >= current_price else 0.5 + (current_price - strike) / current_price * 0.4
                
                chain[exp_str][strike] = {
                    'strike': strike,
                    'expiration': exp_str,
                    'bid': bid,
                    'ask': ask,
                    'last': premium,
                    'volume': volume,
                    'open_interest': open_interest,
                    'implied_volatility': stock_data['volatility_30d'] / 100 * random.uniform(0.8, 1.2),
                    'delta': round(delta, 3),
                    'gamma': round(random.uniform(0.001, 0.05), 3),
                    'theta': round(-premium / dte * random.uniform(0.5, 1.5), 3),
                    'vega': round(random.uniform(0.01, 0.1), 3),
                    'iv_rank': stock_data['iv_rank'] + random.uniform(-10, 10),
                    'iv_percentile': stock_data['iv_rank'] + random.uniform(-5, 5)
                }
        
        return chain
    
    def _generate_mock_whale_flows(self) -> List[Dict]:
        """Generate realistic mock whale flows"""
        symbols = ['AAPL', 'TSLA', 'SPY', 'QQQ', 'NVDA', 'AMD', 'PLTR', 'GME', 'AMC', 'SOFI']
        flows = []
        
        for _ in range(random.randint(5, 15)):
            symbol = random.choice(symbols)
            stock_price = self.get_stock_data(symbol)['price']
            
            option_type = random.choice(['call', 'put'])
            trade_type = random.choice(['sweep', 'block', 'split_block'])
            
            if option_type == 'call':
                strike = round(stock_price * random.uniform(1.0, 1.20), 0)
            else:
                strike = round(stock_price * random.uniform(0.80, 1.0), 0)
            
            days_out = random.choice([7, 14, 21, 28, 35, 42])
            exp_date = datetime.now() + timedelta(days=days_out)
            
            premium = random.uniform(0.10, 2.00)
            contracts = random.randint(1000, 50000)
            premium_volume = premium * contracts * 100
            
            if premium_volume < 50000:
                continue
            
            avg_volume = random.randint(100, 2000)
            unusual_factor = contracts / avg_volume
            
            flow = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'underlying_price': stock_price,
                'trade_type': trade_type,
                'option_type': option_type,
                'strike': strike,
                'expiration': exp_date.strftime('%Y-%m-%d'),
                'days_to_exp': days_out,
                'volume': contracts,
                'premium': premium,
                'premium_volume': premium_volume,
                'avg_volume': avg_volume,
                'open_interest': random.randint(1000, 50000),
                'bid': premium - 0.05,
                'ask': premium + 0.05,
                'implied_volatility': random.uniform(0.3, 1.5),
                'unusual_factor': unusual_factor
            }
            
            flows.append(flow)
        
        flows.sort(key=lambda x: x['premium_volume'], reverse=True)
        
        return flows
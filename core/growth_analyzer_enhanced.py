"""
Enhanced Growth Analyzer - Better differentiation between growth and value stocks
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics


class GrowthAnalyzerEnhanced:
    """Analyze stocks with better growth vs value differentiation"""
    
    def __init__(self):
        # Growth score thresholds
        self.AGGRESSIVE_THRESHOLD = 25    # Below 25: Aggressive calls OK
        self.MODERATE_THRESHOLD = 50      # 25-50: Moderate strategy
        self.CONSERVATIVE_THRESHOLD = 75  # 50-75: Conservative only
        # Above 75: NO COVERED CALLS - High growth protection
        
        # Known growth stocks that should score high
        self.known_growth_stocks = {
            'PLTR': 85,  # Palantir - high growth AI play
            'TSLA': 80,  # Tesla - volatile growth
            'NVDA': 85,  # Nvidia - AI leader
            'AMD': 75,   # AMD - semiconductor growth
            'NET': 80,   # Cloudflare
            'DDOG': 75,  # Datadog
            'SNOW': 80,  # Snowflake
            'CRWD': 75,  # Crowdstrike
            'ABNB': 70,  # Airbnb
            'COIN': 75,  # Coinbase - crypto play
            'SOFI': 70,  # SoFi - fintech growth
            'UPST': 75,  # Upstart
            'RBLX': 70,  # Roblox
            'U': 75,     # Unity
            'SQ': 70,    # Block (Square)
            'SHOP': 75,  # Shopify
            'ROKU': 65,  # Roku
            'ZM': 60,    # Zoom
            'ARKK': 70,  # ARK Innovation ETF
        }
        
        # Known value/income stocks that should score low
        self.known_value_stocks = {
            'T': 15,      # AT&T - high yield
            'VZ': 15,     # Verizon - high yield
            'XOM': 20,    # Exxon - energy value
            'CVX': 20,    # Chevron - energy value
            'IBM': 20,    # IBM - value play
            'INTC': 25,   # Intel - value turnaround
            'F': 20,      # Ford - cyclical value
            'GM': 20,     # GM - cyclical value
            'BAC': 25,    # Bank of America
            'WFC': 25,    # Wells Fargo
            'JPM': 30,    # JP Morgan
            'JNJ': 25,    # Johnson & Johnson
            'PG': 25,     # Procter & Gamble
            'KO': 20,     # Coca-Cola
            'PEP': 25,    # Pepsi
            'MCD': 25,    # McDonald's
            'WMT': 30,    # Walmart
            'HD': 30,     # Home Depot
            'XPO': 35,    # XPO Logistics - your example
            'HWM': 25,    # Howmet Aerospace - your example
        }
        
        # Sector growth tendencies
        self.growth_sectors = ['Technology', 'Communication Services', 'Consumer Discretionary']
        self.value_sectors = ['Utilities', 'Energy', 'Consumer Staples', 'Financials']
    
    def calculate_growth_score(self, symbol: str, market_data: Dict) -> Dict:
        """
        Calculate comprehensive growth score with better differentiation
        """
        symbol = symbol.upper()
        
        # Check if we have a predefined score for known stocks
        if symbol in self.known_growth_stocks:
            base_score = self.known_growth_stocks[symbol]
            variance = self._calculate_variance_adjustment(market_data)
            total_score = max(0, min(100, base_score + variance))
        elif symbol in self.known_value_stocks:
            base_score = self.known_value_stocks[symbol]
            variance = self._calculate_variance_adjustment(market_data)
            total_score = max(0, min(100, base_score + variance))
        else:
            # Calculate from market data
            scores = {}
            
            # Start with market cap bias
            market_cap = market_data.get('market_cap', 0)
            if market_cap > 0:
                if market_cap < 2_000_000_000:  # Small cap - growth potential
                    base_score = 60
                elif market_cap < 10_000_000_000:  # Mid cap
                    base_score = 50
                else:  # Large cap - typically value
                    base_score = 30
            else:
                base_score = 50
            
            # Adjust based on actual metrics
            scores['momentum'] = self._calculate_momentum_score(market_data)
            scores['volatility'] = self._calculate_volatility_score(market_data)
            scores['fundamentals'] = self._calculate_fundamentals_score(market_data)
            scores['technicals'] = self._calculate_technical_score(market_data)
            
            # Weight the scores
            weights = {
                'momentum': 0.30,
                'volatility': 0.25,
                'fundamentals': 0.25,
                'technicals': 0.20
            }
            
            weighted_score = sum(scores[key] * weights[key] for key in scores)
            total_score = (base_score * 0.3) + (weighted_score * 0.7)
        
        # Determine strategy recommendation
        strategy = self._get_strategy_recommendation(total_score)
        
        return {
            'symbol': symbol,
            'total_score': round(total_score),
            'strategy': strategy,
            'protect_position': total_score > self.CONSERVATIVE_THRESHOLD,
            'score_confidence': self._get_score_confidence(symbol, market_data),
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_variance_adjustment(self, data: Dict) -> float:
        """Adjust predefined scores based on recent performance"""
        adjustment = 0
        
        # Recent price performance can shift score
        if 'price_change_1m' in data:
            if data['price_change_1m'] > 30:
                adjustment += 10
            elif data['price_change_1m'] > 15:
                adjustment += 5
            elif data['price_change_1m'] < -20:
                adjustment -= 10
            elif data['price_change_1m'] < -10:
                adjustment -= 5
        
        # High volatility increases growth characteristics
        if 'volatility_30d' in data:
            if data['volatility_30d'] > 60:
                adjustment += 5
            elif data['volatility_30d'] < 20:
                adjustment -= 5
        
        return adjustment
    
    def _calculate_momentum_score(self, data: Dict) -> float:
        """Calculate momentum with better scaling"""
        score = 0
        
        # Price performance (heavily weighted)
        if 'price_change_1m' in data:
            change_1m = data['price_change_1m']
            if change_1m > 30:
                score += 40
            elif change_1m > 20:
                score += 30
            elif change_1m > 10:
                score += 20
            elif change_1m > 0:
                score += 10
            else:
                score += max(-20, change_1m)  # Negative performance hurts score
        
        # Trend strength
        if all(k in data for k in ['price', 'ma_50', 'ma_200']):
            price = data['price']
            ma50 = data['ma_50']
            ma200 = data['ma_200']
            
            # Strong uptrend
            if price > ma50 > ma200:
                score += 30
            # Uptrend
            elif price > ma50:
                score += 20
            # Downtrend
            elif price < ma50 < ma200:
                score -= 20
            # Weak
            else:
                score -= 10
        
        # RSI momentum
        if 'rsi' in data:
            rsi = data['rsi']
            if 60 < rsi < 80:  # Strong but not overbought
                score += 20
            elif rsi > 80:  # Overbought
                score += 10
            elif rsi < 30:  # Oversold
                score -= 10
        
        return max(0, min(100, score + 50))  # Normalize to 0-100
    
    def _calculate_volatility_score(self, data: Dict) -> float:
        """Higher volatility = higher growth characteristics"""
        score = 0
        
        if 'volatility_30d' in data:
            vol = data['volatility_30d']
            if vol > 80:
                score = 90
            elif vol > 60:
                score = 75
            elif vol > 40:
                score = 60
            elif vol > 25:
                score = 40
            else:
                score = 20
        
        # Beta adjustment
        if 'beta' in data:
            beta = data.get('beta', 1.0)
            if beta > 1.5:
                score += 10
            elif beta < 0.8:
                score -= 10
        
        return max(0, min(100, score))
    
    def _calculate_fundamentals_score(self, data: Dict) -> float:
        """Growth fundamentals scoring"""
        score = 50
        
        # Revenue growth is key
        if 'revenue_growth' in data:
            growth = data['revenue_growth']
            if growth > 50:
                score += 30
            elif growth > 25:
                score += 20
            elif growth > 10:
                score += 10
            elif growth < 0:
                score -= 20
        
        # P/E ratio - growth stocks often have high P/E
        if 'pe_ratio' in data:
            pe = data['pe_ratio']
            if pe > 50:
                score += 10  # High P/E suggests growth expectations
            elif pe < 15:
                score -= 10  # Low P/E suggests value stock
        
        # Analyst sentiment
        if 'analyst_rating' in data:
            rating = data['analyst_rating']
            if rating >= 4.5:
                score += 15
            elif rating <= 2.5:
                score -= 15
        
        return max(0, min(100, score))
    
    def _calculate_technical_score(self, data: Dict) -> float:
        """Technical indicators for growth"""
        score = 50
        
        # Price relative to 52-week high
        if all(k in data for k in ['price', '52_week_high', '52_week_low']):
            price = data['price']
            high_52 = data['52_week_high']
            low_52 = data['52_week_low']
            
            # Position in 52-week range
            if high_52 > low_52:
                position = (price - low_52) / (high_52 - low_52)
                if position > 0.8:  # Near 52-week high
                    score += 20
                elif position > 0.6:
                    score += 10
                elif position < 0.3:  # Near 52-week low
                    score -= 10
        
        return max(0, min(100, score))
    
    def _get_strategy_recommendation(self, score: float) -> Dict:
        """Recommend covered call strategy based on growth score"""
        if score < self.AGGRESSIVE_THRESHOLD:
            return {
                'strategy': 'AGGRESSIVE',
                'description': 'Low growth - Maximize income with aggressive strikes',
                'strike_guidance': 'ATM to 2% OTM',
                'expiration_guidance': '30-45 DTE',
                'protection_level': 'LOW'
            }
        elif score < self.MODERATE_THRESHOLD:
            return {
                'strategy': 'MODERATE',
                'description': 'Moderate growth - Balance income and upside',
                'strike_guidance': '3-5% OTM',
                'expiration_guidance': '30-45 DTE',
                'protection_level': 'MEDIUM'
            }
        elif score < self.CONSERVATIVE_THRESHOLD:
            return {
                'strategy': 'CONSERVATIVE',
                'description': 'High growth - Protect upside potential',
                'strike_guidance': '7-10% OTM minimum',
                'expiration_guidance': '30 DTE max',
                'protection_level': 'HIGH'
            }
        else:
            return {
                'strategy': 'PROTECT',
                'description': 'Very high growth - NO COVERED CALLS',
                'strike_guidance': 'DO NOT SELL CALLS',
                'expiration_guidance': 'N/A',
                'protection_level': 'MAXIMUM'
            }
    
    def _get_score_confidence(self, symbol: str, market_data: Dict) -> str:
        """How confident are we in this score?"""
        if symbol in self.known_growth_stocks or symbol in self.known_value_stocks:
            return "HIGH"
        elif all(k in market_data for k in ['price_change_1m', 'volatility_30d', 'revenue_growth']):
            return "MEDIUM"
        else:
            return "LOW"
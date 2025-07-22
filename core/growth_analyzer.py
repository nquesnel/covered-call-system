"""
Growth Analyzer - Strategic scoring system to protect high-growth positions
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics


class GrowthAnalyzer:
    """Analyze stocks to determine growth potential and covered call strategy"""
    
    def __init__(self):
        # Growth score thresholds
        self.AGGRESSIVE_THRESHOLD = 25    # Below 25: Aggressive calls OK
        self.MODERATE_THRESHOLD = 50      # 25-50: Moderate strategy
        self.CONSERVATIVE_THRESHOLD = 75  # 50-75: Conservative only
        # Above 75: NO COVERED CALLS - High growth protection
        
        # Technical indicator weights
        self.weights = {
            'momentum': 0.25,      # Price momentum and trend
            'volume': 0.20,        # Volume analysis
            'volatility': 0.20,    # Historical volatility
            'fundamentals': 0.20,  # Growth metrics
            'sentiment': 0.15      # Market sentiment
        }
    
    def calculate_growth_score(self, symbol: str, market_data: Dict) -> Dict:
        """
        Calculate comprehensive growth score (0-100)
        Higher score = Higher growth potential = More protection needed
        """
        scores = {}
        
        # 1. Momentum Score (0-100)
        scores['momentum'] = self._calculate_momentum_score(market_data)
        
        # 2. Volume Score (0-100)
        scores['volume'] = self._calculate_volume_score(market_data)
        
        # 3. Volatility Score (0-100)
        scores['volatility'] = self._calculate_volatility_score(market_data)
        
        # 4. Fundamentals Score (0-100)
        scores['fundamentals'] = self._calculate_fundamentals_score(market_data)
        
        # 5. Sentiment Score (0-100)
        scores['sentiment'] = self._calculate_sentiment_score(market_data)
        
        # Calculate weighted total score
        total_score = sum(scores[key] * self.weights[key] for key in scores)
        
        # Determine strategy recommendation
        strategy = self._get_strategy_recommendation(total_score)
        
        return {
            'symbol': symbol,
            'total_score': round(total_score),
            'component_scores': scores,
            'strategy': strategy,
            'protect_position': total_score > self.CONSERVATIVE_THRESHOLD,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_momentum_score(self, data: Dict) -> float:
        """Calculate momentum based on price trends"""
        score = 50  # Base score
        
        # Price performance
        if 'price_change_1m' in data:
            if data['price_change_1m'] > 20:
                score += 20
            elif data['price_change_1m'] > 10:
                score += 10
            elif data['price_change_1m'] < -10:
                score -= 10
        
        # Moving average position
        if all(k in data for k in ['price', 'ma_50', 'ma_200']):
            if data['price'] > data['ma_50'] > data['ma_200']:
                score += 15  # Strong uptrend
            elif data['price'] > data['ma_50']:
                score += 10  # Medium uptrend
            elif data['price'] < data['ma_50'] < data['ma_200']:
                score -= 15  # Downtrend
        
        # RSI consideration
        if 'rsi' in data:
            if data['rsi'] > 70:
                score += 10  # Strong momentum
            elif data['rsi'] < 30:
                score -= 10  # Oversold
        
        return max(0, min(100, score))
    
    def _calculate_volume_score(self, data: Dict) -> float:
        """Analyze volume patterns for accumulation/distribution"""
        score = 50
        
        # Volume trend
        if 'avg_volume_10d' in data and 'avg_volume_50d' in data:
            volume_ratio = data['avg_volume_10d'] / data['avg_volume_50d']
            if volume_ratio > 1.5:
                score += 20  # High recent volume
            elif volume_ratio > 1.2:
                score += 10
            elif volume_ratio < 0.7:
                score -= 10  # Low recent volume
        
        # On-balance volume trend
        if 'obv_trend' in data:
            if data['obv_trend'] == 'strong_accumulation':
                score += 15
            elif data['obv_trend'] == 'accumulation':
                score += 10
            elif data['obv_trend'] == 'distribution':
                score -= 15
        
        return max(0, min(100, score))
    
    def _calculate_volatility_score(self, data: Dict) -> float:
        """Higher volatility can mean higher growth potential"""
        score = 50
        
        # Historical volatility
        if 'volatility_30d' in data:
            if data['volatility_30d'] > 60:
                score += 20  # High volatility stock
            elif data['volatility_30d'] > 40:
                score += 10
            elif data['volatility_30d'] < 20:
                score -= 10  # Low volatility
        
        # Beta consideration
        if 'beta' in data:
            if data['beta'] > 1.5:
                score += 10  # High beta growth stock
            elif data['beta'] < 0.8:
                score -= 10  # Defensive stock
        
        return max(0, min(100, score))
    
    def _calculate_fundamentals_score(self, data: Dict) -> float:
        """Analyze fundamental growth metrics"""
        score = 50
        
        # Revenue growth
        if 'revenue_growth_yoy' in data:
            if data['revenue_growth_yoy'] > 50:
                score += 20
            elif data['revenue_growth_yoy'] > 25:
                score += 15
            elif data['revenue_growth_yoy'] > 10:
                score += 10
            elif data['revenue_growth_yoy'] < 0:
                score -= 15
        
        # Earnings growth
        if 'earnings_growth_yoy' in data:
            if data['earnings_growth_yoy'] > 50:
                score += 15
            elif data['earnings_growth_yoy'] > 25:
                score += 10
            elif data['earnings_growth_yoy'] < 0:
                score -= 10
        
        # Forward guidance
        if 'analyst_rating' in data:
            if data['analyst_rating'] >= 4.5:  # Strong buy
                score += 10
            elif data['analyst_rating'] <= 2.5:  # Sell rating
                score -= 10
        
        return max(0, min(100, score))
    
    def _calculate_sentiment_score(self, data: Dict) -> float:
        """Market sentiment and institutional activity"""
        score = 50
        
        # Institutional ownership changes
        if 'institutional_ownership_change' in data:
            if data['institutional_ownership_change'] > 5:
                score += 15  # Institutions accumulating
            elif data['institutional_ownership_change'] < -5:
                score -= 15  # Institutions selling
        
        # Options flow sentiment
        if 'options_sentiment' in data:
            if data['options_sentiment'] == 'very_bullish':
                score += 20
            elif data['options_sentiment'] == 'bullish':
                score += 10
            elif data['options_sentiment'] == 'bearish':
                score -= 15
        
        # Social sentiment
        if 'social_sentiment_score' in data:
            if data['social_sentiment_score'] > 80:
                score += 10
            elif data['social_sentiment_score'] < 20:
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
    
    def batch_analyze(self, symbols: List[str], market_data: Dict[str, Dict]) -> Dict[str, Dict]:
        """Analyze multiple symbols at once"""
        results = {}
        for symbol in symbols:
            if symbol in market_data:
                results[symbol] = self.calculate_growth_score(symbol, market_data[symbol])
        return results
    
    def get_eligible_symbols(self, all_positions: Dict, market_data: Dict[str, Dict], 
                           max_score: float = 75) -> List[Tuple[str, Dict]]:
        """
        Get symbols eligible for covered calls based on growth score
        Returns list of (symbol, analysis) tuples sorted by score (lowest first)
        """
        eligible = []
        
        for symbol in all_positions:
            if symbol in market_data:
                analysis = self.calculate_growth_score(symbol, market_data[symbol])
                if analysis['total_score'] <= max_score:
                    eligible.append((symbol, analysis))
        
        # Sort by score (lowest first = most eligible for covered calls)
        eligible.sort(key=lambda x: x[1]['total_score'])
        
        return eligible
    
    def explain_score(self, analysis: Dict) -> List[str]:
        """Generate human-readable explanation of the growth score"""
        explanations = []
        score = analysis['total_score']
        components = analysis['component_scores']
        
        # Overall assessment
        if score > 75:
            explanations.append("⚠️ VERY HIGH GROWTH - Protect this position!")
        elif score > 50:
            explanations.append("✅ High growth potential - Use conservative strikes only")
        elif score > 25:
            explanations.append("✅ Moderate growth - Balance income with upside")
        else:
            explanations.append("✅ Low growth - Maximize income opportunity")
        
        # Component explanations
        if components['momentum'] > 70:
            explanations.append("• Strong price momentum detected")
        if components['volume'] > 70:
            explanations.append("• High volume accumulation pattern")
        if components['fundamentals'] > 70:
            explanations.append("• Excellent fundamental growth metrics")
        if components['sentiment'] > 70:
            explanations.append("• Very positive market sentiment")
        
        return explanations
"""
Options Scanner - Find high-probability covered call opportunities
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math


class OptionsScanner:
    """Scan for winning covered call opportunities with high confidence"""
    
    def __init__(self, position_manager, growth_analyzer):
        self.position_manager = position_manager
        self.growth_analyzer = growth_analyzer
        
        # Minimum criteria for opportunities
        self.MIN_IV_RANK = 30          # Lowered from 50 for more opportunities
        self.MIN_VOLUME = 10           # Lowered for less liquid options
        self.MAX_SPREAD_PCT = 0.15     # Allow wider spreads
        self.MIN_OPEN_INTEREST = 10    # Lower minimum OI
        self.MIN_PREMIUM = 0.10        # Lower minimum premium
        
        # Target parameters
        self.TARGET_DTE_MIN = 25       # Minimum days to expiration
        self.TARGET_DTE_MAX = 45       # Maximum days to expiration
        self.MIN_MONTHLY_YIELD = 0.02  # Minimum 2% monthly yield
        
    def find_opportunities(self, market_data: Dict, options_data: Dict) -> List[Dict]:
        """Find the best covered call opportunities across all eligible positions"""
        opportunities = []
        
        # Get eligible positions (100+ shares)
        eligible_positions = self.position_manager.get_eligible_positions()
        
        for symbol, position in eligible_positions.items():
            # Skip if no market data
            if symbol not in market_data or symbol not in options_data:
                continue
            
            # Get growth score to determine strategy
            growth_analysis = self.growth_analyzer.calculate_growth_score(
                symbol, market_data[symbol]
            )
            
            # Skip very high growth stocks (score > 75)
            if growth_analysis['total_score'] > 75:
                continue
            
            # Find best strikes for this symbol
            symbol_opportunities = self._analyze_symbol_opportunities(
                symbol, position, growth_analysis, 
                market_data[symbol], options_data[symbol]
            )
            
            opportunities.extend(symbol_opportunities)
        
        # Sort by confidence score (highest first)
        opportunities.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        return opportunities[:20]  # Return top 20 opportunities
    
    def _analyze_symbol_opportunities(self, symbol: str, position: Dict, 
                                    growth_analysis: Dict, market_data: Dict, 
                                    options_chain: Dict) -> List[Dict]:
        """Analyze all strikes for a symbol and return viable opportunities"""
        opportunities = []
        current_price = market_data.get('price', 0)
        
        if not current_price:
            return opportunities
        
        # Get strategy parameters based on growth score
        strategy = growth_analysis['strategy']
        strike_params = self._get_strike_parameters(strategy, current_price)
        
        # Analyze each expiration
        for expiration, strikes in options_chain.items():
            # Calculate days to expiration
            exp_date = datetime.strptime(expiration, '%Y-%m-%d')
            dte = (exp_date - datetime.now()).days
            
            # Skip if outside target DTE range
            if dte < self.TARGET_DTE_MIN or dte > self.TARGET_DTE_MAX:
                continue
            
            # Analyze strikes within our target range
            for strike_price, option_data in strikes.items():
                if strike_price < strike_params['min_strike']:
                    continue
                if strike_price > strike_params['max_strike']:
                    continue
                
                # Validate option liquidity and pricing
                if not self._validate_option(option_data):
                    continue
                
                # Calculate opportunity metrics
                opportunity = self._calculate_opportunity_metrics(
                    symbol, position, growth_analysis, market_data,
                    strike_price, expiration, dte, option_data
                )
                
                if opportunity and opportunity['confidence_score'] > 50:
                    opportunities.append(opportunity)
        
        return opportunities
    
    def _get_strike_parameters(self, strategy: Dict, current_price: float) -> Dict:
        """Get min/max strikes based on growth strategy"""
        if strategy['strategy'] == 'AGGRESSIVE':
            return {
                'min_strike': current_price,  # ATM
                'max_strike': current_price * 1.03  # 3% OTM
            }
        elif strategy['strategy'] == 'MODERATE':
            return {
                'min_strike': current_price * 1.02,  # 2% OTM
                'max_strike': current_price * 1.07   # 7% OTM
            }
        elif strategy['strategy'] == 'CONSERVATIVE':
            return {
                'min_strike': current_price * 1.05,  # 5% OTM
                'max_strike': current_price * 1.12   # 12% OTM
            }
        else:  # PROTECT
            return {'min_strike': float('inf'), 'max_strike': float('inf')}
    
    def _validate_option(self, option_data: Dict) -> bool:
        """Validate option meets minimum criteria"""
        # Check bid-ask spread
        bid = option_data.get('bid', 0)
        ask = option_data.get('ask', 0)
        
        if bid <= 0 or ask <= 0:
            return False
        
        spread_pct = (ask - bid) / ask
        if spread_pct > self.MAX_SPREAD_PCT:
            return False
        
        # Check volume and open interest
        if option_data.get('volume', 0) < self.MIN_VOLUME:
            return False
        
        if option_data.get('open_interest', 0) < self.MIN_OPEN_INTEREST:
            return False
        
        # Check minimum premium
        mid_price = (bid + ask) / 2
        if mid_price < self.MIN_PREMIUM:
            return False
        
        # Check IV rank
        if option_data.get('iv_rank', 0) < self.MIN_IV_RANK:
            return False
        
        return True
    
    def _calculate_opportunity_metrics(self, symbol: str, position: Dict,
                                     growth_analysis: Dict, market_data: Dict,
                                     strike: float, expiration: str, dte: int,
                                     option_data: Dict) -> Optional[Dict]:
        """Calculate all metrics for a covered call opportunity"""
        current_price = market_data['price']
        bid = option_data['bid']
        ask = option_data['ask']
        premium = (bid + ask) / 2
        
        # Calculate yields
        cost_basis = position['cost_basis']
        shares = position['shares']
        contracts = shares // 100
        
        # Static return (if not called)
        static_return = premium / current_price
        static_return_monthly = (static_return / dte) * 30
        
        # Return if called
        if_called_return = ((strike - current_price) + premium) / current_price
        if_called_return_monthly = (if_called_return / dte) * 30
        
        # Skip if monthly yield too low
        if static_return_monthly < self.MIN_MONTHLY_YIELD:
            return None
        
        # Calculate win probability
        win_probability = self._calculate_win_probability(
            current_price, strike, dte, option_data
        )
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            option_data, win_probability, static_return_monthly,
            growth_analysis['total_score']
        )
        
        # Earnings risk check
        earnings_risk = self._check_earnings_risk(symbol, expiration, market_data)
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'strike': strike,
            'expiration': expiration,
            'days_to_exp': dte,
            'strategy': growth_analysis['strategy']['strategy'],
            'growth_score': growth_analysis['total_score'],
            
            # Pricing
            'bid': bid,
            'ask': ask,
            'premium': premium,
            'spread_pct': (ask - bid) / ask,
            
            # Greeks and volatility
            'delta': option_data.get('delta', 0),
            'theta': option_data.get('theta', 0),
            'iv_rank': option_data.get('iv_rank', 0),
            'iv_percentile': option_data.get('iv_percentile', 0),
            'implied_volatility': option_data.get('implied_volatility', 0),
            
            # Volume and liquidity
            'volume': option_data.get('volume', 0),
            'open_interest': option_data.get('open_interest', 0),
            
            # Returns
            'static_return': static_return,
            'static_return_monthly': static_return_monthly,
            'if_called_return': if_called_return,
            'if_called_return_monthly': if_called_return_monthly,
            'monthly_yield': static_return_monthly * 100,  # As percentage
            
            # Risk metrics
            'win_probability': win_probability,
            'confidence_score': confidence_score,
            'earnings_before_exp': earnings_risk,
            'max_contracts': contracts,
            
            # Position details
            'shares_owned': shares,
            'cost_basis': cost_basis,
            'account_type': position.get('account_type', 'taxable')
        }
    
    def _calculate_win_probability(self, current_price: float, strike: float,
                                 dte: int, option_data: Dict) -> float:
        """Calculate probability of option expiring worthless (win for seller)"""
        # Use delta as proxy for probability if available
        if 'delta' in option_data:
            return round((1 - abs(option_data['delta'])) * 100, 1)
        
        # Otherwise calculate using Black-Scholes approximation
        if 'implied_volatility' in option_data:
            iv = option_data['implied_volatility']
            time_factor = dte / 365
            
            # Calculate probability of staying below strike
            # Simplified normal distribution calculation
            moneyness = math.log(strike / current_price)
            vol_time = iv * math.sqrt(time_factor)
            
            if vol_time > 0:
                z_score = moneyness / vol_time
                # Approximate normal CDF
                prob = 0.5 * (1 + math.erf(z_score / math.sqrt(2)))
                return round(prob * 100, 1)
        
        # Fallback: simple distance calculation
        otm_percent = (strike - current_price) / current_price
        if otm_percent > 0.10:
            return 85.0
        elif otm_percent > 0.05:
            return 75.0
        elif otm_percent > 0.02:
            return 65.0
        else:
            return 50.0
    
    def _calculate_confidence_score(self, option_data: Dict, win_probability: float,
                                  monthly_yield: float, growth_score: float) -> int:
        """Calculate overall confidence score for the trade (0-100)"""
        scores = {}
        
        # IV Rank component (25%)
        iv_rank = option_data.get('iv_rank', 0)
        scores['iv'] = min(iv_rank * 1.5, 100) * 0.25
        
        # Win probability component (25%)
        scores['win_prob'] = win_probability * 0.25
        
        # Yield component (20%)
        yield_score = min(monthly_yield * 20, 100)  # 5% monthly = 100
        scores['yield'] = yield_score * 0.20
        
        # Liquidity component (15%)
        volume = option_data.get('volume', 0)
        oi = option_data.get('open_interest', 0)
        liquidity_score = min((volume / 500 + oi / 500) * 50, 100)
        scores['liquidity'] = liquidity_score * 0.15
        
        # Growth protection component (15%)
        # Lower growth score = better for covered calls
        growth_component = max(0, 100 - growth_score)
        scores['growth'] = growth_component * 0.15
        
        total_score = sum(scores.values())
        return round(total_score)
    
    def _check_earnings_risk(self, symbol: str, expiration: str, 
                           market_data: Dict) -> bool:
        """Check if earnings occur before expiration"""
        if 'next_earnings_date' in market_data:
            earnings_date = datetime.strptime(
                market_data['next_earnings_date'], '%Y-%m-%d'
            )
            exp_date = datetime.strptime(expiration, '%Y-%m-%d')
            return earnings_date < exp_date
        return False
    
    def filter_by_criteria(self, opportunities: List[Dict], 
                         min_yield: float = None,
                         min_confidence: int = None,
                         max_delta: float = None,
                         exclude_earnings: bool = False) -> List[Dict]:
        """Filter opportunities by specific criteria"""
        filtered = opportunities.copy()
        
        if min_yield:
            filtered = [o for o in filtered if o['monthly_yield'] >= min_yield]
        
        if min_confidence:
            filtered = [o for o in filtered if o['confidence_score'] >= min_confidence]
        
        if max_delta:
            filtered = [o for o in filtered if abs(o['delta']) <= max_delta]
        
        if exclude_earnings:
            filtered = [o for o in filtered if not o['earnings_before_exp']]
        
        return filtered
    
    def get_best_by_symbol(self, opportunities: List[Dict]) -> Dict[str, Dict]:
        """Get the best opportunity for each symbol"""
        best_by_symbol = {}
        
        for opp in opportunities:
            symbol = opp['symbol']
            if symbol not in best_by_symbol:
                best_by_symbol[symbol] = opp
            elif opp['confidence_score'] > best_by_symbol[symbol]['confidence_score']:
                best_by_symbol[symbol] = opp
        
        return best_by_symbol
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
        
        print(f"\n=== OPTIONS SCANNER DEBUG ===")
        print(f"Eligible positions: {list(eligible_positions.keys())}")
        print(f"Market data available for: {list(market_data.keys())}")
        print(f"Options data available for: {list(options_data.keys())}")
        
        for symbol, position in eligible_positions.items():
            print(f"\nProcessing {symbol}...")
            
            # Skip if no market data at all
            if symbol not in market_data:
                print(f"❌ No market data for {symbol}")
                continue
            
            # Get growth score to determine strategy
            growth_analysis = self.growth_analyzer.calculate_growth_score(
                symbol, market_data[symbol]
            )
            print(f"✓ Growth score: {growth_analysis['total_score']}")
            
            # Skip very high growth stocks (score > 75) - but make this configurable
            if growth_analysis['total_score'] > 85:  # Raised threshold from 75 to 85
                print(f"❌ Skipping {symbol} - growth score too high: {growth_analysis['total_score']}")
                continue
            
            # Check if we have options data
            if symbol not in options_data or not options_data[symbol]:
                print(f"⚠️  No options data for {symbol} - skipping")
                continue
            
            print(f"✓ Options data ready")
            
            # Find best strikes for this symbol
            symbol_opportunities = self._analyze_symbol_opportunities(
                symbol, position, growth_analysis, 
                market_data[symbol], options_data[symbol]
            )
            
            print(f"➡️  Found {len(symbol_opportunities)} opportunities for {symbol}")
            opportunities.extend(symbol_opportunities)
        
        # Sort by confidence score (highest first)
        opportunities.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        print(f"\n=== TOTAL OPPORTUNITIES FOUND: {len(opportunities)} ===")
        print(f"Returning top {min(20, len(opportunities))} opportunities\n")
        
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
    
    # Removed mock options chain generation - use real data only
    
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
        """Check if earnings occur BETWEEN today and expiration"""
        if 'next_earnings_date' in market_data:
            try:
                earnings_date = datetime.strptime(
                    market_data['next_earnings_date'], '%Y-%m-%d'
                )
                exp_date = datetime.strptime(expiration, '%Y-%m-%d')
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Earnings are a risk only if they occur AFTER today AND BEFORE expiration
                return today < earnings_date < exp_date
            except:
                return False
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
    
    def generate_opportunity_commentary(self, opp: Dict) -> Dict[str, str]:
        """Generate intelligent commentary about whether to take this opportunity"""
        reasons_pro = []
        reasons_con = []
        
        # Analyze IV Rank
        if opp['iv_rank'] > 70:
            reasons_pro.append("Very high IV rank (>70) - excellent premium collection opportunity")
        elif opp['iv_rank'] > 50:
            reasons_pro.append("Good IV rank (>50) - favorable for selling options")
        elif opp['iv_rank'] < 30:
            reasons_con.append("Low IV rank (<30) - premiums may not justify the risk")
        
        # Analyze yield
        if opp['monthly_yield'] > 4:
            reasons_pro.append(f"Exceptional monthly yield of {opp['monthly_yield']:.1f}%")
        elif opp['monthly_yield'] > 2.5:
            reasons_pro.append(f"Strong monthly yield of {opp['monthly_yield']:.1f}%")
        elif opp['monthly_yield'] < 1.5:
            reasons_con.append(f"Low monthly yield of {opp['monthly_yield']:.1f}% - consider passing")
        
        # Analyze win probability
        if opp['win_probability'] > 80:
            reasons_pro.append(f"High win probability ({opp['win_probability']:.0f}%) - likely to expire worthless")
        elif opp['win_probability'] < 60:
            reasons_con.append(f"Lower win probability ({opp['win_probability']:.0f}%) - higher assignment risk")
        
        # Analyze growth score
        if opp['growth_score'] < 30:
            reasons_pro.append("Low growth stock - ideal for covered calls")
        elif opp['growth_score'] > 60:
            reasons_con.append("High growth potential - consider protecting upside")
        
        # Check earnings
        if opp.get('earnings_before_exp'):
            reasons_con.append("⚠️ Earnings before expiration - increased volatility risk")
        
        # Analyze liquidity
        if opp['volume'] < 100:
            reasons_con.append("Low option volume - may have wide bid/ask spreads")
        elif opp['volume'] > 1000:
            reasons_pro.append("Excellent liquidity with high volume")
        
        # Generate recommendation
        if len(reasons_pro) >= len(reasons_con) and opp['confidence_score'] > 70:
            recommendation = "STRONG BUY"
            action = "This is an excellent opportunity that aligns well with income generation goals."
        elif len(reasons_pro) > len(reasons_con) and opp['confidence_score'] > 50:
            recommendation = "BUY"
            action = "Good opportunity with favorable risk/reward profile."
        elif opp['confidence_score'] < 40 or len(reasons_con) > len(reasons_pro) + 1:
            recommendation = "PASS"
            action = "Consider passing - better opportunities may be available."
        else:
            recommendation = "NEUTRAL"
            action = "Borderline opportunity - consider your risk tolerance and goals."
        
        # Special cases
        if opp['strategy'] == 'PROTECT':
            recommendation = "STRONG PASS"
            action = "DO NOT sell calls on this high-growth position!"
            reasons_con = ["This is a high-growth stock that should be protected from capping"]
        
        return {
            'recommendation': recommendation,
            'action': action,
            'reasons_pro': reasons_pro,
            'reasons_con': reasons_con,
            'key_insight': self._get_key_insight(opp)
        }
    
    def _get_key_insight(self, opp: Dict) -> str:
        """Generate a key insight for this opportunity"""
        # High confidence opportunities
        if opp['confidence_score'] > 80 and opp['monthly_yield'] > 3:
            return "📊 High-confidence income play with exceptional yield"
        
        # Post-earnings plays
        if opp['iv_rank'] > 60 and opp.get('earnings_before_exp') is False:
            return "📉 Post-earnings IV crush opportunity"
        
        # High yield plays
        if opp['monthly_yield'] > 5:
            return "💰 Premium collector's dream - exceptional yield"
        
        # Safe plays
        if opp['win_probability'] > 85:
            return "🛡️ Conservative income play with high win probability"
        
        # Growth protection needed
        if opp['growth_score'] > 70:
            return "🚀 Growth stock - be very selective with strikes"
        
        # Moderate opportunities
        if opp['confidence_score'] > 60:
            return "✅ Solid income opportunity with good risk/reward"
        
        return "📊 Standard covered call opportunity"
    
    def calculate_recommended_close_price(self, opp: Dict) -> Dict[str, float]:
        """Calculate recommended close prices based on 21-50-7 rule"""
        premium = opp['premium']
        
        # 50% profit target (main target)
        close_at_50_pct = premium * 0.50
        
        # 25% profit target (conservative)
        close_at_25_pct = premium * 0.75
        
        # 75% profit target (aggressive)
        close_at_75_pct = premium * 0.25
        
        # Breakeven minus commission (emergency exit)
        close_at_breakeven = premium * 0.95
        
        # Adjust based on DTE
        if opp['days_to_exp'] <= 7:
            primary_target = close_at_25_pct  # Take profits early when close to exp
            note = "Close ASAP - high gamma risk (7 DTE rule)"
        elif opp['days_to_exp'] <= 21:
            primary_target = close_at_50_pct
            note = "Standard 50% profit target (21 DTE checkpoint)"
        else:
            primary_target = close_at_50_pct
            note = "Hold for 50% profit or until 21 DTE"
        
        return {
            'primary_target': round(primary_target, 2),
            'conservative_target': round(close_at_25_pct, 2),
            'aggressive_target': round(close_at_75_pct, 2),
            'breakeven': round(close_at_breakeven, 2),
            'note': note,
            'profit_at_target': round(premium - primary_target, 2),
            'profit_pct_at_target': round((1 - primary_target/premium) * 100, 1)
        }
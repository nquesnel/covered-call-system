"""
Whale Tracker - Follow institutional "smart money" option flows
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics


class WhaleTracker:
    """
    Detect and analyze institutional option flows for follow opportunities
    Based on patterns like the successful $84K -> $1.3M trade example
    """
    
    def __init__(self):
        # Whale detection thresholds
        self.MIN_PREMIUM_VOLUME = 50000     # $50K minimum flow
        self.MIN_VOLUME_RATIO = 20          # 20x normal volume minimum
        self.MAX_OPTION_PRICE = 1.00        # Focus on cheap options
        self.MAX_DTE = 45                   # Short-term focus
        self.MIN_BLOCK_SIZE = 500           # Minimum contracts for block
        
        # Risk levels for different patterns
        self.risk_levels = {
            'weekly': 'EXTREME_RISK',     # < 7 DTE
            'biweekly': 'HIGH_RISK',      # 7-21 DTE  
            'monthly': 'MODERATE_RISK',   # 21-45 DTE
            'leap': 'LOWER_RISK'          # > 45 DTE
        }
    
    def detect_institutional_flows(self, options_flow_data: List[Dict]) -> List[Dict]:
        """
        Identify significant institutional option flows that retail can follow
        
        Looking for patterns like:
        - Large dollar amounts on cheap options (e.g. $84K on $0.13 calls)
        - Massive volume spikes (e.g. 646K contracts vs 1K daily average)
        - Short-term expirations with unusual size
        - Sweep/block orders indicating urgency
        """
        whale_flows = []
        
        for flow in options_flow_data:
            if self._is_whale_flow(flow):
                # Analyze the flow pattern
                analysis = self._analyze_flow_pattern(flow)
                
                # Build complete flow analysis
                whale_flow = {
                    'timestamp': flow['timestamp'],
                    'symbol': flow['symbol'],
                    'underlying_price': flow['underlying_price'],
                    'flow_type': flow['trade_type'],  # sweep, block, split
                    'option_type': flow['option_type'],  # call/put
                    'strike': flow['strike'],
                    'expiration': flow['expiration'],
                    'days_to_exp': flow['days_to_exp'],
                    
                    # Flow metrics
                    'contracts': flow['volume'],
                    'premium_per_contract': flow['premium'],
                    'total_premium': flow['premium_volume'],
                    'unusual_factor': flow['volume'] / max(flow['avg_volume'], 1),
                    
                    # Market metrics
                    'bid': flow['bid'],
                    'ask': flow['ask'],
                    'bid_ask_spread': flow['ask'] - flow['bid'],
                    'implied_volatility': flow.get('implied_volatility', 0),
                    'volume_oi_ratio': flow['volume'] / max(flow['open_interest'], 1),
                    
                    # Analysis
                    'sentiment': analysis['sentiment'],
                    'aggressiveness': analysis['aggressiveness'],
                    'smart_money_confidence': analysis['confidence'],
                    'pattern_type': analysis['pattern'],
                    'risk_level': self._assess_risk_level(flow)
                }
                
                # Calculate follow trade suggestion using the complete whale_flow data
                follow_trade = self._calculate_follow_trade(whale_flow, analysis)
                
                # Add follow trade to whale flow
                whale_flow['follow_trade'] = follow_trade
                whale_flow['retail_accessible'] = follow_trade is not None
                
                whale_flows.append(whale_flow)
        
        # Sort by total premium (largest flows first)
        whale_flows.sort(key=lambda x: x['total_premium'], reverse=True)
        
        return whale_flows
    
    def _is_whale_flow(self, flow: Dict) -> bool:
        """
        Identify flows that match "smart money" patterns
        
        Example pattern that turned $84K into $1.3M:
        - Stock at $1.20, bought $1.50 calls for $0.13
        - 646,000 contracts when normal volume was 1,000
        - Total investment: $84K
        - Expiration: 18 days
        - Result: Stock went to $3+, calls worth $1.73 each
        """
        # Large dollar volume
        if flow['premium_volume'] < self.MIN_PREMIUM_VOLUME:
            return False
        
        # Cheap options (like the $0.13 example)
        if flow['premium'] > self.MAX_OPTION_PRICE:
            return False
        
        # Massive volume spike
        if flow['avg_volume'] > 0:
            volume_ratio = flow['volume'] / flow['avg_volume']
            if volume_ratio < self.MIN_VOLUME_RATIO:
                return False
        
        # Short-term focus
        if flow['days_to_exp'] > self.MAX_DTE:
            return False
        
        # Institutional trade types
        if flow['trade_type'] not in ['sweep', 'block', 'split_block']:
            return False
        
        # Additional quality checks
        if flow['bid'] <= 0 or flow['ask'] <= 0:
            return False
        
        # Spread not too wide
        spread_pct = (flow['ask'] - flow['bid']) / flow['ask']
        if spread_pct > 0.30:  # 30% max spread
            return False
        
        return True
    
    def _analyze_flow_pattern(self, flow: Dict) -> Dict:
        """Analyze the pattern and intent of the whale flow"""
        analysis = {}
        
        # Determine sentiment
        if flow['option_type'] == 'call':
            if flow['strike'] > flow['underlying_price'] * 1.10:
                analysis['sentiment'] = 'VERY_BULLISH'  # Far OTM calls
            elif flow['strike'] > flow['underlying_price']:
                analysis['sentiment'] = 'BULLISH'       # OTM calls
            else:
                analysis['sentiment'] = 'STRONG_BULLISH'  # ITM calls
        else:  # puts
            if flow['strike'] < flow['underlying_price'] * 0.90:
                analysis['sentiment'] = 'VERY_BEARISH'  # Far OTM puts
            else:
                analysis['sentiment'] = 'BEARISH'
        
        # Determine aggressiveness
        if flow['days_to_exp'] <= 7:
            analysis['aggressiveness'] = 'EXTREME'
        elif flow['days_to_exp'] <= 21:
            analysis['aggressiveness'] = 'HIGH'
        else:
            analysis['aggressiveness'] = 'MODERATE'
        
        # Pattern identification
        if flow['trade_type'] == 'sweep' and flow['volume'] > 10000:
            analysis['pattern'] = 'AGGRESSIVE_SWEEP'
            analysis['confidence'] = 85
        elif flow['trade_type'] == 'block' and flow['premium_volume'] > 100000:
            analysis['pattern'] = 'INSTITUTIONAL_BLOCK'
            analysis['confidence'] = 80
        elif flow['volume'] / max(flow['open_interest'], 1) > 0.5:
            analysis['pattern'] = 'POSITION_OPENING'
            analysis['confidence'] = 75
        else:
            analysis['pattern'] = 'LARGE_TRADE'
            analysis['confidence'] = 70
        
        # Adjust confidence based on OTM percentage
        otm_pct = abs(flow['strike'] - flow['underlying_price']) / flow['underlying_price']
        if otm_pct > 0.20:  # Very far OTM like the $1.50 strike on $1.20 stock
            analysis['confidence'] += 10  # Institution is very confident
        
        return analysis
    
    def _calculate_follow_trade(self, whale_flow: Dict, 
                              analysis: Dict) -> Optional[Dict]:
        """
        Calculate a scaled-down follow trade for retail traders
        
        If whale bought 646K contracts for $84K, we scale down to retail size
        """
        # Only suggest following high-confidence bullish flows
        if analysis['confidence'] < 75:
            return None
        
        if 'BEAR' in analysis['sentiment']:
            return None  # Skip bearish flows for now
        
        # Calculate retail-sized position
        whale_contracts = whale_flow.get('contracts', whale_flow.get('volume', 0))
        whale_investment = whale_flow.get('total_premium', whale_flow.get('premium_volume', 0))
        
        # Scale down by factor based on whale size
        if whale_investment > 1000000:
            scale_factor = 100000  # 1:100,000
        elif whale_investment > 500000:
            scale_factor = 50000   # 1:50,000
        elif whale_investment > 100000:
            scale_factor = 20000   # 1:20,000
        else:
            scale_factor = 10000   # 1:10,000
        
        suggested_contracts = max(1, min(10, whale_contracts // scale_factor))
        
        # Calculate costs
        premium = whale_flow.get('premium_per_contract', whale_flow.get('premium', 0))
        mid_price = (whale_flow['bid'] + whale_flow['ask']) / 2
        cost_per_contract = mid_price * 100
        total_cost = cost_per_contract * suggested_contracts
        
        # Only suggest if cost is reasonable for retail ($200-$2000)
        if total_cost < 200 or total_cost > 2000:
            # Adjust contracts to fit budget
            if total_cost < 200 and cost_per_contract < 200:
                suggested_contracts = max(1, int(200 / cost_per_contract))
            elif total_cost > 2000:
                suggested_contracts = max(1, int(2000 / cost_per_contract))
            
            total_cost = cost_per_contract * suggested_contracts
        
        # Calculate potential returns based on historical patterns
        # Using the 1,230% return example as an upper bound
        conservative_return = 2.0   # 200% (3x)
        moderate_return = 5.0       # 500% (6x)
        aggressive_return = 10.0    # 1000% (11x)
        
        return {
            'suggested_contracts': int(suggested_contracts),
            'premium': mid_price,
            'cost_per_contract': cost_per_contract,
            'total_cost': total_cost,
            'max_loss': total_cost,  # Most you can lose
            'breakeven': whale_flow['strike'] + mid_price,
            
            # Potential returns
            'conservative_target': total_cost * conservative_return,
            'moderate_target': total_cost * moderate_return,
            'aggressive_target': total_cost * aggressive_return,
            
            # Recommendation
            'recommendation': self._generate_recommendation(
                suggested_contracts, total_cost, analysis
            ),
            'confidence_level': analysis['confidence'],
            'risk_reward_ratio': moderate_return  # Risk 1 to make 5
        }
    
    def _generate_recommendation(self, contracts: int, cost: float, 
                               analysis: Dict) -> str:
        """Generate human-readable follow recommendation"""
        if analysis['confidence'] >= 85:
            strength = "STRONG FOLLOW"
        elif analysis['confidence'] >= 80:
            strength = "Consider following"
        else:
            strength = "Speculative follow"
        
        risk_warning = ""
        if analysis['aggressiveness'] == 'EXTREME':
            risk_warning = " ⚠️ EXTREME RISK - Weekly expiration!"
        elif analysis['aggressiveness'] == 'HIGH':
            risk_warning = " ⚠️ HIGH RISK - Short-term play"
        
        return (f"{strength}: {contracts} contracts for ${cost:.0f} total. "
                f"Risk ${cost:.0f} to potentially make "
                f"${cost * 5:.0f}-${cost * 10:.0f}{risk_warning}")
    
    def _assess_risk_level(self, flow: Dict) -> str:
        """Assess risk level based on time to expiration"""
        dte = flow['days_to_exp']
        
        if dte <= 7:
            return self.risk_levels['weekly']
        elif dte <= 21:
            return self.risk_levels['biweekly']
        elif dte <= 45:
            return self.risk_levels['monthly']
        else:
            return self.risk_levels['leap']
    
    def get_success_stories(self) -> List[Dict]:
        """Return examples of successful whale trades for education"""
        return [
            {
                'date': '2024-01-15',
                'symbol': 'OPEN',
                'setup': 'Stock at $1.20, whale bought $1.50 calls for $0.13',
                'size': '646,000 contracts for $84K total',
                'result': 'Stock surged to $3+, calls worth $1.73 each',
                'return': '1,230% gain, $84K became $1.3M',
                'lesson': 'Massive volume on cheap OTM calls can signal insider confidence'
            },
            # Add more historical examples as found
        ]
    
    def filter_flows(self, flows: List[Dict], min_confidence: int = 75,
                    option_type: str = None, max_risk: str = None) -> List[Dict]:
        """Filter whale flows by criteria"""
        filtered = flows.copy()
        
        if min_confidence:
            filtered = [f for f in filtered 
                       if f['smart_money_confidence'] >= min_confidence]
        
        if option_type:
            filtered = [f for f in filtered 
                       if f['option_type'] == option_type]
        
        if max_risk:
            risk_order = ['MODERATE_RISK', 'HIGH_RISK', 'EXTREME_RISK']
            if max_risk in risk_order:
                max_risk_index = risk_order.index(max_risk)
                filtered = [f for f in filtered 
                           if risk_order.index(f.get('risk_level', 'EXTREME_RISK')) <= max_risk_index]
        
        return filtered
    
    def get_daily_summary(self, flows: List[Dict]) -> Dict:
        """Summarize whale activity for the day"""
        if not flows:
            return {
                'total_flows': 0,
                'bullish_flows': 0,
                'bearish_flows': 0,
                'total_premium': 0,
                'avg_confidence': 0,
                'top_symbols': []
            }
        
        bullish = [f for f in flows if 'BULL' in f['sentiment']]
        bearish = [f for f in flows if 'BEAR' in f['sentiment']]
        
        # Get top symbols by premium volume
        symbol_premium = {}
        for flow in flows:
            symbol = flow['symbol']
            symbol_premium[symbol] = symbol_premium.get(symbol, 0) + flow['total_premium']
        
        top_symbols = sorted(symbol_premium.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_flows': len(flows),
            'bullish_flows': len(bullish),
            'bearish_flows': len(bearish),
            'total_premium': sum(f['total_premium'] for f in flows),
            'avg_confidence': statistics.mean(f['smart_money_confidence'] for f in flows),
            'top_symbols': [{'symbol': s[0], 'premium': s[1]} for s in top_symbols],
            'highest_confidence': max(flows, key=lambda x: x['smart_money_confidence']) if flows else None
        }
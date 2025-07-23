"""
Enhanced Whale Tracker - Based on Unusual Whales Research
Implements proven patterns for finding massive winning trades
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_validator import DataValidator


class EnhancedWhaleTracker:
    """
    Advanced whale detection based on real winning trade patterns
    Incorporates research from Unusual Whales successful trades
    """
    
    def __init__(self):
        # Enhanced thresholds based on research
        self.thresholds = {
            # Premium thresholds - raised based on institutional patterns
            'min_premium_high_conviction': 250000,  # $250K for highest conviction
            'min_premium_moderate': 100000,         # $100K for solid signals
            'min_premium_interesting': 50000,       # $50K worth watching
            
            # Volume/OI ratios - key indicator of new positions
            'volume_oi_ratio_strong': 2.0,         # Volume 2x OI = very strong
            'volume_oi_ratio_moderate': 1.5,       # Volume 1.5x OI = strong
            'volume_oi_ratio_minimum': 1.0,        # Volume = OI minimum
            
            # Time patterns
            'max_dte_directional': 45,             # Short-term directional plays
            'min_dte_conviction': 7,               # At least 1 week to expiry
            'optimal_dte_range': (14, 35),         # Sweet spot for big moves
            
            # Strike selection (% OTM)
            'max_otm_percentage': 20,              # 20% OTM max for reasonable probability
            'min_otm_percentage': 5,               # 5% OTM min for meaningful upside
            'sweet_spot_otm': (7, 15),            # 7-15% OTM optimal
            
            # Contract size patterns
            'round_lot_sizes': [1000, 5000, 10000, 25000, 50000],  # Institutional sizes
            'min_contracts_institutional': 500,     # Minimum for institutional
            
            # Clustering patterns
            'time_cluster_window': 15,             # Minutes for related trades
            'min_cluster_trades': 3,               # Minimum trades in cluster
            
            # Spread quality
            'max_bid_ask_spread_pct': 10,         # Maximum 10% spread
            'min_open_interest': 1000,            # Minimum liquidity
        }
        
        # Proven winning patterns from research
        self.winning_patterns = {
            'perfect_storm': {
                'volume_oi_ratio': 2.0,
                'min_premium': 500000,
                'trade_type': ['sweep'],
                'execution_side': 'ask',
                'description': 'All indicators align - highest conviction'
            },
            'accumulation': {
                'min_trades': 5,
                'time_window': 10,  # days
                'increasing_size': True,
                'description': 'Institutional building position over time'
            },
            'pre_breakout': {
                'otm_range': (10, 20),
                'dte_range': (20, 40),
                'technical_setup': True,
                'description': 'Positioning before technical breakout'
            },
            'earnings_runner': {
                'days_before_earnings': (10, 21),
                'otm_range': (5, 15),
                'min_premium': 100000,
                'description': 'Pre-earnings institutional positioning'
            }
        }
        
        # Track historical performance
        self.pattern_success_rates = {}
    
    def analyze_whale_flow(self, flow_data: Dict) -> Dict:
        """
        Comprehensive analysis of a single flow using all research insights
        """
        analysis = {
            'whale_score': 0,  # 0-100 score
            'pattern_matches': [],
            'conviction_level': 'LOW',
            'risk_reward_rating': 'POOR',
            'institutional_probability': 0,
            'recommended_action': 'PASS',
            'key_insights': []
        }
        
        try:
            # Validate and normalize flow data first
            validated_flow = DataValidator.validate_whale_flow(flow_data)
            
            # Calculate base metrics with validated data
            metrics = self._calculate_flow_metrics(validated_flow)
        except Exception as e:
            print(f"Error analyzing whale flow: {e}")
            print(f"Flow data keys: {list(flow_data.keys())}")
            # Return error analysis
            return DataValidator.create_error_response(str(e), 'whale_flow')
        
        # Score based on multiple factors
        score_components = {
            'premium_score': self._score_premium(metrics['total_premium']),
            'volume_oi_score': self._score_volume_oi(metrics['volume_oi_ratio']),
            'execution_score': self._score_execution(flow_data),
            'timing_score': self._score_timing(metrics),
            'size_score': self._score_size_pattern(metrics['contracts']),
            'liquidity_score': self._score_liquidity(flow_data)
        }
        
        # Calculate weighted whale score
        weights = {
            'premium_score': 0.20,
            'volume_oi_score': 0.25,
            'execution_score': 0.20,
            'timing_score': 0.15,
            'size_score': 0.10,
            'liquidity_score': 0.10
        }
        
        whale_score = sum(score_components[k] * weights[k] for k in weights)
        analysis['whale_score'] = round(whale_score)
        
        # Check for winning patterns with validated flow
        pattern_matches = self._check_winning_patterns(validated_flow, metrics)
        analysis['pattern_matches'] = pattern_matches
        
        # Determine conviction level
        if whale_score >= 85:
            analysis['conviction_level'] = 'EXTREME'
            analysis['recommended_action'] = 'STRONG FOLLOW'
        elif whale_score >= 75:
            analysis['conviction_level'] = 'HIGH'
            analysis['recommended_action'] = 'FOLLOW'
        elif whale_score >= 65:
            analysis['conviction_level'] = 'MODERATE'
            analysis['recommended_action'] = 'CONSIDER'
        else:
            analysis['conviction_level'] = 'LOW'
            analysis['recommended_action'] = 'PASS'
        
        # Calculate institutional probability
        inst_indicators = 0
        if metrics['total_premium'] > self.thresholds['min_premium_moderate']:
            inst_indicators += 1
        if flow_data['trade_type'] in ['sweep', 'block']:
            inst_indicators += 1
        if metrics['contracts'] in self.thresholds['round_lot_sizes']:
            inst_indicators += 1
        if metrics['volume_oi_ratio'] > self.thresholds['volume_oi_ratio_moderate']:
            inst_indicators += 1
        
        analysis['institutional_probability'] = (inst_indicators / 4) * 100
        
        # Generate key insights
        analysis['key_insights'] = self._generate_insights(validated_flow, metrics, pattern_matches)
        
        # Risk/Reward assessment
        analysis['risk_reward_rating'] = self._assess_risk_reward(validated_flow, metrics)
        
        return analysis
    
    def _calculate_flow_metrics(self, flow: Dict) -> Dict:
        """Calculate key metrics from flow data"""
        current_price = flow.get('underlying_price', 0)
        strike = flow.get('strike', 0)
        
        # OTM percentage calculation with safety checks
        if current_price > 0:
            if flow.get('option_type') == 'call':
                otm_pct = ((strike - current_price) / current_price) * 100
            else:  # put
                otm_pct = ((current_price - strike) / current_price) * 100
        else:
            otm_pct = 0
        
        # Handle both 'volume' and 'contracts' field names
        volume = flow.get('contracts', flow.get('volume', 0))
        
        # Calculate volume/OI ratio safely
        if 'volume_oi_ratio' in flow:
            vol_oi_ratio = flow['volume_oi_ratio']
        else:
            open_interest = flow.get('open_interest', 1)
            vol_oi_ratio = volume / max(open_interest, 1) if open_interest > 0 else 0
        
        # Calculate spread percentage safely
        ask = flow.get('ask', 0)
        bid = flow.get('bid', 0)
        spread = ask - bid
        spread_pct = (spread / ask * 100) if ask > 0 else 0
        
        return {
            'contracts': volume,
            'total_premium': flow.get('total_premium', flow.get('premium_volume', 0)),
            'premium_per_contract': flow.get('premium_per_contract', flow.get('premium', 0)),
            'volume_oi_ratio': vol_oi_ratio,
            'days_to_exp': flow.get('days_to_exp', 0),
            'otm_percentage': max(0, otm_pct),
            'bid_ask_spread': flow.get('bid_ask_spread', spread),
            'spread_percentage': spread_pct
        }
    
    def _score_premium(self, premium: float) -> float:
        """Score based on premium size (0-100)"""
        if premium >= self.thresholds['min_premium_high_conviction']:
            return 100
        elif premium >= self.thresholds['min_premium_moderate']:
            return 80
        elif premium >= self.thresholds['min_premium_interesting']:
            return 60
        else:
            # Linear scale below threshold
            return (premium / self.thresholds['min_premium_interesting']) * 60
    
    def _score_volume_oi(self, ratio: float) -> float:
        """Score based on volume/OI ratio (0-100)"""
        if ratio >= self.thresholds['volume_oi_ratio_strong']:
            return 100
        elif ratio >= self.thresholds['volume_oi_ratio_moderate']:
            return 80
        elif ratio >= self.thresholds['volume_oi_ratio_minimum']:
            return 60
        else:
            return ratio * 60  # Linear scale below 1.0
    
    def _score_execution(self, flow: Dict) -> float:
        """Score based on execution quality (0-100)"""
        score = 0
        
        # Trade type scoring
        if flow.get('trade_type') == 'sweep':
            score += 40  # Sweeps show urgency
        elif flow.get('trade_type') == 'block':
            score += 35  # Blocks show institutional
        elif flow.get('trade_type') == 'split':
            score += 25
        else:
            score += 10
        
        # Execution side scoring
        if flow.get('execution_side') == 'ask':
            score += 30  # Aggressive buying
        elif flow.get('execution_side') == 'mid':
            score += 20
        else:
            score += 10
        
        # Time of day bonus
        hour = datetime.fromisoformat(flow.get('timestamp', datetime.now().isoformat())).hour
        if 10 <= hour <= 15:  # Mid-day trading
            score += 20
        elif hour < 10:  # Opening hour
            score += 5
        else:  # Late day
            score += 10
        
        # Multiple strikes bonus
        if flow.get('multi_strike', False):
            score += 10
        
        return min(100, score)
    
    def _score_timing(self, metrics: Dict) -> float:
        """Score based on expiration timing (0-100)"""
        dte = metrics['days_to_exp']
        
        if self.thresholds['optimal_dte_range'][0] <= dte <= self.thresholds['optimal_dte_range'][1]:
            return 100  # Perfect timing window
        elif self.thresholds['min_dte_conviction'] <= dte <= self.thresholds['max_dte_directional']:
            # Linear scale outside optimal
            if dte < self.thresholds['optimal_dte_range'][0]:
                return 60 + (dte / self.thresholds['optimal_dte_range'][0]) * 40
            else:
                return 60 + ((self.thresholds['max_dte_directional'] - dte) / 
                            (self.thresholds['max_dte_directional'] - self.thresholds['optimal_dte_range'][1])) * 40
        else:
            return 30  # Too short or too long
    
    def _score_size_pattern(self, contracts: int) -> float:
        """Score based on contract size patterns (0-100)"""
        # Check for round lots (institutional pattern)
        for round_size in sorted(self.thresholds['round_lot_sizes'], reverse=True):
            if contracts >= round_size and contracts % round_size == 0:
                return 100
        
        # Check if it's close to round lots
        for round_size in self.thresholds['round_lot_sizes']:
            if 0.9 * round_size <= contracts <= 1.1 * round_size:
                return 80
        
        # Score based on absolute size
        if contracts >= self.thresholds['min_contracts_institutional']:
            return 60 + min(40, (contracts / 10000) * 40)
        else:
            return (contracts / self.thresholds['min_contracts_institutional']) * 60
    
    def _score_liquidity(self, flow: Dict) -> float:
        """Score based on option liquidity (0-100)"""
        score = 0
        
        # Open interest score
        oi = flow.get('open_interest', 0)
        if oi >= 10000:
            score += 50
        elif oi >= 5000:
            score += 40
        elif oi >= self.thresholds['min_open_interest']:
            score += 30
        else:
            score += (oi / self.thresholds['min_open_interest']) * 30
        
        # Bid-ask spread score
        spread_pct = ((flow.get('ask', 0) - flow.get('bid', 0)) / max(flow.get('ask', 1), 1)) * 100
        if spread_pct <= 2:
            score += 50
        elif spread_pct <= 5:
            score += 40
        elif spread_pct <= self.thresholds['max_bid_ask_spread_pct']:
            score += 30
        else:
            score += max(0, 30 - (spread_pct - self.thresholds['max_bid_ask_spread_pct']) * 2)
        
        return score
    
    def _check_winning_patterns(self, flow: Dict, metrics: Dict) -> List[str]:
        """Check if flow matches known winning patterns"""
        matches = []
        
        # Perfect Storm Pattern
        if (metrics['volume_oi_ratio'] >= self.winning_patterns['perfect_storm']['volume_oi_ratio'] and
            metrics['total_premium'] >= self.winning_patterns['perfect_storm']['min_premium'] and
            flow.get('trade_type') in self.winning_patterns['perfect_storm']['trade_type'] and
            flow.get('execution_side') == self.winning_patterns['perfect_storm']['execution_side']):
            matches.append('PERFECT_STORM')
        
        # Pre-Breakout Pattern
        otm = metrics['otm_percentage']
        if (self.winning_patterns['pre_breakout']['otm_range'][0] <= otm <= self.winning_patterns['pre_breakout']['otm_range'][1] and
            self.winning_patterns['pre_breakout']['dte_range'][0] <= metrics['days_to_exp'] <= self.winning_patterns['pre_breakout']['dte_range'][1]):
            matches.append('PRE_BREAKOUT')
        
        # Add more pattern checks as needed
        
        return matches
    
    def _generate_insights(self, flow: Dict, metrics: Dict, patterns: List[str]) -> List[str]:
        """Generate actionable insights from analysis"""
        insights = []
        
        # Premium insights
        if metrics['total_premium'] >= self.thresholds['min_premium_high_conviction']:
            insights.append(f"💰 Massive ${metrics['total_premium']:,.0f} bet shows extreme conviction")
        elif metrics['total_premium'] >= self.thresholds['min_premium_moderate']:
            insights.append(f"💵 Large ${metrics['total_premium']:,.0f} institutional-sized bet")
        
        # Volume/OI insights
        if metrics['volume_oi_ratio'] >= 2.0:
            insights.append(f"📊 Volume {metrics['volume_oi_ratio']:.1f}x OI - aggressive NEW position opening")
        elif metrics['volume_oi_ratio'] >= 1.5:
            insights.append(f"📈 Volume exceeds OI by {metrics['volume_oi_ratio']:.1f}x - likely new positions")
        
        # Execution insights
        if flow.get('trade_type') == 'sweep' and flow.get('execution_side') == 'ask':
            insights.append("🚨 URGENT: Sweep at ASK - someone needs these contracts NOW")
        elif flow.get('trade_type') == 'block':
            insights.append("🏢 Block trade indicates institutional positioning")
        
        # Timing insights
        if metrics['days_to_exp'] <= 14:
            insights.append(f"⏰ Only {metrics['days_to_exp']} days to expiry - expects FAST move")
        elif self.thresholds['optimal_dte_range'][0] <= metrics['days_to_exp'] <= self.thresholds['optimal_dte_range'][1]:
            insights.append("📅 Optimal 2-5 week timeframe for explosive moves")
        
        # Pattern insights
        if 'PERFECT_STORM' in patterns:
            insights.append("🌟 PERFECT STORM SETUP - All whale indicators align!")
        if 'PRE_BREAKOUT' in patterns:
            insights.append("🚀 Pre-breakout positioning detected")
        
        # OTM insights
        if 10 <= metrics['otm_percentage'] <= 20:
            insights.append(f"🎯 {metrics['otm_percentage']:.1f}% OTM - betting on significant move")
        
        return insights
    
    def _assess_risk_reward(self, flow: Dict, metrics: Dict) -> str:
        """Assess risk/reward profile"""
        # Simple risk/reward based on OTM % and premium
        if metrics['otm_percentage'] > 20:
            return 'HIGH_RISK'
        elif metrics['otm_percentage'] > 15:
            if metrics['total_premium'] > self.thresholds['min_premium_moderate']:
                return 'MODERATE_REWARD'
            else:
                return 'MODERATE_RISK'
        elif metrics['otm_percentage'] > 10:
            return 'BALANCED'
        else:
            return 'CONSERVATIVE'
    
    def rank_whale_flows(self, flows: List[Dict]) -> List[Dict]:
        """Rank flows by whale score and return top candidates"""
        analyzed_flows = []
        
        for flow in flows:
            try:
                analysis = self.analyze_whale_flow(flow)
                flow['whale_analysis'] = analysis
                analyzed_flows.append(flow)
            except Exception as e:
                print(f"Error analyzing flow {flow.get('symbol', 'Unknown')}: {e}")
                # Add basic analysis on error
                flow['whale_analysis'] = {
                    'whale_score': 0,
                    'pattern_matches': [],
                    'conviction_level': 'ERROR',
                    'risk_reward_rating': 'UNKNOWN',
                    'institutional_probability': 0,
                    'recommended_action': 'SKIP',
                    'key_insights': ['Error analyzing flow']
                }
                analyzed_flows.append(flow)
        
        # Sort by whale score descending
        analyzed_flows.sort(key=lambda x: x['whale_analysis']['whale_score'], reverse=True)
        
        return analyzed_flows
    
    def get_follow_recommendation(self, flow: Dict, analysis: Dict, 
                                 portfolio_size: float = 10000) -> Dict:
        """
        Generate specific follow trade recommendations based on portfolio size
        """
        if analysis['whale_score'] < 65:
            return {
                'should_follow': False,
                'reason': 'Whale score too low - wait for better setups'
            }
        
        # Calculate position sizing based on conviction
        if analysis['conviction_level'] == 'EXTREME':
            risk_percentage = 0.03  # Risk 3% on highest conviction
        elif analysis['conviction_level'] == 'HIGH':
            risk_percentage = 0.02  # Risk 2% on high conviction
        else:
            risk_percentage = 0.01  # Risk 1% on moderate conviction
        
        max_risk = portfolio_size * risk_percentage
        
        # Calculate contracts based on premium
        premium_per_contract = flow.get('premium', 0) * 100
        if premium_per_contract <= 0:
            return {
                'should_follow': False,
                'reason': 'Invalid option pricing'
            }
        
        suggested_contracts = max(1, int(max_risk / premium_per_contract))
        total_cost = suggested_contracts * premium_per_contract
        
        # Adjust for expensive options
        while total_cost > max_risk and suggested_contracts > 1:
            suggested_contracts -= 1
            total_cost = suggested_contracts * premium_per_contract
        
        # Calculate potential returns
        if flow['option_type'] == 'call':
            # For calls, calculate breakeven and targets
            breakeven = flow['strike'] + flow.get('premium', 0)
            target_1 = breakeven * 1.1  # 10% above breakeven
            target_2 = breakeven * 1.2  # 20% above breakeven
            target_3 = breakeven * 1.5  # 50% above breakeven
        else:
            # For puts
            breakeven = flow['strike'] - flow.get('premium', 0)
            target_1 = breakeven * 0.9
            target_2 = breakeven * 0.8
            target_3 = breakeven * 0.7
        
        return {
            'should_follow': True,
            'suggested_contracts': suggested_contracts,
            'total_cost': total_cost,
            'max_loss': total_cost,
            'risk_percentage': risk_percentage * 100,
            'breakeven': breakeven,
            'targets': {
                'conservative': target_1,
                'moderate': target_2,
                'aggressive': target_3
            },
            'position_management': {
                'entry': 'Buy at mid or better',
                'stop_loss': 'Mental stop at -50%',
                'take_profit_1': '25% position at 100% gain',
                'take_profit_2': '50% position at 200% gain',
                'runner': 'Let 25% run for home run'
            },
            'conviction_notes': ' | '.join(analysis['key_insights'][:3])
        }
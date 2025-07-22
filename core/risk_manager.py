"""
Risk Manager - Monitor and manage covered call position risks
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class RiskManager:
    """Real-time risk monitoring and 21-50-7 rule enforcement"""
    
    def __init__(self):
        # Risk thresholds
        self.MAX_PROFIT_PCT = 50      # Close at 50% profit
        self.DTE_WARNING = 21         # Consider closing at 21 DTE
        self.DTE_CRITICAL = 7         # Must close at 7 DTE (gamma risk)
        
        # Assignment risk thresholds
        self.HIGH_DELTA = 0.70        # High assignment risk
        self.CRITICAL_DELTA = 0.85    # Very high assignment risk
        
        # Distance to strike thresholds
        self.CLOSE_TO_STRIKE = 0.02   # Within 2% of strike
        self.AT_STRIKE = 0.005        # Within 0.5% of strike
    
    def monitor_active_positions(self, active_trades: List[Dict], 
                               market_data: Dict) -> List[str]:
        """Monitor all active positions and generate alerts"""
        alerts = []
        
        for trade in active_trades:
            symbol = trade['symbol']
            
            # Get current market data
            if symbol not in market_data:
                alerts.append(f"⚠️ {symbol}: No market data available")
                continue
            
            current_price = market_data[symbol].get('price', 0)
            if not current_price:
                continue
            
            # Check 21-50-7 rule
            rule_alerts = self._check_21_50_7_rule(trade, current_price)
            alerts.extend(rule_alerts)
            
            # Check assignment risk
            assignment_alerts = self._check_assignment_risk(trade, current_price)
            alerts.extend(assignment_alerts)
            
            # Check IV conditions
            iv_alerts = self._check_iv_conditions(trade, market_data[symbol])
            alerts.extend(iv_alerts)
            
            # Check earnings
            earnings_alerts = self._check_earnings_risk(trade, market_data[symbol])
            alerts.extend(earnings_alerts)
        
        return alerts
    
    def _check_21_50_7_rule(self, trade: Dict, current_price: float) -> List[str]:
        """Check compliance with 21-50-7 rule"""
        alerts = []
        symbol = trade['symbol']
        dte = trade.get('days_to_exp', 0)
        
        # Calculate current profit/loss
        premium = trade['premium']
        # Estimate current option price (simplified)
        time_decay = (trade.get('original_dte', 30) - dte) / trade.get('original_dte', 30)
        estimated_current_premium = premium * (1 - time_decay * 0.7)  # Rough estimate
        
        profit_pct = ((premium - estimated_current_premium) / premium) * 100
        
        # 50% profit rule - ALWAYS close
        if profit_pct >= self.MAX_PROFIT_PCT:
            alerts.append(
                f"⚠️ {symbol}: {profit_pct:.0f}% profit reached - "
                f"CLOSE IMMEDIATELY (50% rule)"
            )
        
        # 21 DTE rule - Consider closing if profitable
        elif dte <= self.DTE_WARNING and profit_pct > 25:
            alerts.append(
                f"⚠️ {symbol}: {dte} DTE with {profit_pct:.0f}% profit - "
                f"Consider closing (21 DTE rule)"
            )
        
        # 7 DTE rule - High gamma risk
        elif dte <= self.DTE_CRITICAL:
            alerts.append(
                f"⚠️ {symbol}: Only {dte} DTE - HIGH GAMMA RISK - "
                f"Close to avoid assignment (7 DTE rule)"
            )
        
        return alerts
    
    def _check_assignment_risk(self, trade: Dict, current_price: float) -> List[str]:
        """Check assignment risk based on price and delta"""
        alerts = []
        symbol = trade['symbol']
        strike = trade['strike']
        
        # Calculate distance to strike
        distance = strike - current_price
        distance_pct = abs(distance / strike)
        
        # Price proximity warnings
        if current_price >= strike:
            alerts.append(
                f"⚠️ {symbol}: Stock ABOVE strike ${strike:.2f} - "
                f"HIGH ASSIGNMENT RISK"
            )
        elif distance_pct <= self.AT_STRIKE:
            alerts.append(
                f"⚠️ {symbol}: Within 0.5% of strike - "
                f"CRITICAL assignment risk"
            )
        elif distance_pct <= self.CLOSE_TO_STRIKE:
            alerts.append(
                f"⚠️ {symbol}: Within {distance_pct*100:.1f}% of strike - "
                f"Monitor closely"
            )
        
        # Delta warnings
        delta = abs(trade.get('delta', 0))
        if delta >= self.CRITICAL_DELTA:
            alerts.append(
                f"⚠️ {symbol}: Delta {delta:.2f} - "
                f"VERY HIGH assignment probability"
            )
        elif delta >= self.HIGH_DELTA:
            alerts.append(
                f"⚠️ {symbol}: Delta {delta:.2f} - "
                f"High assignment probability"
            )
        
        return alerts
    
    def _check_iv_conditions(self, trade: Dict, market_data: Dict) -> List[str]:
        """Check for IV crush opportunities"""
        alerts = []
        symbol = trade['symbol']
        
        current_iv_rank = market_data.get('iv_rank', 0)
        trade_iv_rank = trade.get('iv_rank', 0)
        
        # IV crush detection
        if trade_iv_rank > 0 and current_iv_rank > 0:
            iv_drop = trade_iv_rank - current_iv_rank
            
            if iv_drop > 30:
                alerts.append(
                    f"⚠️ {symbol}: IV crushed from {trade_iv_rank:.0f} to "
                    f"{current_iv_rank:.0f} - Consider closing for profit"
                )
            elif current_iv_rank < 20 and trade.get('profit_pct', 0) > 30:
                alerts.append(
                    f"⚠️ {symbol}: IV Rank now {current_iv_rank:.0f} with profit - "
                    f"Good exit opportunity"
                )
        
        return alerts
    
    def _check_earnings_risk(self, trade: Dict, market_data: Dict) -> List[str]:
        """Check for upcoming earnings"""
        alerts = []
        symbol = trade['symbol']
        
        if 'next_earnings_date' in market_data:
            earnings_date = datetime.strptime(
                market_data['next_earnings_date'], '%Y-%m-%d'
            )
            exp_date = datetime.strptime(trade['expiration'], '%Y-%m-%d')
            
            days_to_earnings = (earnings_date - datetime.now()).days
            
            if earnings_date <= exp_date and days_to_earnings <= 5:
                alerts.append(
                    f"⚠️ {symbol}: Earnings in {days_to_earnings} days - "
                    f"High volatility risk"
                )
        
        return alerts
    
    def calculate_position_risk(self, trade: Dict, market_data: Dict) -> Dict:
        """Calculate comprehensive risk metrics for a position"""
        symbol = trade['symbol']
        current_data = market_data.get(symbol, {})
        current_price = current_data.get('price', 0)
        
        if not current_price:
            return {
                'symbol': symbol,
                'risk_level': 'UNKNOWN',
                'assignment_risk': 'N/A',
                'recommended_action': 'Get price data'
            }
        
        strike = trade['strike']
        dte = trade.get('days_to_exp', 0)
        delta = abs(trade.get('delta', 0))
        
        # Calculate metrics
        distance = strike - current_price
        distance_pct = (distance / strike) * 100
        
        # Determine assignment risk
        if current_price >= strike:
            assignment_risk = 'CRITICAL'
        elif delta >= 0.70:
            assignment_risk = 'HIGH'
        elif delta >= 0.50:
            assignment_risk = 'MODERATE'
        else:
            assignment_risk = 'LOW'
        
        # Determine overall risk level
        if dte <= 7 or current_price >= strike:
            risk_level = 'CRITICAL'
        elif dte <= 21 or delta >= 0.70:
            risk_level = 'HIGH'
        elif delta >= 0.50:
            risk_level = 'MODERATE'
        else:
            risk_level = 'LOW'
        
        # Recommend action
        if risk_level == 'CRITICAL':
            action = 'CLOSE IMMEDIATELY'
        elif risk_level == 'HIGH' and trade.get('profit_pct', 0) > 25:
            action = 'Consider closing'
        else:
            action = 'Hold and monitor'
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'strike': strike,
            'distance_pct': distance_pct,
            'dte': dte,
            'delta': delta,
            'assignment_risk': assignment_risk,
            'risk_level': risk_level,
            'recommended_action': action
        }
    
    def suggest_adjustments(self, trade: Dict, market_data: Dict) -> List[Dict]:
        """Suggest position adjustments to reduce risk"""
        suggestions = []
        risk_metrics = self.calculate_position_risk(trade, market_data)
        
        if risk_metrics['risk_level'] in ['HIGH', 'CRITICAL']:
            # Close position
            suggestions.append({
                'action': 'CLOSE',
                'reason': f"High risk: {risk_metrics['assignment_risk']} assignment risk",
                'urgency': 'HIGH' if risk_metrics['risk_level'] == 'CRITICAL' else 'MEDIUM'
            })
            
            # Roll suggestions
            if risk_metrics['dte'] <= 21 and risk_metrics['distance_pct'] > 2:
                suggestions.append({
                    'action': 'ROLL_OUT',
                    'reason': 'Roll to next month to collect more premium',
                    'urgency': 'MEDIUM'
                })
            
            if risk_metrics['distance_pct'] < 2:
                suggestions.append({
                    'action': 'ROLL_UP_AND_OUT',
                    'reason': 'Roll to higher strike and later date',
                    'urgency': 'HIGH'
                })
        
        return suggestions
    
    def calculate_portfolio_risk(self, active_trades: List[Dict], 
                               market_data: Dict) -> Dict:
        """Calculate overall portfolio risk metrics"""
        total_positions = len(active_trades)
        critical_positions = 0
        high_risk_positions = 0
        total_delta_exposure = 0
        
        for trade in active_trades:
            risk = self.calculate_position_risk(trade, market_data)
            
            if risk['risk_level'] == 'CRITICAL':
                critical_positions += 1
            elif risk['risk_level'] == 'HIGH':
                high_risk_positions += 1
            
            # Sum delta exposure
            contracts = trade.get('contracts', 0)
            delta = trade.get('delta', 0)
            total_delta_exposure += abs(delta) * contracts * 100
        
        # Calculate risk score (0-100, higher = more risk)
        risk_score = (
            (critical_positions / max(total_positions, 1)) * 50 +
            (high_risk_positions / max(total_positions, 1)) * 30 +
            min(total_delta_exposure / 10000, 1) * 20
        )
        
        return {
            'total_positions': total_positions,
            'critical_positions': critical_positions,
            'high_risk_positions': high_risk_positions,
            'total_delta_exposure': total_delta_exposure,
            'portfolio_risk_score': round(risk_score),
            'risk_level': 'CRITICAL' if risk_score > 70 else 'HIGH' if risk_score > 40 else 'MODERATE'
        }
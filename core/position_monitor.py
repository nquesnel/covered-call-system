"""
Position Monitor - Implement the 21-50-7 Rule for optimal exits
Monitor open covered call positions and alert for action
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os


class PositionMonitor:
    """
    Monitor open covered call positions for the 21-50-7 rule:
    - 21 DTE: Start monitoring closely
    - 50% profit: Close for optimal returns
    - 7 DTE: Must close to avoid assignment risk
    """
    
    def __init__(self, trade_tracker):
        self.trade_tracker = trade_tracker
        
        # Alert thresholds
        self.DTE_MONITOR = 21      # Start watching closely
        self.PROFIT_TARGET = 0.50  # Close at 50% profit
        self.DTE_FORCE_CLOSE = 7   # Must close by 7 DTE
        
        # Alert settings
        self.alerts_shown = set()  # Track which alerts have been shown
    
    def check_positions(self, current_prices: Dict[str, float]) -> Dict[str, List[Dict]]:
        """
        Check all open positions against 21-50-7 rules
        
        Returns:
            Dict with alert categories: 'close_now', 'monitor', 'approaching_21dte'
        """
        alerts = {
            'close_now': [],      # 50% profit or 7 DTE
            'monitor': [],        # Under 21 DTE
            'approaching_21dte': [], # 22-30 DTE
            'all_clear': []       # No action needed
        }
        
        # Get active covered call trades
        active_trades = self.trade_tracker.get_active_trades()
        
        for trade in active_trades:
            analysis = self._analyze_position(trade, current_prices)
            
            if analysis['action'] == 'CLOSE_NOW':
                alerts['close_now'].append(analysis)
            elif analysis['action'] == 'MONITOR':
                alerts['monitor'].append(analysis)
            elif analysis['action'] == 'APPROACHING':
                alerts['approaching_21dte'].append(analysis)
            else:
                alerts['all_clear'].append(analysis)
        
        return alerts
    
    def _analyze_position(self, trade: Dict, current_prices: Dict[str, float]) -> Dict:
        """Analyze a single position against 21-50-7 rules"""
        symbol = trade['symbol']
        
        # Calculate days to expiration
        exp_date = datetime.strptime(trade['expiration'], '%Y-%m-%d')
        today = datetime.now()
        dte = (exp_date - today).days
        
        # Get current option price (estimate if not available)
        current_price = current_prices.get(symbol, trade['underlying_price'])
        current_option_price = self._estimate_option_price(
            trade, current_price, dte
        )
        
        # Calculate profit/loss
        entry_price = trade['premium']
        current_profit = entry_price - current_option_price
        profit_pct = current_profit / entry_price if entry_price > 0 else 0
        
        # Determine action based on 21-50-7 rule
        action, priority, reason = self._determine_action(dte, profit_pct)
        
        return {
            'trade': trade,
            'symbol': symbol,
            'strike': trade['strike'],
            'expiration': trade['expiration'],
            'dte': dte,
            'entry_price': entry_price,
            'current_price': current_option_price,
            'current_profit': current_profit,
            'profit_pct': profit_pct,
            'profit_target': entry_price * (1 - self.PROFIT_TARGET),
            'action': action,
            'priority': priority,
            'reason': reason,
            'alert_id': f"{symbol}_{trade['strike']}_{trade['expiration']}_{action}"
        }
    
    def _determine_action(self, dte: int, profit_pct: float) -> Tuple[str, str, str]:
        """
        Determine what action to take based on 21-50-7 rule
        
        Returns:
            (action, priority, reason)
        """
        # Rule 1: Close at 50% profit regardless of DTE
        if profit_pct >= self.PROFIT_TARGET:
            return ('CLOSE_NOW', 'HIGH', f'Hit {profit_pct:.0%} profit target!')
        
        # Rule 2: Must close at 7 DTE
        if dte <= self.DTE_FORCE_CLOSE:
            if dte <= 1:
                return ('CLOSE_NOW', 'CRITICAL', f'EXPIRES TOMORROW! Only {dte} days left')
            elif dte <= 3:
                return ('CLOSE_NOW', 'URGENT', f'Only {dte} days to expiration!')
            else:
                return ('CLOSE_NOW', 'HIGH', f'7-DTE rule: Close with {dte} days left')
        
        # Rule 3: Monitor closely at 21 DTE
        if dte <= self.DTE_MONITOR:
            if profit_pct >= 0.40:
                return ('MONITOR', 'MEDIUM', f'{dte} DTE with {profit_pct:.0%} profit - consider closing')
            else:
                return ('MONITOR', 'LOW', f'{dte} DTE - monitoring position')
        
        # Approaching 21 DTE
        if dte <= 30:
            return ('APPROACHING', 'INFO', f'{dte} DTE - will monitor at 21 DTE')
        
        # No action needed yet
        return ('NONE', 'INFO', f'{dte} DTE - no action needed')
    
    def _estimate_option_price(self, trade: Dict, current_stock_price: float, 
                              dte: int) -> float:
        """
        Estimate current option price based on time decay and stock movement
        This is a simplified model - real pricing would use Black-Scholes
        """
        original_price = trade['premium']
        strike = trade['strike']
        original_dte = trade.get('original_dte', 45)
        
        # Time decay factor (theta decay accelerates near expiration)
        if original_dte > 0:
            time_decay_factor = (dte / original_dte) ** 0.5
        else:
            time_decay_factor = 0
        
        # Intrinsic value for ITM options
        intrinsic_value = max(0, current_stock_price - strike)
        
        # Extrinsic value decays over time
        original_extrinsic = original_price - max(0, trade['underlying_price'] - strike)
        current_extrinsic = original_extrinsic * time_decay_factor
        
        # Current option price
        estimated_price = intrinsic_value + current_extrinsic
        
        # Options rarely go below $0.05 if there's any time left
        if dte > 0:
            estimated_price = max(0.05, estimated_price)
        
        return round(estimated_price, 2)
    
    def get_closing_recommendations(self, alerts: Dict[str, List[Dict]]) -> List[Dict]:
        """
        Get specific recommendations for positions that should be closed
        """
        recommendations = []
        
        # Process all close_now alerts
        for alert in alerts['close_now']:
            rec = {
                'symbol': alert['symbol'],
                'strike': alert['strike'],
                'expiration': alert['expiration'],
                'current_price': alert['current_price'],
                'profit': alert['current_profit'],
                'profit_pct': alert['profit_pct'],
                'reason': alert['reason'],
                'priority': alert['priority'],
                'action_required': 'CLOSE POSITION',
                'instructions': self._get_closing_instructions(alert)
            }
            recommendations.append(rec)
        
        # Add high-profit positions from monitor list
        for alert in alerts['monitor']:
            if alert['profit_pct'] >= 0.40:  # 40%+ profit
                rec = {
                    'symbol': alert['symbol'],
                    'strike': alert['strike'],
                    'expiration': alert['expiration'],
                    'current_price': alert['current_price'],
                    'profit': alert['current_profit'],
                    'profit_pct': alert['profit_pct'],
                    'reason': f"Consider closing - {alert['profit_pct']:.0%} profit with {alert['dte']} DTE",
                    'priority': 'MEDIUM',
                    'action_required': 'CONSIDER CLOSING',
                    'instructions': self._get_closing_instructions(alert)
                }
                recommendations.append(rec)
        
        # Sort by priority
        priority_order = {'CRITICAL': 0, 'URGENT': 1, 'HIGH': 2, 'MEDIUM': 3, 'LOW': 4}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 5))
        
        return recommendations
    
    def _get_closing_instructions(self, alert: Dict) -> str:
        """Get specific instructions for closing a position"""
        if alert['current_price'] <= 0.05:
            return (f"BUY TO CLOSE {alert['symbol']} ${alert['strike']} call "
                   f"at market (likely $0.05 or less)")
        else:
            limit_price = round(alert['current_price'] * 1.05, 2)  # 5% above current
            return (f"BUY TO CLOSE {alert['symbol']} ${alert['strike']} call "
                   f"at limit ${limit_price} or better (current: ${alert['current_price']})")
    
    def should_show_alert(self, alert_id: str, frequency_hours: int = 24) -> bool:
        """
        Check if we should show an alert (to avoid alert fatigue)
        """
        if alert_id not in self.alerts_shown:
            self.alerts_shown.add(alert_id)
            return True
        
        # For now, always show critical alerts
        if 'CRITICAL' in alert_id or 'URGENT' in alert_id:
            return True
        
        return False
    
    def get_summary_metrics(self, alerts: Dict[str, List[Dict]]) -> Dict:
        """Get summary metrics for the dashboard"""
        total_positions = sum(len(alerts[cat]) for cat in alerts)
        
        # Calculate total profit available to capture
        total_profit_available = sum(
            alert['current_profit'] * alert['trade']['contracts'] * 100
            for alert in alerts['close_now'] + alerts['monitor']
            if alert['current_profit'] > 0
        )
        
        # Positions at different profit levels
        profit_breakdown = {
            'over_50': len([a for a in alerts['close_now'] if a['profit_pct'] >= 0.50]),
            'over_40': len([a for cat in alerts.values() for a in cat if a['profit_pct'] >= 0.40]),
            'over_30': len([a for cat in alerts.values() for a in cat if a['profit_pct'] >= 0.30]),
            'profitable': len([a for cat in alerts.values() for a in cat if a['profit_pct'] > 0]),
        }
        
        return {
            'total_positions': total_positions,
            'close_now_count': len(alerts['close_now']),
            'monitoring_count': len(alerts['monitor']),
            'total_profit_available': total_profit_available,
            'profit_breakdown': profit_breakdown,
            'critical_alerts': len([a for a in alerts['close_now'] if a['priority'] in ['CRITICAL', 'URGENT']])
        }
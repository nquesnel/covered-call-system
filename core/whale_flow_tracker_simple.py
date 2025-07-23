"""
Simple Whale Flow Tracker - In-memory only version for Streamlit Cloud
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class SimpleWhaleFlowTracker:
    """Simple in-memory whale flow tracker without database dependencies"""
    
    def __init__(self):
        self.flows = []
        self.followed_flows = []
        self._initialized = True
    
    def log_flow(self, flow: Dict) -> int:
        """Log a new whale flow to memory"""
        try:
            # Add an ID
            flow_id = len(self.flows) + 1
            flow_with_id = {
                'id': flow_id,
                'logged_at': datetime.now().isoformat(),
                **flow
            }
            self.flows.append(flow_with_id)
            return flow_id
        except Exception as e:
            print(f"Error logging flow: {e}")
            return -1
    
    def record_follow(self, flow_id: int, contracts: int, cost: float) -> bool:
        """Record that we followed a whale flow"""
        try:
            # Find the flow
            for flow in self.flows:
                if flow.get('id') == flow_id:
                    flow['followed'] = True
                    flow['followed_contracts'] = contracts
                    flow['followed_cost'] = cost
                    if flow not in self.followed_flows:
                        self.followed_flows.append(flow)
                    return True
            return False
        except Exception as e:
            print(f"Error recording follow: {e}")
            return False
    
    def toggle_followed(self, flow_id: int, contracts: int = 1, cost: float = None) -> bool:
        """Toggle followed status for a flow"""
        try:
            for flow in self.flows:
                if flow.get('id') == flow_id:
                    current_followed = flow.get('followed', False)
                    flow['followed'] = not current_followed
                    
                    if flow['followed']:
                        flow['followed_contracts'] = contracts
                        flow['followed_cost'] = cost or (contracts * flow.get('premium', 0) * 100)
                        if flow not in self.followed_flows:
                            self.followed_flows.append(flow)
                    else:
                        flow['followed_contracts'] = 0
                        flow['followed_cost'] = 0
                        if flow in self.followed_flows:
                            self.followed_flows.remove(flow)
                    return True
            return False
        except Exception as e:
            print(f"Error toggling follow: {e}")
            return False
    
    def update_outcome(self, flow_id: int, result_price: float, 
                      outcome: str, notes: str = "") -> Tuple[bool, Dict]:
        """Update the outcome of a whale flow"""
        try:
            for flow in self.flows:
                if flow.get('id') == flow_id:
                    flow['result_price'] = result_price
                    flow['result_date'] = datetime.now().isoformat()
                    flow['outcome'] = outcome
                    flow['notes'] = notes
                    
                    # Calculate P&L if followed
                    if flow.get('followed'):
                        contracts = flow.get('followed_contracts', 0)
                        cost = flow.get('followed_cost', 0)
                        revenue = result_price * contracts * 100
                        pnl = revenue - cost
                        return_pct = (pnl / cost * 100) if cost > 0 else 0
                        
                        flow['result_pnl'] = pnl
                        flow['result_return_pct'] = return_pct
                    else:
                        flow['result_pnl'] = 0
                        flow['result_return_pct'] = 0
                    
                    return True, {
                        'pnl': flow.get('result_pnl', 0),
                        'return_pct': flow.get('result_return_pct', 0),
                        'outcome': outcome
                    }
            
            return False, {}
        except Exception as e:
            print(f"Error updating outcome: {e}")
            return False, {}
    
    def get_recent_flows(self, days: int = 30) -> List[Dict]:
        """Get recent whale flows"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            recent = []
            
            for flow in reversed(self.flows):  # Most recent first
                # Parse timestamp
                timestamp_str = flow.get('timestamp', flow.get('logged_at', ''))
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if timestamp > cutoff:
                            recent.append(flow)
                    except:
                        recent.append(flow)  # Include if can't parse date
                        
            return recent[:50]  # Limit to 50 most recent
        except Exception as e:
            print(f"Error getting recent flows: {e}")
            return []
    
    def get_followed_flows(self) -> List[Dict]:
        """Get all flows we followed"""
        return [f for f in self.flows if f.get('followed', False)]
    
    def get_all_flows_count(self) -> int:
        """Get total count of all flows"""
        return len(self.flows)
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics for followed flows"""
        try:
            total_flows = len(self.flows)
            followed = [f for f in self.flows if f.get('followed', False)]
            flows_followed = len(followed)
            
            wins = len([f for f in followed if f.get('outcome') == 'WIN'])
            losses = len([f for f in followed if f.get('outcome') == 'LOSS'])
            completed = wins + losses
            
            total_pnl = sum(f.get('result_pnl', 0) for f in followed)
            
            returns = [f.get('result_return_pct', 0) for f in followed if f.get('result_return_pct')]
            avg_return = sum(returns) / len(returns) if returns else 0
            
            # Best and worst trades
            completed_trades = [f for f in followed if f.get('result_pnl') is not None]
            best_trade = max(completed_trades, key=lambda x: x.get('result_pnl', 0)) if completed_trades else None
            worst_trade = min(completed_trades, key=lambda x: x.get('result_pnl', 0)) if completed_trades else None
            
            return {
                'total_flows_seen': total_flows,
                'flows_followed': flows_followed,
                'follow_rate': flows_followed / max(total_flows, 1),
                'wins': wins,
                'losses': losses,
                'win_rate': wins / max(completed, 1) if completed else 0,
                'total_pnl': total_pnl,
                'avg_return_pct': avg_return,
                'best_trade': {
                    'symbol': best_trade.get('symbol', ''),
                    'pnl': best_trade.get('result_pnl', 0),
                    'return_pct': best_trade.get('result_return_pct', 0)
                } if best_trade else None,
                'worst_trade': {
                    'symbol': worst_trade.get('symbol', ''),
                    'pnl': worst_trade.get('result_pnl', 0),
                    'return_pct': worst_trade.get('result_return_pct', 0)
                } if worst_trade else None
            }
        except Exception as e:
            print(f"Error getting performance stats: {e}")
            return {
                'total_flows_seen': 0,
                'flows_followed': 0,
                'follow_rate': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_return_pct': 0,
                'best_trade': None,
                'worst_trade': None
            }
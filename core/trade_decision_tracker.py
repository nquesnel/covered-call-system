"""
Trade Decision Tracker - Log every opportunity shown (TAKE/PASS) to analyze winners
Track outcomes 30-45 days later to identify patterns in successful trades
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd


class TradeDecisionTracker:
    """
    Track every covered call opportunity shown to the user
    Log whether they took it or passed, and track actual outcomes
    """
    
    def __init__(self, decisions_file: str = "data/trade_decisions.json"):
        self.decisions_file = decisions_file
        self.decisions = []
        self._ensure_data_dir()
        self.load_decisions()
    
    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist"""
        data_dir = os.path.dirname(self.decisions_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
    
    def load_decisions(self):
        """Load decisions from JSON file"""
        if os.path.exists(self.decisions_file):
            try:
                with open(self.decisions_file, 'r') as f:
                    self.decisions = json.load(f)
            except:
                self.decisions = []
        else:
            self.decisions = []
            self.save_decisions()
    
    def save_decisions(self):
        """Save decisions to JSON file"""
        try:
            with open(self.decisions_file, 'w') as f:
                json.dump(self.decisions, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not save decisions: {e}")
    
    def log_opportunity(self, opportunity: Dict, decision: str, notes: str = "") -> str:
        """
        Log an opportunity that was shown to the user
        
        Args:
            opportunity: The opportunity details from scanner
            decision: 'TAKE', 'PASS', or 'PENDING'
            notes: User notes about why they made this decision
        """
        decision_record = {
            'id': f"{opportunity['symbol']}_{opportunity['strike']}_{opportunity['expiration']}_{datetime.now().isoformat()}",
            'timestamp': datetime.now().isoformat(),
            'decision': decision,
            'notes': notes,
            
            # Opportunity details
            'symbol': opportunity['symbol'],
            'strike': opportunity['strike'],
            'expiration': opportunity['expiration'],
            'days_to_exp': opportunity['days_to_exp'],
            'current_price': opportunity['current_price'],
            'premium': opportunity['premium'],
            'monthly_yield': opportunity['monthly_yield'],
            'static_return': opportunity['static_return'],
            'if_called_return': opportunity['if_called_return'],
            
            # Risk metrics at time of decision
            'iv_rank': opportunity.get('iv_rank', 0),
            'delta': opportunity.get('delta', 0),
            'win_probability': opportunity['win_probability'],
            'confidence_score': opportunity['confidence_score'],
            'growth_score': opportunity['growth_score'],
            'earnings_before_exp': opportunity.get('earnings_before_exp', False),
            
            # Outcome tracking (to be filled later)
            'outcome': None,  # 'WIN', 'LOSS', 'EXPIRED_WORTHLESS', 'CLOSED_EARLY'
            'actual_return': None,
            'stock_price_at_exp': None,
            'closed_date': None,
            'closed_price': None,
            'days_held': None
        }
        
        self.decisions.append(decision_record)
        self.save_decisions()
        
        return decision_record['id']
    
    def update_decision(self, decision_id: str, updates: Dict) -> bool:
        """Update a decision record (e.g., change from PENDING to TAKE/PASS)"""
        for decision in self.decisions:
            if decision['id'] == decision_id:
                decision.update(updates)
                self.save_decisions()
                return True
        return False
    
    def record_outcome(self, decision_id: str, outcome: str, 
                      stock_price_at_exp: float, closed_price: float = None,
                      closed_date: str = None) -> bool:
        """
        Record the actual outcome of a trade decision
        
        Args:
            decision_id: The ID of the decision to update
            outcome: 'WIN', 'LOSS', 'EXPIRED_WORTHLESS', 'CLOSED_EARLY'
            stock_price_at_exp: Stock price at expiration
            closed_price: Price at which option was closed (if closed early)
            closed_date: Date when position was closed
        """
        for decision in self.decisions:
            if decision['id'] == decision_id:
                decision['outcome'] = outcome
                decision['stock_price_at_exp'] = stock_price_at_exp
                
                if closed_price:
                    decision['closed_price'] = closed_price
                if closed_date:
                    decision['closed_date'] = closed_date
                    # Calculate days held
                    entry_date = datetime.fromisoformat(decision['timestamp'])
                    close_date = datetime.fromisoformat(closed_date)
                    decision['days_held'] = (close_date - entry_date).days
                
                # Calculate actual return
                if decision['decision'] == 'TAKE':
                    premium = decision['premium']
                    if outcome == 'EXPIRED_WORTHLESS':
                        decision['actual_return'] = premium
                    elif outcome == 'CLOSED_EARLY' and closed_price:
                        decision['actual_return'] = premium - closed_price
                    elif outcome == 'LOSS':
                        # Stock was called away
                        strike_gain = decision['strike'] - decision['current_price']
                        decision['actual_return'] = premium + strike_gain
                
                self.save_decisions()
                return True
        return False
    
    def get_pending_outcomes(self, days_past_exp: int = 3) -> List[Dict]:
        """Get decisions that need outcome recording (past expiration)"""
        pending = []
        today = datetime.now()
        
        for decision in self.decisions:
            if decision['decision'] == 'TAKE' and decision['outcome'] is None:
                exp_date = datetime.strptime(decision['expiration'], '%Y-%m-%d')
                if (today - exp_date).days >= days_past_exp:
                    pending.append(decision)
        
        return pending
    
    def get_statistics(self) -> Dict:
        """Calculate win rate and other statistics"""
        taken_trades = [d for d in self.decisions if d['decision'] == 'TAKE']
        completed_trades = [d for d in taken_trades if d['outcome'] is not None]
        
        if not completed_trades:
            return {
                'total_shown': len(self.decisions),
                'total_taken': len(taken_trades),
                'total_passed': len([d for d in self.decisions if d['decision'] == 'PASS']),
                'take_rate': len(taken_trades) / len(self.decisions) if self.decisions else 0,
                'completed_trades': 0,
                'win_rate': 0,
                'avg_return': 0,
                'best_trade': None,
                'worst_trade': None
            }
        
        wins = [d for d in completed_trades if d['outcome'] in ['WIN', 'EXPIRED_WORTHLESS']]
        total_return = sum(d.get('actual_return', 0) for d in completed_trades if d.get('actual_return'))
        
        best_trade = max(completed_trades, key=lambda x: x.get('actual_return', 0))
        worst_trade = min(completed_trades, key=lambda x: x.get('actual_return', 0))
        
        return {
            'total_shown': len(self.decisions),
            'total_taken': len(taken_trades),
            'total_passed': len([d for d in self.decisions if d['decision'] == 'PASS']),
            'take_rate': len(taken_trades) / len(self.decisions) if self.decisions else 0,
            'completed_trades': len(completed_trades),
            'win_rate': len(wins) / len(completed_trades) if completed_trades else 0,
            'avg_return': total_return / len(completed_trades) if completed_trades else 0,
            'total_return': total_return,
            'best_trade': best_trade,
            'worst_trade': worst_trade
        }
    
    def analyze_patterns(self) -> Dict:
        """Analyze patterns in winning vs losing trades"""
        completed = [d for d in self.decisions if d['outcome'] is not None]
        
        if not completed:
            return {'message': 'No completed trades to analyze'}
        
        df = pd.DataFrame(completed)
        
        # Define winners
        df['is_winner'] = df['outcome'].isin(['WIN', 'EXPIRED_WORTHLESS'])
        
        # Analyze by various factors
        patterns = {
            'by_iv_rank': self._analyze_by_factor(df, 'iv_rank', bins=[0, 30, 50, 70, 100]),
            'by_delta': self._analyze_by_factor(df, 'delta', bins=[0, 0.2, 0.3, 0.4, 1.0]),
            'by_dte': self._analyze_by_factor(df, 'days_to_exp', bins=[0, 21, 35, 45, 60]),
            'by_yield': self._analyze_by_factor(df, 'monthly_yield', bins=[0, 2, 4, 6, 10, 100]),
            'by_growth_score': self._analyze_by_factor(df, 'growth_score', bins=[0, 40, 60, 75, 100]),
            'earnings_impact': {
                'with_earnings': df[df['earnings_before_exp'] == True]['is_winner'].mean() if any(df['earnings_before_exp']) else 0,
                'without_earnings': df[df['earnings_before_exp'] == False]['is_winner'].mean() if any(~df['earnings_before_exp']) else 0
            }
        }
        
        # Find best performing characteristics
        best_characteristics = []
        for factor, analysis in patterns.items():
            if isinstance(analysis, dict) and 'ranges' in analysis:
                for range_data in analysis['ranges']:
                    if range_data['win_rate'] > 0.7 and range_data['count'] >= 5:
                        best_characteristics.append({
                            'factor': factor,
                            'range': range_data['range'],
                            'win_rate': range_data['win_rate'],
                            'sample_size': range_data['count']
                        })
        
        patterns['best_characteristics'] = sorted(
            best_characteristics, 
            key=lambda x: x['win_rate'], 
            reverse=True
        )[:5]
        
        return patterns
    
    def _analyze_by_factor(self, df: pd.DataFrame, factor: str, bins: List[float]) -> Dict:
        """Analyze win rate by a specific factor"""
        if factor not in df.columns:
            return {'error': f'Factor {factor} not found'}
        
        df['range'] = pd.cut(df[factor], bins=bins)
        
        analysis = []
        for range_val in df['range'].unique():
            if pd.isna(range_val):
                continue
            
            range_df = df[df['range'] == range_val]
            if len(range_df) > 0:
                analysis.append({
                    'range': str(range_val),
                    'count': len(range_df),
                    'win_rate': range_df['is_winner'].mean(),
                    'avg_return': range_df['actual_return'].mean() if 'actual_return' in range_df else 0
                })
        
        return {
            'ranges': sorted(analysis, key=lambda x: x['range']),
            'best_range': max(analysis, key=lambda x: x['win_rate']) if analysis else None
        }
    
    def get_recent_decisions(self, days: int = 30) -> List[Dict]:
        """Get decisions from the last N days"""
        cutoff = datetime.now() - timedelta(days=days)
        recent = []
        
        for decision in self.decisions:
            decision_date = datetime.fromisoformat(decision['timestamp'])
            if decision_date >= cutoff:
                recent.append(decision)
        
        return sorted(recent, key=lambda x: x['timestamp'], reverse=True)
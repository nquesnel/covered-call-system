"""
Trade Tracker - Track all trade decisions and outcomes for performance analysis
"""
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class TradeTracker:
    """Track covered call trade opportunities, decisions, and outcomes"""
    
    def __init__(self, db_file: str = "data/trades.db"):
        self.db_file = db_file
        self._ensure_data_dir()
        self.init_database()
    
    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist"""
        data_dir = os.path.dirname(self.db_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
    
    def init_database(self):
        """Create tables for trade tracking"""
        conn = sqlite3.connect(self.db_file)
        
        # Main trade opportunities table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS trade_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_presented TEXT NOT NULL,
                symbol TEXT NOT NULL,
                strategy TEXT,
                strike REAL NOT NULL,
                expiration TEXT NOT NULL,
                days_to_exp INTEGER,
                premium REAL NOT NULL,
                bid REAL,
                ask REAL,
                volume INTEGER,
                open_interest INTEGER,
                iv_rank REAL,
                iv_percentile REAL,
                delta REAL,
                growth_score INTEGER,
                confidence_score INTEGER,
                monthly_yield REAL,
                win_probability REAL,
                decision TEXT,
                contracts INTEGER DEFAULT 0,
                decision_date TEXT,
                reason TEXT,
                date_closed TEXT,
                closing_price REAL,
                profit_loss REAL,
                outcome TEXT,
                notes TEXT
            )
        ''')
        
        # Performance metrics table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                metric_value REAL NOT NULL,
                period_days INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_opportunity(self, trade_data: Dict) -> int:
        """Log new trade opportunity"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trade_opportunities 
            (date_presented, symbol, strategy, strike, expiration, days_to_exp,
             premium, bid, ask, volume, open_interest, iv_rank, iv_percentile,
             delta, growth_score, confidence_score, monthly_yield, win_probability)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            trade_data['symbol'],
            trade_data.get('strategy', 'COVERED_CALL'),
            trade_data['strike'],
            trade_data['expiration'],
            trade_data.get('days_to_exp'),
            trade_data['premium'],
            trade_data.get('bid'),
            trade_data.get('ask'),
            trade_data.get('volume'),
            trade_data.get('open_interest'),
            trade_data.get('iv_rank'),
            trade_data.get('iv_percentile'),
            trade_data.get('delta'),
            trade_data.get('growth_score'),
            trade_data.get('confidence_score'),
            trade_data.get('monthly_yield'),
            trade_data.get('win_probability')
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return trade_id
    
    def update_decision(self, trade_id: int, decision: str, 
                       contracts: int = 0, reason: str = "") -> bool:
        """Update take/pass decision for a trade"""
        if decision not in ['TAKE', 'PASS']:
            raise ValueError("Decision must be 'TAKE' or 'PASS'")
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE trade_opportunities 
            SET decision = ?, contracts = ?, reason = ?, decision_date = ?
            WHERE id = ?
        ''', (decision, contracts, reason, datetime.now().isoformat(), trade_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def close_trade(self, trade_id: int, closing_price: float, 
                   outcome: str, notes: str = "") -> Tuple[bool, Dict]:
        """Log trade closure and calculate P&L"""
        if outcome not in ['WIN', 'LOSS', 'ASSIGNED', 'EXPIRED', 'ROLLED']:
            raise ValueError("Invalid outcome type")
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Get original trade data
        cursor.execute('SELECT * FROM trade_opportunities WHERE id = ?', (trade_id,))
        trade = cursor.fetchone()
        
        if not trade:
            conn.close()
            return False, {}
        
        # Calculate P&L
        premium_collected = trade[7] * trade[19] * 100  # premium * contracts * 100
        closing_cost = closing_price * trade[19] * 100 if closing_price else 0
        profit_loss = premium_collected - closing_cost
        
        # Update trade record
        cursor.execute('''
            UPDATE trade_opportunities 
            SET date_closed = ?, closing_price = ?, profit_loss = ?, 
                outcome = ?, notes = ?
            WHERE id = ?
        ''', (
            datetime.now().isoformat(), 
            closing_price, 
            profit_loss, 
            outcome,
            notes,
            trade_id
        ))
        
        conn.commit()
        conn.close()
        
        return True, {
            'premium_collected': premium_collected,
            'closing_cost': closing_cost,
            'profit_loss': profit_loss,
            'outcome': outcome
        }
    
    def get_trade_by_id(self, trade_id: int) -> Optional[Dict]:
        """Get single trade details"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM trade_opportunities WHERE id = ?', (trade_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_active_trades(self) -> List[Dict]:
        """Get all open trades (taken but not closed)"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM trade_opportunities 
            WHERE decision = 'TAKE' AND outcome IS NULL
            ORDER BY expiration ASC
        ''')
        
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return trades
    
    def get_opportunities(self, days: int = 7) -> List[Dict]:
        """Get recent trade opportunities"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT * FROM trade_opportunities 
            WHERE date_presented > ?
            ORDER BY date_presented DESC
        ''', (cutoff_date,))
        
        opportunities = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return opportunities
    
    def get_performance_stats(self, days: int = 30) -> Dict:
        """Get comprehensive performance statistics"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Overall stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total_opportunities,
                SUM(CASE WHEN decision = 'TAKE' THEN 1 ELSE 0 END) as trades_taken,
                SUM(CASE WHEN decision = 'PASS' THEN 1 ELSE 0 END) as trades_passed,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN outcome = 'ASSIGNED' THEN 1 ELSE 0 END) as assigned,
                SUM(CASE WHEN decision = 'TAKE' THEN profit_loss ELSE 0 END) as total_profit,
                AVG(CASE WHEN decision = 'TAKE' THEN profit_loss ELSE NULL END) as avg_profit,
                AVG(confidence_score) as avg_confidence,
                AVG(CASE WHEN decision = 'TAKE' THEN confidence_score ELSE NULL END) as avg_confidence_taken
            FROM trade_opportunities 
            WHERE date_presented > ?
        ''', (cutoff_date,))
        
        stats = cursor.fetchone()
        
        # Calculate additional metrics
        trades_taken = stats[1] or 0
        wins = stats[3] or 0
        losses = stats[4] or 0
        completed_trades = wins + losses
        
        # Get passed trades that would have been winners
        cursor.execute('''
            SELECT COUNT(*), AVG(monthly_yield)
            FROM trade_opportunities 
            WHERE date_presented > ? 
            AND decision = 'PASS'
            AND confidence_score > 70
        ''', (cutoff_date,))
        
        missed_opportunities = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_opportunities': stats[0] or 0,
            'trades_taken': trades_taken,
            'trades_passed': stats[2] or 0,
            'take_rate': trades_taken / max(stats[0], 1) if stats[0] else 0,
            'wins': wins,
            'losses': losses,
            'assigned': stats[5] or 0,
            'win_rate': wins / max(completed_trades, 1) if completed_trades else 0,
            'total_profit': stats[6] or 0,
            'avg_profit_per_trade': stats[7] or 0,
            'avg_confidence_all': stats[8] or 0,
            'avg_confidence_taken': stats[9] or 0,
            'high_confidence_passes': missed_opportunities[0] or 0,
            'avg_yield_passed': missed_opportunities[1] or 0
        }
    
    def get_symbol_performance(self, symbol: str) -> Dict:
        """Get performance stats for a specific symbol"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(profit_loss) as total_profit,
                AVG(profit_loss) as avg_profit,
                AVG(confidence_score) as avg_confidence,
                MAX(profit_loss) as best_trade,
                MIN(profit_loss) as worst_trade
            FROM trade_opportunities 
            WHERE symbol = ? AND decision = 'TAKE' AND outcome IS NOT NULL
        ''', (symbol,))
        
        stats = cursor.fetchone()
        conn.close()
        
        total_trades = stats[0] or 0
        wins = stats[1] or 0
        
        return {
            'symbol': symbol,
            'total_trades': total_trades,
            'wins': wins,
            'win_rate': wins / max(total_trades, 1) if total_trades else 0,
            'total_profit': stats[2] or 0,
            'avg_profit': stats[3] or 0,
            'avg_confidence': stats[4] or 0,
            'best_trade': stats[5] or 0,
            'worst_trade': stats[6] or 0
        }
    
    def record_metric(self, metric_type: str, metric_value: float, period_days: int = 1):
        """Record a performance metric for tracking"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO performance_metrics (date, metric_type, metric_value, period_days)
            VALUES (?, ?, ?, ?)
        ''', (datetime.now().isoformat(), metric_type, metric_value, period_days))
        
        conn.commit()
        conn.close()
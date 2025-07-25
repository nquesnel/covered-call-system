"""
Whale Flow History Tracker - Track and analyze institutional flows over time
"""
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class WhaleFlowTracker:
    """Track whale flows and their outcomes"""
    
    def __init__(self, db_file: str = "data/whale_flows.db"):
        self.db_file = db_file
        self._initialized = False
        try:
            self._ensure_data_dir()
            self.init_database()
            self._initialized = True
        except Exception as e:
            print(f"Warning: Could not initialize whale flow database: {e}")
            # Use in-memory database as fallback
            self.db_file = ":memory:"
            try:
                self.init_database()
                self._initialized = True
            except Exception as e2:
                print(f"Error: Could not initialize in-memory database: {e2}")
                self._initialized = False
    
    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist"""
        data_dir = os.path.dirname(self.db_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
    
    def init_database(self):
        """Create tables for whale flow tracking"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='whale_flows'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # Create new table with all columns
            conn.execute('''
                CREATE TABLE whale_flows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    flow_type TEXT NOT NULL,
                    option_type TEXT NOT NULL,
                    strike REAL NOT NULL,
                    expiration TEXT NOT NULL,
                    days_to_exp INTEGER,
                    contracts INTEGER NOT NULL,
                    premium REAL NOT NULL,
                    total_premium REAL NOT NULL,
                    unusual_factor REAL,
                    sentiment TEXT,
                    confidence INTEGER,
                    whale_score INTEGER DEFAULT 0,
                    underlying_price REAL,
                    followed BOOLEAN DEFAULT 0,
                    followed_contracts INTEGER DEFAULT 0,
                    followed_cost REAL DEFAULT 0,
                    result_price REAL,
                    result_date TEXT,
                    result_pnl REAL,
                    result_return_pct REAL,
                    outcome TEXT,
                    notes TEXT
                )
            ''')
        else:
            # Table exists, check if whale_score column exists
            cursor.execute("PRAGMA table_info(whale_flows)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'whale_score' not in column_names:
                # Add whale_score column to existing table
                try:
                    conn.execute('ALTER TABLE whale_flows ADD COLUMN whale_score INTEGER DEFAULT 0')
                    print("Added whale_score column to existing whale_flows table")
                except sqlite3.OperationalError:
                    # Column might already exist
                    pass
        
        # Create indexes for faster queries
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_whale_flows_symbol 
            ON whale_flows(symbol)
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_whale_flows_timestamp 
            ON whale_flows(timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def log_flow(self, flow: Dict) -> int:
        """Log a new whale flow"""
        # Skip if database not initialized
        if not self._initialized:
            print("Warning: Database not initialized, skipping flow logging")
            return -1
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return -1
        
        try:
        
        # Check if this exact flow already exists (avoid duplicates)
        try:
            cursor.execute('''
                SELECT id FROM whale_flows 
                WHERE symbol = ? AND strike = ? AND expiration = ? 
                AND ABS(total_premium - ?) < 100
                AND datetime(timestamp) > datetime('now', '-5 minutes')
            ''', (
                flow['symbol'], 
                flow['strike'], 
                flow['expiration'],
                flow['total_premium']
            ))
            existing = cursor.fetchone()
        except sqlite3.OperationalError:
            # Table might not exist, try to create it
            conn.close()
            self.init_database()
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            existing = None
        
        if existing:
            conn.close()
            return existing[0]
        
        # Insert new flow
        try:
            # Try with whale_score column
            cursor.execute('''
                INSERT INTO whale_flows (
                    timestamp, symbol, flow_type, option_type, strike, expiration,
                    days_to_exp, contracts, premium, total_premium, unusual_factor,
                    sentiment, confidence, whale_score, underlying_price
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                flow.get('timestamp', datetime.now().isoformat()),
                flow['symbol'],
                flow['flow_type'],
                flow['option_type'],
                flow['strike'],
                flow['expiration'],
                flow.get('days_to_exp'),
                flow.get('contracts', 0),
                flow.get('premium_per_contract', 0),
                flow['total_premium'],
                flow.get('unusual_factor', 0),
                flow.get('sentiment', ''),
                flow.get('smart_money_confidence', 0),
                flow.get('whale_analysis', {}).get('whale_score', 0) if 'whale_analysis' in flow else 0,
                flow.get('underlying_price', 0)
            ))
        except sqlite3.OperationalError:
            # Fallback without whale_score for old schema
            cursor.execute('''
                INSERT INTO whale_flows (
                    timestamp, symbol, flow_type, option_type, strike, expiration,
                    days_to_exp, contracts, premium, total_premium, unusual_factor,
                    sentiment, confidence, underlying_price
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                flow.get('timestamp', datetime.now().isoformat()),
                flow['symbol'],
                flow['flow_type'],
                flow['option_type'],
                flow['strike'],
                flow['expiration'],
                flow.get('days_to_exp'),
                flow.get('contracts', 0),
                flow.get('premium_per_contract', 0),
                flow['total_premium'],
                flow.get('unusual_factor', 0),
                flow.get('sentiment', ''),
                flow.get('smart_money_confidence', 0),
                flow.get('underlying_price', 0)
            ))
        
            flow_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return flow_id
        except Exception as e:
            print(f"Error in log_flow: {e}")
            try:
                conn.close()
            except:
                pass
            return -1
    
    def record_follow(self, flow_id: int, contracts: int, cost: float) -> bool:
        """Record that we followed a whale flow"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE whale_flows 
            SET followed = 1, followed_contracts = ?, followed_cost = ?
            WHERE id = ?
        ''', (contracts, cost, flow_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def toggle_followed(self, flow_id: int, contracts: int = 1, cost: float = None) -> bool:
        """Toggle followed status for a flow (for manual tracking)"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Get current status
        cursor.execute('SELECT followed, premium FROM whale_flows WHERE id = ?', (flow_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
        
        current_followed, premium = result
        new_followed = 0 if current_followed else 1
        
        # If marking as followed and no cost provided, estimate it
        if new_followed and cost is None:
            cost = contracts * premium * 100
        
        if new_followed:
            cursor.execute('''
                UPDATE whale_flows 
                SET followed = 1, followed_contracts = ?, followed_cost = ?
                WHERE id = ?
            ''', (contracts, cost, flow_id))
        else:
            cursor.execute('''
                UPDATE whale_flows 
                SET followed = 0, followed_contracts = 0, followed_cost = 0
                WHERE id = ?
            ''', (flow_id,))
        
        conn.commit()
        conn.close()
        
        return True
    
    def update_outcome(self, flow_id: int, result_price: float, 
                      outcome: str, notes: str = "") -> Tuple[bool, Dict]:
        """Update the outcome of a whale flow"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Get original flow data
        cursor.execute('SELECT * FROM whale_flows WHERE id = ?', (flow_id,))
        flow = cursor.fetchone()
        
        if not flow:
            conn.close()
            return False, {}
        
        # Calculate P&L if we followed
        if flow[15]:  # followed = True
            contracts = flow[16]  # followed_contracts
            cost = flow[17]      # followed_cost
            revenue = result_price * contracts * 100
            pnl = revenue - cost
            return_pct = (pnl / cost * 100) if cost > 0 else 0
        else:
            pnl = 0
            return_pct = 0
        
        # Update the outcome
        cursor.execute('''
            UPDATE whale_flows 
            SET result_price = ?, result_date = ?, result_pnl = ?,
                result_return_pct = ?, outcome = ?, notes = ?
            WHERE id = ?
        ''', (
            result_price,
            datetime.now().isoformat(),
            pnl,
            return_pct,
            outcome,
            notes,
            flow_id
        ))
        
        conn.commit()
        conn.close()
        
        return True, {
            'pnl': pnl,
            'return_pct': return_pct,
            'outcome': outcome
        }
    
    def get_recent_flows(self, days: int = 30) -> List[Dict]:
        """Get recent whale flows"""
        if not self._initialized:
            return []
        
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return []
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT * FROM whale_flows 
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        ''', (cutoff_date,))
        
        flows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return flows
    
    def get_followed_flows(self) -> List[Dict]:
        """Get all flows we followed"""
        if not self._initialized:
            return []
        
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return []
        
        cursor.execute('''
            SELECT * FROM whale_flows 
            WHERE followed = 1
            ORDER BY timestamp DESC
        ''')
        
        flows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return flows
    
    def get_all_flows_count(self) -> int:
        """Get total count of all flows in database"""
        if not self._initialized:
            return 0
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM whale_flows')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            print(f"Error getting flow count: {e}")
            return 0
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics for followed flows"""
        if not self._initialized:
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
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
        except Exception as e:
            print(f"Error connecting to database: {e}")
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
        
        # Get total flows count
        total_flows_count = self.get_all_flows_count()
        
        # Overall stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total_flows,
                SUM(CASE WHEN followed = 1 THEN 1 ELSE 0 END) as flows_followed,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN followed = 1 THEN result_pnl ELSE 0 END) as total_pnl,
                AVG(CASE WHEN followed = 1 AND result_pnl IS NOT NULL THEN result_return_pct ELSE NULL END) as avg_return
            FROM whale_flows
        ''')
        
        stats = cursor.fetchone()
        
        # Best and worst trades
        cursor.execute('''
            SELECT symbol, result_pnl, result_return_pct, timestamp
            FROM whale_flows 
            WHERE followed = 1 AND result_pnl IS NOT NULL
            ORDER BY result_pnl DESC
            LIMIT 1
        ''')
        best_trade = cursor.fetchone()
        
        cursor.execute('''
            SELECT symbol, result_pnl, result_return_pct, timestamp
            FROM whale_flows 
            WHERE followed = 1 AND result_pnl IS NOT NULL
            ORDER BY result_pnl ASC
            LIMIT 1
        ''')
        worst_trade = cursor.fetchone()
        
        conn.close()
        
        flows_followed = stats[1] or 0
        wins = stats[2] or 0
        losses = stats[3] or 0
        completed = wins + losses
        
        return {
            'total_flows_seen': total_flows_count,
            'flows_followed': flows_followed,
            'follow_rate': flows_followed / max(total_flows_count, 1) if total_flows_count else 0,
            'wins': wins,
            'losses': losses,
            'win_rate': wins / max(completed, 1) if completed else 0,
            'total_pnl': stats[4] or 0,
            'avg_return_pct': stats[5] or 0,
            'best_trade': {
                'symbol': best_trade[0] if best_trade else None,
                'pnl': best_trade[1] if best_trade else 0,
                'return_pct': best_trade[2] if best_trade else 0
            } if best_trade else None,
            'worst_trade': {
                'symbol': worst_trade[0] if worst_trade else None,
                'pnl': worst_trade[1] if worst_trade else 0,
                'return_pct': worst_trade[2] if worst_trade else 0
            } if worst_trade else None
        }
    
    def get_symbol_performance(self, symbol: str) -> Dict:
        """Get whale flow performance for a specific symbol"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_flows,
                SUM(CASE WHEN followed = 1 THEN 1 ELSE 0 END) as flows_followed,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(result_pnl) as total_pnl,
                AVG(result_return_pct) as avg_return
            FROM whale_flows 
            WHERE symbol = ?
        ''', (symbol,))
        
        stats = cursor.fetchone()
        conn.close()
        
        return {
            'symbol': symbol,
            'total_flows': stats[0] or 0,
            'flows_followed': stats[1] or 0,
            'wins': stats[2] or 0,
            'total_pnl': stats[3] or 0,
            'avg_return': stats[4] or 0
        }
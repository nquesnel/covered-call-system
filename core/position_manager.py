"""
Position Manager - Handle portfolio positions for covered call tracking
"""
import json
import os
from datetime import datetime
from typing import Dict, Optional, List


class PositionManager:
    """Manage stock positions for covered call income system"""
    
    def __init__(self, positions_file: str = "data/positions.json"):
        self.positions_file = positions_file
        self.positions = {}
        self._ensure_data_dir()
        self.load_positions()
    
    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist"""
        data_dir = os.path.dirname(self.positions_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
    
    def load_positions(self):
        """Load positions from JSON file"""
        if os.path.exists(self.positions_file):
            try:
                with open(self.positions_file, 'r') as f:
                    self.positions = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                self.positions = {}
        else:
            self.positions = {}
            self.save_positions()
    
    def save_positions(self):
        """Save positions to JSON file"""
        with open(self.positions_file, 'w') as f:
            json.dump(self.positions, f, indent=2)
    
    def add_position(self, symbol: str, shares: int, cost_basis: float, 
                    account_type: str = "taxable", notes: str = "") -> str:
        """Add new stock position"""
        symbol = symbol.upper()
        
        position = {
            'symbol': symbol,
            'shares': int(shares),
            'cost_basis': round(float(cost_basis), 2),
            'account_type': account_type,
            'date_added': datetime.now().isoformat(),
            'notes': notes
        }
        
        self.positions[symbol] = position
        self.save_positions()
        return f"Added {shares} shares of {symbol} at ${cost_basis:.2f}"
    
    def update_position(self, symbol: str, shares: Optional[int] = None, 
                       cost_basis: Optional[float] = None, account_type: Optional[str] = None,
                       notes: Optional[str] = None) -> str:
        """Update existing position"""
        symbol = symbol.upper()
        
        if symbol not in self.positions:
            return f"Position {symbol} not found"
        
        if shares is not None:
            self.positions[symbol]['shares'] = int(shares)
        if cost_basis is not None:
            self.positions[symbol]['cost_basis'] = round(float(cost_basis), 2)
        if account_type is not None:
            self.positions[symbol]['account_type'] = account_type
        if notes is not None:
            self.positions[symbol]['notes'] = notes
            
        self.save_positions()
        return f"Updated {symbol} position"
    
    def delete_position(self, symbol: str) -> str:
        """Remove position entirely"""
        symbol = symbol.upper()
        
        if symbol in self.positions:
            del self.positions[symbol]
            self.save_positions()
            return f"Deleted {symbol} position"
        return f"Position {symbol} not found"
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get single position details"""
        return self.positions.get(symbol.upper())
    
    def get_all_positions(self) -> Dict:
        """Get all positions"""
        return self.positions.copy()
    
    def get_eligible_positions(self, min_shares: int = 100) -> Dict:
        """Return positions with enough shares for covered calls"""
        eligible = {}
        for symbol, pos in self.positions.items():
            if pos['shares'] >= min_shares:
                eligible[symbol] = pos
        return eligible
    
    def get_positions_by_account(self, account_type: str) -> Dict:
        """Get positions filtered by account type"""
        filtered = {}
        for symbol, pos in self.positions.items():
            if pos['account_type'] == account_type:
                filtered[symbol] = pos
        return filtered
    
    def calculate_total_value(self, current_prices: Dict[str, float]) -> Dict:
        """Calculate total portfolio value given current prices"""
        total_value = 0
        total_cost = 0
        positions_value = {}
        
        for symbol, pos in self.positions.items():
            cost = pos['shares'] * pos['cost_basis']
            total_cost += cost
            
            if symbol in current_prices:
                value = pos['shares'] * current_prices[symbol]
                total_value += value
                gain_loss = value - cost
                gain_loss_pct = (gain_loss / cost) * 100 if cost > 0 else 0
                
                positions_value[symbol] = {
                    'shares': pos['shares'],
                    'cost_basis': pos['cost_basis'],
                    'current_price': current_prices[symbol],
                    'total_cost': cost,
                    'total_value': value,
                    'gain_loss': gain_loss,
                    'gain_loss_pct': gain_loss_pct
                }
        
        return {
            'positions': positions_value,
            'total_cost': total_cost,
            'total_value': total_value,
            'total_gain_loss': total_value - total_cost,
            'total_gain_loss_pct': ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
        }
    
    def get_covered_call_capacity(self) -> Dict[str, int]:
        """Calculate how many covered call contracts can be sold"""
        capacity = {}
        for symbol, pos in self.positions.items():
            contracts = pos['shares'] // 100
            if contracts > 0:
                capacity[symbol] = contracts
        return capacity
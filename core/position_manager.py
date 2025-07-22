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
        self._migrate_positions_if_needed()
    
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
    
    def _migrate_positions_if_needed(self):
        """Migrate old symbol-only keys to symbol_account format"""
        needs_migration = False
        migrated_positions = {}
        
        for key, position in self.positions.items():
            # Check if this is an old-style key (no underscore)
            if '_' not in key and isinstance(position, dict) and 'symbol' in position:
                # This is an old position, migrate it
                account_type = position.get('account_type', 'taxable')
                new_key = f"{position['symbol']}_{account_type.upper()}"
                position['position_key'] = new_key
                migrated_positions[new_key] = position
                needs_migration = True
            else:
                # Keep existing positions as-is
                migrated_positions[key] = position
        
        if needs_migration:
            self.positions = migrated_positions
            self.save_positions()
    
    def save_positions(self):
        """Save positions to JSON file"""
        try:
            with open(self.positions_file, 'w') as f:
                json.dump(self.positions, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save positions to file: {e}")
            # On Streamlit Cloud, file system may be read-only
            # Positions will be stored in session state instead
    
    def add_position(self, symbol: str, shares: int, cost_basis: float, 
                    account_type: str = "taxable", notes: str = "") -> str:
        """Add new stock position"""
        symbol = symbol.upper()
        
        # Create composite key: SYMBOL_ACCOUNT
        position_key = f"{symbol}_{account_type.upper()}"
        
        # Check if this exact position already exists
        if position_key in self.positions:
            # Update existing position by adding shares
            existing_shares = self.positions[position_key]['shares']
            self.positions[position_key]['shares'] = existing_shares + int(shares)
            self.save_positions()
            return f"Added {shares} more shares to existing {symbol} position in {account_type} account"
        
        position = {
            'symbol': symbol,
            'shares': int(shares),
            'cost_basis': round(float(cost_basis), 2),
            'account_type': account_type,
            'date_added': datetime.now().isoformat(),
            'notes': notes,
            'position_key': position_key
        }
        
        self.positions[position_key] = position
        self.save_positions()
        return f"Added {shares} shares of {symbol} at ${cost_basis:.2f} in {account_type} account"
    
    def update_position(self, position_key: str, shares: Optional[int] = None, 
                       cost_basis: Optional[float] = None, account_type: Optional[str] = None,
                       notes: Optional[str] = None) -> str:
        """Update existing position using position key"""
        
        if position_key not in self.positions:
            return f"Position {position_key} not found"
        
        if shares is not None:
            self.positions[position_key]['shares'] = int(shares)
        if cost_basis is not None:
            self.positions[position_key]['cost_basis'] = round(float(cost_basis), 2)
        if account_type is not None:
            # If changing account type, we need to create new key and move position
            old_account = self.positions[position_key]['account_type']
            if account_type != old_account:
                symbol = self.positions[position_key]['symbol']
                new_key = f"{symbol}_{account_type.upper()}"
                
                # Move position to new key
                self.positions[new_key] = self.positions[position_key].copy()
                self.positions[new_key]['account_type'] = account_type
                self.positions[new_key]['position_key'] = new_key
                
                # Delete old position
                del self.positions[position_key]
                position_key = new_key
            
            print(f"DEBUG: Updated position to account type {account_type}")
        if notes is not None:
            self.positions[position_key]['notes'] = notes
            
        self.save_positions()
        return f"Updated position"
    
    def delete_position(self, position_key: str) -> str:
        """Remove position entirely using position key"""
        
        if position_key in self.positions:
            symbol = self.positions[position_key]['symbol']
            account = self.positions[position_key]['account_type']
            del self.positions[position_key]
            self.save_positions()
            return f"Deleted {symbol} position from {account} account"
        return f"Position {position_key} not found"
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get single position details"""
        return self.positions.get(symbol.upper())
    
    def get_all_positions(self) -> Dict:
        """Get all positions"""
        return self.positions.copy()
    
    def get_eligible_positions(self, min_shares: int = 100) -> Dict:
        """Return positions with enough shares for covered calls - grouped by symbol"""
        eligible = {}
        # Group by symbol and combine shares across accounts
        symbol_positions = {}
        
        for key, pos in self.positions.items():
            symbol = pos.get('symbol', key.split('_')[0])
            if symbol not in symbol_positions:
                # Use the first position's data as base
                symbol_positions[symbol] = pos.copy()
                symbol_positions[symbol]['position_keys'] = [key]
            else:
                # Combine shares from multiple accounts
                symbol_positions[symbol]['shares'] += pos['shares']
                symbol_positions[symbol]['position_keys'].append(key)
                # Mark as multi-account
                if pos['account_type'] != symbol_positions[symbol]['account_type']:
                    symbol_positions[symbol]['account_type'] = 'multiple'
        
        # Filter for eligible positions
        for symbol, combined_pos in symbol_positions.items():
            if combined_pos['shares'] >= min_shares:
                eligible[symbol] = combined_pos
                
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
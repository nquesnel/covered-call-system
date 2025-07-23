"""
Data Validator - Ensure data integrity and provide meaningful error messages
"""
from typing import Dict, List, Optional, Any


class DataValidator:
    """Validate and normalize data from various sources"""
    
    @staticmethod
    def validate_stock_data(data: Dict, symbol: str) -> Dict:
        """Validate and normalize stock market data"""
        required_fields = {
            'price': 0.0,
            'volume': 0,
            'market_cap': 0,
            'pe_ratio': 0,
            'dividend_yield': 0,
            'volatility_30d': 0,
            'volatility_60d': 0,
            'rsi': 50,
            'iv_rank': 50,
            'iv_percentile': 50,
            'next_earnings': None,
            'earnings_in_days': 999
        }
        
        validated = {}
        for field, default in required_fields.items():
            validated[field] = data.get(field, default)
            
        # Ensure price is positive
        if validated['price'] <= 0:
            raise ValueError(f"Invalid price for {symbol}: {validated['price']}")
            
        return validated
    
    @staticmethod
    def validate_whale_flow(flow: Dict) -> Dict:
        """Validate and normalize whale flow data"""
        # Map alternative field names
        field_mappings = {
            'volume': ['contracts', 'volume'],
            'premium': ['premium_per_contract', 'premium'],
            'total_premium': ['premium_volume', 'total_premium'],
            'volume_oi_ratio': ['volume_oi_ratio', 'vol_oi_ratio']
        }
        
        validated = flow.copy()
        
        # Apply field mappings
        for standard_field, alternatives in field_mappings.items():
            if standard_field not in validated:
                for alt in alternatives:
                    if alt in flow:
                        validated[standard_field] = flow[alt]
                        break
        
        # Required fields with defaults
        required_with_defaults = {
            'symbol': 'UNKNOWN',
            'underlying_price': 0,
            'trade_type': 'unknown',
            'option_type': 'unknown',
            'strike': 0,
            'expiration': '',
            'days_to_exp': 0,
            'volume': 0,
            'premium': 0,
            'total_premium': 0,
            'open_interest': 1,
            'bid': 0,
            'ask': 0,
            'volume_oi_ratio': 0,
            'execution_side': 'unknown',
            'bid_ask_spread': 0
        }
        
        # Apply defaults for missing fields
        for field, default in required_with_defaults.items():
            if field not in validated:
                validated[field] = default
                
        # Calculate derived fields if missing
        if validated['volume_oi_ratio'] == 0 and validated['volume'] > 0:
            validated['volume_oi_ratio'] = validated['volume'] / max(validated['open_interest'], 1)
            
        if validated['total_premium'] == 0 and validated['premium'] > 0:
            validated['total_premium'] = validated['premium'] * validated['volume'] * 100
            
        if validated['bid_ask_spread'] == 0:
            validated['bid_ask_spread'] = validated['ask'] - validated['bid']
            
        return validated
    
    @staticmethod
    def validate_option_data(option: Dict) -> Dict:
        """Validate and normalize option chain data"""
        required_fields = {
            'strike': 0,
            'expiration': '',
            'bid': 0,
            'ask': 0,
            'last': 0,
            'volume': 0,
            'open_interest': 0,
            'implied_volatility': 0,
            'delta': 0,
            'gamma': 0,
            'theta': 0,
            'vega': 0,
            'iv_rank': 50,
            'iv_percentile': 50
        }
        
        validated = {}
        for field, default in required_fields.items():
            validated[field] = option.get(field, default)
            
        # Ensure bid/ask spread is reasonable
        if validated['ask'] > 0:
            spread_pct = (validated['ask'] - validated['bid']) / validated['ask']
            if spread_pct > 0.5:  # 50% spread is too wide
                validated['bid'] = validated['ask'] * 0.85
                
        return validated
    
    @staticmethod
    def validate_position(position: Dict) -> Dict:
        """Validate position data"""
        required_fields = {
            'symbol': '',
            'shares': 0,
            'cost_basis': 0,
            'account_type': 'taxable',
            'position_key': ''
        }
        
        validated = position.copy()
        
        for field, default in required_fields.items():
            if field not in validated:
                validated[field] = default
                
        # Extract symbol from position key if missing
        if not validated['symbol'] and validated.get('position_key'):
            validated['symbol'] = validated['position_key'].split('_')[0]
            
        # Ensure shares is integer
        validated['shares'] = int(validated.get('shares', 0))
        
        return validated
    
    @staticmethod
    def create_error_response(error_msg: str, data_type: str) -> Dict:
        """Create a standardized error response"""
        return {
            'error': True,
            'error_message': error_msg,
            'data_type': data_type,
            'whale_score': 0,
            'conviction_level': 'ERROR',
            'recommended_action': 'SKIP'
        }
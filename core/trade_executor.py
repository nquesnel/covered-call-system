"""
Trade Executor - Automated trade execution and management
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging


class TradeExecutor:
    """Execute and manage covered call trades with broker integration"""
    
    def __init__(self, broker_api=None):
        self.broker_api = broker_api  # TD Ameritrade, IBKR, etc.
        self.logger = logging.getLogger(__name__)
        
        # Execution rules
        self.MIN_CREDIT = 0.20       # Minimum premium to accept
        self.MAX_CONTRACTS = 10      # Max contracts per trade
        self.LIMIT_OFFSET = 0.05     # Offset from mid for limit orders
    
    def execute_covered_call(self, opportunity: Dict, contracts: int) -> Dict:
        """Execute a covered call trade"""
        try:
            # Validate trade
            validation = self._validate_trade(opportunity, contracts)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': validation['reason'],
                    'trade_id': None
                }
            
            # Build order
            order = self._build_covered_call_order(opportunity, contracts)
            
            # Execute with broker
            if self.broker_api:
                result = self.broker_api.place_order(order)
                
                if result['status'] == 'FILLED':
                    return {
                        'success': True,
                        'trade_id': result['order_id'],
                        'fill_price': result['fill_price'],
                        'contracts': contracts,
                        'premium_collected': result['fill_price'] * contracts * 100
                    }
                else:
                    return {
                        'success': False,
                        'error': f"Order {result['status']}: {result.get('message', '')}",
                        'trade_id': result.get('order_id')
                    }
            else:
                # Simulate execution for testing
                return self._simulate_execution(opportunity, contracts)
                
        except Exception as e:
            self.logger.error(f"Trade execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'trade_id': None
            }
    
    def _validate_trade(self, opportunity: Dict, contracts: int) -> Dict:
        """Validate trade before execution"""
        # Check contracts
        if contracts <= 0 or contracts > self.MAX_CONTRACTS:
            return {
                'valid': False,
                'reason': f'Invalid contract count: {contracts}'
            }
        
        # Check premium
        if opportunity['premium'] < self.MIN_CREDIT:
            return {
                'valid': False,
                'reason': f'Premium ${opportunity["premium"]:.2f} below minimum ${self.MIN_CREDIT}'
            }
        
        # Check liquidity
        bid_ask_spread = opportunity['ask'] - opportunity['bid']
        if bid_ask_spread > opportunity['ask'] * 0.15:  # 15% max spread
            return {
                'valid': False,
                'reason': f'Bid-ask spread too wide: ${bid_ask_spread:.2f}'
            }
        
        return {'valid': True, 'reason': None}
    
    def _build_covered_call_order(self, opportunity: Dict, contracts: int) -> Dict:
        """Build order object for broker API"""
        # Calculate limit price (slightly below mid)
        mid_price = (opportunity['bid'] + opportunity['ask']) / 2
        limit_price = round(mid_price - self.LIMIT_OFFSET, 2)
        
        return {
            'symbol': opportunity['symbol'],
            'order_type': 'SELL_TO_OPEN',
            'option_type': 'CALL',
            'strike': opportunity['strike'],
            'expiration': opportunity['expiration'],
            'contracts': contracts,
            'price_type': 'LIMIT',
            'limit_price': limit_price,
            'duration': 'DAY',
            'strategy': 'COVERED_CALL'
        }
    
    def _simulate_execution(self, opportunity: Dict, contracts: int) -> Dict:
        """Simulate trade execution for testing"""
        mid_price = (opportunity['bid'] + opportunity['ask']) / 2
        fill_price = round(mid_price - 0.02, 2)  # Simulate realistic fill
        
        return {
            'success': True,
            'trade_id': f"SIM_{opportunity['symbol']}_{datetime.now().timestamp()}",
            'fill_price': fill_price,
            'contracts': contracts,
            'premium_collected': fill_price * contracts * 100
        }
    
    def close_position(self, position: Dict, market_price: Optional[float] = None) -> Dict:
        """Close an existing covered call position"""
        try:
            # Get current market price if not provided
            if not market_price:
                if self.broker_api:
                    quote = self.broker_api.get_option_quote(
                        position['symbol'],
                        position['strike'],
                        position['expiration'],
                        'CALL'
                    )
                    market_price = (quote['bid'] + quote['ask']) / 2
                else:
                    market_price = position['premium'] * 0.3  # Simulate
            
            # Build closing order
            order = {
                'symbol': position['symbol'],
                'order_type': 'BUY_TO_CLOSE',
                'option_type': 'CALL',
                'strike': position['strike'],
                'expiration': position['expiration'],
                'contracts': position['contracts'],
                'price_type': 'LIMIT',
                'limit_price': round(market_price + self.LIMIT_OFFSET, 2),
                'duration': 'DAY'
            }
            
            # Execute close
            if self.broker_api:
                result = self.broker_api.place_order(order)
                
                if result['status'] == 'FILLED':
                    # Calculate P&L
                    cost_to_close = result['fill_price'] * position['contracts'] * 100
                    premium_collected = position['premium'] * position['contracts'] * 100
                    profit_loss = premium_collected - cost_to_close
                    
                    return {
                        'success': True,
                        'order_id': result['order_id'],
                        'fill_price': result['fill_price'],
                        'profit_loss': profit_loss,
                        'return_pct': (profit_loss / premium_collected) * 100
                    }
            else:
                # Simulate closing
                cost_to_close = market_price * position['contracts'] * 100
                premium_collected = position['premium'] * position['contracts'] * 100
                profit_loss = premium_collected - cost_to_close
                
                return {
                    'success': True,
                    'order_id': f"CLOSE_SIM_{datetime.now().timestamp()}",
                    'fill_price': market_price,
                    'profit_loss': profit_loss,
                    'return_pct': (profit_loss / premium_collected) * 100
                }
                
        except Exception as e:
            self.logger.error(f"Position close failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'order_id': None
            }
    
    def roll_position(self, position: Dict, new_strike: float, 
                     new_expiration: str) -> Dict:
        """Roll a position to new strike/expiration"""
        try:
            # Close current position
            close_result = self.close_position(position)
            
            if not close_result['success']:
                return {
                    'success': False,
                    'error': f"Failed to close original position: {close_result['error']}"
                }
            
            # Open new position
            new_opportunity = {
                'symbol': position['symbol'],
                'strike': new_strike,
                'expiration': new_expiration,
                'premium': 0,  # Will be determined by market
                'bid': 0,
                'ask': 0
            }
            
            # Get current market quotes
            if self.broker_api:
                quote = self.broker_api.get_option_quote(
                    position['symbol'],
                    new_strike,
                    new_expiration,
                    'CALL'
                )
                new_opportunity.update({
                    'premium': (quote['bid'] + quote['ask']) / 2,
                    'bid': quote['bid'],
                    'ask': quote['ask']
                })
            
            # Execute new position
            roll_result = self.execute_covered_call(
                new_opportunity, 
                position['contracts']
            )
            
            if roll_result['success']:
                net_credit = (
                    roll_result['premium_collected'] - 
                    close_result.get('cost_to_close', 0)
                )
                
                return {
                    'success': True,
                    'close_order_id': close_result['order_id'],
                    'open_order_id': roll_result['trade_id'],
                    'net_credit': net_credit,
                    'new_strike': new_strike,
                    'new_expiration': new_expiration
                }
            else:
                return {
                    'success': False,
                    'error': f"Failed to open new position: {roll_result['error']}"
                }
                
        except Exception as e:
            self.logger.error(f"Position roll failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_21_50_7_rule(self, active_positions: List[Dict], 
                           market_data: Dict) -> List[Dict]:
        """Automatically execute 21-50-7 rule actions"""
        actions_taken = []
        
        for position in active_positions:
            symbol = position['symbol']
            
            # Calculate current metrics
            current_price = market_data.get(symbol, {}).get('option_price', 0)
            if not current_price:
                continue
            
            # Calculate profit percentage
            entry_price = position['premium']
            profit_pct = ((entry_price - current_price) / entry_price) * 100
            dte = position.get('days_to_exp', 0)
            
            # 50% profit rule - ALWAYS close
            if profit_pct >= 50:
                result = self.close_position(position, current_price)
                actions_taken.append({
                    'symbol': symbol,
                    'action': 'CLOSED_50_PERCENT',
                    'reason': f'{profit_pct:.0f}% profit achieved',
                    'success': result['success'],
                    'profit_loss': result.get('profit_loss', 0)
                })
            
            # 21 DTE rule with profit
            elif dte <= 21 and profit_pct > 25:
                result = self.close_position(position, current_price)
                actions_taken.append({
                    'symbol': symbol,
                    'action': 'CLOSED_21_DTE',
                    'reason': f'{dte} DTE with {profit_pct:.0f}% profit',
                    'success': result['success'],
                    'profit_loss': result.get('profit_loss', 0)
                })
            
            # 7 DTE rule - gamma risk
            elif dte <= 7:
                result = self.close_position(position, current_price)
                actions_taken.append({
                    'symbol': symbol,
                    'action': 'CLOSED_7_DTE',
                    'reason': f'High gamma risk at {dte} DTE',
                    'success': result['success'],
                    'profit_loss': result.get('profit_loss', 0)
                })
        
        return actions_taken
    
    def get_execution_summary(self, trades: List[Dict]) -> Dict:
        """Generate execution summary statistics"""
        total_trades = len(trades)
        successful_trades = sum(1 for t in trades if t.get('success', False))
        failed_trades = total_trades - successful_trades
        
        total_premium = sum(
            t.get('premium_collected', 0) 
            for t in trades 
            if t.get('success', False)
        )
        
        total_contracts = sum(
            t.get('contracts', 0) 
            for t in trades 
            if t.get('success', False)
        )
        
        return {
            'total_trades_attempted': total_trades,
            'successful_trades': successful_trades,
            'failed_trades': failed_trades,
            'success_rate': (successful_trades / max(total_trades, 1)) * 100,
            'total_premium_collected': total_premium,
            'total_contracts': total_contracts,
            'avg_premium_per_contract': total_premium / max(total_contracts, 1)
        }
"""
Screenshot Parser - Extract positions from uploaded screenshots
"""
import streamlit as st
import pandas as pd
import re
from typing import List, Dict, Optional
import base64
from io import BytesIO


class ScreenshotParser:
    """Parse trading positions from screenshots"""
    
    def __init__(self):
        # Common broker patterns
        self.broker_patterns = {
            'td_ameritrade': {
                'symbol': r'[A-Z]{1,5}',
                'shares': r'[\d,]+(?:\.\d+)?',
                'price': r'\$?[\d,]+\.\d{2}'
            },
            'robinhood': {
                'symbol': r'[A-Z]{1,5}',
                'shares': r'[\d,]+(?:\.\d+)?',
                'price': r'\$?[\d,]+\.\d{2}'
            },
            'fidelity': {
                'symbol': r'[A-Z]{1,5}',
                'shares': r'[\d,]+(?:\.\d+)?',
                'price': r'\$?[\d,]+\.\d{2}'
            }
        }
    
    def parse_screenshot_with_ai(self, image_bytes: bytes, image_format: str = "png") -> List[Dict]:
        """
        Use Claude to parse the screenshot and extract positions
        This is the most reliable method for complex screenshots
        """
        try:
            # Convert image to base64 for Claude
            encoded_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # Create a prompt for Claude to extract positions
            prompt = """
            Please analyze this brokerage screenshot and extract all stock positions.
            For each position, identify:
            1. Symbol (ticker)
            2. Number of shares
            3. Average cost/price per share (if visible)
            
            Return the data in this exact format (one per line):
            SYMBOL,SHARES,COST
            
            For example:
            AAPL,100,150.25
            TSLA,50,200.00
            
            If cost basis is not visible, use 0.
            Only include stocks, not options or other securities.
            """
            
            # This would call Claude's vision API
            # For now, we'll show the interface and manual entry
            st.info("🤖 AI screenshot parsing requires Claude Vision API integration")
            
            # Fallback to manual entry with helper
            return self._manual_entry_helper()
            
        except Exception as e:
            st.error(f"Error parsing screenshot: {str(e)}")
            return []
    
    def parse_screenshot_with_ocr(self, image_bytes: bytes) -> List[Dict]:
        """
        Parse screenshot using OCR (requires pytesseract)
        This is a fallback method
        """
        try:
            import pytesseract
            from PIL import Image
            
            # Convert bytes to PIL Image
            image = Image.open(BytesIO(image_bytes))
            
            # Extract text using OCR
            text = pytesseract.image_to_string(image)
            
            # Parse the text for positions
            return self._parse_text_for_positions(text)
            
        except ImportError:
            st.warning("OCR not available. Install with: pip install pytesseract pillow")
            return self._manual_entry_helper()
        except Exception as e:
            st.error(f"OCR error: {str(e)}")
            return []
    
    def _parse_text_for_positions(self, text: str) -> List[Dict]:
        """Parse extracted text for stock positions"""
        positions = []
        lines = text.split('\n')
        
        # Common patterns to look for
        symbol_pattern = re.compile(r'\b([A-Z]{1,5})\b')
        shares_pattern = re.compile(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:shares?|shs?)?', re.I)
        price_pattern = re.compile(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)(?:\s*(?:avg|cost|price))?', re.I)
        
        # Try to extract positions
        current_position = {}
        
        for line in lines:
            # Look for symbol
            symbol_match = symbol_pattern.search(line)
            if symbol_match and len(symbol_match.group(1)) >= 1:
                if current_position:
                    positions.append(current_position)
                current_position = {'symbol': symbol_match.group(1)}
            
            # Look for shares
            if current_position:
                shares_match = shares_pattern.search(line)
                if shares_match:
                    shares_str = shares_match.group(1).replace(',', '')
                    try:
                        shares = float(shares_str)
                        if shares >= 1:  # Reasonable share count
                            current_position['shares'] = int(shares)
                    except:
                        pass
                
                # Look for price
                price_match = price_pattern.search(line)
                if price_match:
                    price_str = price_match.group(1).replace(',', '')
                    try:
                        price = float(price_str)
                        if 1 <= price <= 10000:  # Reasonable price range
                            current_position['cost_basis'] = price
                    except:
                        pass
        
        # Add last position
        if current_position and 'symbol' in current_position and 'shares' in current_position:
            positions.append(current_position)
        
        # Filter valid positions
        valid_positions = []
        for pos in positions:
            if 'symbol' in pos and 'shares' in pos:
                if 'cost_basis' not in pos:
                    pos['cost_basis'] = 0  # Will need manual entry
                valid_positions.append(pos)
        
        return valid_positions
    
    def _manual_entry_helper(self) -> List[Dict]:
        """Helper for manual position entry from screenshot"""
        st.subheader("📝 Manual Position Entry")
        st.write("Please enter the positions you see in your screenshot:")
        
        positions = []
        
        # Dynamic position entry
        if 'num_positions' not in st.session_state:
            st.session_state.num_positions = 1
        
        for i in range(st.session_state.num_positions):
            st.write(f"**Position {i+1}:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                symbol = st.text_input(f"Symbol", key=f"manual_symbol_{i}").upper()
            with col2:
                shares = st.number_input(f"Shares", min_value=0, step=1, key=f"manual_shares_{i}")
            with col3:
                cost = st.number_input(f"Cost Basis", min_value=0.0, step=0.01, key=f"manual_cost_{i}")
            
            if symbol and shares > 0:
                positions.append({
                    'symbol': symbol,
                    'shares': int(shares),
                    'cost_basis': cost if cost > 0 else None
                })
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Add Another Position"):
                st.session_state.num_positions += 1
                st.rerun()
        
        with col2:
            if st.session_state.num_positions > 1:
                if st.button("➖ Remove Last"):
                    st.session_state.num_positions -= 1
                    st.rerun()
        
        return positions
    
    def validate_positions(self, positions: List[Dict]) -> List[Dict]:
        """Validate and clean extracted positions"""
        valid_positions = []
        
        for pos in positions:
            # Validate symbol
            symbol = pos.get('symbol', '').upper()
            if not re.match(r'^[A-Z]{1,5}$', symbol):
                continue
            
            # Validate shares
            shares = pos.get('shares', 0)
            if not isinstance(shares, (int, float)) or shares < 1:
                continue
            
            # Validate cost basis (optional)
            cost_basis = pos.get('cost_basis', 0)
            if cost_basis < 0:
                cost_basis = 0
            
            valid_positions.append({
                'symbol': symbol,
                'shares': int(shares),
                'cost_basis': float(cost_basis) if cost_basis > 0 else None
            })
        
        return valid_positions
    
    def format_for_import(self, positions: List[Dict]) -> pd.DataFrame:
        """Format positions for display and confirmation"""
        df_data = []
        
        for pos in positions:
            df_data.append({
                'Symbol': pos['symbol'],
                'Shares': pos['shares'],
                'Cost Basis': f"${pos['cost_basis']:.2f}" if pos.get('cost_basis') else 'Not provided',
                'Contracts Available': pos['shares'] // 100
            })
        
        return pd.DataFrame(df_data)
"""
Screenshot Parser with Claude Vision Integration
"""
import streamlit as st
import pandas as pd
import re
from typing import List, Dict, Optional
import base64
from io import BytesIO
import anthropic
import os


class ScreenshotParserClaude:
    """Parse trading positions from screenshots using Claude Vision"""
    
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None
    
    def parse_screenshot_with_ai(self, image_bytes: bytes, image_format: str = "png") -> List[Dict]:
        """
        Use Claude to parse the screenshot and extract positions
        """
        if not self.client:
            st.error("❌ Claude API key not found. Add ANTHROPIC_API_KEY to Streamlit secrets.")
            return self._manual_entry_helper()
        
        try:
            # Convert image to base64 for Claude
            encoded_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # Create the message with image
            message = self.client.messages.create(
                model="claude-3-sonnet-20241022",
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": f"image/{image_format}",
                                    "data": encoded_image
                                }
                            },
                            {
                                "type": "text",
                                "text": """Please analyze this brokerage screenshot and extract all stock positions.
                                
For each position, identify:
1. Symbol/Ticker (e.g., AAPL, TSLA)
2. Number of shares (quantity owned)
3. Average cost per share or total cost basis (if visible)

Return ONLY a CSV format with these columns: Symbol,Shares,CostBasis

Example output:
AAPL,100,150.25
TSLA,50,200.00
SPY,200,450.50

Rules:
- Only include stocks/ETFs, not options or other securities
- If cost basis is not visible, use 0
- Do not include dollar signs or commas in numbers
- One position per line
- No headers, just the data"""
                            }
                        ]
                    }
                ]
            )
            
            # Parse Claude's response
            response_text = message.content[0].text
            return self._parse_claude_response(response_text)
            
        except anthropic.APIError as e:
            st.error(f"Claude API error: {str(e)}")
            return self._manual_entry_helper()
        except Exception as e:
            st.error(f"Error parsing screenshot: {str(e)}")
            return self._manual_entry_helper()
    
    def _parse_claude_response(self, response: str) -> List[Dict]:
        """Parse Claude's CSV response into position dictionaries"""
        positions = []
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            parts = line.split(',')
            if len(parts) >= 2:
                try:
                    symbol = parts[0].strip().upper()
                    shares = float(parts[1].strip())
                    cost_basis = float(parts[2].strip()) if len(parts) > 2 and parts[2].strip() != '0' else None
                    
                    # Validate
                    if re.match(r'^[A-Z]{1,5}$', symbol) and shares > 0:
                        positions.append({
                            'symbol': symbol,
                            'shares': int(shares),
                            'cost_basis': cost_basis
                        })
                except ValueError:
                    continue
        
        return positions
    
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
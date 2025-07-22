"""
Covered Call Income System - Main Streamlit Dashboard
Goal: Generate $2-5K monthly income to pay down $60K margin debt
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import core modules
from core.position_manager import PositionManager
from core.trade_tracker import TradeTracker
try:
    from core.growth_analyzer_enhanced import GrowthAnalyzerEnhanced as GrowthAnalyzer
except ImportError:
    from core.growth_analyzer import GrowthAnalyzer
from core.options_scanner import OptionsScanner
from core.whale_tracker import WhaleTracker
try:
    from core.whale_flow_tracker import WhaleFlowTracker
except ImportError:
    WhaleFlowTracker = None
from core.risk_manager import RiskManager
try:
    from utils.data_fetcher_real import RealDataFetcher as DataFetcher
except ImportError:
    print("Note: yfinance not installed. Using mock data. Install with: pip install yfinance")
    from utils.data_fetcher import DataFetcher

# Page configuration
st.set_page_config(
    page_title="Covered Call Income System",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better mobile experience
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .success-metric {
        background-color: #d4edda;
    }
    .warning-metric {
        background-color: #fff3cd;
    }
    .danger-metric {
        background-color: #f8d7da;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'position_manager' not in st.session_state:
    st.session_state.position_manager = PositionManager()
    st.session_state.trade_tracker = TradeTracker()
    st.session_state.growth_analyzer = GrowthAnalyzer()
    st.session_state.whale_tracker = WhaleTracker()
    st.session_state.whale_flow_tracker = WhaleFlowTracker() if WhaleFlowTracker else None
    st.session_state.risk_manager = RiskManager()
    st.session_state.data_fetcher = DataFetcher()

# Quick access to managers
pos_manager = st.session_state.position_manager
trade_tracker = st.session_state.trade_tracker
growth_analyzer = st.session_state.growth_analyzer
whale_tracker = st.session_state.whale_tracker
whale_flow_tracker = st.session_state.whale_flow_tracker
risk_manager = st.session_state.risk_manager
data_fetcher = st.session_state.data_fetcher

# Initialize scanner with dependencies
scanner = OptionsScanner(pos_manager, growth_analyzer)

# Title and goal reminder
st.title("📈 Covered Call Income System")
st.markdown("**Mission**: Generate $2-5K monthly income to eliminate $60K margin debt")

# Sidebar for portfolio management
with st.sidebar:
    st.header("💼 Portfolio Management")
    
    # Screenshot upload option
    with st.expander("📸 Upload Screenshot", expanded=False):
        st.write("Upload a screenshot of your positions")
        uploaded_file = st.file_uploader(
            "Choose an image", 
            type=['png', 'jpg', 'jpeg'],
            help="Upload a screenshot from your broker showing positions"
        )
        
        if uploaded_file is not None:
            # Import screenshot parser with Claude
            try:
                from utils.screenshot_parser_claude import ScreenshotParserClaude
                parser = ScreenshotParserClaude()
            except ImportError:
                from utils.screenshot_parser import ScreenshotParser
                parser = ScreenshotParser()
            
            # Read image bytes
            image_bytes = uploaded_file.read()
            
            # Try to parse positions
            st.write("🔍 Analyzing screenshot...")
            
            # Try AI parsing first, fall back to OCR/manual
            extracted_positions = parser.parse_screenshot_with_ai(
                image_bytes, 
                uploaded_file.type.split('/')[-1]
            )
            
            if extracted_positions:
                st.success(f"Found {len(extracted_positions)} positions!")
                
                # Show extracted positions
                df = parser.format_for_import(extracted_positions)
                st.dataframe(df, use_container_width=True)
                
                # Account type selection
                account_type = st.selectbox(
                    "Select account type for imported positions:",
                    ["taxable", "roth", "traditional"],
                    key="import_account_type"
                )
                
                # Confirm and import
                if st.button("✅ Import These Positions", type="primary"):
                    imported_count = 0
                    for pos in extracted_positions:
                        try:
                            # Use current price if no cost basis
                            if not pos.get('cost_basis'):
                                stock_data = data_fetcher.get_stock_data(pos['symbol'])
                                cost_basis = stock_data.get('price', 100.0)
                            else:
                                cost_basis = pos['cost_basis']
                            
                            pos_manager.add_position(
                                pos['symbol'],
                                pos['shares'],
                                cost_basis,
                                account_type,  # Use selected account type
                                'Imported from screenshot'
                            )
                            imported_count += 1
                        except Exception as e:
                            st.error(f"Error importing {pos['symbol']}: {str(e)}")
                    
                    if imported_count > 0:
                        st.success(f"✅ Imported {imported_count} positions!")
                        st.rerun()
            else:
                st.info("No positions found. Please enter manually below.")
    
    # Add new position
    with st.expander("➕ Add Position", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            new_symbol = st.text_input("Symbol", key="add_symbol").upper()
            new_shares = st.number_input("Shares", min_value=1, step=100, key="add_shares")
        with col2:
            new_cost = st.number_input("Cost Basis", min_value=0.01, step=0.01, key="add_cost")
            account_type = st.selectbox("Account", ["taxable", "roth", "traditional"], key="add_account")
        
        notes = st.text_area("Notes (optional)", key="add_notes")
        
        if st.button("Add Position", type="primary"):
            if new_symbol and new_shares and new_cost:
                result = pos_manager.add_position(new_symbol, new_shares, new_cost, account_type, notes)
                st.success(result)
                st.rerun()
            else:
                st.error("Please fill all required fields")
    
    # Current positions summary
    st.subheader("Current Positions")
    all_positions = pos_manager.get_all_positions()
    eligible_positions = pos_manager.get_eligible_positions()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Positions", len(all_positions))
    with col2:
        st.metric("CC Eligible", len(eligible_positions))
    
    # Quick position list
    if all_positions:
        st.markdown("**Your Holdings:**")
        for symbol, pos in all_positions.items():
            contracts = pos['shares'] // 100
            st.text(f"{symbol}: {pos['shares']} shares ({contracts} contracts)")
    
    # Manual covered call entry
    with st.expander("📝 Record Covered Call", expanded=False):
        st.write("Manually record a covered call you've written")
        
        # Only show positions with 100+ shares
        eligible_symbols = [s for s, p in all_positions.items() if p['shares'] >= 100]
        
        if eligible_symbols:
            col1, col2 = st.columns(2)
            with col1:
                cc_symbol = st.selectbox("Symbol", eligible_symbols, key="cc_symbol")
                cc_strike = st.number_input("Strike Price", min_value=0.01, step=0.01, key="cc_strike")
                cc_contracts = st.number_input(
                    "Contracts", 
                    min_value=1, 
                    max_value=all_positions[cc_symbol]['shares'] // 100 if cc_symbol in all_positions else 1,
                    key="cc_contracts"
                )
            with col2:
                cc_premium = st.number_input("Premium per Contract", min_value=0.01, step=0.01, key="cc_premium")
                cc_expiration = st.date_input("Expiration Date", key="cc_expiration")
                cc_confidence = st.slider("Confidence %", 0, 100, 75, key="cc_confidence")
            
            cc_notes = st.text_area("Notes (optional)", key="cc_notes")
            
            if st.button("Record Covered Call", type="primary"):
                if cc_symbol and cc_strike and cc_premium and cc_expiration:
                    # Calculate days to expiration
                    dte = (cc_expiration - datetime.now().date()).days
                    
                    # Create opportunity object
                    opportunity = {
                        'symbol': cc_symbol,
                        'current_price': 0,  # Will be updated from market data
                        'strike': cc_strike,
                        'expiration': cc_expiration.strftime('%Y-%m-%d'),
                        'days_to_exp': dte,
                        'premium': cc_premium,
                        'confidence_score': cc_confidence,
                        'monthly_yield': (cc_premium / cc_strike * 30 / dte * 100) if dte > 0 else 0,
                        'win_probability': 0,  # Will calculate later
                        'max_contracts': all_positions[cc_symbol]['shares'] // 100,
                        'manual_entry': True
                    }
                    
                    # Log the trade
                    trade_id = trade_tracker.log_opportunity(opportunity)
                    trade_tracker.update_decision(trade_id, 'TAKE', cc_contracts, f"Manual entry: {cc_notes}")
                    
                    st.success(f"✅ Recorded {cc_contracts} contracts of {cc_symbol} ${cc_strike} calls")
                    st.rerun()
                else:
                    st.error("Please fill all required fields")
        else:
            st.info("No eligible positions (need 100+ shares)")

# Get current market data (mock for now)
@st.cache_data(ttl=30)
def get_market_data():
    """Fetch current market data for all positions"""
    # This would connect to real APIs
    # For now, return mock data
    market_data = {}
    for symbol in all_positions.keys():
        market_data[symbol] = data_fetcher.get_stock_data(symbol)
    return market_data

@st.cache_data(ttl=30)
def get_options_data():
    """Fetch options chains for all positions"""
    options_data = {}
    for symbol in eligible_positions.keys():
        options_data[symbol] = data_fetcher.get_options_chain(symbol)
    return options_data

# Main metrics row
col1, col2, col3, col4, col5 = st.columns(5)

# Calculate current metrics
stats = trade_tracker.get_performance_stats(30)
current_month_income = stats['total_profit']
income_goal = 3500  # Mid-point of $2-5K target
margin_debt = 60000
debt_paid = abs(min(0, current_month_income))  # Only count profits

with col1:
    progress = (current_month_income / income_goal) * 100
    st.metric(
        "Monthly Income Goal", 
        f"${income_goal:,.0f}",
        f"${current_month_income:,.0f} ({progress:.0f}%)"
    )

with col2:
    st.metric(
        "Margin Debt", 
        f"${margin_debt:,.0f}",
        f"-${debt_paid:,.0f} paid"
    )

with col3:
    st.metric(
        "Win Rate",
        f"{stats['win_rate']:.1%}",
        f"{stats['wins']} wins"
    )

with col4:
    st.metric(
        "Active Trades",
        len(trade_tracker.get_active_trades()),
        f"{stats['trades_taken']} taken"
    )

with col5:
    capacity = pos_manager.get_covered_call_capacity()
    total_available = sum(capacity.values())
    active_trades = trade_tracker.get_active_trades()
    total_written = sum(trade.get('contracts', 0) for trade in active_trades)
    st.metric(
        "Contracts",
        f"{total_available} avail / {total_written} written",
        f"{len(capacity)} positions"
    )

# Main content tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Opportunities", 
    "📊 Positions", 
    "📜 Trade History", 
    "🐋 Whale Flows",
    "⚠️ Risk Monitor"
])

# Tab 1: Opportunities
with tab1:
    st.subheader("Today's Best Opportunities")
    
    # Info box
    st.info("📌 **How it works**: The scanner ONLY looks at positions in 'Your Holdings' with 100+ shares. Add positions in the sidebar to see opportunities!")
    
    # Filters with reset button
    filter_col1, filter_col2 = st.columns([4, 1])
    
    with filter_col1:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            min_confidence = st.slider("Min Confidence", 0, 100, 30, key="confidence_slider")
        with col2:
            min_yield = st.slider("Min Monthly Yield %", 0.5, 10.0, 1.0, key="yield_slider")
        with col3:
            exclude_earnings = st.checkbox("Exclude Earnings", False, key="earnings_checkbox")
        with col4:
            max_growth_score = st.slider("Max Growth Score", 25, 100, 75, key="growth_slider")
    
    with filter_col2:
        st.write("")  # Spacer
        if st.button("🔄 Reset Filters", type="secondary"):
            st.session_state.confidence_slider = 30
            st.session_state.yield_slider = 1.0
            st.session_state.earnings_checkbox = False
            st.session_state.growth_slider = 75
            st.rerun()
    
    # Get opportunities
    if eligible_positions:
        with st.spinner("Scanning for opportunities..."):
            market_data = get_market_data()
            options_data = get_options_data()
            
            opportunities = scanner.find_opportunities(market_data, options_data)
            
            # Apply filters
            filtered_opps = scanner.filter_by_criteria(
                opportunities,
                min_yield=min_yield,
                min_confidence=min_confidence,
                exclude_earnings=exclude_earnings
            )
            
            # Filter by growth score
            filtered_opps = [o for o in filtered_opps if o['growth_score'] <= max_growth_score]
        
        if filtered_opps:
            st.success(f"Found {len(filtered_opps)} opportunities matching your criteria")
            
            # Opportunity cards
            for i, opp in enumerate(filtered_opps[:10]):  # Show top 10
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])
                    
                    with col1:
                        st.markdown(f"### {opp['symbol']} - {opp['strategy']}")
                        st.write(f"**Strike**: ${opp['strike']:.2f} | **Premium**: ${opp['premium']:.2f}")
                        st.write(f"**Expiration**: {opp['expiration']} ({opp['days_to_exp']}d)")
                        
                        # Show earnings date if available
                        if opp['symbol'] in market_data and 'next_earnings_date' in market_data[opp['symbol']]:
                            earnings_date = market_data[opp['symbol']]['next_earnings_date']
                            if opp.get('earnings_before_exp'):
                                st.write(f"⚠️ **Earnings**: {earnings_date} (BEFORE exp)")
                            else:
                                st.write(f"✅ **Earnings**: {earnings_date} (after exp)")
                    
                    with col2:
                        yield_color = "🟢" if opp['monthly_yield'] > 3 else "🟡"
                        st.metric("Monthly Yield", f"{yield_color} {opp['monthly_yield']:.1f}%")
                    
                    with col3:
                        confidence_color = "🟢" if opp['confidence_score'] > 80 else "🟡"
                        st.metric("Confidence", f"{confidence_color} {opp['confidence_score']}/100")
                    
                    with col4:
                        st.metric("Win Prob", f"{opp['win_probability']:.0f}%")
                        st.write(f"IV Rank: {opp['iv_rank']:.0f}")
                    
                    with col5:
                        # Take/Pass decision buttons
                        col_take, col_pass = st.columns(2)
                        
                        with col_take:
                            if st.button("✅ TAKE", key=f"take_{i}", type="primary"):
                                # Create a form for taking the trade
                                with st.form(key=f"take_form_{i}"):
                                    contracts = st.number_input(
                                        "Contracts:", 
                                        min_value=1, 
                                        max_value=opp['max_contracts'],
                                        value=min(2, opp['max_contracts']),
                                        key=f"contracts_{i}"
                                    )
                                    reason = st.text_input("Reason (optional):", key=f"reason_take_{i}")
                                    
                                    if st.form_submit_button("Confirm"):
                                        # Log the decision
                                        trade_id = trade_tracker.log_opportunity(opp)
                                        trade_tracker.update_decision(trade_id, 'TAKE', contracts, reason)
                                        st.success(f"✅ Logged TAKE decision for {opp['symbol']}")
                                        st.balloons()
                                        st.rerun()
                        
                        with col_pass:
                            if st.button("❌ PASS", key=f"pass_{i}"):
                                with st.form(key=f"pass_form_{i}"):
                                    reason = st.text_input("Why pass?", key=f"reason_pass_{i}")
                                    if st.form_submit_button("Confirm Pass"):
                                        trade_id = trade_tracker.log_opportunity(opp)
                                        trade_tracker.update_decision(trade_id, 'PASS', 0, reason)
                                        st.info(f"Logged PASS decision for {opp['symbol']}")
                                        st.rerun()
                    
                    # Generate and display commentary
                    commentary = scanner.generate_opportunity_commentary(opp)
                    
                    # Show recommendation with color coding
                    if commentary['recommendation'] == "STRONG BUY":
                        st.success(f"🎯 **{commentary['recommendation']}** - {commentary['key_insight']}")
                    elif commentary['recommendation'] == "BUY":
                        st.info(f"✅ **{commentary['recommendation']}** - {commentary['key_insight']}")
                    elif commentary['recommendation'] == "PASS" or commentary['recommendation'] == "STRONG PASS":
                        st.warning(f"⚠️ **{commentary['recommendation']}** - {commentary['key_insight']}")
                    else:
                        st.info(f"🤔 **{commentary['recommendation']}** - {commentary['key_insight']}")
                    
                    st.write(f"**Action:** {commentary['action']}")
                    
                    # Expandable details
                    with st.expander("View Full Analysis"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Pros:**")
                            if commentary['reasons_pro']:
                                for reason in commentary['reasons_pro']:
                                    st.write(f"✅ {reason}")
                            else:
                                st.write("No strong pros identified")
                            
                            st.write("\n**Greeks & Technicals:**")
                            st.write(f"Delta: {opp.get('delta', 0):.2f}")
                            st.write(f"IV: {opp.get('implied_volatility', 0):.1%}")
                            st.write(f"Volume: {opp.get('volume', 0):,}")
                            st.write(f"Open Interest: {opp.get('open_interest', 0):,}")
                        
                        with col2:
                            st.write("**Cons:**")
                            if commentary['reasons_con']:
                                for reason in commentary['reasons_con']:
                                    st.write(f"❌ {reason}")
                            else:
                                st.write("No major cons identified")
                            
                            st.write("\n**Returns:**")
                            st.write(f"Static: {opp['static_return_monthly']:.2%}/mo")
                            st.write(f"If Called: {opp['if_called_return_monthly']:.2%}/mo")
                            st.write(f"Growth Score: {opp['growth_score']}")
                            st.write(f"Cost Basis: ${opp.get('cost_basis', 0):.2f}")
                        
                        # Add recommended close prices
                        close_prices = scanner.calculate_recommended_close_price(opp)
                        st.write("\n**📊 Recommended Exit Strategy:**")
                        st.info(close_prices['note'])
                        
                        col_close1, col_close2 = st.columns(2)
                        with col_close1:
                            st.write(f"**Primary Target:** ${close_prices['primary_target']:.2f}")
                            st.write(f"Profit: ${close_prices['profit_at_target']:.2f} ({close_prices['profit_pct_at_target']:.1f}%)")
                        
                        with col_close2:
                            st.write(f"**Conservative:** ${close_prices['conservative_target']:.2f} (25% profit)")
                            st.write(f"**Aggressive:** ${close_prices['aggressive_target']:.2f} (75% profit)")
                    
                    st.divider()
        else:
            st.warning("No opportunities found matching your criteria.")
            
            # Helpful suggestions
            with st.expander("💡 Why no opportunities? Click for help"):
                st.markdown("""
                **Common reasons and solutions:**
                
                1. **Filters too restrictive** → Click 'Reset Filters' button above
                2. **Low IV environment** → Lower the 'Min Confidence' filter
                3. **Growth scores too high** → Increase 'Max Growth Score' to 75
                4. **Not enough yield** → Lower 'Min Monthly Yield' to 1%
                
                **Your current positions:**
                """)
                
                for symbol, pos in eligible_positions.items():
                    contracts = pos['shares'] // 100
                    st.write(f"• **{symbol}**: {pos['shares']} shares ({contracts} contracts available)")
                
                st.markdown("""
                **Remember:** The system only scans YOUR positions, not the entire market!
                """)
    else:
        st.warning("No eligible positions found!")
        with st.expander("🚀 Getting Started"):
            st.markdown("""
            **To see covered call opportunities:**
            
            1. Add positions using the sidebar (➕ Add Position)
            2. You need at least **100 shares** to sell 1 covered call
            3. Common starter positions:
               - **SPY** (S&P 500 ETF) - Steady income
               - **QQQ** (Nasdaq ETF) - Tech exposure
               - **AAPL** - High liquidity options
               
            **Example position to add:**
            - Symbol: SPY
            - Shares: 100
            - Cost Basis: $450
            """)

# Tab 2: Positions
with tab2:
    st.subheader("Portfolio Strategic Analysis")
    
    if all_positions:
        # Get current prices
        market_data = get_market_data()
        
        # Calculate portfolio value
        portfolio_value = pos_manager.calculate_total_value(
            {s: d.get('price', 0) for s, d in market_data.items()}
        )
        
        # Portfolio summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Value", f"${portfolio_value['total_value']:,.0f}")
        with col2:
            st.metric("Total Cost", f"${portfolio_value['total_cost']:,.0f}")
        with col3:
            gain_loss = portfolio_value['total_gain_loss']
            st.metric(
                "Gain/Loss", 
                f"${gain_loss:,.0f}",
                f"{portfolio_value['total_gain_loss_pct']:.1f}%"
            )
        with col4:
            st.metric("Positions", len(all_positions))
        
        # Position details table
        position_data = []
        for symbol, pos in all_positions.items():
            if symbol in market_data:
                current_price = market_data[symbol].get('price', 0)
                
                # Get growth analysis
                growth_score = growth_analyzer.calculate_growth_score(symbol, market_data[symbol])
                
                # Calculate metrics
                current_value = current_price * pos['shares']
                total_cost = pos['cost_basis'] * pos['shares']
                gain_loss = current_value - total_cost
                gain_loss_pct = (gain_loss / total_cost * 100) if total_cost > 0 else 0
                contracts = pos['shares'] // 100
                
                position_data.append({
                    'Symbol': symbol,
                    'Shares': pos['shares'],
                    'Contracts': contracts,
                    'Cost Basis': f"${pos['cost_basis']:.2f}",
                    'Current': f"${current_price:.2f}",
                    'Value': f"${current_value:,.0f}",
                    'Gain/Loss': f"${gain_loss:,.0f}",
                    'Gain %': f"{gain_loss_pct:+.1f}%",
                    'Growth Score': growth_score['total_score'],
                    'Strategy': growth_score['strategy']['strategy'],
                    'Account': pos['account_type'].title()
                })
        
        df = pd.DataFrame(position_data)
        
        # Style the dataframe
        def highlight_scores(val):
            if isinstance(val, (int, float)):
                if val > 75:
                    return 'background-color: #ff6b6b; color: white'
                elif val > 50:
                    return 'background-color: #ffd93d'
                else:
                    return 'background-color: #95e1d3'
            return ''
        
        styled_df = df.style.applymap(
            highlight_scores, 
            subset=['Growth Score']
        )
        
        st.dataframe(styled_df, use_container_width=True)
        
        # Position management
        with st.expander("🔧 Manage Positions"):
            edit_symbol = st.selectbox("Select position to edit:", list(all_positions.keys()))
            
            if edit_symbol:
                pos = all_positions[edit_symbol]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_shares = st.number_input(
                        "Shares:", 
                        value=pos['shares'],
                        min_value=0,
                        step=100
                    )
                with col2:
                    new_cost = st.number_input(
                        "Cost Basis:", 
                        value=pos['cost_basis'],
                        min_value=0.01,
                        step=0.01
                    )
                with col3:
                    st.write("") # Spacer
                    if st.button("Update Position"):
                        pos_manager.update_position(edit_symbol, new_shares, new_cost)
                        st.success(f"Updated {edit_symbol}")
                        st.rerun()
                
                if st.button("🗑️ Delete Position", type="secondary"):
                    if st.checkbox("Confirm deletion"):
                        pos_manager.delete_position(edit_symbol)
                        st.success(f"Deleted {edit_symbol}")
                        st.rerun()
    else:
        st.info("No positions added yet. Use the sidebar to add your first position.")

# Tab 3: Trade History
with tab3:
    st.subheader("Trade Decision History & Performance")
    
    # Time period selector
    col1, col2, col3 = st.columns(3)
    with col1:
        period = st.selectbox("Time Period", ["Last 7 days", "Last 30 days", "Last 90 days", "All time"])
        days_map = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90, "All time": 9999}
        selected_days = days_map[period]
    
    # Get performance stats
    stats = trade_tracker.get_performance_stats(selected_days)
    
    # Performance metrics
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Opportunities", stats['total_opportunities'])
    
    with col2:
        take_rate = stats['take_rate'] * 100
        color = "🟢" if take_rate > 30 else "🟡"
        st.metric("Take Rate", f"{color} {take_rate:.0f}%")
    
    with col3:
        win_rate = stats['win_rate'] * 100
        color = "🟢" if win_rate > 70 else "🟡"
        st.metric("Win Rate", f"{color} {win_rate:.0f}%")
    
    with col4:
        st.metric("Total P&L", f"${stats['total_profit']:,.0f}")
    
    with col5:
        st.metric("Avg per Trade", f"${stats['avg_profit_per_trade']:,.0f}")
    
    with col6:
        st.metric("High Conf Passes", stats['high_confidence_passes'])
    
    # Trade history
    trades = trade_tracker.get_opportunities(selected_days)
    
    if trades:
        # Create DataFrame
        trade_df = pd.DataFrame(trades)
        
        # Format columns
        display_columns = [
            'date_presented', 'symbol', 'strike', 'premium', 
            'days_to_exp', 'confidence_score', 'decision', 
            'contracts', 'profit_loss', 'outcome'
        ]
        
        # Filter to display columns that exist
        display_columns = [col for col in display_columns if col in trade_df.columns]
        
        # Show the table
        st.dataframe(
            trade_df[display_columns],
            use_container_width=True
        )
        
        # Active trades management
        active_trades = trade_tracker.get_active_trades()
        if active_trades:
            st.subheader("📈 Active Trades - Monitoring & Alerts")
            
            # Check for any urgent alerts
            urgent_alerts = []
            for trade in active_trades:
                # Calculate current profit (mock - would use real market data)
                current_bid = trade['premium'] * 0.4  # Mock: assume we can buy back at 40% of premium
                profit_pct = (1 - current_bid/trade['premium']) * 100
                days_remaining = trade.get('days_to_exp', 30)
                
                # Apply 21-50-7 rule
                if profit_pct >= 50:
                    urgent_alerts.append(f"🚨 {trade['symbol']}: At {profit_pct:.0f}% profit - CLOSE NOW (50% rule)")
                elif days_remaining <= 7:
                    urgent_alerts.append(f"🚨 {trade['symbol']}: Only {days_remaining} days left - HIGH GAMMA RISK")
                elif days_remaining <= 21 and profit_pct >= 25:
                    urgent_alerts.append(f"⚠️ {trade['symbol']}: {days_remaining} DTE with {profit_pct:.0f}% profit - Consider closing")
            
            if urgent_alerts:
                alert_container = st.container()
                with alert_container:
                    st.error("🚨 **URGENT ACTION REQUIRED**")
                    for alert in urgent_alerts:
                        st.warning(alert)
                st.divider()
            
            for trade in active_trades:
                with st.container():
                    # Calculate metrics (mock data)
                    current_bid = trade['premium'] * 0.4
                    profit_pct = (1 - current_bid/trade['premium']) * 100
                    days_remaining = trade.get('days_to_exp', 30)
                    
                    # Determine status color
                    if profit_pct >= 50 or days_remaining <= 7:
                        status_color = "🔴"
                        action_text = "CLOSE NOW"
                    elif days_remaining <= 21 and profit_pct >= 25:
                        status_color = "🟡"
                        action_text = "Consider Closing"
                    else:
                        status_color = "🟢"
                        action_text = "Hold"
                    
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                    
                    with col1:
                        st.write(f"{status_color} **{trade['symbol']}** ${trade['strike']} x{trade['contracts']} contracts")
                        st.write(f"Opened: {trade.get('date_taken', 'Unknown')} | Expires: {trade['expiration']}")
                    
                    with col2:
                        st.write(f"**Premium:** ${trade['premium']:.2f}")
                        st.write(f"**Current:** ${current_bid:.2f}")
                    
                    with col3:
                        st.metric("Profit %", f"{profit_pct:.0f}%")
                        st.write(f"**Action:** {action_text}")
                    
                    with col4:
                        st.metric("DTE", days_remaining)
                        if days_remaining <= 21:
                            st.write("⚠️ 21 DTE rule")
                    
                    with col5:
                        closing_price = st.number_input(
                            "Close at:", 
                            min_value=0.0,
                            value=current_bid,
                            step=0.01,
                            key=f"close_{trade['id']}"
                        )
                        
                        if st.button("Close Trade", key=f"close_btn_{trade['id']}", type="primary" if status_color == "🔴" else "secondary"):
                            outcome = "WIN" if closing_price < trade['premium'] else "LOSS"
                            success, result = trade_tracker.close_trade(
                                trade['id'], closing_price, outcome
                            )
                            if success:
                                st.success(f"Closed with {outcome}: ${result['profit_loss']:.0f}")
                                st.rerun()
                    
                    # Show recommended actions
                    if status_color != "🟢":
                        with st.expander("📊 Detailed Recommendation"):
                            if profit_pct >= 50:
                                st.error("**50% PROFIT RULE TRIGGERED**")
                                st.write("You've achieved 50% of max profit. Statistically, it's optimal to close now and redeploy capital.")
                            elif days_remaining <= 7:
                                st.error("**7 DTE RULE TRIGGERED**")
                                st.write("Gamma risk is extremely high. The position can move against you rapidly. Close immediately.")
                            elif days_remaining <= 21 and profit_pct >= 25:
                                st.warning("**21 DTE CHECKPOINT**")
                                st.write(f"With {profit_pct:.0f}% profit and {days_remaining} days left, consider taking profits.")
                            
                            # Calculate what happens if we hold
                            remaining_profit = trade['premium'] - current_bid
                            days_to_earn = days_remaining
                            daily_theta = remaining_profit / days_to_earn if days_to_earn > 0 else 0
                            
                            st.write(f"\n**If you hold to expiration:**")
                            st.write(f"- Additional profit potential: ${remaining_profit:.2f}")
                            st.write(f"- Daily theta decay: ${daily_theta:.2f}/day")
                            st.write(f"- Risk: Assignment if stock rises above ${trade['strike']:.2f}")
                    
                    st.divider()
    else:
        st.info("No trades recorded yet. Start taking opportunities to build history.")

# Tab 4: Whale Flows
with tab4:
    st.subheader("🐋 Institutional Flow Tracker")
    st.markdown("*Follow the smart money - detect large option flows that could signal big moves*")
    
    # Create subtabs for current flows and history
    flow_tab1, flow_tab2 = st.tabs(["🔴 Live Flows", "📊 History & Performance"])
    
    with flow_tab1:
        # Get whale flows (mock data for now)
        raw_flows = data_fetcher.get_whale_flows()
        
        # Process flows through whale tracker to add analysis
        whale_flows = whale_tracker.detect_institutional_flows(raw_flows)
        
        if whale_flows and whale_flow_tracker:
            # Log all flows to history
            for flow in whale_flows:
                whale_flow_tracker.log_flow(flow)
        
        if whale_flows:
            # Summary metrics
            summary = whale_tracker.get_daily_summary(whale_flows)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Flows", summary['total_flows'])
            with col2:
                st.metric("Bullish", f"🟢 {summary['bullish_flows']}")
            with col3:
                st.metric("Bearish", f"🔴 {summary['bearish_flows']}")
            with col4:
                st.metric("Total Premium", f"${summary['total_premium']:,.0f}")
            
            # Flow cards
            st.subheader("Notable Flows")
            
            for idx, flow in enumerate(whale_flows[:10]):  # Show top 10
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
                    
                    with col1:
                        sentiment_emoji = "🟢" if "BULL" in flow['sentiment'] else "🔴"
                        st.markdown(f"### {sentiment_emoji} {flow['symbol']} - {flow['flow_type']}")
                        st.write(f"**{flow['option_type'].upper()}** ${flow['strike']} exp {flow['expiration']}")
                        st.write(f"Premium Volume: ${flow['total_premium']:,}")
                    
                    with col2:
                        st.metric("Unusual Factor", f"{flow['unusual_factor']:.0f}x")
                        st.write(f"Contracts: {flow['contracts']:,}")
                    
                    with col3:
                        confidence_color = "🟢" if flow['smart_money_confidence'] > 80 else "🟡"
                        st.metric("Confidence", f"{confidence_color} {flow['smart_money_confidence']}")
                        st.write(f"Risk: {flow['risk_level']}")
                    
                    with col4:
                        if flow['follow_trade']:
                            ft = flow['follow_trade']
                            st.success("✅ Follow Opportunity")
                            st.write(ft['recommendation'])
                            
                            if st.button(f"Follow with {ft['suggested_contracts']} contracts", 
                                       key=f"follow_{flow['symbol']}_{flow['strike']}_{idx}"):
                                if whale_flow_tracker:
                                    # Record the follow
                                    flow_id = whale_flow_tracker.log_flow(flow)
                                    cost = ft['suggested_contracts'] * flow.get('premium_per_contract', 0) * 100
                                    whale_flow_tracker.record_follow(flow_id, ft['suggested_contracts'], cost)
                                    st.success(f"✅ Following {flow['symbol']} ${flow['strike']} calls with {ft['suggested_contracts']} contracts")
                                    st.rerun()
                                else:
                                    st.info(f"Track this trade: {flow['symbol']} ${flow['strike']} calls")
                        else:
                            st.warning("Not recommended for retail")
                    
                    st.divider()
            
            # Educational section
            with st.expander("📚 Learn from Success Stories"):
                success_stories = whale_tracker.get_success_stories()
                for story in success_stories:
                    st.markdown(f"**{story['date']} - {story['symbol']}**")
                    st.write(f"Setup: {story['setup']}")
                    st.write(f"Size: {story['size']}")
                    st.write(f"Result: {story['result']}")
                    st.success(f"Return: {story['return']}")
                    st.info(f"Lesson: {story['lesson']}")
                    st.divider()
        else:
            st.info("No significant whale flows detected today. Check back later.")
    
    with flow_tab2:
        if whale_flow_tracker:
            st.subheader("📊 Whale Flow Performance")
            
            # Get performance stats
            stats = whale_flow_tracker.get_performance_stats()
            
            # Performance metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Flows Seen", stats['total_flows_seen'])
                st.metric("Flows Followed", stats['flows_followed'])
            
            with col2:
                follow_rate = stats['follow_rate'] * 100
                st.metric("Follow Rate", f"{follow_rate:.1f}%")
                win_rate = stats['win_rate'] * 100 if stats['flows_followed'] > 0 else 0
                st.metric("Win Rate", f"{win_rate:.1f}%")
            
            with col3:
                st.metric("Total P&L", f"${stats['total_pnl']:,.0f}")
                st.metric("Avg Return", f"{stats['avg_return_pct']:.1f}%")
            
            with col4:
                if stats['best_trade']:
                    st.metric("Best Trade", f"${stats['best_trade']['pnl']:,.0f}")
                if stats['worst_trade']:
                    st.metric("Worst Trade", f"${stats['worst_trade']['pnl']:,.0f}")
            
            # Recent flows table
            st.subheader("📜 Recent Whale Flows (30 days)")
            recent_flows = whale_flow_tracker.get_recent_flows(30)
            
            if recent_flows:
                # Convert to DataFrame for display
                df_data = []
                for flow in recent_flows[:50]:  # Show last 50
                    df_data.append({
                        'Date': flow['timestamp'][:10],
                        'Symbol': flow['symbol'],
                        'Type': flow['flow_type'],
                        'Strike': f"${flow['strike']:.2f}",
                        'Premium': f"${flow['total_premium']:,.0f}",
                        'Followed': '✅' if flow['followed'] else '',
                        'Outcome': flow.get('outcome', '-'),
                        'P&L': f"${flow.get('result_pnl', 0):,.0f}" if flow.get('result_pnl') else '-'
                    })
                
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True)
                
                # Followed flows management
                followed_flows = whale_flow_tracker.get_followed_flows()
                if followed_flows:
                    st.subheader("🎯 Manage Followed Flows")
                    
                    for flow in followed_flows:
                        if not flow.get('outcome'):  # Only show open positions
                            with st.container():
                                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                                
                                with col1:
                                    st.write(f"**{flow['symbol']}** ${flow['strike']} - {flow['option_type']}")
                                    st.write(f"Followed: {flow['timestamp'][:10]}")
                                
                                with col2:
                                    st.write(f"Contracts: {flow['followed_contracts']}")
                                    st.write(f"Cost: ${flow['followed_cost']:,.0f}")
                                
                                with col3:
                                    result_price = st.number_input(
                                        "Exit Price:",
                                        min_value=0.0,
                                        step=0.01,
                                        key=f"whale_exit_{flow['id']}"
                                    )
                                
                                with col4:
                                    outcome = st.selectbox(
                                        "Outcome:",
                                        ["WIN", "LOSS", "BREAKEVEN"],
                                        key=f"whale_outcome_{flow['id']}"
                                    )
                                    
                                    if st.button("Update", key=f"whale_update_{flow['id']}"):
                                        success, result = whale_flow_tracker.update_outcome(
                                            flow['id'], result_price, outcome
                                        )
                                        if success:
                                            st.success(f"Updated: {outcome} with {result['return_pct']:.1f}% return")
                                            st.rerun()
                            
                            st.divider()
            else:
                st.info("No whale flow history yet. Start following flows to build history!")
        else:
            st.warning("Whale flow tracking not available. Check installation.")

# Tab 5: Risk Monitor
with tab5:
    st.subheader("⚠️ Real-Time Risk Monitoring")
    
    active_trades = trade_tracker.get_active_trades()
    
    if active_trades:
        # Get risk alerts
        alerts = risk_manager.monitor_active_positions(active_trades, market_data)
        
        if alerts:
            st.error(f"🚨 {len(alerts)} Risk Alerts")
            for alert in alerts:
                st.warning(alert)
        else:
            st.success(" All positions within normal risk parameters")
        
        # Position risk details
        st.subheader("Position Risk Analysis")
        
        risk_data = []
        for trade in active_trades:
            risk_metrics = risk_manager.calculate_position_risk(trade, market_data)
            risk_data.append({
                'Symbol': trade['symbol'],
                'Strike': f"${trade['strike']:.2f}",
                'DTE': trade['days_to_exp'],
                'Delta': f"{risk_metrics.get('delta', 0):.2f}",
                'Assignment Risk': risk_metrics.get('assignment_risk', 'Low'),
                'Distance to Strike': f"{risk_metrics.get('distance_pct', 0):.1f}%",
                'Action': risk_metrics.get('recommended_action', 'Hold')
            })
        
        risk_df = pd.DataFrame(risk_data)
        st.dataframe(risk_df, use_container_width=True)
        
        # 21-50-7 Rule Monitor
        st.subheader("📏 21-50-7 Rule Compliance")
        
        for trade in active_trades:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**{trade['symbol']}**")
            
            with col2:
                # Calculate profit percentage (mock)
                profit_pct = 25  # Would calculate from real data
                if profit_pct >= 50:
                    st.error(f"🚨 {profit_pct}% profit - CLOSE NOW (50% rule)")
                elif trade['days_to_exp'] <= 21 and profit_pct > 25:
                    st.warning(f"⚠️ {trade['days_to_exp']} DTE - Consider closing (21 DTE rule)")
                elif trade['days_to_exp'] <= 7:
                    st.error(f"🚨 {trade['days_to_exp']} DTE - High gamma risk (7 DTE rule)")
                else:
                    st.success(f" Within parameters")
            
            with col3:
                if st.button(f"Quick Close", key=f"quick_close_{trade['id']}"):
                    st.info("Use Trade History tab to close")
    else:
        st.info("No active trades to monitor")

# Help/Glossary section
with st.expander("📚 Help & Glossary - Understanding the Metrics"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### Option Greeks
        
        **🔢 Delta**
        - Measures how much option price changes when stock moves $1
        - Range: 0 to 1 (calls) or 0 to -1 (puts)
        - 0.30 delta = 30% chance of finishing in-the-money
        - Lower delta = safer for covered calls
        
        **⏰ Theta**
        - Daily time decay in dollars
        - How much the option loses per day
        - Positive for option sellers (you collect theta)
        - Higher theta = more daily income
        
        **📈 Gamma**
        - Rate of change of delta
        - Higher near expiration
        - High gamma = high risk (price can move quickly)
        
        **📊 Vega**
        - Sensitivity to volatility changes
        - How much option price changes with 1% IV move
        """)
    
    with col2:
        st.markdown("""
        ### Key Metrics
        
        **📊 IV Rank (0-100)**
        - Where current IV sits vs past year
        - >50 = High volatility (good for selling)
        - <30 = Low volatility (poor premiums)
        
        **🎯 Win Probability %**
        - Chance option expires worthless (you keep premium)
        - Based on delta and statistics
        - >70% = Conservative, <50% = Aggressive
        
        **💰 Monthly Yield %**
        - Premium income as % of stock price
        - Annualized to monthly for comparison
        - Target: 2-5% monthly for income
        
        **🏆 Confidence Score (0-100)**
        - Overall opportunity quality
        - Factors: IV rank, yield, liquidity, growth
        - >70 = High confidence, <50 = Low confidence
        """)
    
    with col3:
        st.markdown("""
        ### Strategy Rules
        
        **📏 The 21-50-7 Rule**
        - **50% Rule**: Close at 50% max profit
        - **21 DTE**: Review all positions at 21 days
        - **7 DTE**: Must close to avoid gamma risk
        
        **🌱 Growth Scores (0-100)**
        - 0-25: Value stocks (aggressive calls OK)
        - 25-50: Moderate growth (balanced approach)
        - 50-75: High growth (conservative only)
        - 75-100: DO NOT sell calls (protect growth)
        
        **🎭 Strategy Types**
        - **AGGRESSIVE**: ATM to 2% OTM strikes
        - **MODERATE**: 3-5% OTM strikes
        - **CONSERVATIVE**: 7-10% OTM strikes
        - **PROTECT**: No covered calls allowed
        """)
    
    st.divider()
    
    st.markdown("""
    ### 🎯 Quick Decision Guide
    
    **When to TAKE an opportunity:**
    - IV Rank > 50 (high volatility to sell)
    - Monthly yield > 2%
    - Win probability > 70%
    - Growth score < 50
    - No earnings before expiration
    
    **When to PASS:**
    - Growth score > 75 (protect high growth)
    - IV Rank < 30 (poor premiums)
    - Earnings before expiration
    - Low liquidity (volume < 100)
    - Monthly yield < 1%
    
    **When to CLOSE a position:**
    - Reached 50% of max profit
    - Less than 7 days to expiration
    - 21 days left with >25% profit
    - Stock approaching strike price
    """)

# Footer with key reminders
st.divider()
st.markdown("""
<div style='text-align: center; color: #666;'>
<b>Remember:</b> Only sell calls when IV Rank > 50% | Protect growth stocks (score > 75) | Follow the 21-50-7 rule
</div>
""", unsafe_allow_html=True)
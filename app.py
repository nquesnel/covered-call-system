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
    st.session_state.risk_manager = RiskManager()
    st.session_state.data_fetcher = DataFetcher()

# Quick access to managers
pos_manager = st.session_state.position_manager
trade_tracker = st.session_state.trade_tracker
growth_analyzer = st.session_state.growth_analyzer
whale_tracker = st.session_state.whale_tracker
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
                                'taxable',
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
    total_contracts = sum(capacity.values())
    st.metric(
        "Available Contracts",
        total_contracts,
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
            min_confidence = st.slider("Min Confidence", 50, 100, 70, key="confidence_slider")
        with col2:
            min_yield = st.slider("Min Monthly Yield %", 1.0, 10.0, 2.0, key="yield_slider")
        with col3:
            exclude_earnings = st.checkbox("Exclude Earnings", True, key="earnings_checkbox")
        with col4:
            max_growth_score = st.slider("Max Growth Score", 25, 75, 50, key="growth_slider")
    
    with filter_col2:
        st.write("")  # Spacer
        if st.button("🔄 Reset Filters", type="secondary"):
            st.session_state.confidence_slider = 70
            st.session_state.yield_slider = 2.0
            st.session_state.earnings_checkbox = True
            st.session_state.growth_slider = 50
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
                    
                    # Expandable details
                    with st.expander("View Details"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Greeks:**")
                            st.write(f"Delta: {opp.get('delta', 0):.2f}")
                            st.write(f"IV: {opp.get('implied_volatility', 0):.1%}")
                            st.write(f"Volume: {opp.get('volume', 0):,}")
                        with col2:
                            st.write("**Returns:**")
                            st.write(f"Static: {opp['static_return_monthly']:.2%}/mo")
                            st.write(f"If Called: {opp['if_called_return_monthly']:.2%}/mo")
                            st.write(f"Growth Score: {opp['growth_score']}")
                    
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
            st.subheader("📈 Active Trades")
            
            for trade in active_trades:
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{trade['symbol']}** ${trade['strike']} x{trade['contracts']} contracts")
                        st.write(f"Expires: {trade['expiration']}")
                    
                    with col2:
                        st.write(f"Premium: ${trade['premium']:.2f}")
                    
                    with col3:
                        closing_price = st.number_input(
                            "Close at:", 
                            min_value=0.0,
                            step=0.01,
                            key=f"close_{trade['id']}"
                        )
                    
                    with col4:
                        if st.button("Close Trade", key=f"close_btn_{trade['id']}"):
                            outcome = "WIN" if closing_price < trade['premium'] else "LOSS"
                            success, result = trade_tracker.close_trade(
                                trade['id'], closing_price, outcome
                            )
                            if success:
                                st.success(f"Closed with {outcome}: ${result['profit_loss']:.0f}")
                                st.rerun()
    else:
        st.info("No trades recorded yet. Start taking opportunities to build history.")

# Tab 4: Whale Flows
with tab4:
    st.subheader("🐋 Institutional Flow Tracker")
    st.markdown("*Follow the smart money - detect large option flows that could signal big moves*")
    
    # Get whale flows (mock data for now)
    raw_flows = data_fetcher.get_whale_flows()
    
    # Process flows through whale tracker to add analysis
    whale_flows = whale_tracker.detect_institutional_flows(raw_flows)
    
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

# Footer with key reminders
st.divider()
st.markdown("""
<div style='text-align: center; color: #666;'>
<b>Remember:</b> Only sell calls when IV Rank > 50% | Protect growth stocks (score > 75) | Follow the 21-50-7 rule
</div>
""", unsafe_allow_html=True)
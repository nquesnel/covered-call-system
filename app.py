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
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import core modules
from core.position_manager import PositionManager
from core.trade_tracker import TradeTracker
from core.trade_decision_tracker import TradeDecisionTracker
from core.position_monitor import PositionMonitor
try:
    from core.growth_analyzer_enhanced import GrowthAnalyzerEnhanced as GrowthAnalyzer
except ImportError:
    from core.growth_analyzer import GrowthAnalyzer
from core.options_scanner import OptionsScanner
from core.whale_tracker import WhaleTracker
from core.whale_tracker_enhanced import EnhancedWhaleTracker

# Import simple version first (always works)
try:
    from core.whale_flow_tracker_simple import SimpleWhaleFlowTracker
except Exception as e:
    print(f"Error importing SimpleWhaleFlowTracker: {e}")
    SimpleWhaleFlowTracker = None

# Check if we're on Streamlit Cloud BEFORE importing database version
import os
is_cloud = ('/mount/src/' in os.getcwd() or 
           os.environ.get('STREAMLIT_SHARING_MODE') is not None or 
           os.environ.get('STREAMLIT_RUNTIME_ENV') is not None)

if is_cloud:
    # Don't even try to import database version on cloud
    WhaleFlowTracker = None
    print("Detected Streamlit Cloud - skipping database tracker")
else:
    # Only import database version on local
    try:
        from core.whale_flow_tracker import WhaleFlowTracker
    except Exception as e:
        print(f"Warning: Could not import WhaleFlowTracker: {e}")
        WhaleFlowTracker = None
from core.risk_manager import RiskManager
try:
    import yfinance as yf
    from utils.data_fetcher_real import RealDataFetcher as DataFetcher
    print("Using real market data from Yahoo Finance")
except ImportError:
    st.error("⚠️ yfinance not installed! Install with: pip install yfinance")
    st.stop()

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
    st.session_state.enhanced_whale_tracker = EnhancedWhaleTracker()
    st.session_state.decision_tracker = TradeDecisionTracker()
    st.session_state.position_monitor = PositionMonitor(st.session_state.trade_tracker)

# Initialize data fetcher
data_fetcher = DataFetcher()

# We already detected cloud environment during imports
# Always use SimpleWhaleFlowTracker if available
if 'whale_flow_tracker' not in st.session_state:
    if SimpleWhaleFlowTracker:
        try:
            st.session_state.whale_flow_tracker = SimpleWhaleFlowTracker()
            print("SUCCESS: Using SimpleWhaleFlowTracker (in-memory)")
        except Exception as e:
            print(f"Error initializing SimpleWhaleFlowTracker: {e}")
            st.session_state.whale_flow_tracker = None
    else:
        print("ERROR: SimpleWhaleFlowTracker not available")
        st.session_state.whale_flow_tracker = None
            
    st.session_state.risk_manager = RiskManager()
    st.session_state.data_fetcher = DataFetcher()

# Quick access to managers
pos_manager = st.session_state.position_manager
trade_tracker = st.session_state.trade_tracker
growth_analyzer = st.session_state.growth_analyzer
whale_tracker = st.session_state.whale_tracker
enhanced_whale_tracker = st.session_state.enhanced_whale_tracker
whale_flow_tracker = st.session_state.get('whale_flow_tracker', None)
risk_manager = st.session_state.risk_manager
data_fetcher = st.session_state.data_fetcher

# Initialize scanner with dependencies
scanner = OptionsScanner(pos_manager, growth_analyzer)

# Title and goal reminder
st.title("📈 Covered Call Income System")
st.markdown("**Mission**: Generate $2-5K monthly income to eliminate $60K margin debt")

# 21-50-7 Rule Alerts (show before everything else)
if st.session_state.trade_tracker.get_active_trades():
    with st.container():
        # Get current market prices for monitoring
        active_symbols = list(set(t['symbol'] for t in st.session_state.trade_tracker.get_active_trades()))
        current_prices = {}
        for symbol in active_symbols:
            try:
                data = data_fetcher.get_stock_data(symbol)
                if data and 'price' in data:
                    current_prices[symbol] = data['price']
            except:
                pass
        
        # Check positions against 21-50-7 rules
        alerts = st.session_state.position_monitor.check_positions(current_prices)
        
        # Show critical alerts
        if alerts['close_now']:
            st.error("🚨 **POSITIONS REQUIRING ACTION (21-50-7 Rule)**")
            for alert in alerts['close_now']:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.warning(f"⚠️ {alert['symbol']} ${alert['strike']} - {alert['reason']}")
                with col2:
                    st.metric("Profit", f"${alert['current_profit']:.2f} ({alert['profit_pct']:.0%})")
                with col3:
                    if st.button(f"Close {alert['symbol']}", key=f"close_{alert['alert_id']}"):
                        st.info(alert['instructions'])
        
        # Show monitoring alerts
        if alerts['monitor']:
            with st.expander(f"👀 Positions Under 21 DTE ({len(alerts['monitor'])})"): 
                for alert in alerts['monitor']:
                    st.info(f"{alert['symbol']} ${alert['strike']} - {alert['dte']} DTE, "
                           f"{alert['profit_pct']:.0%} profit - {alert['reason']}")
        
        # Summary metrics
        if alerts['close_now'] or alerts['monitor']:
            metrics = st.session_state.position_monitor.get_summary_metrics(alerts)
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Profit Available", f"${metrics['total_profit_available']:,.0f}")
            with col2:
                st.metric("At 50% Target", metrics['profit_breakdown']['over_50'])
            with col3:
                st.metric("Critical Alerts", metrics['critical_alerts'])
            with col4:
                st.metric("Total Monitored", metrics['monitoring_count'])

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
                                pos.get('shares', 0),
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
        
        # Simple account type update section
        with st.expander("🔄 Update Account Types", expanded=False):
            st.write("Change account type for positions:")
            
            # Single position selector approach - show symbol and account
            position_options = {}
            for key, pos in all_positions.items():
                symbol = pos.get('symbol', key.split('_')[0])
                account = pos.get('account_type', 'taxable')
                display_name = f"{symbol} ({account})"
                position_options[display_name] = key
            
            selected_display = st.selectbox(
                "Select position to update:",
                list(position_options.keys()),
                key="position_selector"
            )
            
            if selected_display:
                position_to_update = position_options[selected_display]
                pos = all_positions[position_to_update]
                symbol = pos.get('symbol', position_to_update.split('_')[0])
                current_account = pos.get('account_type', 'taxable')
                st.write(f"Current account type for {symbol}: **{current_account.upper()}**")
                
                new_account_type = st.radio(
                    f"Change to:",
                    ["taxable", "roth", "traditional"],
                    key="new_account_radio"
                )
                
                if st.button("✅ Update Account Type", type="primary"):
                    # Direct update
                    pos_manager.positions[position_to_update]['account_type'] = new_account_type
                    pos_manager.save_positions()
                    st.success(f"✅ Updated {position_to_update} from {current_account} to {new_account_type}")
                    time.sleep(1)  # Give user time to see the message
                    st.rerun()
        
        # Show current positions
        for position_key, pos in all_positions.items():
            if isinstance(pos, dict):
                symbol = pos.get('symbol', position_key.split('_')[0])  # Extract symbol from key
                contracts = pos.get('shares', 0) // 100
                account = pos.get('account_type', 'taxable').upper()
                shares = pos.get('shares', 0)
                st.text(f"{symbol}: {shares} shares ({contracts} contracts) - {account}")
            else:
                st.text(f"{position_key}: Invalid position data")
    
    # Manual covered call entry
    with st.expander("📝 Record Covered Call", expanded=False):
        st.write("Manually record a covered call you've written")
        
        # Only show positions with 100+ shares
        eligible_for_cc = {}
        for key, pos in all_positions.items():
            if pos.get('shares', 0) >= 100:
                symbol = pos.get('symbol', key.split('_')[0])
                account = pos.get('account_type', 'taxable')
                display_name = f"{symbol} ({account})"
                eligible_for_cc[display_name] = (key, pos)
        
        if eligible_for_cc:
            col1, col2 = st.columns(2)
            with col1:
                selected_position = st.selectbox("Position", list(eligible_for_cc.keys()), key="cc_position")
                position_key, position_data = eligible_for_cc[selected_position]
                cc_symbol = position_data.get('symbol', position_key.split('_')[0])
                cc_strike = st.number_input("Strike Price", min_value=0.01, step=0.01, key="cc_strike")
                cc_contracts = st.number_input(
                    "Contracts", 
                    min_value=1, 
                    max_value=position_data['shares'] // 100,
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
@st.cache_data(ttl=300)  # Cache for 5 minutes instead of 30 seconds
def get_market_data(positions_tuple):
    """Fetch current market data for all positions"""
    # Convert tuple back to dict (for caching)
    positions_dict = dict(positions_tuple)
    market_data = {}
    
    # Extract unique symbols from position keys
    symbols = set()
    for position_key in positions_dict.keys():
        if isinstance(positions_dict[position_key], dict):
            symbol = positions_dict[position_key].get('symbol', position_key.split('_')[0])
            symbols.add(symbol)
    
    # Fetch data for each symbol
    for symbol in symbols:
        try:
            market_data[symbol] = data_fetcher.get_stock_data(symbol)
        except Exception as e:
            st.warning(f"Failed to fetch data for {symbol}: {e}")
            # Don't include symbols we can't fetch data for
            continue
    
    return market_data

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_options_data(positions_tuple):
    """Fetch options chains for eligible positions"""
    positions_dict = dict(positions_tuple)
    options_data = {}
    
    # The positions_dict here has symbols as keys when coming from eligible_positions
    for symbol, position in positions_dict.items():
        try:
            chain = data_fetcher.get_options_chain(symbol)
            if chain:  # Only add if we got valid data
                options_data[symbol] = chain
            else:
                # Skip if no real data available
                print(f"No options data available for {symbol}")
        except Exception as e:
            print(f"Failed to fetch options for {symbol}: {e}")
            # Skip if error
            print(f"Error getting options for {symbol}: {e}")
    
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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🎯 Opportunities", 
    "📊 Positions", 
    "📜 Trade History", 
    "🐋 Whale Flows",
    "⚠️ Risk Monitor",
    "🧠 Decision Analysis"
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
    
    # Get opportunities - using scanner's eligible positions
    scanner_eligible = pos_manager.get_eligible_positions()  # Get fresh eligible positions
    
    # Enhanced debugging
    if not scanner_eligible:
        st.error("❌ No eligible positions found!")
        all_pos = pos_manager.get_all_positions()
        if all_pos:
            st.write("Current positions (need 100+ shares for covered calls):")
            for key, pos in all_pos.items():
                symbol = pos.get('symbol', key.split('_')[0])
                shares = pos.get('shares', 0)
                account = pos.get('account_type', 'unknown')
                contracts_available = shares // 100
                st.write(f"• **{symbol}** ({account}): {shares} shares = {contracts_available} contracts")
        else:
            st.info("No positions found. Add positions in the sidebar.")
    
    if scanner_eligible:
        with st.spinner("Scanning for opportunities..."):
            # Convert to tuple for caching
            positions_tuple = tuple(all_positions.items())
            eligible_tuple = tuple(scanner_eligible.items())
            
            market_data = get_market_data(positions_tuple)
            options_data = get_options_data(eligible_tuple)
            
            opportunities = scanner.find_opportunities(market_data, options_data)
            
            # Debug info
            if st.checkbox("Show Debug Info", value=False):
                st.write(f"Market data available for: {list(market_data.keys())}")
                st.write(f"Options data available for: {list(options_data.keys())}")
                st.write(f"Scanner eligible positions: {list(scanner_eligible.keys())}")
                st.write(f"Total opportunities found before filters: {len(opportunities)}")
            
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
                            try:
                                earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d')
                                exp_dt = datetime.strptime(opp['expiration'], '%Y-%m-%d')
                                today = datetime.now()
                                
                                if earnings_dt < today:
                                    st.write(f"✅ **Earnings**: {earnings_date} (already passed)")
                                elif earnings_dt < exp_dt:
                                    days_until = (earnings_dt - today).days
                                    st.write(f"⚠️ **Earnings**: {earnings_date} (in {days_until} days - BEFORE exp)")
                                else:
                                    st.write(f"✅ **Earnings**: {earnings_date} (after exp)")
                            except:
                                st.write(f"**Earnings**: {earnings_date}")
                    
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
                    
                    # Decision tracking buttons
                    decision_col1, decision_col2, decision_col3 = st.columns([1, 1, 3])
                    
                    # Check if this opportunity has been decided on
                    recent_decisions = st.session_state.decision_tracker.get_recent_decisions(7)
                    already_decided = None
                    for decision in recent_decisions:
                        if (decision['symbol'] == opp['symbol'] and 
                            decision['strike'] == opp['strike'] and
                            decision['expiration'] == opp['expiration']):
                            already_decided = decision
                            break
                    
                    with decision_col1:
                        if already_decided and already_decided['decision'] == 'TAKE':
                            st.success("✅ TAKEN")
                        else:
                            if st.button("✅ TAKE", key=f"take_{idx}_{opp['symbol']}_{opp['strike']}"):
                                # Log the decision immediately
                                decision_id = st.session_state.decision_tracker.log_opportunity(
                                    opp, 'TAKE', ''
                                )
                                # Also record in trade tracker
                                trade_id = st.session_state.trade_tracker.record_trade(
                                    symbol=opp['symbol'],
                                    trade_type='covered_call',
                                    strike=opp['strike'], 
                                    expiration=opp['expiration'],
                                    contracts=opp.get('max_contracts', 1),
                                    premium=opp['premium'],
                                    underlying_price=opp['current_price']
                                )
                                st.success(f"✅ Recorded TAKE decision for {opp['symbol']} ${opp['strike']}")
                                st.rerun()
                    
                    with decision_col2:
                        if already_decided and already_decided['decision'] == 'PASS':
                            st.info("❌ PASSED")
                        else:
                            if st.button("❌ PASS", key=f"pass_{idx}_{opp['symbol']}_{opp['strike']}"):
                                # Log the decision immediately
                                decision_id = st.session_state.decision_tracker.log_opportunity(
                                    opp, 'PASS', ''
                                )
                                st.info(f"❌ Recorded PASS decision for {opp['symbol']} ${opp['strike']}")
                                st.rerun()
                    
                    with decision_col3:
                        # Show decision details if already decided
                        if already_decided:
                            if already_decided['decision'] == 'TAKE':
                                st.write(f"📅 Taken on {already_decided['timestamp'][:10]}")
                            elif already_decided['decision'] == 'PASS':
                                st.write(f"📅 Passed on {already_decided['timestamp'][:10]}")
                            if already_decided.get('notes'):
                                st.caption(f"Note: {already_decided['notes']}")
                        else:
                            st.write("🆕 New opportunity")
                    
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
                    if isinstance(pos, dict):
                        shares = pos.get('shares', 0)
                        contracts = shares // 100
                        st.write(f"• **{symbol}**: {shares} shares ({contracts} contracts available)")
                    else:
                        st.write(f"• **{symbol}**: Position data unavailable")
                
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
        positions_tuple = tuple(all_positions.items())
        market_data = get_market_data(positions_tuple)
        
        # Calculate portfolio value
        # Extract prices from market data
        current_prices = {}
        for symbol, data in market_data.items():
            if data and 'price' in data:
                current_prices[symbol] = data['price']
        
        # Debug: show what data we have
        if st.checkbox("Show portfolio debug info", value=False):
            st.write("Market data symbols:", list(market_data.keys()))
            st.write("Current prices:", current_prices)
            st.write("Position keys:", list(all_positions.keys()))
        
        portfolio_value = pos_manager.calculate_total_value(current_prices)
        
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
        for position_key, pos in all_positions.items():
            if not isinstance(pos, dict):
                continue  # Skip invalid positions
            symbol = pos.get('symbol', position_key.split('_')[0])
            
            # Get market data if available, otherwise use cost basis
            if symbol in market_data and market_data[symbol]:
                current_price = market_data[symbol].get('price', pos.get('cost_basis', 0))
                # Get growth analysis
                growth_score = growth_analyzer.calculate_growth_score(symbol, market_data[symbol])
            else:
                # Use cost basis as fallback if no market data
                current_price = pos.get('cost_basis', 0)
                # Use default growth score if no market data
                growth_score = {
                    'total_score': 50,
                    'strategy': {'strategy': 'No Data'}
                }
            
            # Calculate metrics
            current_value = current_price * pos.get('shares', 0)
            total_cost = pos.get('cost_basis', 0) * pos.get('shares', 0)
            gain_loss = current_value - total_cost
            gain_loss_pct = (gain_loss / total_cost * 100) if total_cost > 0 else 0
            contracts = pos.get('shares', 0) // 100
            
            position_data.append({
                'Symbol': symbol,
                'Shares': pos.get('shares', 0),
                'Contracts': contracts,
                'Cost Basis': f"${pos.get('cost_basis', 0):.2f}",
                'Current': f"${current_price:.2f}",
                'Value': f"${current_value:,.0f}",
                'Gain/Loss': f"${gain_loss:,.0f}",
                'Gain %': f"{gain_loss_pct:+.1f}%",
                'Growth Score': growth_score['total_score'],
                'Strategy': growth_score['strategy']['strategy'],
                'Account': pos['account_type'].title()
            })
        
        df = pd.DataFrame(position_data)
        
        if not df.empty and 'Growth Score' in df.columns:
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
        elif not df.empty:
            # Display without styling if Growth Score column is missing
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No position data available. Add positions to see portfolio analysis.")
        
        # Position management
        with st.expander("🔧 Manage Positions"):
            # Create display options for position editing
            edit_options = {}
            for key, pos in all_positions.items():
                symbol = pos.get('symbol', key.split('_')[0])
                account = pos.get('account_type', 'taxable')
                display_name = f"{symbol} ({account})"
                edit_options[display_name] = key
            
            if edit_options:
                selected_edit_display = st.selectbox("Select position to edit:", list(edit_options.keys()))
                edit_position_key = edit_options[selected_edit_display] if selected_edit_display else None
            else:
                st.info("No positions available to edit.")
                edit_position_key = None
            
            if edit_position_key:
                pos = all_positions[edit_position_key]
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    new_shares = st.number_input(
                        "Shares:", 
                        value=pos.get('shares', 0),
                        min_value=0,
                        step=100
                    )
                with col2:
                    new_cost = st.number_input(
                        "Cost Basis:", 
                        value=pos.get('cost_basis', 0),
                        min_value=0.01,
                        step=0.01
                    )
                with col3:
                    # Add account type selector
                    current_account = pos.get('account_type', 'taxable')
                    new_account_type = st.selectbox(
                        "Account Type:",
                        ["taxable", "roth", "traditional"],
                        index=["taxable", "roth", "traditional"].index(current_account),
                        key=f"account_type_{edit_position_key}"
                    )
                with col4:
                    st.write("") # Spacer
                    if st.button("Update Position"):
                        # Update the position with new account type
                        pos_manager.update_position(edit_position_key, new_shares, new_cost, new_account_type)
                        symbol = pos.get('symbol', edit_position_key.split('_')[0])
                        st.success(f"Updated {symbol}")
                        st.rerun()
                
                if st.button("🗑️ Delete Position", type="secondary"):
                    if st.checkbox("Confirm deletion"):
                        symbol = pos.get('symbol', edit_position_key.split('_')[0])
                        pos_manager.delete_position(edit_position_key)
                        st.success(f"Deleted {symbol}")
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
                # Calculate current profit (estimate based on time decay)
                days_held = (datetime.now() - datetime.fromisoformat(trade['entry_date'])).days
                time_decay_factor = min(0.9, days_held / 30)  # Assume 90% decay in 30 days
                current_bid = trade['premium'] * (1 - time_decay_factor)
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
                    # Calculate metrics
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
        # Get whale flows from market data
        raw_flows = data_fetcher.get_whale_flows()
        
        # Process flows through whale tracker to add analysis
        whale_flows = whale_tracker.detect_institutional_flows(raw_flows)
        
        # Enhance with advanced analysis
        enhanced_flows = st.session_state.enhanced_whale_tracker.rank_whale_flows(whale_flows)
        
        if whale_flows and whale_flow_tracker:
            # Log all flows to history
            try:
                for flow in whale_flows:
                    try:
                        whale_flow_tracker.log_flow(flow)
                    except:
                        # Silently skip individual flow errors
                        pass
            except Exception as e:
                # This should catch any remaining errors
                pass
        
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
            
            # Flow cards with enhanced analysis
            st.subheader("🎯 Top Whale Flows - Ranked by Conviction")
            
            # Filter toggle
            show_only_high = st.checkbox("Show only HIGH+ conviction flows", value=True)
            
            # Display enhanced flows
            flows_to_show = enhanced_flows
            if show_only_high:
                flows_to_show = [f for f in enhanced_flows if f['whale_analysis']['whale_score'] >= 75]
            
            if not flows_to_show:
                st.info("No high conviction flows detected. Showing all flows...")
                flows_to_show = enhanced_flows
            
            for idx, flow in enumerate(flows_to_show[:10]):  # Show top 10
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
                    
                    with col1:
                        # Enhanced display with whale score
                        analysis = flow['whale_analysis']
                        score = analysis['whale_score']
                        
                        # Score-based emoji
                        if score >= 85:
                            score_emoji = "🌟"  # Perfect setup
                        elif score >= 75:
                            score_emoji = "🎯"  # High conviction
                        elif score >= 65:
                            score_emoji = "💡"  # Interesting
                        else:
                            score_emoji = "👀"  # Watch
                        
                        sentiment_emoji = "🟢" if "BULL" in flow['sentiment'] else "🔴"
                        st.markdown(f"### {score_emoji} {flow['symbol']} - Whale Score: {score}")
                        st.write(f"{sentiment_emoji} **{flow['option_type'].upper()}** ${flow['strike']} exp {flow['expiration']}")
                        st.write(f"💰 Premium: ${flow['total_premium']:,} | Type: {flow['flow_type']}")
                        
                        # Show pattern matches
                        if analysis['pattern_matches']:
                            patterns_str = ' | '.join(analysis['pattern_matches'])
                            st.success(f"🎯 Patterns: {patterns_str}")
                    
                    with col2:
                        # Conviction and metrics
                        conviction = analysis['conviction_level']
                        if conviction == 'EXTREME':
                            conv_color = "🔴"
                        elif conviction == 'HIGH':
                            conv_color = "🟠"
                        elif conviction == 'MODERATE':
                            conv_color = "🟡"
                        else:
                            conv_color = "⚪"
                        
                        st.metric("Conviction", f"{conv_color} {conviction}")
                        st.metric("Vol/OI Ratio", f"{flow.get('volume_oi_ratio', 0):.1f}x")
                        st.metric("Action", analysis['recommended_action'])
                    
                    with col3:
                        # Risk and timing
                        st.metric("Inst. Probability", f"{analysis['institutional_probability']:.0f}%")
                        st.metric("Risk/Reward", analysis['risk_reward_rating'])
                        st.metric("Days to Exp", flow['days_to_exp'])
                    
                    with col4:
                        # Enhanced follow recommendation
                        analysis = flow['whale_analysis']
                        
                        # Key insights
                        st.markdown("**💡 Key Insights:**")
                        for insight in analysis['key_insights'][:2]:  # Show top 2 insights
                            st.caption(insight)
                        
                        # Follow recommendation
                        if flow['follow_trade'] and analysis['whale_score'] >= 65:
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
            
            # Enhanced educational section with research findings
            col1, col2 = st.columns(2)
            
            with col1:
                with st.expander("🌟 Proven Winning Patterns", expanded=False):
                    st.markdown("""
                    ### Based on Unusual Whales Research
                    
                    **🔥 The Perfect Storm Setup:**
                    - Volume > 2x Open Interest
                    - Premium > $500,000
                    - Sweep orders on ASK side
                    - Multiple strikes being hit
                    - Score: 85+ required
                    
                    **📈 Pre-Breakout Pattern:**
                    - 10-20% OTM calls
                    - 20-40 days to expiration
                    - Near technical resistance
                    - Accumulation over days
                    
                    **🎯 Earnings Runner:**
                    - 10-21 days before earnings
                    - 5-15% OTM strikes
                    - Premium > $100K
                    - Multiple expiration dates
                    
                    **🏆 Real Winners (2024):**
                    - OPEN: $84K → $1.3M (1,500%)
                    - TSLA: $210C → 451% gain
                    - BSX: $67.5C → 227% gain
                    """)
            
            with col2:
                with st.expander("🛡️ Risk Management Rules", expanded=False):
                    st.markdown("""
                    ### Professional Risk Management
                    
                    **Position Sizing:**
                    - EXTREME conviction: 3% of portfolio
                    - HIGH conviction: 2% of portfolio
                    - MODERATE: 1% of portfolio
                    - Never exceed these limits!
                    
                    **Entry Rules:**
                    - Only follow scores 65+
                    - Check liquidity (spread < 10%)
                    - Avoid < 7 DTE trades
                    - Skip pre-earnings unless confident
                    
                    **Exit Strategy:**
                    - 25% at 100% gain
                    - 50% at 200% gain
                    - Let 25% run for home run
                    - Mental stop at -50%
                    
                    **Red Flags to Avoid:**
                    - Wide bid-ask spreads
                    - Low open interest < 1000
                    - Against strong trend
                    - Emotional market periods
                    """)
            
            # Success stories in expandable section
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
        
        # Whale Flow Glossary
        with st.expander("🐋 Understanding Whale Flows - Glossary"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("""
                ### Flow Types
                
                **🔄 Sweep**
                - Aggressive order that "sweeps" multiple exchanges
                - Buyer/seller willing to pay any price to fill immediately
                - Shows urgency and strong conviction
                - Most bullish/bearish signal
                
                **📦 Block**
                - Large single order negotiated off-exchange
                - Usually institutional positioning
                - Less urgent than sweeps
                - Often hedging or portfolio adjustments
                
                **🔀 Split**
                - Large order broken into smaller pieces
                - Trying to hide size or get better fills
                - Can indicate accumulation/distribution
                
                **🚨 Unusual**
                - Any flow significantly above normal volume
                - Not necessarily sweep or block
                - Worth monitoring for potential moves
                """)
            
            with col2:
                st.markdown("""
                ### Key Metrics
                
                **📊 Unusual Factor (e.g., 81x)**
                - How many times above average volume
                - 10x+ = Notable, 50x+ = Very unusual
                - 100x+ = Extremely rare, high conviction
                
                **💰 Premium Volume**
                - Total dollar amount spent on options
                - $1M+ = Significant institutional flow
                - $5M+ = Major positioning
                
                **📈 Implied Move %**
                - How much the stock needs to move for profit
                - Calculated: (Strike - Current Price) / Current Price
                - Shows expected volatility
                
                **🎯 Days to Expiration (DTE)**
                - Time until option expires
                - <7 DTE = Very short-term bet (earnings/news)
                - 30-45 DTE = Standard positioning
                - >90 DTE = Long-term conviction
                """)
            
            with col3:
                st.markdown("""
                ### Reading the Flows
                
                **Example: SPY 662C sweep**
                - Current SPY: $628
                - Strike: $662
                - **Implied move: +5.4%** in 2 weeks
                - Very aggressive bullish bet
                
                **🟢 Bullish Signals:**
                - Call sweeps above current price
                - Put sells below current price
                - Increasing call/put ratio
                
                **🔴 Bearish Signals:**
                - Put sweeps below current price
                - Call sells above current price
                - Increasing put/call ratio
                
                **⚠️ Risk Levels:**
                - LOW: Hedging flows, far OTM
                - MODERATE: Directional bets, reasonable size
                - HIGH: Aggressive near-term bets
                - EXTREME: Massive size, short DTE
                """)
            
            st.divider()
            
            st.markdown("""
            ### 🎯 How to Use Whale Flows
            
            **When to FOLLOW a whale flow:**
            - Sweep orders with high unusual factor (50x+)
            - Multiple flows in same direction
            - Flows align with technical levels
            - Reasonable implied moves (<10%)
            - 30+ DTE for time to work
            
            **When to AVOID:**
            - Flows before earnings (could be hedges)
            - Extremely far OTM strikes (lottery tickets)
            - Very short DTE (<7 days)
            - Against strong trend
            - When you don't understand the setup
            
            **Risk Management:**
            - Never risk more than 1-2% per whale follow
            - Use smaller size than the whale (1-10 contracts)
            - Set stop loss at 50% of premium paid
            - Take profits at 50-100% gains
            """)
    
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
                for i, flow in enumerate(recent_flows[:50]):  # Show last 50
                    df_data.append({
                        'ID': flow.get('id', i),
                        'Date': flow.get('timestamp', '')[:10] if flow.get('timestamp') else '-',
                        'Symbol': flow.get('symbol', '-'),
                        'Type': flow.get('flow_type', '-'),
                        'Strike': f"${flow.get('strike', 0):.2f}",
                        'Premium': f"${flow.get('total_premium', 0):,.0f}",
                        'Score': flow.get('whale_score', '-'),
                        'Followed': '✅' if flow.get('followed', False) else '❌',
                        'Outcome': flow.get('outcome', '-'),
                        'P&L': f"${flow.get('result_pnl', 0):,.0f}" if flow.get('result_pnl') else '-'
                    })
                
                df = pd.DataFrame(df_data)
                
                # Style the dataframe
                def style_score(val):
                    if val == '-' or pd.isna(val):
                        return ''
                    score = int(val) if not pd.isna(val) else 0
                    if score >= 85:
                        return 'background-color: #4CAF50; color: white'
                    elif score >= 75:
                        return 'background-color: #8BC34A'
                    elif score >= 65:
                        return 'background-color: #FFC107'
                    else:
                        return ''
                
                # Apply styling
                styled_df = df.style.applymap(style_score, subset=['Score'])
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
                
                # Manual follow tracking section
                st.divider()
                st.subheader("🔄 Update Follow Status")
                st.write("Mark flows you followed manually (outside the app)")
                
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    # Get list of recent flows for selection
                    flow_options = {}
                    for flow in recent_flows[:20]:  # Last 20 flows
                        symbol = flow.get('symbol', 'Unknown')
                        strike = flow.get('strike', 0)
                        option_type = flow.get('option_type', 'call')
                        timestamp = flow.get('timestamp', '')[:10] if flow.get('timestamp') else '-'
                        key = f"{symbol} ${strike} {option_type} - {timestamp}"
                        flow_options[key] = flow.get('id', i)
                    
                    selected_flow = st.selectbox(
                        "Select flow to update:",
                        options=list(flow_options.keys()),
                        key="manual_follow_select"
                    )
                
                with col2:
                    contracts = st.number_input(
                        "Contracts:",
                        min_value=1,
                        value=1,
                        key="manual_follow_contracts"
                    )
                
                with col3:
                    if st.button("🔄 Toggle Follow Status", type="secondary"):
                        if selected_flow and whale_flow_tracker:
                            flow_id = flow_options[selected_flow]
                            success = whale_flow_tracker.toggle_followed(flow_id, contracts)
                            if success:
                                st.success("Updated follow status!")
                                st.rerun()
                            else:
                                st.error("Failed to update status")
                
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
        # Get market data for risk monitoring
        positions_tuple = tuple(all_positions.items())
        risk_market_data = get_market_data(positions_tuple)
        
        # Get risk alerts
        alerts = risk_manager.monitor_active_positions(active_trades, risk_market_data)
        
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
            risk_metrics = risk_manager.calculate_position_risk(trade, risk_market_data)
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
                # Calculate profit percentage
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

# Tab 6: Decision Analysis
with tab6:
    st.subheader("🧠 Trade Decision Analysis")
    
    # Get statistics
    stats = st.session_state.decision_tracker.get_statistics()
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Opportunities Shown", stats['total_shown'])
        st.metric("Take Rate", f"{stats['take_rate']:.1%}")
    with col2:
        st.metric("Trades Taken", stats['total_taken'])
        st.metric("Win Rate", f"{stats['win_rate']:.1%}" if stats['completed_trades'] > 0 else "N/A")
    with col3:
        st.metric("Trades Passed", stats['total_passed'])
        st.metric("Avg Return", f"${stats['avg_return']:.2f}" if stats['completed_trades'] > 0 else "N/A")
    with col4:
        st.metric("Completed", stats['completed_trades'])
        st.metric("Total Return", f"${stats.get('total_return', 0):,.2f}")
    
    # Pattern Analysis
    if stats['completed_trades'] >= 5:
        st.subheader("📈 Winning Pattern Analysis")
        patterns = st.session_state.decision_tracker.analyze_patterns()
        
        if patterns.get('best_characteristics'):
            st.success("🏆 Best Performing Characteristics:")
            for char in patterns['best_characteristics']:
                st.write(f"- **{char['factor']}** in range {char['range']}: "
                        f"{char['win_rate']:.0%} win rate ({char['sample_size']} trades)")
        
        # Show analysis by factor
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Win Rate by IV Rank:**")
            if 'by_iv_rank' in patterns and patterns['by_iv_rank'].get('ranges'):
                for r in patterns['by_iv_rank']['ranges']:
                    st.write(f"- {r['range']}: {r['win_rate']:.0%} ({r['count']} trades)")
            
            st.write("\n**Win Rate by Monthly Yield:**")
            if 'by_yield' in patterns and patterns['by_yield'].get('ranges'):
                for r in patterns['by_yield']['ranges']:
                    st.write(f"- {r['range']}: {r['win_rate']:.0%} ({r['count']} trades)")
        
        with col2:
            st.write("**Win Rate by Delta:**")
            if 'by_delta' in patterns and patterns['by_delta'].get('ranges'):
                for r in patterns['by_delta']['ranges']:
                    st.write(f"- {r['range']}: {r['win_rate']:.0%} ({r['count']} trades)")
            
            st.write("\n**Earnings Impact:**")
            if 'earnings_impact' in patterns:
                st.write(f"- With earnings: {patterns['earnings_impact']['with_earnings']:.0%}")
                st.write(f"- No earnings: {patterns['earnings_impact']['without_earnings']:.0%}")
    
    # Recent Decisions
    st.subheader("📅 Recent Decisions (Last 30 Days)")
    recent = st.session_state.decision_tracker.get_recent_decisions(30)
    
    if recent:
        decision_data = []
        for d in recent[:20]:  # Show last 20
            decision_data.append({
                'Date': d['timestamp'][:10],
                'Symbol': d['symbol'],
                'Strike': f"${d['strike']}",
                'Decision': d['decision'],
                'Yield': f"{d['monthly_yield']:.1%}",
                'IV Rank': f"{d.get('iv_rank', 0):.0f}",
                'Confidence': d['confidence_score'],
                'Outcome': d.get('outcome', 'Pending'),
                'Return': f"${d.get('actual_return', 0):.2f}" if d.get('actual_return') else '-'
            })
        
        df = pd.DataFrame(decision_data)
        st.dataframe(df, use_container_width=True)
        
        # Pending outcomes
        pending = st.session_state.decision_tracker.get_pending_outcomes()
        if pending:
            st.warning(f"⚠️ {len(pending)} trades need outcome recording")
            for p in pending:
                st.write(f"- {p['symbol']} ${p['strike']} exp {p['expiration']} - Taken on {p['timestamp'][:10]}")
    else:
        st.info("No trade decisions recorded yet. Start by evaluating opportunities in the Opportunities tab!")
    
    # Export functionality
    if st.button("💾 Export Decision History"):
        df = pd.DataFrame(st.session_state.decision_tracker.decisions)
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"trade_decisions_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# Footer with key reminders
st.divider()
st.markdown("""
<div style='text-align: center; color: #666;'>
<b>Remember:</b> Only sell calls when IV Rank > 50% | Protect growth stocks (score > 75) | Follow the 21-50-7 rule
</div>
""", unsafe_allow_html=True)
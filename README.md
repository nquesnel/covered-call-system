# Covered Call Income System

A web-based system to generate $2-5K monthly income through strategic covered call options trading, with a focus on protecting high-growth positions and following institutional "smart money" flows.

## 🎯 Mission

Generate consistent monthly income to pay down $60K margin debt while protecting high-growth stock positions from being capped.

## 🚀 Quick Start

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd covered-call-system
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

4. **Run the application:**
   ```bash
   streamlit run app.py
   ```

5. **Access the dashboard:**
   Open http://localhost:8501 in your browser

## 📊 Key Features

### 1. **Growth Protection System**
- Strategic scoring (0-100) for every position
- Automatic protection of high-growth stocks (score > 75)
- Tailored strategies: Aggressive, Moderate, Conservative, or PROTECT

### 2. **Winning Trade Selection**
- IV Rank > 50% filter (only sell expensive options)
- Post-earnings IV crush detection
- Technical confirmation (RSI, MACD, support/resistance)
- Liquidity requirements enforcement

### 3. **Institutional Flow Tracking**
- Detect large option flows ($50K+ on cheap options)
- Identify massive volume spikes (20x+ normal)
- Follow "smart money" with scaled retail positions
- Success story examples and education

### 4. **Risk Management**
- **21-50-7 Rule Automation:**
  - Close at 50% profit (always)
  - Consider closing at 21 DTE with profit
  - Must close at 7 DTE (gamma risk)
- Real-time position monitoring
- Assignment risk alerts
- IV crush opportunity detection

### 5. **Trade Decision Tracking**
- Log every opportunity (TAKE or PASS)
- Track actual outcomes vs. passed trades
- Performance analytics and win rate tracking
- Complete audit trail for tax purposes

## 🏗️ System Architecture

```
covered-call-system/
├── app.py                    # Streamlit main dashboard
├── config.py                 # Configuration management
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
├── data/                    # Data storage
│   ├── positions.json       # Your stock positions
│   ├── trades.db           # Trade history database
│   └── cache/              # API response cache
├── core/                    # Core business logic
│   ├── position_manager.py  # Portfolio management
│   ├── trade_tracker.py    # Trade decision tracking
│   ├── growth_analyzer.py  # Growth scoring system
│   ├── options_scanner.py  # Opportunity discovery
│   ├── whale_tracker.py    # Institutional flow detection
│   ├── risk_manager.py     # Risk monitoring
│   └── trade_executor.py   # Order execution
└── utils/                   # Utilities
    └── data_fetcher.py     # Market data APIs
```

## 📈 Dashboard Overview

### Main Metrics
- Monthly income progress toward goal
- Margin debt paydown tracking
- Win rate and active trades
- Available contracts for covered calls

### Five Main Tabs

1. **🎯 Opportunities**
   - Real-time scanning for best trades
   - Confidence scoring and filtering
   - One-click TAKE/PASS decisions
   - Detailed Greeks and returns

2. **📊 Positions**
   - Portfolio value and P&L
   - Growth scores with color coding
   - Position management (add/edit/delete)
   - Strategy recommendations

3. **📈 Trade History**
   - Complete decision log
   - Performance analytics
   - Active trade management
   - Win/loss tracking

4. **🐋 Whale Flows**
   - Institutional option flow detection
   - Follow trade suggestions
   - Success story examples
   - Risk/reward analysis

5. **⚠️ Risk Monitor**
   - Real-time alerts
   - 21-50-7 rule compliance
   - Assignment risk warnings
   - Position adjustment suggestions

## 🔧 Configuration

### Required API Keys (in .env file)
- **Yahoo Finance**: Free tier for basic data
- **TD Ameritrade**: Free with brokerage account
- **Unusual Whales**: $50/month for institutional flows
- **Polygon.io**: $99/month for real-time options

### Key Settings
- `MIN_IV_RANK`: Minimum IV rank to consider (default: 50)
- `MIN_MONTHLY_YIELD`: Minimum acceptable yield (default: 2%)
- `MAX_CONTRACTS_PER_TRADE`: Position size limit (default: 10)
- `MONTHLY_INCOME_GOAL`: Your target income (default: $3,500)

## 📱 Usage Tips

### Adding Positions
1. Use the sidebar "Add Position" form
2. Enter symbol, shares, and cost basis
3. Positions with 100+ shares become eligible for covered calls

### Taking Opportunities
1. Review opportunities sorted by confidence score
2. Check growth score (avoid if > 75)
3. Verify IV Rank > 50%
4. Click TAKE and specify number of contracts
5. System logs decision for tracking

### Following Whale Flows
1. Look for flows with 80+ confidence
2. Check risk level (prefer MODERATE or lower)
3. Use suggested retail contract size
4. Risk only what you can afford to lose

## 🚨 Important Rules

1. **Never sell calls on positions with growth score > 75**
2. **Only sell when IV Rank > 50%**
3. **Always follow the 21-50-7 rule**
4. **Track every decision (TAKE or PASS)**
5. **Size positions appropriately for your account**

## 🛠️ Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black .
flake8 .
```

### Adding New Features
1. Create feature branch
2. Update relevant core modules
3. Add UI components to app.py
4. Update configuration if needed
5. Test thoroughly with mock data

## 📊 Success Metrics

- **Primary**: Generate $2,500+ monthly income
- **Win Rate**: Maintain 80%+ on taken trades
- **Assignment Rate**: Keep below 5%
- **Growth Protection**: Zero high-growth positions capped

## 🚀 Future Enhancements

- [ ] Real broker API integration (TD, IBKR)
- [ ] Automated trade execution
- [ ] Mobile app version
- [ ] Advanced backtesting
- [ ] Multi-account support
- [ ] Tax optimization features

## ⚖️ Disclaimer

This system is for educational purposes. Options trading involves substantial risk. Past performance does not guarantee future results. Always do your own research and consider consulting with a financial advisor.

## 📞 Support

For issues or questions:
1. Check existing issues
2. Create detailed bug report
3. Include error messages and screenshots
4. Specify your configuration

---

**Remember**: The goal is making money, not looking pretty. Focus on execution over aesthetics.
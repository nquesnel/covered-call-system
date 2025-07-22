"""
Configuration settings for Covered Call Income System
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""
    
    # Application settings
    APP_NAME = "Covered Call Income System"
    VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Data directories
    DATA_DIR = os.getenv("DATA_DIR", "data")
    CACHE_DIR = os.path.join(DATA_DIR, "cache")
    
    # Database
    POSITIONS_FILE = os.path.join(DATA_DIR, "positions.json")
    TRADES_DB = os.path.join(DATA_DIR, "trades.db")
    
    # Trading parameters
    MIN_IV_RANK = int(os.getenv("MIN_IV_RANK", "50"))
    MIN_PREMIUM = float(os.getenv("MIN_PREMIUM", "0.20"))
    MIN_MONTHLY_YIELD = float(os.getenv("MIN_MONTHLY_YIELD", "0.02"))
    MAX_CONTRACTS_PER_TRADE = int(os.getenv("MAX_CONTRACTS_PER_TRADE", "10"))
    
    # Risk management
    MAX_PROFIT_PCT_CLOSE = float(os.getenv("MAX_PROFIT_PCT_CLOSE", "50"))
    DTE_WARNING_THRESHOLD = int(os.getenv("DTE_WARNING_THRESHOLD", "21"))
    DTE_CRITICAL_THRESHOLD = int(os.getenv("DTE_CRITICAL_THRESHOLD", "7"))
    
    # API Keys (set in .env file or environment)
    YAHOO_FINANCE_API_KEY = os.getenv("YAHOO_FINANCE_API_KEY", "")
    TD_AMERITRADE_API_KEY = os.getenv("TD_AMERITRADE_API_KEY", "")
    TD_AMERITRADE_ACCOUNT_ID = os.getenv("TD_AMERITRADE_ACCOUNT_ID", "")
    UNUSUAL_WHALES_API_KEY = os.getenv("UNUSUAL_WHALES_API_KEY", "")
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")
    
    # Cache settings
    CACHE_DURATION_SECONDS = int(os.getenv("CACHE_DURATION_SECONDS", "30"))
    
    # UI Settings
    REFRESH_INTERVAL_SECONDS = int(os.getenv("REFRESH_INTERVAL_SECONDS", "60"))
    MAX_OPPORTUNITIES_DISPLAY = int(os.getenv("MAX_OPPORTUNITIES_DISPLAY", "20"))
    
    # Whale tracking
    MIN_WHALE_PREMIUM = float(os.getenv("MIN_WHALE_PREMIUM", "50000"))
    MIN_UNUSUAL_VOLUME_RATIO = float(os.getenv("MIN_UNUSUAL_VOLUME_RATIO", "20"))
    
    # Goals
    MONTHLY_INCOME_GOAL = float(os.getenv("MONTHLY_INCOME_GOAL", "3500"))
    MARGIN_DEBT_TOTAL = float(os.getenv("MARGIN_DEBT_TOTAL", "60000"))
    
    @classmethod
    def validate(cls):
        """Validate configuration settings"""
        # Ensure data directories exist
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.CACHE_DIR, exist_ok=True)
        
        # Validate numeric ranges
        assert 0 <= cls.MIN_IV_RANK <= 100, "MIN_IV_RANK must be between 0 and 100"
        assert cls.MIN_PREMIUM >= 0, "MIN_PREMIUM must be non-negative"
        assert 0 <= cls.MIN_MONTHLY_YIELD <= 1, "MIN_MONTHLY_YIELD must be between 0 and 1"
        assert cls.MAX_CONTRACTS_PER_TRADE > 0, "MAX_CONTRACTS_PER_TRADE must be positive"
        
        return True


# Validate configuration on import
Config.validate()
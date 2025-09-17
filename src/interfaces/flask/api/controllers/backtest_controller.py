from flask import Blueprint, request, jsonify
import logging
from datetime import datetime

from application.services.misbuffet import Misbuffet
from application.managers.project_managers.test_project_backtest.test_project_backtest_manager import TestProjectBacktestManager
from application.managers.project_managers.test_project_live_trading.test_project_live_trading_manager import TestProjectLiveTradingManager
from application.managers.database_managers.database_manager import DatabaseManager
from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository

backtest_api = Blueprint("backtest_api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)

@backtest_api.route("/backtest", methods=["POST"])
def run_backtest():
    params = request.json  # JSON body
    service = Misbuffet()
    results = service.run(params)
    return jsonify(results.to_dict())

@backtest_api.route("/test_managers/backtest", methods=["POST"])
def run_test_backtest_api():
    """API endpoint to run TestProjectBacktestManager"""
    try:
        logger.info("API: Starting TestProjectBacktestManager execution...")
        manager = TestProjectBacktestManager()
        result = manager.run()
        
        return jsonify({
            "success": True,
            "message": "TestProjectBacktestManager executed successfully",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API Error running TestProjectBacktestManager: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@backtest_api.route("/test_managers/live_trading", methods=["POST"])
def run_test_live_trading_api():
    """API endpoint to run TestProjectLiveTradingManager"""
    try:
        logger.info("API: Starting TestProjectLiveTradingManager execution...")
        manager = TestProjectLiveTradingManager()
        result = manager.run()
        
        return jsonify({
            "success": True,
            "message": "TestProjectLiveTradingManager executed successfully",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API Error running TestProjectLiveTradingManager: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@backtest_api.route("/entities/company_shares", methods=["GET"])
def get_company_shares():
    """Get all company shares entities data"""
    try:
        # Initialize database and repository
        db_manager = DatabaseManager("sqlite")
        db_manager.db.initialize_database_and_create_all_tables()
        
        repository = CompanyShareRepository(db_manager.session)
        
        # Get all company shares
        shares = repository.get_all()
        
        # Convert to JSON serializable format
        shares_data = []
        for share in shares:
            share_dict = {
                "id": share.id,
                "ticker": share.ticker,
                "exchange_id": share.exchange_id,
                "company_id": share.company_id,
                "start_date": share.start_date.isoformat() if share.start_date else None,
                "end_date": share.end_date.isoformat() if share.end_date else None,
                "company_name": getattr(share, 'company_name', None),
                "sector": getattr(share, 'sector', None)
            }
            
            # Add market data if available
            if hasattr(share, 'current_market_data') and share.current_market_data:
                share_dict["market_data"] = {
                    "price": float(share.current_market_data.price),
                    "volume": float(share.current_market_data.volume),
                    "timestamp": share.current_market_data.timestamp.isoformat()
                }
            
            # Add fundamental data if available
            if hasattr(share, 'fundamental_data') and share.fundamental_data:
                share_dict["fundamental_data"] = {
                    "pe_ratio": float(share.fundamental_data.pe_ratio) if share.fundamental_data.pe_ratio else None,
                    "dividend_yield": float(share.fundamental_data.dividend_yield) if share.fundamental_data.dividend_yield else None,
                    "market_cap": float(share.fundamental_data.market_cap) if share.fundamental_data.market_cap else None,
                    "shares_outstanding": float(share.fundamental_data.shares_outstanding) if share.fundamental_data.shares_outstanding else None,
                    "sector": share.fundamental_data.sector,
                    "industry": share.fundamental_data.industry
                }
            
            shares_data.append(share_dict)
        
        return jsonify({
            "success": True,
            "data": shares_data,
            "count": len(shares_data),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API Error retrieving company shares: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@backtest_api.route("/entities/company_shares/<int:share_id>", methods=["GET"])
def get_company_share_by_id(share_id):
    """Get specific company share by ID"""
    try:
        # Initialize database and repository
        db_manager = DatabaseManager("sqlite")
        db_manager.db.initialize_database_and_create_all_tables()
        
        repository = CompanyShareRepository(db_manager.session)
        
        # Get specific share
        share = repository.get_by_id(share_id)
        
        if not share:
            return jsonify({
                "success": False,
                "error": f"Company share with ID {share_id} not found",
                "timestamp": datetime.now().isoformat()
            }), 404
        
        # Convert to JSON serializable format
        share_data = {
            "id": share.id,
            "ticker": share.ticker,
            "exchange_id": share.exchange_id,
            "company_id": share.company_id,
            "start_date": share.start_date.isoformat() if share.start_date else None,
            "end_date": share.end_date.isoformat() if share.end_date else None,
            "company_name": getattr(share, 'company_name', None),
            "sector": getattr(share, 'sector', None)
        }
        
        # Add market data if available
        if hasattr(share, 'current_market_data') and share.current_market_data:
            share_data["market_data"] = {
                "price": float(share.current_market_data.price),
                "volume": float(share.current_market_data.volume),
                "timestamp": share.current_market_data.timestamp.isoformat()
            }
        
        # Add fundamental data if available
        if hasattr(share, 'fundamental_data') and share.fundamental_data:
            share_data["fundamental_data"] = {
                "pe_ratio": float(share.fundamental_data.pe_ratio) if share.fundamental_data.pe_ratio else None,
                "dividend_yield": float(share.fundamental_data.dividend_yield) if share.fundamental_data.dividend_yield else None,
                "market_cap": float(share.fundamental_data.market_cap) if share.fundamental_data.market_cap else None,
                "shares_outstanding": float(share.fundamental_data.shares_outstanding) if share.fundamental_data.shares_outstanding else None,
                "sector": share.fundamental_data.sector,
                "industry": share.fundamental_data.industry
            }
        
        return jsonify({
            "success": True,
            "data": share_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API Error retrieving company share {share_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@backtest_api.route("/entities/summary", methods=["GET"])
def get_entities_summary():
    """Get summary of all entities in the database"""
    try:
        # Initialize database and repository
        db_manager = DatabaseManager("sqlite")
        db_manager.db.initialize_database_and_create_all_tables()
        
        repository = CompanyShareRepository(db_manager.session)
        
        # Get counts and basic info
        all_shares = repository.get_all()
        
        # Calculate summary statistics
        total_shares = len(all_shares)
        sectors = {}
        tickers = []
        
        for share in all_shares:
            tickers.append(share.ticker)
            
            # Count by sector if available
            sector = getattr(share, 'sector', 'Unknown')
            if hasattr(share, 'fundamental_data') and share.fundamental_data:
                sector = share.fundamental_data.sector or 'Unknown'
            
            if sector in sectors:
                sectors[sector] += 1
            else:
                sectors[sector] = 1
        
        return jsonify({
            "success": True,
            "data": {
                "total_company_shares": total_shares,
                "unique_tickers": list(set(tickers)),
                "sectors_breakdown": sectors,
                "database_type": "sqlite"
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API Error retrieving entities summary: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

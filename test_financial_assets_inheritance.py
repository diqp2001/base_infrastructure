#!/usr/bin/env python3
"""
Test script to verify the joined-table inheritance pattern for financial assets.
This script demonstrates the core invariant: Creating subtype automatically populates root.
"""

import os
import sys
from datetime import datetime, date
from decimal import Decimal

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.infrastructure.models import ModelBase
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
from src.infrastructure.models.finance.financial_assets.company_share import CompanyShareModel
from src.infrastructure.models.finance.financial_assets.bond import BondModel
from src.infrastructure.models.finance.financial_assets.etf_share import ETFShareModel
from src.infrastructure.models.finance.financial_assets.currency import CurrencyModel
from src.infrastructure.models.finance.financial_assets.commodity import CommodityModel
from src.infrastructure.models.finance.holding.holding import HoldingModel


def create_test_database():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=True)
    ModelBase.metadata.create_all(engine)
    return engine


def test_core_invariant():
    """Test the core invariant: Creating subtype automatically populates root."""
    engine = create_test_database()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🧪 Testing Core Invariant: Concrete asset = root row + subtype row")
        print("=" * 70)
        
        # Test 1: Create CompanyShareModel
        print("\n1️⃣ Testing CompanyShareModel Creation:")
        company_share = CompanyShareModel(
            ticker="AAPL",
            company_id=1,
            exchange_id=1,
            start_date=date.today(),
            name="Apple Inc."
        )
        session.add(company_share)
        session.commit()
        
        # Verify both tables are populated
        root_asset = session.query(FinancialAssetModel).filter_by(id=company_share.id).first()
        print(f"✅ Root table entry: ID={root_asset.id}, type={root_asset.asset_type}, name={root_asset.name}")
        print(f"✅ Child table entry: ID={company_share.id}, ticker={company_share.ticker}")
        assert root_asset.asset_type == 'company_share'
        assert root_asset.name == "Apple Inc."
        
        # Test 2: Create BondModel
        print("\n2️⃣ Testing BondModel Creation:")
        bond = BondModel(
            isin="US037833100",
            name="Apple Inc. Bond",
            issuer="Apple Inc.",
            bond_type="Corporate",
            face_value=Decimal("1000.00"),
            coupon_rate=Decimal("3.5"),
            issue_date=date.today(),
            maturity_date=date(2030, 1, 1),
            description="Apple corporate bond"
        )
        session.add(bond)
        session.commit()
        
        # Verify both tables are populated
        root_bond = session.query(FinancialAssetModel).filter_by(id=bond.id).first()
        print(f"✅ Root table entry: ID={root_bond.id}, type={root_bond.asset_type}, name={root_bond.name}")
        print(f"✅ Child table entry: ID={bond.id}, isin={bond.isin}")
        assert root_bond.asset_type == 'bond'
        assert root_bond.name == "Apple Inc. Bond"
        
        # Test 3: Create ETFShareModel
        print("\n3️⃣ Testing ETFShareModel Creation:")
        etf = ETFShareModel(
            ticker="SPY",
            exchange_id=1,
            start_date=date.today(),
            fund_name="SPDR S&P 500 ETF Trust",
            name="SPY ETF"
        )
        session.add(etf)
        session.commit()
        
        # Verify both tables are populated
        root_etf = session.query(FinancialAssetModel).filter_by(id=etf.id).first()
        print(f"✅ Root table entry: ID={root_etf.id}, type={root_etf.asset_type}, name={root_etf.name}")
        print(f"✅ Child table entry: ID={etf.id}, ticker={etf.ticker}")
        assert root_etf.asset_type == 'etf_share'
        assert root_etf.name == "SPY ETF"
        
        # Test 4: Test polymorphic resolution through holdings
        print("\n4️⃣ Testing Polymorphic Resolution through Holdings:")
        holding = HoldingModel(
            asset_id=company_share.id,
            container_id=1,
            start_date=datetime.now()
        )
        session.add(holding)
        session.commit()
        
        # Test automatic type resolution
        retrieved_holding = session.query(HoldingModel).filter_by(id=holding.id).first()
        resolved_asset = retrieved_holding.asset
        print(f"✅ Holding asset resolution: {type(resolved_asset).__name__}")
        print(f"✅ Asset type: {resolved_asset.asset_type}")
        print(f"✅ Asset ticker: {resolved_asset.ticker}")
        assert isinstance(resolved_asset, CompanyShareModel)
        assert hasattr(resolved_asset, 'ticker')
        
        # Test 5: Query all assets polymorphically
        print("\n5️⃣ Testing Polymorphic Queries:")
        all_assets = session.query(FinancialAssetModel).all()
        print(f"✅ Total assets: {len(all_assets)}")
        for asset in all_assets:
            print(f"   - {asset.asset_type}: {asset.name} (ID: {asset.id})")
            # Verify we get the correct subclass instances
            if asset.asset_type == 'company_share':
                assert isinstance(asset, CompanyShareModel)
                assert hasattr(asset, 'ticker')
            elif asset.asset_type == 'bond':
                assert isinstance(asset, BondModel)
                assert hasattr(asset, 'isin')
            elif asset.asset_type == 'etf_share':
                assert isinstance(asset, ETFShareModel)
                assert hasattr(asset, 'fund_name')
        
        print("\n🎉 ALL TESTS PASSED! Core invariant verified:")
        print("   Concrete asset = root row + subtype row")
        print("   Creating subtype automatically populates root")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        session.close()


def test_direct_root_creation_prevention():
    """Test that direct FinancialAssetModel creation should be avoided."""
    engine = create_test_database()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("\n⚠️ Testing Direct Root Creation (should be avoided):")
        print("=" * 50)
        
        # This works but creates an orphaned root entry without specialized data
        root_asset = FinancialAssetModel(
            asset_type="financial_asset",
            name="Generic Asset"
        )
        session.add(root_asset)
        session.commit()
        
        print(f"⚠️ Direct root creation: ID={root_asset.id}, type={root_asset.asset_type}")
        print("⚠️ This creates an orphaned row with no specialized asset data")
        print("✅ Rule: Always create concrete types (CompanyShareModel, BondModel, etc.)")
        
    except Exception as e:
        print(f"Info: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    print("🚀 Testing Financial Assets Joined-Table Inheritance")
    print("=" * 60)
    
    test_core_invariant()
    test_direct_root_creation_prevention()
    
    print("\n✨ Summary:")
    print("   ✅ Core invariant verified: Concrete asset = root row + subtype row")
    print("   ✅ Automatic dual-table population working correctly")
    print("   ✅ Polymorphic resolution through holdings working")
    print("   ✅ SQLAlchemy inheritance pattern implemented successfully")
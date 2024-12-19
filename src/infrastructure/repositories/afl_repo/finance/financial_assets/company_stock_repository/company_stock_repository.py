from sqlalchemy import MetaData

from infrastructure.models.identification_tables.company_stock_identification_table import create_company_stock_identification_table, update_company_stock_identification_table
from infrastructure.models import KeyCompanyStock
from ..financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models import CompanyStock as CompanyStockModel
from src.domain.entities.finance.financial_assets.company_stock import CompanyStock as CompanyStockEntity




class CompanyStockRepository(FinancialAssetRepository):
    def __init__(self, db, session):
        super().__init__(db, session)

    
    def get_by_id(self, id: int) -> CompanyStockEntity:
        """Fetches a Stock asset by its ID."""
        try:
            return self.session.query(CompanyStockModel).filter(CompanyStockModel.id == id).first()
        except Exception as e:
            print(f"Error retrieving stock by ID: {e}")
            return None
        finally:
            self.session.close()

    def save_list(self, list_company_stock_entity) -> None:
        """
        Saves a list of CompanyStock entities to the database. For each entity:
        - Check if it already exists in the CompanyStock table.
        - If it doesn't exist, create a new record and integrate its keys.
        - Trigger the update of the identification table after saving all new stocks.
        """
        try:
            # Ensure metadata for dynamic updates
            metadata = self.db.model_registry.base_factory.Base.metadata

            for company_stock_entity in list_company_stock_entity:
                # Check if the stock already exists
                exists = self.session.query(CompanyStockModel).filter(
                    CompanyStockModel.id == company_stock_entity.id
                ).first()

                if not exists:
                    # Create and save the new CompanyStock record
                    company_stock_model = CompanyStockModel(
                        id=company_stock_entity.id,
                        ticker=company_stock_entity.ticker,
                        exchange_id=company_stock_entity.exchange_id,
                        company_id=company_stock_entity.company_id,
                        start_date=company_stock_entity.start_date,
                        end_date=company_stock_entity.end_date,
                        # Include other fields as necessary
                    )
                    self.session.add(company_stock_model)

                    # If the entity includes keys, integrate them
                    for key_id, key_value in company_stock_entity.keys.items():
                        key_record = KeyCompanyStock(
                            company_stock_id=company_stock_entity.id,
                            key_id=key_id,
                            key_value=key_value,
                        )
                        self.session.add(key_record)
                    # Commit all changes before updating the identification table
                    self.session.commit()

                    # Update the company_stock_identification_table
                    update_company_stock_identification_table(metadata, self.session)

            

        except Exception as e:
            self.session.rollback()  # Rollback in case of an error
            print(f"An error occurred while saving: {e}")

    def add(self, id: int, ticker: str, exchange_id: int, company_id: int, start_date, end_date, key_df=None) -> None:
        """
        Saves a single CompanyStock to the database along with its keys.
        Parameters:
        - id: int - The ID of the company stock.
        - ticker: str - The ticker symbol.
        - exchange_id: int - The exchange ID.
        - company_id: int - The company ID.
        - start_date: datetime - The start date of the company stock.
        - end_date: datetime - The end date of the company stock.
        - key_df: DataFrame - A DataFrame containing `key_id` and `key_value`.
        """
        check = None
        try:
            # Check if the stock already exists
            existing_stock = self.session.query(CompanyStockModel).filter(CompanyStockModel.id == id).first()

            if existing_stock:
                print(f"Company stock with ID {id} already exists. ")
                
                
            else:

                # Create and save the new CompanyStock record
                new_stock = CompanyStockModel(
                    CompanyStockEntity(id, ticker, exchange_id, company_id,  start_date, end_date)
                )
                self.session.add(new_stock)
                check = 1

            
            # Step 1: Identify existing keys
            existing_keys = (
                self.session.query(KeyCompanyStock.key_id, KeyCompanyStock.key_value)
                .filter(KeyCompanyStock.company_stock_id == id)
                .all()
            )

            # Convert existing keys to a set for fast lookups
            existing_keys_set = {(key.key_id, key.key_value) for key in existing_keys}
            
            # Step 2: Add missing keys from the DataFrame
            for _, row in key_df.iterrows():
                key_tuple = (row["key_id"], row["key_value"])
                if key_tuple not in existing_keys_set:
                    check = 1
                    print(f"Company stock with ID {id} keys missing. ")  # Only add keys not already in the database
                    key_record = KeyCompanyStock(
                        company_stock_id=id,
                        key_id=row["key_id"],
                        key_value=row["key_value"],
                        start_date=start_date,
                        end_date=end_date,
                    )
                    self.session.add(key_record)
            # Commit the new stock and keys
            self.session.commit()

            # Update the company_stock_identification_table
            if 'company_stock_identification_table' not in self.db.model_registry.base_factory.Base.metadata.tables:
                
                create_company_stock_identification_table(self.db, self.session)
            elif check is not None:
                update_company_stock_identification_table(self.db, self.session)

            print(f"Successfully saved company stock with ID {id}.")

        except Exception as e:
            self.session.rollback()  # Rollback in case of an error
            print(f"An error occurred while saving the company stock: {e}")

            
    def exists_by_id(self, id: int) -> bool:
        """Checks if a stock exists by its ID."""
        try:
            # Query the database to check if a stock with the given ID exists
            company_stock = self.session.query(CompanyStockModel).filter(CompanyStockModel.id == id).first()
            return company_stock is not None  # If no stock is found, returns False
        except Exception as e:
            print(f"Error checking if stock exists by ID: {e}")
            return False
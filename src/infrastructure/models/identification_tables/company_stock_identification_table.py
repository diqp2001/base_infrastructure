from sqlalchemy import MetaData, Table, Column, Integer, Date, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
from sqlalchemy import Table, select, update, insert
from sqlalchemy.orm import Session

# Assume the following imports exist for related models and utility functions
from src.infrastructure.models import KeyCompanyStock, CompanyStock



# Define the CompanyStockIdentification table dynamically
def create_company_stock_identification_table(db, session):
    """
    Creates or updates the `company_stock_identification_table` dynamically.
    :param metadata: SQLAlchemy MetaData object.
    :param session: SQLAlchemy session object.
    """
    # Dynamically retrieve keys from the KeyCompanyStock table
    key_company_stocks_table = KeyCompanyStock.__table__
    try:
        key_ids = session.execute(select(key_company_stocks_table.c.key_id.distinct())).fetchall()
        print("Distinct key IDs:", key_ids)
    except Exception as e:
        session.rollback()  # Rollback in case of an error
        print(f"An error occurred while saving the company stock: {e}")

    key_ids = [key_id[0] for key_id in key_ids]

    # Define the identification table schema dynamically
    columns = [
        Column("company_stock_id", Integer, nullable=False),
        Column("start_date", Date, nullable=False),
        Column("end_date", Date, nullable=True),
    ] + [Column(key_id, String, nullable=True) for key_id in key_ids]
    metadata = db.model_registry.base_factory.Base.metadata
    company_stock_identification_table = Table(
        "company_stock_identification_table", metadata, *columns, extend_existing=True
    )

    # Create or update the table in the database
    db.model_registry.base_factory.Base.metadata.create_all(bind=session.bind)
    print(db.model_registry.base_factory.Base.metadata.tables.keys())
    # Perform incremental updates
    update_company_stock_identification_table(db, session)

    return company_stock_identification_table




def update_company_stock_identification_table(db, session):
    """
    Incrementally updates the `company_stock_identification_table` based on changes
    in `KeyCompanyStock` and `CompanyStock` tables.
    :param db: Database object with metadata.
    :param session: SQLAlchemy session object.
    """
    # Get references to tables
    key_company_stocks_table = KeyCompanyStock.__table__
    company_stocks_table = CompanyStock.__table__
    identification_table = db.model_registry.base_factory.Base.metadata.tables.get('company_stock_identification_table')
    print(f"Type of identification_table: {type(identification_table)}")
    print(f"Identification table columns: {[col.name for col in identification_table.columns]}")
    print(f"Identification table object: {identification_table}")


    if 'company_stock_identification_table' not in db.model_registry.base_factory.Base.metadata.tables:
        raise RuntimeError("The company_stock_identification_table does not exist in metadata.")


    # Step 1: Identify new or updated rows
    join_condition = key_company_stocks_table.c.company_stock_id == company_stocks_table.c.id

    # Corrected select statement
    select_stmt = select(
        company_stocks_table.c.id.label("company_stock_id"),
        company_stocks_table.c.start_date,
        company_stocks_table.c.end_date,
        *[
            key_company_stocks_table.c.key_value.label(key_column.name)
            for key_column in identification_table.columns
            if key_column.name not in ('company_stock_id', 'start_date', 'end_date')
        ]
    ).select_from(company_stocks_table.join(key_company_stocks_table, join_condition))

    # Fetch existing rows to check for changes
    existing_rows = session.execute(
        select(
            identification_table.c.company_stock_id,
            identification_table.c.start_date,
            identification_table.c.end_date,
        )
    ).fetchall()

    # Determine rows to insert or update
    new_or_updated_rows = session.execute(select_stmt).fetchall()
    rows_to_insert = []
    rows_to_update = []

    for new_row in new_or_updated_rows:
        existing_row = next((row for row in existing_rows if row.company_stock_id == new_row.company_stock_id), None)
        if not existing_row:
            # Row is new
            rows_to_insert.append(new_row)
        elif existing_row != new_row:
            # Row exists but is updated
            rows_to_update.append(new_row)

    # Step 2: Perform incremental updates
    if rows_to_insert:
        session.execute(insert(identification_table), [row._asdict() for row in rows_to_insert])

    for row in rows_to_update:
        update_stmt = (
            update(identification_table)
            .where(identification_table.c.company_stock_id == row.company_stock_id)
            .values(row._asdict())
        )
        session.execute(update_stmt)

    session.commit()

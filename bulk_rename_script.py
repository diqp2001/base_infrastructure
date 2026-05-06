#!/usr/bin/env python3

import os
import re
import shutil

# Base directory
BASE_DIR = "/home/runner/work/base_infrastructure/base_infrastructure"

# File mappings from old to new names
DOMAIN_FILES = [
    "portfolio_company_share_option_factor.py",
    "portfolio_company_share_option_bates_price_factor.py",
    "portfolio_company_share_option_black_scholes_merton_price_factor.py",
    "portfolio_company_share_option_cox_ross_rubinstein_price_factor.py",
    "portfolio_company_share_option_delta_factor.py",
    "portfolio_company_share_option_dupire_local_volatility_price_factor.py",
    "portfolio_company_share_option_gamma_factor.py",
    "portfolio_company_share_option_heston_price_factor.py",
    "portfolio_company_share_option_hull_white_price_factor.py",
    "portfolio_company_share_option_price_factor.py",
    "portfolio_company_share_option_price_return_factor.py",
    "portfolio_company_share_option_rho_factor.py",
    "portfolio_company_share_option_sabr_price_factor.py",
    "portfolio_company_share_option_theta_factor.py",
    "portfolio_company_share_option_vega_factor.py",
]

MAPPER_FILES = [
    "portfolio_company_share_option_bates_price_factor_mapper.py",
    "portfolio_company_share_option_black_scholes_merton_price_factor_mapper.py",
    "portfolio_company_share_option_cox_ross_rubinstein_price_factor_mapper.py",
    "portfolio_company_share_option_delta_factor_mapper.py",
    "portfolio_company_share_option_dupire_local_volatility_price_factor_mapper.py",
    "portfolio_company_share_option_factor_mapper.py",
    "portfolio_company_share_option_heston_price_factor_mapper.py",
    "portfolio_company_share_option_hull_white_price_factor_mapper.py",
    "portfolio_company_share_option_price_factor_mapper.py",
    "portfolio_company_share_option_price_return_factor_mapper.py",
    "portfolio_company_share_option_sabr_price_factor_mapper.py",
]

# Directories
DOMAIN_DIR = "src/domain/entities/factor/finance/financial_assets/derivatives/option/company_share_portfolio_option"
MAPPER_DIR = "src/infrastructure/repositories/mappers/factor/finance/financial_assets/derivatives/option/company_share_portfolio_option"

def rename_filename(old_name):
    """Convert portfolio_company_share_option_* to company_share_portfolio_option_*"""
    return old_name.replace("portfolio_company_share_option", "company_share_portfolio_option")

def update_class_names(content):
    """Update class names from PortfolioCompanyShareOption* to CompanySharePortfolioOption*"""
    # Update class names
    content = re.sub(r'\bPortfolioCompanyShareOption([A-Za-z]*)\b', r'CompanySharePortfolioOption\1', content)
    return content

def update_imports(content):
    """Update import statements"""
    # Update module imports
    content = re.sub(r'from.*portfolio_company_share_option', 
                    lambda m: m.group(0).replace('portfolio_company_share_option', 'company_share_portfolio_option'), 
                    content)
    # Update model imports
    content = re.sub(r'PortfolioCompanyShareOptionFactorModel', 'CompanySharePortfolioOptionFactorModel', content)
    return content

def update_discriminator(content):
    """Update discriminator values"""
    content = re.sub(r"return 'portfolio_company_share_option'", "return 'company_share_portfolio_option'", content)
    return content

def process_files():
    """Process all files for renaming and content updates"""
    
    print("Processing domain entity files...")
    for old_filename in DOMAIN_FILES:
        old_path = os.path.join(BASE_DIR, DOMAIN_DIR, old_filename)
        new_filename = rename_filename(old_filename)
        new_path = os.path.join(BASE_DIR, DOMAIN_DIR, new_filename)
        
        if os.path.exists(old_path):
            # Read content
            with open(old_path, 'r') as f:
                content = f.read()
            
            # Update content
            content = update_class_names(content)
            content = update_imports(content)
            
            # Write to new file
            with open(new_path, 'w') as f:
                f.write(content)
            
            print(f"  Renamed: {old_filename} -> {new_filename}")
        else:
            print(f"  Warning: {old_path} not found")
    
    print("\nProcessing mapper files...")
    for old_filename in MAPPER_FILES:
        old_path = os.path.join(BASE_DIR, MAPPER_DIR, old_filename)
        new_filename = rename_filename(old_filename)
        new_path = os.path.join(BASE_DIR, MAPPER_DIR, new_filename)
        
        if os.path.exists(old_path):
            # Read content
            with open(old_path, 'r') as f:
                content = f.read()
            
            # Update content
            content = update_class_names(content)
            content = update_imports(content)
            content = update_discriminator(content)
            
            # Write to new file
            with open(new_path, 'w') as f:
                f.write(content)
            
            print(f"  Renamed: {old_filename} -> {new_filename}")
        else:
            print(f"  Warning: {old_path} not found")

if __name__ == "__main__":
    process_files()
    print("\nRenaming complete!")
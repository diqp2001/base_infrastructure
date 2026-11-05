from src.domain.entities.finance.financial_assets.derivatives.option.share_option import ShareOption


class CompanyShareOption(ShareOption):
    """
    Option written on a company share. Contract terms (strike, multiplier, expiry, exchange) come from ShareOption.
    """

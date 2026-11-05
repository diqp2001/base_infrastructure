from src.domain.entities.finance.financial_assets.derivatives.option.share_option import ShareOption


class ETFShareOption(ShareOption):
    """
    Option written on an ETF share (underlying_asset_id = the ETFShare). Contract terms come from ShareOption.
    """

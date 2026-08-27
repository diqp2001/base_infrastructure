from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_discounted_value_factor import BondFutureDiscountedValueFactor
from src.domain.ports.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_discounted_value_factor_port import BondFutureDiscountedValueFactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRBondFutureDiscountedValueFactorRepository(BaseIBKRFactorRepository, BondFutureDiscountedValueFactorPort):

    def __init__(self, ibkr_client, factory=None):
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('BondFutureDiscountedValueFactor')

    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity() if self.local_repo else BondFutureDiscountedValueFactor

    def _create_or_get(self, name: str, **kwargs):
        try:
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(
                    BondFutureDiscountedValueFactor, primary_key=name, **kwargs
                )
                if created_factor:
                    return created_factor

            print(f"Failed to create bond future discounted value factor: {name}")
            return None

        except Exception as e:
            print(f"Error in get_or_create for bond future discounted value factor {name}: {e}")
            return None

    def get_by_name(self, name: str) -> Optional[BondFutureDiscountedValueFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_id(self, factor_id: int) -> Optional[BondFutureDiscountedValueFactor]:
        return self.local_repo.get_by_id(factor_id) if self.local_repo else None

    def get_all(self) -> List[BondFutureDiscountedValueFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: BondFutureDiscountedValueFactor) -> Optional[BondFutureDiscountedValueFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: BondFutureDiscountedValueFactor) -> Optional[BondFutureDiscountedValueFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, factor_id: int) -> bool:
        return self.local_repo.delete(factor_id) if self.local_repo else False

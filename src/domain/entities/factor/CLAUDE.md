factor structure and needs:
1. Domain entity in src.domain.entities.factor. with a calculate function if the factor value has dependencies
2. It's definition in factor library src.application.services.data.entities.factor.factor_library in the proper entity library
    2.1 it will be written if the factor has dependcies like this
    "return_open": {
        "class": IndexFuturePriceReturnFactor, 
        "name": "return_open",
        "group": "return",
        "subgroup": "minutes",
        "frequency": "1m",
        "data_type": "numeric",
        "description": "Minute-level open price return",
        "dependencies": {
            "start_price": {
                "class": IndexFutureFactor,
                    "name": "open", 
                    "group": "price",
                    "subgroup": "minutes",
                    "data_type": "numeric",
                    "description": "Minute-level open price",
                    "dependencies": [],
                    "parameters": {"lag":timedelta(days=5, hours=3, minutes=10)}
                },
            "end_price": {
                "class": IndexFutureFactor,
                    "name": "open", 
                    "group": "price",
                    "subgroup": "minutes",
                    "data_type": "numeric",
                    "description": "Minute-level open price",
                    "dependencies": [],
                    "parameters": {"lag":timedelta(days=4, hours=3, minutes=10)}
                },
                },
        "parameters": {}
    },
    if it has dependencies, it has a calculate function

3. It needs a mapper in src.infrastructure.repositories.mappers.factor with the following 
    IndexFuturePriceReturnFactorMapper, so add FactorMapper to Domain entity factor name class
    3.1  a  discriminator property
    in this example 
    IndexFuturePriceReturnFactorMapper
    is factor of financial_asset IndexFuture, so the discriminator is index_future
    @property
    def discriminator(self):
        return 'index_future'

    3.2 all the following function that should not need explanation
    @property
    def model_class(self):
        return IndexFuturePriceReturnFactorModel
    
    def get_factor_model(self):
        return IndexFuturePriceReturnFactorModel
    
    def get_factor_entity(self):
        return IndexFuturePriceReturnFactor
    
    def to_domain(self, orm_model: Optional[IndexFuturePriceReturnFactorModel]) -> Optional[IndexFuturePriceReturnFactor]:
        """Convert ORM model to IndexFuturePriceReturnFactor domain entity."""
        if not orm_model:
            return None
        
        return IndexFuturePriceReturnFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition
        )
    
    def to_orm(self, domain_entity: IndexFuturePriceReturnFactor) -> IndexFuturePriceReturnFactorModel:
        """Convert IndexFuturePriceReturnFactor domain entity to ORM model."""
        return IndexFuturePriceReturnFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )

4. it needs a factor model in src.infrastructure.models.factor.factor.py
    the class needs to look like this
    class IndexFuturePriceReturnFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_future_price_return_factor"
    }
5. it needs a local factor repository in src.infrastructure.repositories.local_repo.factor
    like IndexFuturePriceReturnFactorRepository
    5.1 the parent class needs to be BaseFactorRepository class IndexFuturePriceReturnFactorRepository(BaseFactorRepository, IndexFuturePriceReturnFactorPort): and IndexFuturePriceReturnFactorPort
    5.2 init function takes session and factory, with self.factory and self.mapper and self.mapper_value 
        def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = IndexFuturePriceReturnFactorMapper()
        self.mapper_value = FactorValueMapper()
    5.3  it needs the following property
        @property
        def entity_class(self):
            return self.get_factor_entity()
        @property
        def model_class(self):
            return self.mapper.model_class

    5.4 the _create_or_get function with the following structure

        def _create_or_get(self, entity_cls, primary_key: str, **kwargs):
        """
        Get or create an index future price return factor with dependency resolution.
        
        Args:
            primary_key: Factor name identifier
            **kwargs: Additional parameters for factor creation
            
        Returns:
            Factor entity or None if creation failed
        """
        try:
            # Check existing by primary identifier (factor name)
            existing = self.get_by_all(
                name=primary_key,
                group=kwargs.get('group', 'return'),
                factor_type=kwargs.get('factor_type', 'index_future_price_return_factor')
            )
            if existing:
                return self._to_entity(existing)
            
            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group', 'return'),
                subgroup=kwargs.get('subgroup', 'daily'),
                frequency=kwargs.get('frequency', '1d'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'calculated'),
                definition=kwargs.get('definition', f'{self.mapper.discriminator} factor: {primary_key}')
            )
            
            # Use FactorMapper to convert domain entity to ORM model
            # This ensures entity_type is properly set
            orm_factor = self._to_model(domain_factor)
            
            self.session.add(orm_factor)
            #create_or_get dependencies
            if kwargs.get('dependencies'):
                dependencies = kwargs.get('dependencies')
                for dependency in dependencies.items():
                    entity_class = dependency[1].get('class')
                    repo = self.factory.get_local_repository(entity_class)
                    
                    dependency_config = dependency[1]
                    dependency_entity = repo._create_or_get(
                            entity_class,
                            primary_key=dependency_config.get("name"),
                            group=dependency_config.get("group"),
                            subgroup=dependency_config.get("subgroup"),
                            frequency=dependency_config.get("frequency", "1d"),
                            data_type=dependency_config.get("data_type"),
                            factor_type=dependency_config.get("factor_type"),
                            source=dependency_config.get("source"),
                            definition=dependency_config.get("definition"),)


                    repo_factor_dependency = self.factory.get_local_repository(FactorDependency)
                    repo_factor_dependency._create_or_get(independent_factor=dependency_entity, dependent_factor=self._to_entity(orm_factor), lag = dependency_config.get("parameters").get("lag"))
 
            
            self.session.commit()
            if orm_factor:
                return self._to_entity(orm_factor)
            
        except Exception as e:
            print(f"Error in get_or_create index future price return factor {primary_key}: {e}")
            return None
    5.5 get_by_all function with this structure
        def get_by_all(
        self,
        name: str,
        group: str,
        factor_type: Optional[str] = None,
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
    ):
        """Retrieve a factor matching all provided (non-None) fields."""
        try:
            FactorModel = self.get_factor_model()

            query = self.session.query(FactorModel)

            # Mandatory filters
            query = query.filter(
                FactorModel.name == name,
                FactorModel.group == group,
            )

            # Optional filters
            if factor_type is not None:
                query = query.filter(FactorModel.factor_type == factor_type)

            if subgroup is not None:
                query = query.filter(FactorModel.subgroup == subgroup)

            if frequency is not None:
                query = query.filter(FactorModel.frequency == frequency)

            if data_type is not None:
                query = query.filter(FactorModel.data_type == data_type)

            if source is not None:
                query = query.filter(FactorModel.source == source)

            return query.first()

        except Exception as e:
            print(f"Error retrieving index future price return factor by all attributes: {e}")
            return None
    5.6 and all these functions
           def get_by_id(self, id: int):
        entity = self._to_entity(self.session
            .query(self.model_class)
            .filter(self.model_class.id == id)
            .one_or_none())
        return entity
    
    def get_factor_model(self):
        return self.mapper.get_factor_model()
    
    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    def get_factor_value_model(self):
        return self.mapper_value.get_factor_value_model()
    
    def get_factor_value_entity(self):
        return self.mapper_value.get_factor_value_entity()

    def _to_entity(self, infra_obj):
        """Convert ORM model to domain entity."""
        return self.mapper.to_domain(infra_obj)
    
    def _to_model(self, entity):
        """Convert domain entity to ORM model."""
        return self.mapper.to_orm(entity)

    5.7 the repository needs to be added in the RepositoryFactory in src.infrastructure.repositories.repository_factory in the function

    create_local_repositories like this 'index_future_price_return_factor': IndexFuturePriceReturnFactorRepository(self.session, factory=self),

    and 

    a property like this :
     @property
    def index_future_price_return_factor_local_repo(self):
        """Get index_future_price_return_factor repository for dependency injection."""
        return self._local_repositories.get('index_future_price_return_factor')
6.  it needs repository for IBKR IBKRIndexFuturePriceReturnFactorRepository 
class IBKRIndexFuturePriceReturnFactorRepository(BaseIBKRFactorRepository, IndexFuturePriceReturnFactorPort):
    6.1 init function needs to look like this
    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR Index Future Price Return Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('index_future_price_return_factor')
    and  the parent class needs to be BaseFactorRepository IBKRIndexFuturePriceReturnFactorRepository(BaseIBKRFactorRepository, IndexFuturePriceReturnFactorPort) and IndexFuturePriceReturnFactorPort

    
    6.2  it needs the following property
        @property
        def entity_class(self):
            return self.local_repo.get_factor_entity()
        @property
        def model_class(self):
            return self.local_repo.get_factor_model()

    6.3 the _create_or_get function with the following structure

        def _create_or_get(self, name: str, **kwargs):
        """
        Get or create an index future price return factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "return")
            subgroup: Factor subgroup (default: "daily")
            
        Returns:
            IndexFuturePriceReturnFactor entity from database or newly created
        """
        try:
            # Enhance with IBKR-specific return calculation data
            enhanced_kwargs = self._enhance_with_ibkr_return_data(name, **kwargs)
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(primary_key=name, **enhanced_kwargs)
                if created_factor:
                    return created_factor
            
            print(f"Failed to create index future price return factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for index future price return factor {name}: {e}")
            return None

        ***** very important the parameters of _create_or_get needs to look like this
        (self, name: str,**kwargs)


    6.4 it also needs all these functions

    # Delegate standard operations to local repository
    def get_by_name(self, name: str) -> Optional[IndexFuturePriceReturnFactor]:
        """Get factor by name (delegates to local repo)."""
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_id(self, factor_id: int) -> Optional[IndexFuturePriceReturnFactor]:
        """Get factor by ID (delegates to local repo)."""
        return self.local_repo.get_by_id(factor_id) if self.local_repo else None

    def get_by_group(self, group: str) -> List[IndexFuturePriceReturnFactor]:
        """Get factors by group (delegates to local repo)."""
        return self.local_repo.get_by_group(group) if self.local_repo else []

    def get_by_subgroup(self, subgroup: str) -> List[IndexFuturePriceReturnFactor]:
        """Get factors by subgroup (delegates to local repo)."""
        return self.local_repo.get_by_subgroup(subgroup) if self.local_repo else []

    def get_all(self) -> List[IndexFuturePriceReturnFactor]:
        """Get all factors (delegates to local repo)."""
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: IndexFuturePriceReturnFactor) -> Optional[IndexFuturePriceReturnFactor]:
        """Add factor entity (delegates to local repo)."""
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: IndexFuturePriceReturnFactor) -> Optional[IndexFuturePriceReturnFactor]:
        """Update factor entity (delegates to local repo)."""
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, factor_id: int) -> bool:
        """Delete factor entity (delegates to local repo)."""
        return self.local_repo.delete(factor_id) if self.local_repo else False
    6.5 the repository needs to be added in the RepositoryFactory in src.infrastructure.repositories.repository_factory in the function

    create_ibkr_repositories like this 'index_future_price_return_factor': IBKRIndexFuturePriceReturnFactorRepository(
                    ibkr_client=client,
                    factory=self
                ),
    and 

    a property like this :
     @property
    def index_future_price_return_factor_ibkr_repo(self):
        """Get index_future_price_return_factor repository for dependency injection."""
        return self._ibkr_repositories.get('index_future_price_return_factor')


7. it needs a FactorPort like IndexFuturePriceReturnFactorPort in src.domain.ports.factor







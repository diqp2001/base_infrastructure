from sqlalchemy.orm import Session
from src.infrastructure.repositories import Repo

class RepoRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self):
        """Retrieve all Key records from the database."""
        return self.session.query(Repo).all()

    def get_by_id(self, repo_id: int):
        """Retrieve a single Key record by its ID."""
        return self.session.query(Repo).filter(Repo.id == repo_id).first()

    def add(self, name: int):
        """Add a new Key record to the database, ensuring no duplicates."""
        existing_repo = self.session.query(Repo).filter(Repo.name == name).first()
        if existing_repo:
            return existing_repo  # Return the existing key instead of adding a duplicate
        
        new_repo = Repo(name=name)
        self.session.add(new_repo)
        self.session.commit()
        return new_repo

    def update(self, repo_id: int, name: int):
        """Update an existing Key record's name by its ID."""
        repo = self.get_repo_by_id(repo_id)
        if repo:
            repo.name = name
            self.session.commit()
            return repo
        return None

    def delete(self, repo_id: int):
        """Delete a Key record by its ID."""
        repo = self.get_by_id(repo_id)
        if repo:
            self.session.delete(repo)
            self.session.commit()
            return True
        return False
    
    def get_or_create(self, name: str):
        """
        Get or create a repository record by name.
        
        This method follows the established pattern:
        1. Check if repository already exists by name
        2. If not, create new repository
        3. Return the created/found repository
        
        Args:
            name: Repository name
            
        Returns:
            Repo entity or None if creation/retrieval failed
        """
        try:
            # Check if repository already exists by name (same logic as add method)
            existing_repo = self.session.query(Repo).filter(Repo.name == name).first()
            if existing_repo:
                return existing_repo
            
            # Create new repository
            new_repo = Repo(name=name)
            self.session.add(new_repo)
            self.session.commit()
            return new_repo
            
        except Exception as e:
            print(f"Error in get_or_create for repo {name}: {e}")
            self.session.rollback()
            return None
    
    def get_by_name(self, name: str):
        """Get repository by name."""
        return self.session.query(Repo).filter(Repo.name == name).first()
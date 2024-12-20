from sqlalchemy.orm import Session
from src.infrastructure.models.repos.repo import Repo

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
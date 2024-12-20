from sqlalchemy.orm import Session
from src.infrastructure.models.keys.key import Key

class KeyRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self):
        """Retrieve all Key records from the database."""
        return self.session.query(Key).all()

    def get_by_id(self, key_id: int):
        """Retrieve a single Key record by its ID."""
        return self.session.query(Key).filter(Key.id == key_id).first()

    def add(self, name: int):
        """Add a new Key record to the database, ensuring no duplicates."""
        existing_key = self.session.query(Key).filter(Key.name == name).first()
        if existing_key:
            return existing_key  # Return the existing key instead of adding a duplicate
        
        new_key = Key(name=name)
        self.session.add(new_key)
        self.session.commit()
        return new_key

    def update(self, key_id: int, name: int):
        """Update an existing Key record's name by its ID."""
        key = self.get_key_by_id(key_id)
        if key:
            key.name = name
            self.session.commit()
            return key
        return None

    def delete(self, key_id: int):
        """Delete a Key record by its ID."""
        key = self.get_key_by_id(key_id)
        if key:
            self.session.delete(key)
            self.session.commit()
            return True
        return False
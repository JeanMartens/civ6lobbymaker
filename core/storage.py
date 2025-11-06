import json
import os
from typing import Dict, Any, List, Optional

class Storage:
    """Simple JSON-based storage for game data"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data: List[Dict[str, Any]] = []
        self.load()
    
    def load(self) -> None:
        """Load data from JSON file"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.data = []
        else:
            self.data = []
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            self.save()
    
    def save(self) -> None:
        """Save data to JSON file"""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def add(self, item: Dict[str, Any]) -> None:
        """Add a new item to storage"""
        self.data.append(item)
        self.save()
    
    def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get an item by its ID"""
        for item in self.data:
            if item.get("id") == item_id:
                return item
        return None
    
    def update(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """Update an item by its ID"""
        for item in self.data:
            if item.get("id") == item_id:
                item.update(updates)
                self.save()
                return True
        return False
    
    def delete(self, item_id: str) -> bool:
        """Delete an item by its ID"""
        for i, item in enumerate(self.data):
            if item.get("id") == item_id:
                del self.data[i]
                self.save()
                return True
        return False
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all items from storage"""
        return self.data.copy()
    
    def clear(self) -> None:
        """Clear all data from storage"""
        self.data = []
        self.save()

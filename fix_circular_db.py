#!/usr/bin/env python3
"""
Fix circular parent-child relationships in categories table
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'enterprise_wiki_dev.db')

def fix_circular_relationships():
    """Fix circular parent-child relationships"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check for circular relationships
        print("Checking for circular parent-child relationships...")

        # Find all categories
        cursor.execute("SELECT id, name, parent_id FROM categories")
        categories = cursor.fetchall()

        print(f"Found {len(categories)} categories")

        # Build parent map
        parent_map = {cat[0]: cat[2] for cat in categories}

        # Check for cycles
        cycles_found = []
        for cat_id, name, parent_id in categories:
            visited = set()
            current = cat_id
            while current and current not in visited:
                visited.add(current)
                parent = parent_map.get(current)
                if parent == cat_id:  # Self-reference
                    cycles_found.append((cat_id, name, parent_id, "Self-reference"))
                    break
                elif parent in visited:  # Cycle detected
                    cycles_found.append((cat_id, name, parent_id, "Circular reference"))
                    break
                current = parent

        if cycles_found:
            print(f"Found {len(cycles_found)} circular relationships:")
            for cat_id, name, parent_id, issue_type in cycles_found:
                print(f"  - Category {cat_id} ({name}) -> Parent {parent_id} ({issue_type})")

            # Fix by removing parent relationships for problematic categories
            for cat_id, name, parent_id, issue_type in cycles_found:
                print(f"Fixing category {cat_id} ({name}) - removing parent relationship")
                cursor.execute("UPDATE categories SET parent_id = NULL WHERE id = ?", (cat_id,))

            conn.commit()
            print("Fixed circular relationships by setting parent_id to NULL")
        else:
            print("No circular relationships found")

        # Vacuum database to fix any locking issues
        print("Vacuuming database to fix potential locking issues...")
        cursor.execute("VACUUM")
        conn.commit()

        print("Database optimization completed")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    if os.path.exists(db_path):
        fix_circular_relationships()
    else:
        print(f"Database not found at {db_path}")
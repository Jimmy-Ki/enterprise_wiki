#!/usr/bin/env python3
"""
Create test data for the enterprise wiki
"""
import sqlite3
from datetime import datetime

def create_test_data():
    conn = sqlite3.connect('instance/enterprise_wiki_dev.db')
    cursor = conn.cursor()

    try:
        # Create test user if not exists
        cursor.execute('SELECT id FROM users WHERE username = ?', ('testuser',))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (username, email, name, password_hash, is_active, confirmed, member_since, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                'testuser',
                'test@example.com',
                'Test User',
                'pbkdf2:sha256:260000$salt$hash',  # dummy hash
                1,  # is_active
                1,  # confirmed
                datetime.utcnow(),
                datetime.utcnow()
            ))
            print('Test user created')

        # Get test user ID
        cursor.execute('SELECT id FROM users WHERE username = ?', ('testuser',))
        test_user_id = cursor.fetchone()[0]

        # Create test page
        cursor.execute('''
            INSERT INTO pages (title, slug, content, author_id, is_public, is_published, allow_comments, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Test Article',
            'test-article',
            'This is a test article for testing the comment system. You can leave comments below to test the functionality.',
            test_user_id,
            1,  # is_public
            1,  # is_published
            1,  # allow_comments
            datetime.utcnow(),
            datetime.utcnow()
        ))
        print('Test page created')

        # Get page ID
        cursor.execute('SELECT id FROM pages WHERE slug = ?', ('test-article',))
        page_id = cursor.fetchone()[0]

        # Create initial version
        cursor.execute('''
            INSERT INTO page_versions (page_id, title, content, editor_id, change_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            page_id,
            'Test Article',
            'This is a test article for testing the comment system. You can leave comments below to test the functionality.',
            test_user_id,
            'Initial version',
            datetime.utcnow()
        ))
        print('Initial version created')

        # Create another test page
        cursor.execute('''
            INSERT INTO pages (title, slug, content, author_id, is_public, is_published, allow_comments, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Welcome to Enterprise Wiki',
            'welcome',
            '# Welcome to Enterprise Wiki\n\nThis is a collaborative platform for knowledge sharing. Feel free to create pages, add comments, and collaborate with your team.\n\n## Features\n- Rich text editing\n- Comment system with @mentions\n- User profiles\n- And much more!',
            test_user_id,
            1,  # is_public
            1,  # is_published
            1,  # allow_comments
            datetime.utcnow(),
            datetime.utcnow()
        ))
        print('Welcome page created')

        conn.commit()
        print('\nTest data created successfully!')
        print('Test user: testuser / test@example.com')
        print('Test pages:')
        print('- http://localhost:5001/page/test-article')
        print('- http://localhost:5001/page/welcome')

    except Exception as e:
        print(f'Error: {e}')
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    create_test_data()
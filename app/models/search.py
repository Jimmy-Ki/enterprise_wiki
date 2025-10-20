from datetime import datetime
from whoosh.analysis import StandardAnalyzer, StemmingAnalyzer
from whoosh.fields import Schema, ID, TEXT, KEYWORD, DATETIME
from whoosh.index import create_in, open_dir, exists_in
from whoosh.query import And, Or, Term
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.filedb.filestore import FileStorage
import os
from app import db
from .wiki import Page, Category, Attachment

class SearchIndex:
    """Handles full-text search using Whoosh"""

    def __init__(self, index_dir='search_index'):
        self.index_dir = index_dir
        self.analyzer = StemmingAnalyzer()
        self.schema = Schema(
            id=ID(stored=True),
            type=KEYWORD(stored=True),
            title=TEXT(analyzer=self.analyzer, stored=True),
            content=TEXT(analyzer=self.analyzer, stored=True),
            author=TEXT(stored=True),
            category=KEYWORD(stored=True),
            tags=KEYWORD(stored=True),
            created_at=DATETIME(stored=True),
            updated_at=DATETIME(stored=True),
            url=ID(stored=True)
        )

        os.makedirs(index_dir, exist_ok=True)

        if exists_in(index_dir):
            self.index = open_dir(index_dir)
        else:
            self.index = create_in(index_dir, self.schema)

    def add_or_update_document(self, doc_type, doc_id, title, content, author=None,
                              category=None, tags=None, created_at=None, updated_at=None, url=None):
        """Add or update a document in the search index"""
        writer = self.index.writer()

        # Delete existing document if it exists
        writer.delete_by_term('id', f"{doc_type}_{doc_id}")

        # Add new document
        writer.add_document(
            id=f"{doc_type}_{doc_id}",
            type=doc_type,
            title=title,
            content=content,
            author=author or '',
            category=category or '',
            tags=tags or '',
            created_at=created_at or datetime.utcnow(),
            updated_at=updated_at or datetime.utcnow(),
            url=url or ''
        )

        writer.commit()

    def delete_document(self, doc_type, doc_id):
        """Delete a document from the search index"""
        writer = self.index.writer()
        writer.delete_by_term('id', f"{doc_type}_{doc_id}")
        writer.commit()

    def search(self, query_str, page=1, per_page=10, doc_type=None, category=None):
        """Search documents"""
        with self.index.searcher() as searcher:
            # Parse query
            parser = MultifieldParser(['title', 'content'], self.index.schema)
            query = parser.parse(query_str)

            # Add filters
            if doc_type:
                query = And([query, Term('type', doc_type)])
            if category:
                query = And([query, Term('category', category)])

            # Search
            results = searcher.search_page(query, page, pagelen=per_page)

            # Convert to dict format
            search_results = []
            for hit in results:
                doc = hit.fields()
                search_results.append({
                    'id': doc['id'].split('_', 1)[1],  # Remove type prefix
                    'type': doc['type'],
                    'title': doc['title'],
                    'content': doc['content'][:200] + '...' if len(doc['content']) > 200 else doc['content'],
                    'author': doc['author'],
                    'category': doc['category'],
                    'score': hit.score,
                    'url': doc['url'],
                    'created_at': doc['created_at'],
                    'updated_at': doc['updated_at']
                })

            return {
                'results': search_results,
                'total': len(results),
                'page': page,
                'per_page': per_page,
                'query': query_str
            }

    def rebuild_index(self):
        """Rebuild the entire search index"""
        # Clear existing index
        storage = FileStorage(self.index_dir)
        storage.create_index(self.schema)
        self.index = open_dir(self.index_dir)

        # Index all pages
        pages = Page.query.filter_by(is_published=True).all()
        for page in pages:
            content = f"{page.title} {page.content}"
            if page.summary:
                content += f" {page.summary}"

            self.add_or_update_document(
                doc_type='page',
                doc_id=page.id,
                title=page.title,
                content=content,
                author=page.author.username if page.author else '',
                category=page.category.name if page.category else '',
                tags='',  # Could add tags field to Page model
                created_at=page.created_at,
                updated_at=page.updated_at,
                url=f'/wiki/{page.slug}'
            )

        # Index attachments
        attachments = Attachment.query.filter_by(is_public=True).all()
        for attachment in attachments:
            self.add_or_update_document(
                doc_type='attachment',
                doc_id=attachment.id,
                title=attachment.original_filename,
                content=attachment.description or '',
                author=attachment.uploader.username if attachment.uploader else '',
                category='',
                tags='',
                created_at=attachment.uploaded_at,
                updated_at=attachment.uploaded_at,
                url=f'/files/{attachment.filename}'
            )

# Global search index instance
search_index = SearchIndex()

def update_search_index(sender, changes):
    """Update search index when models change"""
    for change in changes:
        obj = change[0]  # Get the object
        operation = change[1]  # 'insert', 'update', or 'delete'

        if isinstance(obj, Page):
            if operation in ['insert', 'update'] and obj.is_published:
                content = f"{obj.title} {obj.content}"
                if obj.summary:
                    content += f" {obj.summary}"

                search_index.add_or_update_document(
                    doc_type='page',
                    doc_id=obj.id,
                    title=obj.title,
                    content=content,
                    author=obj.author.username if obj.author else '',
                    category=obj.category.name if obj.category else '',
                    tags='',
                    created_at=obj.created_at,
                    updated_at=obj.updated_at,
                    url=f'/wiki/{obj.slug}'
                )
            elif operation == 'delete':
                search_index.delete_document('page', obj.id)

        elif isinstance(obj, Attachment):
            if operation in ['insert', 'update'] and obj.is_public:
                search_index.add_or_update_document(
                    doc_type='attachment',
                    doc_id=obj.id,
                    title=obj.original_filename,
                    content=obj.description or '',
                    author=obj.uploader.username if obj.uploader else '',
                    category='',
                    tags='',
                    created_at=obj.uploaded_at,
                    updated_at=obj.uploaded_at,
                    url=f'/files/{obj.filename}'
                )
            elif operation == 'delete':
                search_index.delete_document('attachment', obj.id)
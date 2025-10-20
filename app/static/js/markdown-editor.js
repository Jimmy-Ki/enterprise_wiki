/**
 * Markdown Editor with Real-time Preview
 * Features: syntax highlighting, toolbar, auto-save, preview mode
 */
class MarkdownEditor {
    constructor(textarea, options = {}) {
        this.textarea = textarea;
        this.options = {
            previewUrl: '/preview',
            autoSave: true,
            autoSaveDelay: 5000,
            toolbar: true,
            fullscreen: true,
            ...options
        };

        this.init();
    }

    init() {
        this.createEditor();
        this.createPreview();
        this.createToolbar();
        this.createStatusbar();
        this.bindEvents();
        this.setupAutoSave();
        this.restoreContent();
    }

    createEditor() {
        this.container = document.createElement('div');
        this.container.className = 'markdown-editor-container';

        this.editor = document.createElement('div');
        this.editor.className = 'markdown-editor';

        // Replace textarea with editor
        this.textarea.parentNode.insertBefore(this.container, this.textarea);
        this.container.appendChild(this.textarea);
        this.textarea.style.display = 'none';

        this.editorContainer = document.createElement('div');
        this.editorContainer.className = 'editor-pane';
        this.container.appendChild(this.editorContainer);
    }

    createPreview() {
        this.previewPane = document.createElement('div');
        this.previewPane.className = 'preview-pane';
        this.previewPane.innerHTML = '<div class="preview-content">Preview will appear here...</div>';
        this.container.appendChild(this.previewPane);
    }

    createToolbar() {
        if (!this.options.toolbar) return;

        this.toolbar = document.createElement('div');
        this.toolbar.className = 'markdown-toolbar';

        const buttons = [
            { icon: 'B', title: 'Bold', action: 'bold' },
            { icon: 'I', title: 'Italic', action: 'italic' },
            { icon: 'H', title: 'Heading', action: 'heading' },
            { icon: '"', title: 'Quote', action: 'quote' },
            { icon: 'UL', title: 'Unordered List', action: 'ul' },
            { icon: 'OL', title: 'Ordered List', action: 'ol' },
            { icon: 'LINK', title: 'Link', action: 'link' },
            { icon: 'IMG', title: 'Image', action: 'image' },
            { icon: 'CODE', title: 'Code', action: 'code' },
            { icon: 'TABLE', title: 'Table', action: 'table' },
            { icon: 'HORIZONTAL', title: 'Horizontal Rule', action: 'hr' },
            { icon: 'PREVIEW', title: 'Toggle Preview', action: 'preview' },
            { icon: 'FULLSCREEN', title: 'Toggle Fullscreen', action: 'fullscreen' }
        ];

        buttons.forEach(btn => {
            const button = document.createElement('button');
            button.className = `toolbar-btn toolbar-btn-${btn.action}`;
            button.title = btn.title;
            button.innerHTML = this.getToolbarIcon(btn.icon);
            button.type = 'button';
            button.addEventListener('click', () => this.handleToolbarAction(btn.action));
            this.toolbar.appendChild(button);
        });

        this.editorContainer.insertBefore(this.toolbar, this.editorContainer.firstChild);
    }

    createStatusbar() {
        this.statusbar = document.createElement('div');
        this.statusbar.className = 'markdown-statusbar';

        this.wordCount = document.createElement('span');
        this.wordCount.className = 'word-count';
        this.statusbar.appendChild(this.wordCount);

        this.saveStatus = document.createElement('span');
        this.saveStatus.className = 'save-status';
        this.statusbar.appendChild(this.saveStatus);

        this.container.appendChild(this.statusbar);
    }

    bindEvents() {
        // Editor content changes
        this.textarea.addEventListener('input', () => {
            this.updatePreview();
            this.updateWordCount();
            this.markDirty();
        });

        // Keyboard shortcuts
        this.textarea.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });

        // Window resize
        window.addEventListener('resize', () => {
            this.adjustLayout();
        });

        // Auto-save on blur
        this.textarea.addEventListener('blur', () => {
            if (this.isDirty) {
                this.saveContent();
            }
        });

        // Initialize preview
        this.updatePreview();
        this.updateWordCount();
    }

    setupAutoSave() {
        if (!this.options.autoSave) return;

        this.autoSaveTimer = null;
        this.isDirty = false;
        this.lastSaveTime = localStorage.getItem(`markdown_autosave_${this.getStorageKey()}`);

        setInterval(() => {
            if (this.isDirty) {
                this.saveContent();
            }
        }, this.options.autoSaveDelay);
    }

    handleKeyboardShortcuts(e) {
        if (e.ctrlKey || e.metaKey) {
            switch(e.key) {
                case 'b':
                    e.preventDefault();
                    this.wrapSelection('**', '**');
                    break;
                case 'i':
                    e.preventDefault();
                    this.wrapSelection('*', '*');
                    break;
                case 'k':
                    e.preventDefault();
                    this.insertLink();
                    break;
                case 's':
                    e.preventDefault();
                    this.saveContent();
                    break;
            }
        }

        // Tab handling
        if (e.key === 'Tab') {
            e.preventDefault();
            this.insertTab();
        }
    }

    handleToolbarAction(action) {
        switch(action) {
            case 'bold':
                this.wrapSelection('**', '**');
                break;
            case 'italic':
                this.wrapSelection('*', '*');
                break;
            case 'heading':
                this.insertHeading();
                break;
            case 'quote':
                this.insertPrefix('> ');
                break;
            case 'ul':
                this.insertPrefix('- ');
                break;
            case 'ol':
                this.insertNumberedList();
                break;
            case 'link':
                this.insertLink();
                break;
            case 'image':
                this.insertImage();
                break;
            case 'code':
                this.wrapSelection('`', '`');
                break;
            case 'table':
                this.insertTable();
                break;
            case 'hr':
                this.insertText('\n---\n');
                break;
            case 'preview':
                this.togglePreview();
                break;
            case 'fullscreen':
                this.toggleFullscreen();
                break;
        }
    }

    wrapSelection(prefix, suffix) {
        const start = this.textarea.selectionStart;
        const end = this.textarea.selectionEnd;
        const text = this.textarea.value;
        const selectedText = text.substring(start, end);

        const replacement = prefix + selectedText + suffix;
        this.textarea.value = text.substring(0, start) + replacement + text.substring(end);

        // Restore cursor position
        this.textarea.selectionStart = start + prefix.length;
        this.textarea.selectionEnd = start + prefix.length + selectedText.length;
        this.textarea.focus();

        this.triggerInput();
    }

    insertPrefix(prefix) {
        const start = this.textarea.selectionStart;
        const end = this.textarea.selectionEnd;
        const text = this.textarea.value;
        const lines = text.substring(start, end).split('\n');

        const prefixedLines = lines.map(line => prefix + line);
        const replacement = prefixedLines.join('\n');

        this.textarea.value = text.substring(0, start) + replacement + text.substring(end);
        this.textarea.focus();
        this.triggerInput();
    }

    insertHeading() {
        this.wrapSelection('## ', '');
    }

    insertNumberedList() {
        const start = this.textarea.selectionStart;
        const end = this.textarea.selectionEnd;
        const text = this.textarea.value;
        const lines = text.substring(start, end).split('\n');

        const numberedLines = lines.map((line, index) => `${index + 1}. ${line}`);
        const replacement = numberedLines.join('\n');

        this.textarea.value = text.substring(0, start) + replacement + text.substring(end);
        this.textarea.focus();
        this.triggerInput();
    }

    insertLink() {
        const url = prompt('Enter URL:');
        if (url) {
            const link = `[${this.textarea.value.substring(this.textarea.selectionStart, this.textarea.selectionEnd) || 'Link Text'}](${url})`;
            this.insertText(link);
        }
    }

    insertImage() {
        const url = prompt('Enter image URL:');
        if (url) {
            const alt = prompt('Enter alt text (optional):') || '';
            const image = `![${alt}](${url})`;
            this.insertText(image);
        }
    }

    insertTable() {
        const rows = prompt('Number of rows:', '3');
        const cols = prompt('Number of columns:', '3');

        if (rows && cols) {
            let table = '\n';
            for (let i = 0; i < parseInt(rows); i++) {
                table += '|';
                for (let j = 0; j < parseInt(cols); j++) {
                    table += ` Cell ${i + 1}-${j + 1} |`;
                }
                table += '\n';
                if (i === 0) {
                    table += '|';
                    for (let j = 0; j < parseInt(cols); j++) {
                        table += '---|';
                    }
                    table += '\n';
                }
            }
            table += '\n';
            this.insertText(table);
        }
    }

    insertText(text) {
        const start = this.textarea.selectionStart;
        const end = this.textarea.selectionEnd;
        const value = this.textarea.value;

        this.textarea.value = value.substring(0, start) + text + value.substring(end);
        this.textarea.selectionStart = this.textarea.selectionEnd = start + text.length;
        this.textarea.focus();
        this.triggerInput();
    }

    insertTab() {
        const start = this.textarea.selectionStart;
        const value = this.textarea.value;
        this.textarea.value = value.substring(0, start) + '    ' + value.substring(start);
        this.textarea.selectionStart = this.textarea.selectionEnd = start + 4;
        this.textarea.focus();
        this.triggerInput();
    }

    async updatePreview() {
        const content = this.textarea.value;

        if (this.options.previewUrl) {
            try {
                const response = await fetch(this.options.previewUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify({ content })
                });

                if (response.ok) {
                    const data = await response.json();
                    this.previewPane.querySelector('.preview-content').innerHTML = data.html;
                }
            } catch (error) {
                console.error('Preview error:', error);
                this.fallbackPreview(content);
            }
        } else {
            this.fallbackPreview(content);
        }
    }

    fallbackPreview(content) {
        // Simple markdown to HTML conversion (fallback)
        let html = content
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
            .replace(/\*(.*)\*/gim, '<em>$1</em>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2">$1</a>')
            .replace(/`([^`]+)`/gim, '<code>$1</code>')
            .replace(/\n\n/gim, '</p><p>')
            .replace(/\n/gim, '<br>');

        html = '<p>' + html + '</p>';
        this.previewPane.querySelector('.preview-content').innerHTML = html;
    }

    updateWordCount() {
        const text = this.textarea.value;
        const words = text.trim() ? text.trim().split(/\s+/).length : 0;
        const chars = text.length;
        this.wordCount.textContent = `${words} words, ${chars} characters`;
    }

    togglePreview() {
        this.previewPane.style.display = this.previewPane.style.display === 'none' ? 'block' : 'none';
        this.adjustLayout();
    }

    toggleFullscreen() {
        this.container.classList.toggle('fullscreen');
        document.body.classList.toggle('markdown-editor-fullscreen');
        this.adjustLayout();
    }

    adjustLayout() {
        if (this.previewPane.style.display !== 'none') {
            this.editorContainer.style.width = '50%';
            this.previewPane.style.width = '50%';
        } else {
            this.editorContainer.style.width = '100%';
        }
    }

    markDirty() {
        this.isDirty = true;
        this.saveStatus.textContent = 'Unsaved changes';
        this.saveStatus.className = 'save-status unsaved';
    }

    async saveContent() {
        try {
            // Save to localStorage for auto-save
            localStorage.setItem(`markdown_content_${this.getStorageKey()}`, this.textarea.value);
            localStorage.setItem(`markdown_autosave_${this.getStorageKey()}`, Date.now());

            // Update save status
            this.saveStatus.textContent = `Saved at ${new Date().toLocaleTimeString()}`;
            this.saveStatus.className = 'save-status saved';
            this.isDirty = false;
        } catch (error) {
            console.error('Save error:', error);
            this.saveStatus.textContent = 'Save failed';
            this.saveStatus.className = 'save-status error';
        }
    }

    restoreContent() {
        const savedContent = localStorage.getItem(`markdown_content_${this.getStorageKey()}`);
        if (savedContent && !this.textarea.value.trim()) {
            this.textarea.value = savedContent;
            this.updatePreview();
            this.updateWordCount();
            this.saveStatus.textContent = 'Restored from auto-save';
            this.saveStatus.className = 'save-status restored';
        }
    }

    clearAutoSave() {
        localStorage.removeItem(`markdown_content_${this.getStorageKey()}`);
        localStorage.removeItem(`markdown_autosave_${this.getStorageKey()}`);
    }

    getStorageKey() {
        // Create a unique key based on the page/field
        return window.location.pathname + '_' + this.textarea.name;
    }

    getCSRFToken() {
        const token = document.querySelector('meta[name=csrf-token]');
        return token ? token.getAttribute('content') : '';
    }

    triggerInput() {
        const event = new Event('input', { bubbles: true });
        this.textarea.dispatchEvent(event);
    }

    getToolbarIcon(icon) {
        const icons = {
            'B': '<strong>B</strong>',
            'I': '<em>I</em>',
            'H': 'H₁',
            '"': '❝',
            'UL': '•',
            'OL': '1.',
            'LINK': '🔗',
            'IMG': '🖼',
            'CODE': '</>',
            'TABLE': '⊞',
            'HORIZONTAL': '—',
            'PREVIEW': '👁',
            'FULLSCREEN': '⛶'
        };
        return icons[icon] || icon;
    }
}

// Initialize editor when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const textareas = document.querySelectorAll('.markdown-editor');
    textareas.forEach(textarea => {
        new MarkdownEditor(textarea, {
            previewUrl: '/preview',
            autoSave: true,
            toolbar: true
        });
    });
});

// Export for use in other modules
window.MarkdownEditor = MarkdownEditor;
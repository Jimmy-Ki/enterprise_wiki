/**
 * 评论系统 JavaScript 模块
 * 包含评论CRUD、@提及自动完成、实时更新等功能
 */
class CommentSystem {
    constructor(options = {}) {
        this.options = {
            targetType: options.targetType,
            targetId: options.targetId,
            currentUser: options.currentUser || null,
            apiBaseUrl: options.apiBaseUrl || '',
            enableMentions: options.enableMentions !== false,
            enablePreview: options.enablePreview !== false,
            ...options
        };

        
        this.currentPage = 1;
        this.hasMoreComments = true;
        this.isLoading = false;
        this.mentionCache = new Map();
        this.mentionDebounceTimer = null;

        this.init();
    }

    /**
     * 初始化评论系统
     */
    init() {
        this.bindEvents();
        this.loadComments();
        this.initializeMentionSystem();

        // 定期检查新评论
        if (this.options.autoRefresh) {
            setInterval(() => this.checkNewComments(), 30000);
        }
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 评论表单提交
        $(document).on('submit', '.comment-form', (e) => {
            e.preventDefault();
            this.handleCommentSubmit(e.target);
        });

        // 回复按钮
        $(document).on('click', '.comment-reply-btn', (e) => {
            e.preventDefault();
            this.showReplyForm($(e.currentTarget));
        });

        // 编辑按钮
        $(document).on('click', '.comment-edit-btn', (e) => {
            e.preventDefault();
            this.showEditForm($(e.currentTarget));
        });

        // 删除按钮
        $(document).on('click', '.comment-delete-btn', (e) => {
            e.preventDefault();
            this.confirmDelete($(e.currentTarget));
        });

        // 取消按钮
        $(document).on('click', '.comment-cancel-btn', (e) => {
            e.preventDefault();
            this.cancelAction($(e.currentTarget));
        });

        // 富文本编辑器工具栏按钮
        $(document).on('click', '.toolbar-btn[data-command]', (e) => {
            e.preventDefault();
            this.execCommand($(e.currentTarget).data('command'));
        });

        // 表情符号按钮
        $(document).on('click', '.emoji-picker-btn', (e) => {
            e.preventDefault();
            this.toggleEmojiPicker($(e.currentTarget));
        });

        // 表情符号选择
        $(document).on('click', '.emoji-item', (e) => {
            e.preventDefault();
            this.insertEmoji($(e.currentTarget).text());
        });

        // 表情符号标签页
        $(document).on('click', '.emoji-tab', (e) => {
            e.preventDefault();
            this.switchEmojiTab($(e.currentTarget));
        });

        // 表情符号选择器关闭
        $(document).on('click', '.emoji-picker-close', (e) => {
            e.preventDefault();
            this.hideEmojiPicker();
        });

        // Markdown切换
        $(document).on('click', '.comment-markdown-toggle', (e) => {
            e.preventDefault();
            this.toggleMarkdownMode($(e.currentTarget));
        });

        // 预览切换
        $(document).on('click', '.comment-preview-toggle', (e) => {
            e.preventDefault();
            this.togglePreview($(e.currentTarget));
        });

        // 富文本编辑器输入事件
        $(document).on('input', '.comment-editor', (e) => {
            this.handleEditorInput(e.target);
            this.updateHiddenTextarea(e.target);
            // 自动保存草稿
            this.saveDraft(e.target);
        });

        // 文本区域输入事件（用于@提及）
        $(document).on('input', '.comment-textarea', (e) => {
            this.handleTextareaInput(e.target);
            // 自动保存草稿
            this.saveDraft(e.target);
        });

        // 富文本编辑器键盘事件，处理@标签的整体操作
        $(document).on('keydown', '.comment-editor', (e) => {
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const startContainer = range.startContainer;

                // 检查光标是否在@标签内部或旁边
                let parentElement = startContainer.nodeType === Node.TEXT_NODE
                    ? startContainer.parentElement
                    : startContainer;

                if (parentElement && parentElement.classList.contains('mention')) {
                    // 如果光标在@标签内，阻止输入并移动到标签后面
                    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
                        e.preventDefault();
                        const mentionElement = parentElement;
                        const nextSibling = mentionElement.nextSibling;

                        if (nextSibling && nextSibling.nodeType === Node.TEXT_NODE) {
                            const newRange = document.createRange();
                            newRange.selectNodeContents(nextSibling);
                            newRange.collapse(false);
                            selection.removeAllRanges();
                            selection.addRange(newRange);
                        }
                    }
                }

                // 处理退格键删除@标签
                if (e.key === 'Backspace' && range.collapsed && range.startOffset === 0) {
                    const previousNode = range.startContainer.previousSibling;
                    if (previousNode && previousNode.classList && previousNode.classList.contains('mention')) {
                        e.preventDefault();
                        previousNode.remove();
                        // 触发内容更新
                        $(e.target).trigger('input');
                    }
                }
            }
        });

        // @提及建议点击
        $(document).on('click', '.mention-suggestion', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const $suggestion = $(e.currentTarget);
            const username = $suggestion.data('username');
            console.log('Mention clicked:', username);
            this.selectMention($suggestion);
        });

        // @提及点击跳转用户详情
        $(document).on('click', '.mention', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const $mention = $(e.currentTarget);
            const username = $mention.data('mention') || $mention.text().replace('@', '');
            if (username) {
                console.log('Mention clicked, navigating to user:', username);
                // 跳转到用户详情页面
                window.location.href = `/user/${username}`;
            }
        });

        
        // 分页点击
        $(document).on('click', '.comments-pagination a', (e) => {
            e.preventDefault();
            this.loadPage($(e.currentTarget).data('page'));
        });

        // 全局点击事件（关闭弹出层）
        $(document).on('click', (e) => {
            if (!$(e.target).closest('.emoji-picker, .emoji-picker-btn').length) {
                this.hideEmojiPicker();
            }
            // 包含富文本编辑器、普通textarea、悬浮窗本身和关闭按钮
            if (!$(e.target).closest('.comment-editor, .comment-textarea, #mention-suggestions, .mention-suggestions-close').length) {
                this.hideMentionSuggestions();
            }
        });

        // ESC键取消操作
        $(document).on('keydown', (e) => {
            if (e.key === 'Escape') {
                this.cancelAllActions();
                this.hideEmojiPicker();
                this.hideMentionSuggestions();
            }
        });
    }

    /**
     * 加载评论列表
     */
    async loadComments(page = 1) {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoading();

        try {
            const response = await fetch(`${this.options.apiBaseUrl}/api/comments?target_type=${this.options.targetType}&target_id=${this.options.targetId}&page=${page}&include_replies=true`);

            if (!response.ok) {
                throw new Error('Failed to load comments');
            }

            const data = await response.json();

            if (page === 1) {
                this.renderComments(data.comments);
            } else {
                this.appendComments(data.comments);
            }

            this.updatePagination(data);
            this.currentPage = page;
            this.hasMoreComments = data.has_next;

        } catch (error) {
            console.error('Error loading comments:', error);
            this.showError('Failed to load comments. Please try again.');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }

    /**
     * 渲染评论列表
     */
    renderComments(comments) {
        const container = $('.comments-list');
        container.empty();

        if (comments.length === 0) {
            container.html(this.getEmptyTemplate());
            return;
        }

        comments.forEach(comment => {
            container.append(this.renderComment(comment));
        });
    }

    /**
     * 渲染单个评论
     */
    renderComment(comment, isReply = false) {
        const $comment = $(this.getCommentTemplate(comment, isReply));

        // 如果有回复，渲染回复
        if (comment.replies && comment.replies.length > 0) {
            const $repliesContainer = $('<div class="comment-replies"></div>');
            comment.replies.forEach(reply => {
                $repliesContainer.append(this.renderComment(reply, true));
            });
            $comment.append($repliesContainer);
        }

        return $comment;
    }

    /**
     * 获取评论模板
     */
    getCommentTemplate(comment, isReply = false) {
        const timeAgo = this.formatTimeAgo(new Date(comment.created_at));
        const isAuthor = comment.author.id === this.options.currentUser?.id;
        const editBadge = comment.is_edited ? '<span class="comment-edited">(edited)</span>' : '';

        return `
            <div class="comment-item" data-comment-id="${comment.id}">
                <div class="comment-header">
                    <img src="${comment.author.avatar}" alt="${comment.author.name}" class="comment-avatar">
                    <div class="comment-meta">
                        <a href="/user/${comment.author.username}" class="comment-author ${isAuthor ? 'current-user' : ''}">
                            ${comment.author.name}
                            ${isAuthor ? '<span class="comment-badge">You</span>' : ''}
                        </a>
                        <span class="comment-time">${timeAgo}</span>
                        ${editBadge}
                    </div>
                </div>
                <div class="comment-content">
                    ${this.processMentions(comment.content_html)}
                </div>
                <div class="comment-footer">
                    ${!isReply ? `<button class="comment-reply-btn" data-comment-id="${comment.id}">
                        <i class="fas fa-reply"></i> Reply
                    </button>` : ''}
                    ${isAuthor ? `
                        <button class="comment-edit-btn" data-comment-id="${comment.id}">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button class="comment-delete-btn" data-comment-id="${comment.id}">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * 处理评论提交
     */
    async handleCommentSubmit(form) {
        const $form = $(form);
        const $editor = $form.find('.comment-editor');
        const $textarea = $form.find('.comment-textarea');
        const $submitBtn = $form.find('button[type="submit"]');

        // 获取内容，优先从富文本编辑器获取
        let content = '';
        if ($editor.length > 0) {
            content = $editor.html().trim();
            // 同时更新隐藏的textarea
            $textarea.val(this.htmlToText(content));
        } else {
            content = $textarea.val().trim();
        }

        if (!content || content === '<br>') {
            this.showValidationError($editor.length > 0 ? $editor : $textarea, 'Please enter a comment');
            return;
        }

        const parent_id = $form.data('parent-id');
        const comment_id = $form.data('comment-id'); // 用于编辑

        $submitBtn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Posting...');

        try {
            let response;
            const data = {
                target_type: this.options.targetType,
                target_id: this.options.targetId,
                content: content
            };

            if (comment_id) {
                // 编辑评论
                response = await fetch(`${this.options.apiBaseUrl}/api/comments/${comment_id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
            } else {
                // 创建新评论
                if (parent_id) {
                    data.parent_id = parent_id;
                }
                response = await fetch(`${this.options.apiBaseUrl}/api/comments`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
            }

            if (!response.ok) {
                throw new Error(comment_id ? 'Failed to update comment' : 'Failed to create comment');
            }

            const result = await response.json();

            if (comment_id) {
                this.updateCommentInDOM(result.comment);
                this.showSuccess('Comment updated successfully!');
            } else {
                this.addCommentToDOM(result.comment, parent_id);
                this.showSuccess('Comment posted successfully!');
            }

            // 清空表单
            if ($editor.length > 0) {
                $editor.html('');
                $textarea.val('');
            } else {
                $textarea.val('');
            }
            this.clearDraft($editor.length > 0 ? $editor[0] : $textarea[0]);

            // 移除表单（如果是回复或编辑表单）
            if (parent_id || comment_id) {
                $form.closest('.reply-form, .comment-edit-form').remove();
            }

        } catch (error) {
            console.error('Error submitting comment:', error);
            this.showError('Failed to post comment. Please try again.');
        } finally {
            $submitBtn.prop('disabled', false).html('<i class="fas fa-paper-plane"></i> Post');
        }
    }

    /**
     * 显示回复表单
     */
    showReplyForm($button) {
        const commentId = $button.data('comment-id');
        const $commentItem = $button.closest('.comment-item');

        // 移除现有的回复表单
        $('.reply-form').remove();

        const replyForm = `
            <div class="reply-form">
                <div class="d-flex align-items-start mb-2">
                    <img src="${this.options.currentUser?.avatar || '/static/img/default-avatar.png'}"
                         alt="${this.options.currentUser?.name}"
                         class="comment-avatar me-2">
                    <div class="flex-grow-1">
                        <strong class="text-muted">Replying to ${$commentItem.find('.comment-author').text().trim()}</strong>
                    </div>
                </div>
                <form class="comment-form" data-parent-id="${commentId}">
                    <textarea class="form-control comment-textarea"
                              placeholder="Write a reply..."
                              rows="3"
                              required></textarea>
                    <div class="comment-actions">
                        <button type="button" class="btn btn-outline-secondary btn-sm comment-cancel-btn">
                            Cancel
                        </button>
                        <button type="submit" class="btn btn-primary btn-sm">
                            <i class="fas fa-paper-plane"></i> Reply
                        </button>
                    </div>
                </form>
            </div>
        `;

        $commentItem.find('.comment-replies').append(replyForm);

        // 聚焦到文本区域
        $commentItem.find('.comment-textarea').focus();
    }

    /**
     * 显示编辑表单
     */
    showEditForm($button) {
        const commentId = $button.data('comment-id');
        const $commentItem = $button.closest('.comment-item');
        const $content = $commentItem.find('.comment-content');

        // 移除现有的编辑表单
        $('.comment-edit-form').remove();

        const originalContent = $commentItem.find('.comment-content').data('original-content') ||
                               $content.text().trim();

        const editForm = `
            <div class="comment-edit-form">
                <form class="comment-form" data-comment-id="${commentId}">
                    <textarea class="form-control comment-edit-textarea comment-textarea"
                              rows="4"
                              required>${originalContent}</textarea>
                    <div class="comment-actions">
                        <button type="button" class="btn btn-outline-secondary btn-sm comment-cancel-btn">
                            Cancel
                        </button>
                        <button type="submit" class="btn btn-primary btn-sm">
                            <i class="fas fa-save"></i> Update
                        </button>
                    </div>
                </form>
            </div>
        `;

        $content.after(editForm);
        $content.hide();

        // 聚焦到文本区域
        $commentItem.find('.comment-edit-textarea').focus();
    }

    /**
     * 确认删除评论
     */
    confirmDelete($button) {
        const commentId = $button.data('comment-id');
        const $commentItem = $button.closest('.comment-item');

        // 移除现有的确认对话框
        $('.comment-delete-confirm').remove();

        const confirmDialog = `
            <div class="comment-delete-confirm">
                <div class="comment-delete-text">
                    Are you sure you want to delete this comment? This action cannot be undone.
                </div>
                <div class="d-flex gap-2">
                    <button class="btn btn-outline-secondary btn-sm comment-cancel-btn">
                        Cancel
                    </button>
                    <button class="btn btn-danger btn-sm" data-comment-id="${commentId}">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </div>
        `;

        $commentItem.find('.comment-content').after(confirmDialog);
    }

    /**
     * 删除评论
     */
    async deleteComment(commentId) {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/api/comments/${commentId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Failed to delete comment');
            }

            // 移除评论元素
            $(`.comment-item[data-comment-id="${commentId}"]`).fadeOut(300, function() {
                $(this).remove();
            });

            this.showSuccess('Comment deleted successfully!');

        } catch (error) {
            console.error('Error deleting comment:', error);
            this.showError('Failed to delete comment. Please try again.');
        }
    }

    /**
     * 取消操作
     */
    cancelAction($button) {
        const $form = $button.closest('.reply-form, .comment-edit-form, .comment-delete-confirm');

        if ($form.hasClass('comment-edit-form')) {
            // 显示原始内容
            $form.prev('.comment-content').show();
        }

        $form.remove();
    }

    /**
     * 取消所有操作
     */
    cancelAllActions() {
        $('.reply-form, .comment-edit-form, .comment-delete-confirm').remove();
    }

    /**
     * 初始化@提及系统
     */
    initializeMentionSystem() {
        if (!this.options.enableMentions) return;

        // 创建@提及建议容器
        $('body').append('<div id="mention-suggestions" class="mention-suggestions" style="display: none;"></div>');

        // 全局点击事件（隐藏建议）- 已移至bindEvents方法中

        // 键盘导航
        $(document).on('keydown', '.comment-textarea, .comment-editor', (e) => {
            this.handleMentionKeydown(e);
        });
    }

    /**
     * 处理文本区域输入
     */
    handleTextareaInput(textarea) {
        if (!this.options.enableMentions) return;

        const $textarea = $(textarea);
        let text, cursorPos;

        
        // 判断是富文本编辑器还是普通textarea
        if ($textarea.hasClass('comment-editor')) {
            // 富文本编辑器 - 改进的文本获取逻辑
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);

                // 创建一个新的范围来获取光标前的文本
                const preCaretRange = document.createRange();
                preCaretRange.selectNodeContents($textarea[0]);
                preCaretRange.setEnd(range.endContainer, range.endOffset);

                // 获取纯文本内容
                text = preCaretRange.toString();
                cursorPos = text.length;
            } else {
                // 如果没有选区，获取整个文本内容
                text = $textarea[0].innerText || $textarea.text() || '';
                cursorPos = text.length;
            }
        } else {
            // 普通textarea
            cursorPos = $textarea[0].selectionStart;
            text = $textarea.val();
        }

        // 检查是否正在输入@提及
        const mentionMatch = text.match(/@(\w*)$/);

        if (mentionMatch) {
            const query = mentionMatch[1];
            // 立即显示@提及建议，即使没有输入任何字符
            if (query.length >= 0) {
                this.showMentionSuggestions(query, $textarea);
            }
        } else {
            // 只有在没有@符号时才隐藏，确保用户输入时不会意外关闭
            this.hideMentionSuggestions();
        }
    }

    /**
     * 显示@提及建议
     */
    async showMentionSuggestions(query, $textarea) {
        // 立即显示加载状态
        if (query.length === 0) {
            this.renderMentionLoading($textarea);
        }

        // 防抖，但对于空查询立即执行
        clearTimeout(this.mentionDebounceTimer);
        const delay = query.length === 0 ? 0 : 150;

        this.mentionDebounceTimer = setTimeout(async () => {
            try {
                // 检查缓存
                const cacheKey = query.toLowerCase();
                if (this.mentionCache.has(cacheKey)) {
                    this.renderMentionSuggestions(this.mentionCache.get(cacheKey), $textarea);
                    return;
                }

                const response = await fetch(`${this.options.apiBaseUrl}/api/users/search?q=${encodeURIComponent(query)}&limit=10`);

                if (!response.ok) {
                    throw new Error('Failed to search users');
                }

                const data = await response.json();

                // 缓存结果
                this.mentionCache.set(cacheKey, data.users);

                this.renderMentionSuggestions(data.users, $textarea);

            } catch (error) {
                console.error('Error searching users:', error);
                this.renderMentionError($textarea);
            }
        }, delay);
    }

    /**
     * 渲染@提及加载状态
     */
    renderMentionLoading($textarea) {
        const $suggestions = $('#mention-suggestions');

        const loadingHtml = `
            <div class="mention-loading">
                <div class="mention-loading-spinner"></div>
                <div class="mention-loading-text">输入用户名进行搜索...</div>
            </div>
        `;

        $suggestions.html(loadingHtml);

        // 强制显示加载状态
        $suggestions.css({
            'display': 'block',
            'visibility': 'visible',
            'opacity': '1'
        });

        this.positionMentionSuggestions($textarea);
        this.currentMentionTextarea = $textarea;

            }

    /**
     * 渲染@提及错误状态
     */
    renderMentionError($textarea) {
        const $suggestions = $('#mention-suggestions');

        const errorHtml = `
            <div class="mention-error">
                <div class="mention-error-text">搜索失败，请重试</div>
            </div>
        `;

        $suggestions.html(errorHtml);

        // 强制显示错误状态
        $suggestions.css({
            'display': 'block',
            'visibility': 'visible',
            'opacity': '1'
        });

        this.positionMentionSuggestions($textarea);
        this.currentMentionTextarea = $textarea;

        console.log('Mention error state rendered');
    }

    /**
     * 渲染@提及建议
     */
    renderMentionSuggestions(users, $textarea) {
        const $suggestions = $('#mention-suggestions');

        if (users.length === 0) {
            this.hideMentionSuggestions();
            return;
        }

        const suggestionsHtml = users.map((user, index) => `
            <div class="mention-suggestion ${index === 0 ? 'active' : ''}"
                 data-username="${user.username}">
                @${user.username}
            </div>
        `).join('');

        // 简化的HTML结构
        const html = suggestionsHtml;

        // 先设置内容，然后显示
        $suggestions.html(html);

        // 显示悬浮窗
        $suggestions.css({
            'display': 'block',
            'visibility': 'visible',
            'opacity': '1',
            'z-index': '9999'
        });

        
        // 智能定位建议框
        this.positionMentionSuggestions($textarea);

        this.currentMentionIndex = 0;
        this.currentMentionTextarea = $textarea;

        // 调试：在控制台输出信息
        console.log('Mention suggestions rendered:', users.length, 'users');
        console.log('Suggestions container:', $suggestions[0]);
    }

    /**
     * 智能定位@提及建议框
     */
    positionMentionSuggestions($textarea) {
        const $suggestions = $('#mention-suggestions');
        const textareaRect = $textarea[0].getBoundingClientRect();

        // 获取当前光标位置
        let cursorPosition = { x: 0, y: 0 };

        if ($textarea.hasClass('comment-editor')) {
            // 富文本编辑器：使用选区位置
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const rect = range.getBoundingClientRect();
                if (rect.width > 0 || rect.height > 0) {
                    cursorPosition = {
                        x: rect.left,
                        y: rect.bottom
                    };
                } else {
                    // 如果光标不可见，使用编辑器底部
                    cursorPosition = {
                        x: textareaRect.left,
                        y: textareaRect.bottom
                    };
                }
            } else {
                cursorPosition = {
                    x: textareaRect.left,
                    y: textareaRect.bottom
                };
            }
        } else {
            // 普通textarea：估算光标位置
            cursorPosition = {
                x: textareaRect.left + 10, // 稍微偏移以避免遮挡
                y: textareaRect.bottom
            };
        }

        // 设置建议框的初始位置
        let top = cursorPosition.y + window.scrollY + 5; // 5px 间隙
        let left = cursorPosition.x + window.scrollX;

        // 获取建议框尺寸（先设置为可见以获取正确尺寸）
        $suggestions.css({
            visibility: 'hidden',
            display: 'block',
            top: top,
            left: left
        });

        const suggestionsRect = $suggestions[0].getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const viewportWidth = window.innerWidth;
        const scrollTop = window.scrollY;
        const scrollLeft = window.scrollX;

        // 检查是否超出底部边界
        if (top + suggestionsRect.height > scrollTop + viewportHeight) {
            // 尝试显示在光标上方
            top = cursorPosition.y + window.scrollY - suggestionsRect.height - 5;

            // 如果上方空间仍然不够，则固定在视口顶部
            if (top < scrollTop) {
                top = scrollTop + 10;
            }
        }

        // 检查是否超出右边界
        if (left + suggestionsRect.width > scrollLeft + viewportWidth) {
            // 尝试左对齐
            left = cursorPosition.x + window.scrollX - suggestionsRect.width;

            // 如果仍然超出，则右对齐到视口边缘
            if (left < scrollLeft) {
                left = scrollLeft + viewportWidth - suggestionsRect.width - 10;
            }
        }

        // 检查是否超出左边界
        if (left < scrollLeft) {
            left = scrollLeft + 10;
        }

        // 应用最终位置并显示
        $suggestions.css({
            'visibility': 'visible',
            'display': 'block',
            'top': top + 'px',
            'left': left + 'px',
            'z-index': '9999',
            'opacity': '1'
        });

            }

    /**
     * 隐藏@提及建议
     */
    hideMentionSuggestions(force = false) {
        const $suggestions = $('#mention-suggestions');

        // 检查鼠标是否在建议框内，如果是则不隐藏（除非强制隐藏）
        if (!force && $suggestions.length && $suggestions.is(':visible') &&
            $suggestions.find(':hover').length > 0) {
            return;
        }

        $suggestions.hide();
        // 不清除currentMentionTextarea，这样用户可以继续输入@符号重新触发
        this.currentMentionIndex = 0;
    }

    /**
     * 处理@提及键盘导航
     */
    handleMentionKeydown(e) {
        const $suggestions = $('#mention-suggestions');

        if (!$suggestions.is(':visible')) return;

        const $items = $suggestions.find('.mention-suggestion');

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.currentMentionIndex = Math.min(this.currentMentionIndex + 1, $items.length - 1);
                this.updateMentionSelection($items);
                break;

            case 'ArrowUp':
                e.preventDefault();
                this.currentMentionIndex = Math.max(this.currentMentionIndex - 1, 0);
                this.updateMentionSelection($items);
                break;

            case 'Enter':
            case 'Tab':
                e.preventDefault();
                $items.eq(this.currentMentionIndex).click();
                break;

            case 'Escape':
                e.preventDefault();
                this.hideMentionSuggestions();
                break;
        }
    }

    /**
     * 更新@提及选择
     */
    updateMentionSelection($items) {
        $items.removeClass('active');
        $items.eq(this.currentMentionIndex).addClass('active');
    }

    /**
     * 选择@提及
     */
    selectMention($suggestion) {
        const username = $suggestion.data('username');
        const $textarea = this.currentMentionTextarea;

        console.log('selectMention called:', username, 'textarea:', $textarea ? $textarea.attr('id') : 'null');

        if (!$textarea) {
            console.log('No textarea found');
            return;
        }

        if ($textarea.hasClass('comment-editor')) {
            // 富文本编辑器处理 - 创建整体标签
            const currentContent = $textarea.html();
            console.log('Current editor content:', currentContent);

            // 创建一个整体的@username标签，后面不自动加空格
            const mentionTag = `<span class="mention" contenteditable="false" data-mention="${username}">@${username}</span>`;
            const newContent = currentContent.replace(/@[\w]*\s*$/, mentionTag + ' ');
            console.log('New editor content:', newContent);

            $textarea.html(newContent);

            // 同步到隐藏的textarea
            const $hiddenTextarea = $('#' + $textarea.attr('id').replace('-editor', '-textarea'));
            if ($hiddenTextarea.length) {
                const textContent = currentContent.replace(/@[\w]*\s*$/, `@${username} `);
                $hiddenTextarea.val(textContent);
            }

            // 设置光标到@标签后面的空格位置
            setTimeout(() => {
                $textarea.focus();
                try {
                    const selection = window.getSelection();
                    if (selection.rangeCount > 0) {
                        // 找到最后一个文本节点（空格）
                        const walker = document.createTreeWalker(
                            $textarea[0],
                            NodeFilter.SHOW_TEXT,
                            null,
                            false
                        );

                        let lastTextNode = null;
                        let node;
                        while (node = walker.nextNode()) {
                            if (node.nodeValue.trim() !== '') {
                                lastTextNode = node;
                            }
                        }

                        if (lastTextNode) {
                            const range = document.createRange();
                            range.selectNodeContents(lastTextNode);
                            range.collapse(false);
                            selection.removeAllRanges();
                            selection.addRange(range);
                        } else {
                            // 回退方案：设置到编辑器末尾
                            const range = selection.getRangeAt(0);
                            range.selectNodeContents($textarea[0]);
                            range.collapse(false);
                            selection.removeAllRanges();
                            selection.addRange(range);
                        }
                    }
                } catch (error) {
                    console.log('Error setting cursor:', error);
                    // 回退方案：简单的focus
                    $textarea.focus();
                }
            }, 10);

        } else {
            // 普通textarea处理 - 将@用户名作为整体
            const text = $textarea.val();
            const cursorPos = $textarea[0].selectionStart;
            const textBeforeCursor = text.substring(0, cursorPos);

            console.log('Plain textarea - text before cursor:', textBeforeCursor);
            console.log('Plain textarea - cursor position:', cursorPos);

            // 替换@符号后面的任何字符序列，作为整体替换
            const newText = textBeforeCursor.replace(/@[\w]*\s*$/, '@' + username + ' ') + text.substring(cursorPos);

            console.log('Plain textarea - new text:', newText);
            $textarea.val(newText);

            // 设置光标到正确位置（@username 后面的空格末尾）
            const mentionText = '@' + username + ' ';
            const newCursorPos = textBeforeCursor.replace(/@[\w]*\s*$/, mentionText).length;
            $textarea[0].setSelectionRange(newCursorPos, newCursorPos);
            console.log('Plain textarea - new cursor position:', newCursorPos, 'after mention:', mentionText);
        }

        this.hideMentionSuggestions(true); // 强制隐藏
        $textarea.focus();
    }

    /**
     * 处理@提及内容
     */
    processMentions(content) {
        if (!content) return content;

        // 将@username转换为链接
        return content.replace(/@(\w+)/g, '<a href="/user/$1" class="mention">@$1</a>');
    }

    /**
     * 保存草稿
     */
    saveDraft(textarea) {
        const draftKey = `comment_draft_${this.options.targetType}_${this.options.targetId}`;
        localStorage.setItem(draftKey, textarea.value);
    }

    /**
     * 清除草稿
     */
    clearDraft(textarea) {
        const draftKey = `comment_draft_${this.options.targetType}_${this.options.targetId}`;
        localStorage.removeItem(draftKey);
    }

    /**
     * 加载草稿
     */
    loadDraft(textarea) {
        const draftKey = `comment_draft_${this.options.targetType}_${this.options.targetId}`;
        const draft = localStorage.getItem(draftKey);

        if (draft) {
            textarea.value = draft;
        }
    }

    /**
     * 显示加载状态
     */
    showLoading() {
        $('.comments-list').html(`
            <div class="comments-loading">
                <div class="comments-spinner"></div>
                <div>Loading comments...</div>
            </div>
        `);
    }

    /**
     * 隐藏加载状态
     */
    hideLoading() {
        $('.comments-loading').remove();
    }

    /**
     * 显示错误信息
     */
    showError(message) {
        this.showToast(message, 'danger');
    }

    /**
     * 显示成功信息
     */
    showSuccess(message) {
        this.showToast(message, 'success');
    }

    /**
     * 显示验证错误
     */
    showValidationError($element, message) {
        $element.addClass('is-invalid');

        let $feedback = $element.siblings('.invalid-feedback');
        if ($feedback.length === 0) {
            $feedback = $('<div class="invalid-feedback"></div>');
            $element.after($feedback);
        }

        $feedback.text(message);

        // 移除错误状态
        setTimeout(() => {
            $element.removeClass('is-invalid');
            $feedback.fadeOut();
        }, 3000);
    }

    /**
     * 显示Toast消息
     */
    showToast(message, type = 'info') {
        // 创建toast容器（如果不存在）
        if ($('#toast-container').length === 0) {
            $('body').append('<div id="toast-container" style="position: fixed; top: 20px; right: 20px; z-index: 9999;"></div>');
        }

        const toastId = 'toast_' + Date.now();
        const toast = `
            <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0 mb-2" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;

        $('#toast-container').append(toast);

        const $toastElement = $(`#${toastId}`);
        const toastInstance = new bootstrap.Toast($toastElement[0]);
        toastInstance.show();

        // 自动移除
        setTimeout(() => {
            $toastElement.remove();
        }, 5000);
    }

    /**
     * 获取空状态模板
     */
    getEmptyTemplate() {
        return `
            <div class="comments-empty">
                <div class="comments-empty-icon">
                    <i class="fas fa-comments"></i>
                </div>
                <div class="comments-empty-text">No comments yet</div>
                <div class="comments-empty-subtext">Be the first to share your thoughts!</div>
            </div>
        `;
    }

    /**
     * 格式化时间
     */
    formatTimeAgo(date) {
        const now = new Date();
        const diff = now - date;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 365) {
            const years = Math.floor(days / 365);
            return `${years} year${years !== 1 ? 's' : ''} ago`;
        } else if (days > 0) {
            return `${days} day${days !== 1 ? 's' : ''} ago`;
        } else if (hours > 0) {
            return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
        } else if (minutes > 0) {
            return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
        } else {
            return 'Just now';
        }
    }

    /**
     * 更新分页
     */
    updatePagination(data) {
        const $pagination = $('.comments-pagination');

        if (data.pages <= 1) {
            $pagination.empty();
            return;
        }

        let paginationHtml = '<nav><ul class="pagination pagination-comments">';

        // 上一页
        if (data.has_prev) {
            paginationHtml += `<li class="page-item">
                <a class="page-link" href="#" data-page="${data.current_page - 1}">Previous</a>
            </li>`;
        }

        // 页码
        const startPage = Math.max(1, data.current_page - 2);
        const endPage = Math.min(data.pages, data.current_page + 2);

        if (startPage > 1) {
            paginationHtml += `<li class="page-item">
                <a class="page-link" href="#" data-page="1">1</a>
            </li>`;
            if (startPage > 2) {
                paginationHtml += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            paginationHtml += `<li class="page-item ${i === data.current_page ? 'active' : ''}">
                <a class="page-link" href="#" data-page="${i}">${i}</a>
            </li>`;
        }

        if (endPage < data.pages) {
            if (endPage < data.pages - 1) {
                paginationHtml += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
            paginationHtml += `<li class="page-item">
                <a class="page-link" href="#" data-page="${data.pages}">${data.pages}</a>
            </li>`;
        }

        // 下一页
        if (data.has_next) {
            paginationHtml += `<li class="page-item">
                <a class="page-link" href="#" data-page="${data.current_page + 1}">Next</a>
            </li>`;
        }

        paginationHtml += '</ul></nav>';
        $pagination.html(paginationHtml);
    }

    /**
     * 加载指定页面
     */
    loadPage(page) {
        this.loadComments(page);
    }

    /**
     * 添加评论到DOM
     */
    addCommentToDOM(comment, parentId) {
        const $comment = $(this.renderComment(comment));

        if (parentId) {
            // 回复评论
            const $parentComment = $(`.comment-item[data-comment-id="${parentId}"]`);
            let $repliesContainer = $parentComment.find('.comment-replies');

            if ($repliesContainer.length === 0) {
                $repliesContainer = $('<div class="comment-replies"></div>');
                $parentComment.append($repliesContainer);
            }

            $repliesContainer.append($comment);
        } else {
            // 新评论，添加到顶部
            const $container = $('.comments-list');

            // 如果是空状态，先清空
            if ($container.find('.comments-empty').length > 0) {
                $container.empty();
            }

            $container.prepend($comment);
            $comment.hide().fadeIn(300);
        }
    }

    /**
     * 更新DOM中的评论
     */
    updateCommentInDOM(comment) {
        const $commentItem = $(`.comment-item[data-comment-id="${comment.id}"]`);

        if ($commentItem.length > 0) {
            const $newComment = $(this.renderComment(comment));
            $commentItem.replaceWith($newComment);
        }
    }

    /**
     * 追加评论到列表
     */
    appendComments(comments) {
        const $container = $('.comments-list');

        comments.forEach(comment => {
            $container.append($(this.renderComment(comment)));
        });
    }

    /**
     * 检查新评论
     */
    async checkNewComments() {
        if (this.isLoading) return;

        try {
            const response = await fetch(`${this.options.apiBaseUrl}/api/comments?target_type=${this.options.targetType}&target_id=${this.options.targetId}&page=1&per_page=1`);

            if (!response.ok) return;

            const data = await response.json();

            if (data.comments.length > 0) {
                const latestComment = data.comments[0];
                const $firstComment = $('.comment-item').first();

                if ($firstComment.length === 0 || $firstComment.data('comment-id') !== latestComment.id) {
                    // 有新评论，显示提示
                    this.showNewCommentsNotification();
                }
            }
        } catch (error) {
            console.error('Error checking new comments:', error);
        }
    }

    /**
     * 显示新评论通知
     */
    showNewCommentsNotification() {
        const notification = $(`
            <div class="alert alert-info alert-dismissible fade show position-fixed"
                 style="top: 20px; right: 20px; z-index: 9999; max-width: 300px;"
                 role="alert">
                <strong>New Comment!</strong><br>
                <small>Someone posted a new comment. Click to refresh.</small>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `);

        $('body').append(notification);

        notification.on('click', () => {
            this.loadComments(1);
            notification.alert('close');
        });

        // 自动移除
        setTimeout(() => {
            notification.alert('close');
        }, 10000);
    }

    /**
     * 执行编辑器命令
     */
    execCommand(command) {
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            document.execCommand(command, false, null);
            this.updateHiddenTextarea(document.activeElement);
        }
    }

    /**
     * 切换表情符号选择器
     */
    toggleEmojiPicker($button) {
        const $emojiPicker = $('#emoji-picker');

        if ($emojiPicker.is(':visible')) {
            this.hideEmojiPicker();
        } else {
            this.showEmojiPicker($button);
        }
    }

    /**
     * 显示表情符号选择器
     */
    showEmojiPicker($button) {
        const $emojiPicker = $('#emoji-picker');
        const buttonRect = $button[0].getBoundingClientRect();

        // 如果是第一次显示，加载表情符号数据
        if ($emojiPicker.find('.emoji-grid').is(':empty')) {
            this.loadEmojiData();
        }

        $emojiPicker.css({
            top: buttonRect.bottom + window.scrollY,
            left: Math.max(buttonRect.left + window.scrollX - 150, 10) // 确保不超出屏幕左边界
        }).show();

        // 默认显示第一个标签页
        $emojiPicker.find('.emoji-tab').first().click();
    }

    /**
     * 隐藏表情符号选择器
     */
    hideEmojiPicker() {
        $('#emoji-picker').hide();
    }

    /**
     * 加载表情符号数据
     */
    loadEmojiData() {
        const emojiData = {
            smileys: ['😀', '😁', '😂', '🤣', '😃', '😄', '😅', '😆', '😉', '😊', '😋', '😎', '😍', '😘', '😗', '😙', '😚', '🙂', '🤗', '🤩', '🤔', '🤨', '😐', '😑', '😶', '🙄', '😏', '😣', '😥', '😮', '🤐', '😯', '😪', '😫', '😴', '😌', '😛', '😜', '😝', '🤤', '😒', '😓', '😔', '😕', '🙃', '🤑', '😲', '☹️', '🙁', '😖', '😞', '😟', '😤', '😢', '😭', '😦', '😧', '😨', '😩', '🤯', '😬', '😰', '😱', '🥵', '🥶', '😳', '🥺', '😵', '😡', '😠', '🤬', '😷', '🤒', '🤕', '🤢', '🤮', '🥴', '🤧', '😇', '🤠', '🥳', '🥸'],
            people: ['👶', '👧', '🧒', '👦', '👩', '🧑', '👨', '👱', '👱‍♀️', '👱‍♂️', '🧓', '👴', '👵', '🙍', '🙍‍♀️', '🙍‍♂️', '🙎', '🙎‍♀️', '🙎‍♂️', '🙏', '🙏‍♀️', '🙏‍♂️', '💪', '💪‍♀️', '💪‍♂️', '👋', '👋🏻', '👋🏼', '👋🏽', '👋🏾', '👋🏿', '🤚', '🤚🏻', '🤚🏼', '🤚🏽', '🤚🏾', '🤚🏿', '🖐️', '🖐🏻', '🖐🏼', '🖐🏽', '🖐🏾', '🖐🏿', '✋', '✋🏻', '✋🏼', '✋🏽', '✋🏾', '✋🏿', '🖖', '🖖🏻', '🖖🏼', '🖖🏽', '🖖🏾', '🖖🏿', '👌', '👌🏻', '👌🏼', '👌🏽', '👌🏾', '👌🏿', '🤌', '🤌🏻', '🤌🏼', '🤌🏽', '🤌🏾', '🤌🏿', '🤏', '🤏🏻', '🤏🏼', '🤏🏽', '🤏🏾', '🤏🏿', '✌️', '✌🏻', '✌🏼', '✌🏽', '✌🏾', '✌🏿', '🤞', '🤞🏻', '🤞🏼', '🤞🏽', '🤞🏾', '🤞🏿', '🤟', '🤟🏻', '🤟🏼', '🤟🏽', '🤟🏾', '🤟🏿', '🤘', '🤘🏻', '🤘🏼', '🤘🏽', '🤘🏾', '🤘🏿', '🤙', '🤙🏻', '🤙🏼', '🤙🏽', '🤙🏾', '🤙🏿'],
            animals: ['🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯', '🦁', '🐮', '🐷', '🐽', '🐸', '🐵', '🙈', '🙉', '🙊', '🐒', '🐔', '🐧', '🐦', '🐤', '🐣', '🐥', '🦆', '🦅', '🦉', '🦇', '🐺', '🐗', '🐴', '🦄', '🐝', '🐛', '🦋', '🐌', '🐞', '🐜', '🦟', '🦗', '🕷️', '🕸️', '🦂', '🐢', '🐍', '🦎', '🦖', '🦕', '🐙', '🦑', '🦐', '🦞', '🦀', '🐡', '🐠', '🐟', '🐬', '🐳', '🐋', '🦈', '🐊', '🐅', '🐆', '🦓', '🦍', '🦧', '🐘', '🦛', '🦏', '🐪', '🐫', '🦒', '🦘', '🐃', '🐂', '🐄', '🐎', '🐖', '🐏', '🐑', '🦙', '🐐', '🦌', '🐕', '🐩', '🦮', '🐈', '🐓', '🦃', '🦚', '🦜', '🦢', '🦩', '🕊️', '🐇', '🦝', '🦨', '🦡', '🦦', '🦥', '🐁', '🐀', '🦔'],
            food: ['🍏', '🍎', '🍐', '🍊', '🍋', '🍌', '🍉', '🍇', '🍓', '🍈', '🍒', '🍑', '🥭', '🍍', '🥥', '🥝', '🍅', '🍆', '🥑', '🥦', '🥬', '🥒', '🌶️', '🌽', '🥕', '🥔', '🍠', '🥐', '🍞', '🥖', '🥨', '🧀', '🥚', '🍳', '🥞', '🥓', '🥩', '🍗', '🍖', '🌭', '🍔', '🍟', '🍕', '🥪', '🥙', '🌮', '🌯', '🥗', '🥘', '🥫', '🍝', '🍜', '🍲', '🍛', '🍣', '🍱', '🥟', '🍤', '🍙', '🍚', '🍘', '🍥', '🥠', '🥮', '🍢', '🍡', '🍧', '🍨', '🍦', '🥧', '🧁', '🍰', '🎂', '🍮', '🍭', '🍬', '🍫', '🍿', '🍩', '🍪', '🌰', '🥜', '🍯', '🥛', '🍼', '☕', '🍵', '🥤', '🍶', '🍺', '🍻', '🥂', '🍷', '🥃', '🍸', '🍹', '🍾', '🥃', '🥃'],
            activities: ['⚽', '🏀', '🏈', '⚾', '🥎', '🎾', '🏐', '🏉', '🥏', '🎱', '🏓', '🏸', '🏒', '🏑', '🥍', '🏏', '🥅', '⛳', '🏹', '🎣', '🤿', '🥊', '🥋', '🎽', '🛹', '🛷', '⛸️', '🥌', '🎿', '⛷️', '🏂', '🏋️', '🏋️‍♀️', '🏋️‍♂️', '🤼', '🤼‍♀️', '🤼‍♂️', '🤸', '🤸‍♀️', '🤸‍♂️', '⛹️', '⛹️‍♀️', '⛹️‍♂️', '🤺', '🤾', '🤾‍♀️', '🤾‍♂️', '🏌️', '🏌️‍♀️', '🏌️‍♂️', '🏇', '🧘', '🧘‍♀️', '🧘‍♂️', '🏄', '🏄‍♀️', '🏄‍♂️', '🏊', '🏊‍♀️', '🏊‍♂️', '🤽', '🤽‍♀️', '🤽‍♂️', '🚣', '🚣‍♀️', '🚣‍♂️', '🧗', '🧗‍♀️', '🧗‍♂️', '🚵', '🚵‍♀️', '🚵‍♂️', '🚴', '🚴‍♀️', '🚴‍♂️', '🏆', '🥇', '🥈', '🥉', '🏅', '🎖️', '🏵️', '🎗️', '🎫', '🎟️', '🎪', '🤹', '🤹‍♀️', '🤹‍♂️', '🎭', '🩰', '🎨', '🎬', '🎤', '🎧', '🎼', '🎹', '🥁', '🎷', '🎺', '🎸', '🪕', '🎻', '🎲', '♟️', '🎯', '🎳', '🎮', '🎰', '🧩'],
            travel: ['🚗', '🚕', '🚙', '🚌', '🚎', '🏎️', '🚓', '🚑', '🚒', '🚐', '🛻', '🚚', '🚛', '🚜', '🏍️', '🛵', '🚲', '🛴', '🛹', '🛼', '🚁', '🛸', '🚀', '✈️', '🛩️', '🛫', '🛬', '⛵', '🚤', '🛥️', '🚢', '⚓', '⛽', '🚧', '🚦', '🚥', '🚏', '🗺️', '🗿', '🗽', '🗼', '🏰', '🏯', '🏟️', '🎡', '🎢', '🎠', '⛲', '⛱️', '🏖️', '🏝️', '🏜️', '🌋', '⛰️', '🏔️', '🗻', '🏕️', '⛺', '🏠', '🏡', '🏘️', '🏚️', '🏗️', '🏭', '🏢', '🏬', '🏣', '🏤', '🏥', '🏦', '🏨', '🏪', '🏫', '🏩', '💒', '🏛️', '⛪', '🕌', '🛕', '🕍', '⛩️', '🛤️', '🛣️', '🗾', '🎑', '🏞️', '🌅', '🌄', '🌠', '🎇', '🎆', '🌇', '🌆', '🏙️', '🌃', '🌌', '🌉', '🌁'],
            objects: ['⌚', '📱', '📲', '💻', '⌨️', '🖥️', '🖨️', '🖱️', '🖲️', '🕹️', '🗜️', '💽', '💾', '💿', '📀', '📼', '📷', '📸', '📹', '🎥', '📽️', '🎞️', '📞', '☎️', '📟', '📠', '📺', '📻', '🎙️', '🎚️', '🎛️', '🧭', '⏱️', '⏲️', '⏰', '🕰️', '⏳', '⌛', '📡', '🔋', '🔌', '💡', '🔦', '🕯️', '🪔', '🧯', '🛢️', '💸', '💵', '💴', '💶', '💷', '💰', '💳', '💎', '⚖️', '🧰', '🔧', '🔨', '⚒️', '🛠️', '⛏️', '🔩', '⚙️', '🧱', '⛓️', '🧲', '🔫', '💣', '🧨', '🪓', '🔪', '🗡️', '⚔️', '🛡️', '🚬', '⚰️', '⚱️', '🏺', '🔮', '📿', '🧿', '💈', '⚗️', '🔭', '🔬', '🕳️', '🩹', '🩺', '💊', '💉', '🩸', '🧬', '🦠', '🧫', '🧪', '🌡️', '🧹', '🧺', '🧻', '🚽', '🚰', '🚿', '🛁', '🛀', '🧼', '🪒', '🧽', '🧴', '🛎️', '🔑', '🗝️', '🚪', '🪑', '🛋️', '🛏️', '🛌', '🧸', '🖼️', '🛍️', '🎁', '🎈', '🎏', '🎀', '🎊', '🎉', '🎎', '🏮', '🎐', '🧧', '✉️', '📩', '📨', '📧', '💌', '📥', '📤', '📦', '🏷️', '📪', '📫', '📬', '📭', '📮', '📯', '📜', '📃', '📄', '📑', '🧾', '📊', '📈', '📉', '🗒️', '🗓️', '📆', '📅', '🗑️', '📇', '🗃️', '🗳️', '🗄️', '📋', '📁', '📂', '🗂️', '🗞️', '📰', '📓', '📔', '📒', '📕', '📗', '📘', '📙', '📚', '📖', '🔖', '🧷', '🔗', '📎', '🖇️', '📐', '📏', '🧮', '📌', '📍', '✂️', '🖊️', '🖋️', '✒️', '🖌️', '🖍️', '📝', '✏️', '🔍', '🔎', '🔏', '🔐', '🔒', '🔓'],
            symbols: ['❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '❣️', '💕', '💞', '💓', '💗', '💖', '💘', '💝', '👍', '👍🏻', '👍🏼', '👍🏽', '👍🏾', '👍🏿', '👎', '👎🏻', '👎🏼', '👎🏽', '👎🏾', '👎🏿', '👌', '👌🏻', '👌🏼', '👌🏽', '👌🏾', '👌🏿', '✌️', '✌🏻', '✌🏼', '✌🏽', '✌🏾', '✌🏿', '🤞', '🤞🏻', '🤞🏼', '🤞🏽', '🤞🏾', '🤞🏿', '🤟', '🤟🏻', '🤟🏼', '🤟🏽', '🤟🏾', '🤟🏿', '🤘', '🤘🏻', '🤘🏼', '🤘🏽', '🤘🏾', '🤘🏿', '🤙', '🤙🏻', '🤙🏼', '🤙🏽', '🤙🏾', '🤙🏿', '👈', '👈🏻', '👈🏼', '👈🏽', '👈🏾', '👈🏿', '👉', '👉🏻', '👉🏼', '👉🏽', '👉🏾', '👉🏿', '👆', '👆🏻', '👆🏼', '👆🏽', '👆🏾', '👆🏿', '👇', '👇🏻', '👇🏼', '👇🏽', '👇🏾', '👇🏿', '☝️', '☝🏻', '☝🏼', '☝🏽', '☝🏾', '☝🏿', '✋', '✋🏻', '✋🏼', '✋🏽', '✋🏾', '✋🏿', '🤚', '🤚🏻', '🤚🏼', '🤚🏽', '🤚🏾', '🤚🏿', '🖐️', '🖐🏻', '🖐🏼', '🖐🏽', '🖐🏾', '🖐🏿', '🖖', '🖖🏻', '🖖🏼', '🖖🏽', '🖖🏾', '🖖🏿', '👋', '👋🏻', '👋🏼', '👋🏽', '👋🏾', '👋🏿', '🤝', '🙏', '🙏🏻', '🙏🏼', '🙏🏽', '🙏🏾', '🙏🏿', '💪', '💪🏻', '💪🏼', '💪🏽', '💪🏾', '💪🏿', '✍️', '✍🏻', '✍🏼', '✍🏽', '✍🏾', '✍🏿', '🧠', '🫀', '🫁', '🦷', '🦴', '👀', '👁️', '👅', '👄', '👶', '🧒', '👦', '👧', '🧑', '👱', '👨', '🧔', '👩', '🧓', '👴', '👵', '🙍', '🙍🏻', '🙍🏼', '🙍🏽', '🙍🏾', '🙍🏿', '🙎', '🙎🏻', '🙎🏼', '🙎🏽', '🙎🏾', '🙎🏿', '🙅', '🙅🏻', '🙅🏼', '🙅🏽', '🙅🏾', '🙅🏿', '🙆', '🙆🏻', '🙆🏼', '🙆🏽', '🙆🏾', '🙆🏿', '💁', '💁🏻', '💁🏼', '💁🏽', '💁🏾', '💁🏿', '🙋', '🙋🏻', '🙋🏼', '🙋🏽', '🙋🏾', '🙋🏿', '🧏', '🧏🏻', '🧏🏼', '🧏🏽', '🧏🏾', '🧏🏿', '🙇', '🙇🏻', '🙇🏼', '🙇🏽', '🙇🏾', '🙇🏿', '🤦', '🤦🏻', '🤦🏼', '🤦🏽', '🤦🏾', '🤦🏿', '🤷', '🤷🏻', '🤷🏼', '🤷🏽', '🤷🏾', '🤷🏿', '👨‍⚕️', '👩‍⚕️', '👨‍🎓', '👩‍🎓', '👨‍🏫', '👩‍🏫', '👨‍⚖️', '👩‍⚖️', '👨‍🌾', '👩‍🌾', '👨‍🍳', '👩‍🍳', '👨‍🔧', '👩‍🔧', '👨‍🏭', '👩‍🏭', '👨‍💼', '👩‍💼', '👨‍🔬', '👩‍🔬', '👨‍💻', '👩‍💻', '👨‍🎤', '👩‍🎤', '👨‍🎨', '👩‍🎨', '👨‍✈️', '👩‍✈️', '👨‍🚀', '👩‍🚀', '👨‍🚒', '👩‍🚒', '👮', '👮🏻', '👮🏼', '👮🏽', '👮🏾', '👮🏿', '🕵️', '🕵️‍♀️', '🕵️‍♂️', '💂', '💂🏻', '💂🏼', '💂🏽', '💂🏾', '💂🏿', '👷', '👷🏻', '👷🏼', '👷🏽', '👷🏾', '👷🏿', '🤴', '🤴🏻', '🤴🏼', '🤴🏽', '🤴🏾', '🤴🏿', '👸', '👸🏻', '👸🏼', '👸🏽', '👸🏾', '👸🏿', '👳', '👳🏻', '👳🏼', '👳🏽', '👳🏾', '👳🏿', '👲', '🧕', '🧕🏻', '🧕🏼', '🧕🏽', '🧕🏾', '🧕🏿', '🤵', '🤵🏻', '🤵🏼', '🤵🏽', '🤵🏾', '🤵🏿', '👰', '👰🏻', '👰🏼', '👰🏽', '👰🏾', '👰🏿', '🤰', '🤰🏻', '🤰🏼', '🤰🏽', '🤰🏾', '🤰🏿', '🤱', '🤱🏻', '🤱🏼', '🤱🏽', '🤱🏾', '🤱🏿', '👼', '👼🏻', '👼🏼', '👼🏽', '👼🏾', '👼🏿', '🎅', '🎅🏻', '🎅🏼', '🎅🏽', '🎅🏾', '🎅🏿', '🤶', '🤶🏻', '🤶🏼', '🤶🏽', '🤶🏾', '🤶🏿', '🦸', '🦸🏻', '🦸🏼', '🦸🏽', '🦸🏾', '🦸🏿', '🦸‍♀️', '🦸‍♀️🏻', '🦸‍♀️🏼', '🦸‍♀️🏽', '🦸‍♀️🏾', '🦸‍♀️🏿', '🦸‍♂️', '🦸‍♂️🏻', '🦸‍♂️🏼', '🦸‍♂️🏽', '🦸‍♂️🏾', '🦸‍♂️🏿', '🦹', '🦹🏻', '🦹🏼', '🦹🏽', '🦹🏾', '🦹🏿', '🦹‍♀️', '🦹‍♀️🏻', '🦹‍♀️🏼', '🦹‍♀️🏽', '🦹‍♀️🏾', '🦹‍♀️🏿', '🦹‍♂️', '🦹‍♂️🏻', '🦹‍♂️🏼', '🦹‍♂️🏽', '🦹‍♂️🏾', '🦹‍♂️🏿', '🧙', '🧙🏻', '🧙🏼', '🧙🏽', '🧙🏾', '🧙🏿', '🧙‍♀️', '🧙‍♀️🏻', '🧙‍♀️🏼', '🧙‍♀️🏽', '🧙‍♀️🏾', '🧙‍♀️🏿', '🧙‍♂️', '🧙‍♂️🏻', '🧙‍♂️🏼', '🧙‍♂️🏽', '🧙‍♂️🏾', '🧙‍♂️🏿', '🧚', '🧚🏻', '🧚🏼', '🧚🏽', '🧚🏾', '🧚🏿', '🧚‍♀️', '🧚‍♀️🏻', '🧚‍♀️🏼', '🧚‍♀️🏽', '🧚‍♀️🏾', '🧚‍♀️🏿', '🧚‍♂️', '🧚‍♂️🏻', '🧚‍♂️🏼', '🧚‍♂️🏽', '🧚‍♂️🏾', '🧚‍♂️🏿', '🧛', '🧛🏻', '🧛🏼', '🧛🏽', '🧛🏾', '🧛🏿', '🧛‍♀️', '🧛‍♀️🏻', '🧛‍♀️🏼', '🧛‍♀️🏽', '🧛‍♀️🏾', '🧛‍♀️🏿', '🧛‍♂️', '🧛‍♂️🏻', '🧛‍♂️🏼', '🧛‍♂️🏽', '🧛‍♂️🏾', '🧛‍♂️🏿', '🧜', '🧜🏻', '🧜🏼', '🧜🏽', '🧜🏾', '🧜🏿', '🧜‍♀️', '🧜‍♀️🏻', '🧜‍♀️🏼', '🧜‍♀️🏽', '🧜‍♀️🏾', '🧜‍♀️🏿', '🧜‍♂️', '🧜‍♂️🏻', '🧜‍♂️🏼', '🧜‍♂️🏽', '🧜‍♂️🏾', '🧜‍♂️🏿', '🧝', '🧝🏻', '🧝🏼', '🧝🏽', '🧝🏾', '🧝🏿', '🧝‍♀️', '🧝‍♀️🏻', '🧝‍♀️🏼', '🧝‍♀️🏽', '🧝‍♀️🏾', '🧝‍♀️🏿', '🧝‍♂️', '🧝‍♂️🏻', '🧝‍♂️🏼', '🧝‍♂️🏽', '🧝‍♂️🏾', '🧝‍♂️🏿', '🧞', '🧞🏻', '🧞🏼', '🧞🏽', '🧞🏾', '🧞🏿', '🧞‍♀️', '🧞‍♀️🏻', '🧞‍♀️🏼', '🧞‍♀️🏽', '🧞‍♀️🏾', '🧞‍♀️🏿', '🧞‍♂️', '🧞‍♂️🏻', '🧞‍♂️🏼', '🧞‍♂️🏽', '🧞‍♂️🏾', '🧞‍♂️🏿', '🧟', '🧟🏻', '🧟🏼', '🧟🏽', '🧟🏾', '🧟🏿', '🧟‍♀️', '🧟‍♀️🏻', '🧟‍♀️🏼', '🧟‍♀️🏽', '🧟‍♀️🏾', '🧟‍♀️🏿', '🧟‍♂️', '🧟‍♂️🏻', '🧟‍♂️🏼', '🧟‍♂️🏽', '🧟‍♂️🏾', '🧟‍♂️🏿', '💀', '👻', '👽', '👾', '🤖', '🎃', '😺', '😸', '😹', '😻', '😼', '😽', '🙀', '😿', '😾'],
            flags: ['🏁', '🚩', '🎌', '🏴', '🏳️', '🏳️‍🌈', '🏳️‍⚧️', '🏴‍☠️', '🇦🇨', '🇦🇩', '🇦🇪', '🇦🇫', '🇦🇬', '🇦🇮', '🇦🇱', '🇦🇲', '🇦🇴', '🇦🇶', '🇦🇷', '🇦🇸', '🇦🇹', '🇦🇺', '🇦🇼', '🇦🇽', '🇦🇿', '🇧🇦', '🇧🇧', '🇧🇩', '🇧🇪', '🇧🇫', '🇧🇬', '🇧🇭', '🇧🇮', '🇧🇯', '🇧🇱', '🇧🇲', '🇧🇳', '🇧🇴', '🇧🇶', '🇧🇷', '🇧🇸', '🇧🇹', '🇧🇻', '🇧🇼', '🇧🇾', '🇧🇿', '🇨🇦', '🇨🇨', '🇨🇩', '🇨🇫', '🇨🇬', '🇨🇭', '🇨🇮', '🇨🇰', '🇨🇱', '🇨🇲', '🇨🇳', '🇨🇴', '🇨🇵', '🇨🇷', '🇨🇺', '🇨🇻', '🇨🇼', '🇨🇽', '🇨🇾', '🇨🇿', '🇩🇪', '🇩🇬', '🇩🇯', '🇩🇰', '🇩🇲', '🇩🇴', '🇩🇿', '🇪🇦', '🇪🇨', '🇪🇪', '🇪🇬', '🇪🇭', '🇪🇷', '🇪🇸', '🇪🇹', '🇪🇺', '🇫🇮', '🇫🇯', '🇫🇰', '🇫🇲', '🇫🇴', '🇫🇷', '🇬🇦', '🇬🇧', '🇬🇩', '🇬🇪', '🇬🇫', '🇬🇬', '🇬🇭', '🇬🇮', '🇬🇱', '🇬🇲', '🇬🇳', '🇬🇵', '🇬🇶', '🇬🇷', '🇬🇸', '🇬🇹', '🇬🇺', '🇬🇼', '🇬🇾', '🇭🇰', '🇭🇲', '🇭🇳', '🇭🇷', '🇭🇹', '🇭🇺', '🇮🇨', '🇮🇩', '🇮🇪', '🇮🇱', '🇮🇲', '🇮🇳', '🇮🇴', '🇮🇶', '🇮🇷', '🇮🇸', '🇮🇹', '🇯🇪', '🇯🇲', '🇯🇴', '🇯🇵', '🇰🇪', '🇰🇬', '🇰🇭', '🇰🇮', '🇰🇲', '🇰🇳', '🇰🇵', '🇰🇷', '🇰🇼', '🇰🇾', '🇰🇿', '🇱🇦', '🇱🇧', '🇱🇨', '🇱🇮', '🇱🇰', '🇱🇷', '🇱🇸', '🇱🇹', '🇱🇺', '🇱🇻', '🇱🇾', '🇲🇦', '🇲🇨', '🇲🇩', '🇲🇪', '🇲🇫', '🇲🇬', '🇲🇭', '🇲🇰', '🇲🇱', '🇲🇲', '🇲🇳', '🇲🇴', '🇲🇵', '🇲🇶', '🇲🇷', '🇲🇸', '🇲🇹', '🇲🇺', '🇲🇻', '🇲🇼', '🇲🇽', '🇲🇾', '🇲🇿', '🇳🇦', '🇳🇨', '🇳🇪', '🇳🇫', '🇳🇬', '🇳🇮', '🇳🇱', '🇳🇴', '🇳🇵', '🇳🇷', '🇳🇺', '🇳🇿', '🇴🇲', '🇵🇦', '🇵🇪', '🇵🇫', '🇵🇬', '🇵🇭', '🇵🇰', '🇵🇱', '🇵🇲', '🇵🇳', '🇵🇷', '🇵🇸', '🇵🇹', '🇵🇼', '🇵🇾', '🇶🇦', '🇷🇪', '🇷🇴', '🇷🇸', '🇷🇺', '🇷🇼', '🇸🇦', '🇸🇧', '🇸🇨', '🇸🇩', '🇸🇪', '🇸🇬', '🇸🇭', '🇸🇮', '🇸🇯', '🇸🇰', '🇸🇱', '🇸🇲', '🇸🇳', '🇸🇴', '🇸🇷', '🇸🇸', '🇸🇹', '🇸🇻', '🇸🇽', '🇸🇾', '🇸🇿', '🇹🇦', '🇹🇨', '🇹🇩', '🇹🇫', '🇹🇬', '🇹🇭', '🇹🇯', '🇹🇰', '🇹🇱', '🇹🇲', '🇹🇳', '🇹🇴', '🇹🇷', '🇹🇹', '🇹🇻', '🇹🇼', '🇹🇿', '🇺🇦', '🇺🇬', '🇺🇲', '🇺🇸', '🇺🇾', '🇺🇿', '🇻🇦', '🇻🇨', '🇻🇪', '🇻🇬', '🇻🇮', '🇻🇳', '🇻🇺', '🇼🇫', '🇪🇭', '🇪🇺', '🇫🇷', '🇬🇧', '🇬🇬', '🇮🇹', '🇯🇵', '🇰🇷', '🇨🇳', '🇷🇺', '🇺🇸']
        };

        let firstCategory = true;
        for (const [category, emojis] of Object.entries(emojiData)) {
            const $tab = $(`.emoji-tab[data-category="${category}"]`);
            const $grid = $(`<div class="emoji-grid" data-category="${category}" style="display: ${firstCategory ? 'grid' : 'none'};"></div>`);

            emojis.forEach(emoji => {
                $grid.append(`<div class="emoji-item">${emoji}</div>`);
            });

            $('#emoji-picker .emoji-picker-content').append($grid);
            firstCategory = false;
        }
    }

    /**
     * 切换表情符号标签页
     */
    switchEmojiTab($tab) {
        const category = $tab.data('category');

        // 更新标签页状态
        $('#emoji-picker .emoji-tab').removeClass('active');
        $tab.addClass('active');

        // 显示对应的表情符号网格
        $('#emoji-picker .emoji-grid').hide();
        $(`#emoji-picker .emoji-grid[data-category="${category}"]`).show();
    }

    /**
     * 插入表情符号
     */
    insertEmoji(emoji) {
        const $activeEditor = $('.comment-editor:focus');
        if ($activeEditor.length === 0) return;

        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const textNode = document.createTextNode(emoji);
            range.insertNode(textNode);
            range.setStartAfter(textNode);
            range.setEndAfter(textNode);
            selection.removeAllRanges();
            selection.addRange(range);
        } else {
            $activeEditor.append(emoji);
        }

        this.updateHiddenTextarea($activeEditor[0]);
        $activeEditor.focus();
    }

    /**
     * 切换Markdown模式
     */
    toggleMarkdownMode($button) {
        $button.toggleClass('active');
        const isMarkdown = $button.hasClass('active');

        // 这里可以添加Markdown模式的逻辑
        if (isMarkdown) {
            this.showSuccess('Markdown mode enabled');
        } else {
            this.showSuccess('Rich text mode enabled');
        }
    }

    /**
     * 切换预览
     */
    togglePreview($button) {
        const $preview = $('#main-comment-preview');
        const $editor = $('#main-comment-editor');
        const $textarea = $('#main-comment-textarea');

        if ($preview.is(':visible')) {
            $preview.hide();
            $editor.show();
            $button.html('<i class="fas fa-eye me-1"></i>Preview');
        } else {
            const content = $editor.html() || $textarea.val();
            const previewContent = this.markdownToHtml(content);
            $('#main-comment-preview-content').html(previewContent);
            $preview.show();
            $editor.hide();
            $button.html('<i class="fas fa-edit me-1"></i>Edit');
        }
    }

    /**
     * 处理富文本编辑器输入
     */
    handleEditorInput(editor) {
        // 处理@提及
        this.handleTextareaInput(editor);

        // 检查空状态
        const content = editor.innerHTML.trim();
        if (content === '' || content === '<br>') {
            editor.setAttribute('data-placeholder', editor.getAttribute('data-placeholder'));
        } else {
            editor.removeAttribute('data-placeholder');
        }
    }

    /**
     * 更新隐藏的textarea
     */
    updateHiddenTextarea(editor) {
        const $editor = $(editor);
        const $textarea = $editor.closest('.comment-form').find('.comment-textarea');
        if ($textarea.length > 0) {
            $textarea.val(this.htmlToText($editor.html()));
        }
    }

    /**
     * HTML转纯文本
     */
    htmlToText(html) {
        const temp = document.createElement('div');
        temp.innerHTML = html;

        // 处理@提及标签，将标签转换为纯文本格式
        const mentionElements = temp.querySelectorAll('.mention[data-mention]');
        mentionElements.forEach(element => {
            const username = element.getAttribute('data-mention');
            if (username) {
                element.textContent = `@${username}`;
            }
        });

        return temp.textContent || temp.innerText || '';
    }

    /**
     * Markdown转HTML
     */
    markdownToHtml(markdown) {
        if (!markdown) return '';

        return markdown
            // 粗体
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // 斜体
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // 代码块
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            // 行内代码
            .replace(/`(.*?)`/g, '<code>$1</code>')
            // 链接
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
            // 标题
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            // 列表
            .replace(/^\* (.+)$/gim, '<li>$1</li>')
            .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
            // 换行
            .replace(/\n/g, '<br>');
    }
}

// 全局函数，用于初始化评论系统
window.initCommentSystem = function(options) {
    return new CommentSystem(options);
};

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CommentSystem;
}
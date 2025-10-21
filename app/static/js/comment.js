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

        // 文本区域输入事件（用于@提及）
        $(document).on('input', '.comment-textarea', (e) => {
            this.handleTextareaInput(e.target);

            // 自动保存草稿
            this.saveDraft(e.target);
        });

        // 预览切换
        $(document).on('click', '.comment-preview-toggle', (e) => {
            e.preventDefault();
            this.togglePreview($(e.currentTarget));
        });

        // @提及建议点击
        $(document).on('click', '.mention-suggestion', (e) => {
            e.preventDefault();
            this.selectMention($(e.currentTarget));
        });

        // 分页点击
        $(document).on('click', '.comments-pagination a', (e) => {
            e.preventDefault();
            this.loadPage($(e.currentTarget).data('page'));
        });

        // ESC键取消操作
        $(document).on('keydown', (e) => {
            if (e.key === 'Escape') {
                this.cancelAllActions();
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
        const $textarea = $form.find('.comment-textarea');
        const $submitBtn = $form.find('button[type="submit"]');
        const content = $textarea.val().trim();

        if (!content) {
            this.showValidationError($textarea, 'Please enter a comment');
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
            $textarea.val('');
            this.clearDraft($textarea[0]);

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

        // 全局点击事件（隐藏建议）
        $(document).on('click', (e) => {
            if (!$(e.target).closest('.comment-textarea, #mention-suggestions').length) {
                this.hideMentionSuggestions();
            }
        });

        // 键盘导航
        $(document).on('keydown', '.comment-textarea', (e) => {
            this.handleMentionKeydown(e);
        });
    }

    /**
     * 处理文本区域输入
     */
    handleTextareaInput(textarea) {
        if (!this.options.enableMentions) return;

        const $textarea = $(textarea);
        const cursorPos = $textarea[0].selectionStart;
        const text = $textarea.val();
        const textBeforeCursor = text.substring(0, cursorPos);

        // 检查是否正在输入@提及
        const mentionMatch = textBeforeCursor.match(/@(\w*)$/);

        if (mentionMatch) {
            const query = mentionMatch[1];
            if (query.length >= 2) {
                this.showMentionSuggestions(query, $textarea);
            } else {
                this.hideMentionSuggestions();
            }
        } else {
            this.hideMentionSuggestions();
        }
    }

    /**
     * 显示@提及建议
     */
    async showMentionSuggestions(query, $textarea) {
        // 防抖
        clearTimeout(this.mentionDebounceTimer);
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
                this.hideMentionSuggestions();
            }
        }, 200);
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

        const html = users.map((user, index) => `
            <div class="mention-suggestion ${index === 0 ? 'active' : ''}"
                 data-username="${user.username}"
                 data-name="${user.name}"
                 data-email="${user.email}">
                <img src="${user.avatar}" alt="${user.name}" class="mention-suggestion-avatar">
                <div class="mention-suggestion-info">
                    <div class="mention-suggestion-name">${user.name}</div>
                    <div class="mention-suggestion-username">@${user.username}</div>
                    <div class="mention-suggestion-email">${user.email}</div>
                </div>
            </div>
        `).join('');

        $suggestions.html(html).show();

        // 定位建议框
        const textareaRect = $textarea[0].getBoundingClientRect();
        $suggestions.css({
            top: textareaRect.bottom + window.scrollY,
            left: textareaRect.left + window.scrollX
        });

        this.currentMentionIndex = 0;
        this.currentMentionTextarea = $textarea;
    }

    /**
     * 隐藏@提及建议
     */
    hideMentionSuggestions() {
        $('#mention-suggestions').hide();
        this.currentMentionTextarea = null;
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

        if (!$textarea) return;

        const text = $textarea.val();
        const cursorPos = $textarea[0].selectionStart;
        const textBeforeCursor = text.substring(0, cursorPos);

        // 替换@user部分
        const newText = textBeforeCursor.replace(/@\w*$/, '@' + username) + text.substring(cursorPos);

        $textarea.val(newText);

        // 设置光标位置
        const newCursorPos = textBeforeCursor.replace(/@\w*$/, '@' + username).length;
        $textarea[0].setSelectionRange(newCursorPos, newCursorPos);

        this.hideMentionSuggestions();
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
}

// 全局函数，用于初始化评论系统
window.initCommentSystem = function(options) {
    return new CommentSystem(options);
};

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CommentSystem;
}
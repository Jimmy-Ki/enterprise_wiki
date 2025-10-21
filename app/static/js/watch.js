/**
 * Watch功能JavaScript模块
 * 处理页面/分类关注和通知功能
 */

class WatchManager {
    constructor() {
        this.unreadCount = 0;
        this.notifications = [];
        this.watchStatus = new Map(); // 缓存watch状态
        this.init();
    }

    init() {
        this.updateUnreadCount();
        this.setupEventListeners();

        // 每30秒检查一次新通知
        setInterval(() => {
            this.updateUnreadCount();
        }, 30000);
    }

    setupEventListeners() {
        // Watch按钮点击事件
        document.addEventListener('click', (e) => {
            if (e.target.matches('.watch-btn')) {
                e.preventDefault();
                this.handleWatchToggle(e.target);
            }
        });

        // 通知相关事件
        document.addEventListener('click', (e) => {
            if (e.target.matches('.notification-item')) {
                this.handleNotificationClick(e.target);
            }
            if (e.target.matches('.mark-all-read-btn')) {
                e.preventDefault();
                this.markAllAsRead();
            }
            if (e.target.matches('.mark-read-btn')) {
                e.preventDefault();
                const notificationId = e.target.dataset.notificationId;
                this.markAsRead(notificationId);
            }
        });
    }

    // Watch功能
    async handleWatchToggle(button) {
        const targetType = button.dataset.targetType;
        const targetId = button.dataset.targetId;

        if (!targetType || !targetId) {
            console.error('Missing target type or ID');
            return;
        }

        // 检查当前状态
        const isCurrentlyWatching = button.classList.contains('watching');

        try {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            const response = await fetch('/api/watch/toggle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    target_type: targetType,
                    target_id: parseInt(targetId),
                    events: this.getDefaultEvents(targetType)
                })
            });

            const data = await response.json();

            if (data.success) {
                this.updateWatchButton(button, !isCurrentlyWatching);
                this.watchStatus.set(`${targetType}-${targetId}`, data.watch);

                // 显示提示信息
                this.showToast(
                    isCurrentlyWatching ? '已取消关注' : '关注成功',
                    isCurrentlyWatching ? 'info' : 'success'
                );
            } else {
                throw new Error(data.error || '操作失败');
            }
        } catch (error) {
            console.error('Watch toggle error:', error);
            this.showToast('操作失败，请稍后重试', 'error');
        } finally {
            button.disabled = false;
        }
    }

    updateWatchButton(button, isWatching) {
        if (isWatching) {
            button.classList.add('watching');
            button.classList.remove('btn-outline-primary');
            button.classList.add('btn-primary');
            button.innerHTML = '<i class="fas fa-eye-slash"></i> 取消关注';
        } else {
            button.classList.remove('watching');
            button.classList.add('btn-outline-primary');
            button.classList.remove('btn-primary');
            button.innerHTML = '<i class="fas fa-eye"></i> 关注';
        }
    }

    getDefaultEvents(targetType) {
        if (targetType === 'page') {
            return ['page_updated', 'page_deleted', 'attachment_added', 'attachment_removed'];
        } else if (targetType === 'category') {
            return ['page_created', 'page_updated', 'page_deleted', 'category_updated'];
        }
        return [];
    }

    // 通知功能
    async updateUnreadCount() {
        try {
            const response = await fetch('/api/notifications/unread-count');
            const data = await response.json();

            if (data.success) {
                this.setUnreadCount(data.unread_count);
            }
        } catch (error) {
            console.error('Error updating unread count:', error);
        }
    }

    setUnreadCount(count) {
        this.unreadCount = count;

        // 更新UI
        const badge = document.querySelector('.notification-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    }

    async loadNotifications() {
        try {
            const response = await fetch('/api/notifications?limit=20');
            const data = await response.json();

            if (data.success) {
                this.notifications = data.notifications;
                this.renderNotifications(data.notifications);
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }

    renderNotifications(notifications) {
        const container = document.querySelector('.notifications-dropdown');
        if (!container) return;

        const list = container.querySelector('.notification-list');
        if (!list) return;

        if (notifications.length === 0) {
            list.innerHTML = `
                <div class="notification-empty text-center p-3 text-muted">
                    <i class="fas fa-bell-slash fa-2x mb-2"></i>
                    <p>暂无新通知</p>
                </div>
            `;
            return;
        }

        list.innerHTML = notifications.map(notification => `
            <div class="notification-item ${notification.is_read ? 'read' : 'unread'}"
                 data-notification-id="${notification.id}"
                 style="cursor: pointer; padding: 12px; border-bottom: 1px solid #eee;">
                <div class="d-flex">
                    <div class="flex-grow-1">
                        <div class="fw-bold ${notification.is_read ? '' : 'text-primary'}">
                            ${notification.title}
                        </div>
                        <div class="small text-muted">${notification.message}</div>
                        <div class="small text-muted mt-1">
                            <i class="far fa-clock"></i> ${this.timeAgo(notification.created_at)}
                            ${notification.actor ? ` · 由 ${notification.actor}` : ''}
                        </div>
                    </div>
                    <div class="ms-2">
                        ${notification.url ? `
                            <a href="${notification.url}" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-external-link-alt"></i>
                            </a>
                        ` : ''}
                        ${!notification.is_read ? `
                            <button class="btn btn-sm btn-outline-secondary mark-read-btn"
                                    data-notification-id="${notification.id}">
                                <i class="fas fa-check"></i>
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `).join('');

        // 添加"全部标记为已读"按钮
        const unreadCount = notifications.filter(n => !n.is_read).length;
        if (unreadCount > 0) {
            const markAllBtn = document.createElement('div');
            markAllBtn.className = 'text-center p-2 border-top';
            markAllBtn.innerHTML = `
                <button class="btn btn-sm btn-outline-primary mark-all-read-btn">
                    <i class="fas fa-check-double"></i> 全部标记为已读 (${unreadCount})
                </button>
            `;
            list.appendChild(markAllBtn);
        }
    }

    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/api/notifications/${notificationId}/read`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();

            if (data.success) {
                // 更新UI
                const notificationElement = document.querySelector(`[data-notification-id="${notificationId}"]`);
                if (notificationElement) {
                    notificationElement.classList.add('read');
                    notificationElement.classList.remove('unread');
                    const markBtn = notificationElement.querySelector('.mark-read-btn');
                    if (markBtn) {
                        markBtn.remove();
                    }
                }

                // 更新未读计数
                this.setUnreadCount(data.unread_count);
            }
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }

    async markAllAsRead() {
        try {
            const response = await fetch('/api/notifications/read-all', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();

            if (data.success) {
                this.showToast(`已标记 ${data.marked_count} 条通知为已读`, 'success');
                this.loadNotifications(); // 重新加载通知列表
                this.setUnreadCount(0);
            }
        } catch (error) {
            console.error('Error marking all notifications as read:', error);
        }
    }

    handleNotificationClick(element) {
        const notificationId = element.dataset.notificationId;
        if (notificationId) {
            this.markAsRead(notificationId);
        }

        // 如果有链接，则跳转
        const link = element.querySelector('a[href]');
        if (link) {
            window.location.href = link.href;
        }
    }

    // 工具函数
    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    timeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;

        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return '刚刚';
        if (minutes < 60) return `${minutes}分钟前`;
        if (hours < 24) return `${hours}小时前`;
        if (days < 30) return `${days}天前`;
        return date.toLocaleDateString();
    }

    showToast(message, type = 'info') {
        // 使用现有的toast系统或创建简单的提示
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
        toast.style.zIndex = '9999';
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    // 初始化页面上的watch按钮状态
    async initializeWatchButtons() {
        const watchButtons = document.querySelectorAll('.watch-btn[data-target-type][data-target-id]');

        for (const button of watchButtons) {
            const targetType = button.dataset.targetType;
            const targetId = button.dataset.targetId;

            try {
                const response = await fetch(`/api/watch/${targetType}/${targetId}`);
                const data = await response.json();

                if (data.is_watching) {
                    this.updateWatchButton(button, true);
                }
            } catch (error) {
                console.error('Error checking watch status:', error);
            }
        }
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.watchManager = new WatchManager();

    // 初始化watch按钮状态
    window.watchManager.initializeWatchButtons();
});

// 导出供其他模块使用
window.WatchManager = WatchManager;
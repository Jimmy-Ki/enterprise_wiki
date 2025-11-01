"""OAuth登录控制器"""
from flask import Blueprint, redirect, url_for, request, current_app, session, flash, render_template
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models import User
from app.models.oauth import OAuthAccount, OAuthProvider
from app.services.oauth_service import oauth_service

oauth = Blueprint('oauth', __name__)


@oauth.route('/login/<provider_name>')
def login(provider_name):
    """OAuth登录入口"""
    if current_user.is_authenticated:
        return redirect(url_for('wiki.index'))

    try:
        auth_response = oauth_service.get_authorization_url(provider_name)

        # 检查返回的是否是Flask Response对象（重定向）
        if hasattr(auth_response, 'status_code') and auth_response.status_code in [302, 307]:
            # 直接返回重定向响应
            return auth_response
        elif hasattr(auth_response, 'location'):
            # 如果有location属性，直接重定向
            return redirect(auth_response.location)
        else:
            # 如果是字符串URL，正常重定向
            return redirect(auth_response)

    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('auth.login'))
    except Exception as e:
        current_app.logger.error(f"OAuth login error for {provider_name}: {str(e)}")
        flash('登录失败，请稍后重试', 'danger')
        return redirect(url_for('auth.login'))


@oauth.route('/callback/<provider_name>')
def callback(provider_name):
    """OAuth回调处理"""
    if current_user.is_authenticated:
        return redirect(url_for('wiki.index'))

    try:
        # 处理OAuth回调
        result = oauth_service.handle_callback(
            provider_name=provider_name,
            code=request.args.get('code'),
            state=request.args.get('state'),
            error=request.args.get('error')
        )

        user = result['user']
        oauth_account = result['oauth_account']
        sso_session_id = result['sso_session_id']
        skip_2fa = result['skip_2fa']

        # 清理OAuth会话数据
        session.pop('oauth_state', None)
        session.pop('oauth_provider', None)

        # 存储SSO会话信息
        session['sso_session_id'] = sso_session_id

        # 检查用户状态
        if not user.is_active:
            flash('您的账户已被禁用，请联系管理员', 'danger')
            return redirect(url_for('auth.login'))

        # 根据提供商设置决定是否跳过2FA
        if skip_2fa or not user.two_factor_enabled:
            # 直接登录
            login_user(user, remember=True)
            flash(f'通过 {oauth_account.provider.display_name} 登录成功！', 'success')

            next_page = request.args.get('next') or url_for('wiki.index')
            return redirect(next_page)
        else:
            # 需要验证2FA
            session['2fa_user_id'] = user.id
            session['2fa_next'] = request.args.get('next') or url_for('wiki.index')
            session['2fa_remember'] = True
            session['sso_login'] = True  # 标记为SSO登录

            flash('请输入双因素认证码', 'info')
            return redirect(url_for('two_factor.verify'))

    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('auth.login'))
    except Exception as e:
        current_app.logger.error(f"OAuth callback error for {provider_name}: {str(e)}")
        flash('登录失败，请稍后重试', 'danger')
        return redirect(url_for('auth.login'))


@oauth.route('/link/<provider_name>')
@login_required
def link_account(provider_name):
    """绑定OAuth账户到当前用户"""
    try:
        auth_response = oauth_service.get_authorization_url(provider_name)
        session['link_oauth'] = True  # 标记为绑定操作

        # 检查返回的是否是Flask Response对象（重定向）
        if hasattr(auth_response, 'status_code') and auth_response.status_code in [302, 307]:
            # 直接返回重定向响应
            return auth_response
        elif hasattr(auth_response, 'location'):
            # 如果有location属性，直接重定向
            return redirect(auth_response.location)
        else:
            # 如果是字符串URL，正常重定向
            return redirect(auth_response)

    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('user.profile'))
    except Exception as e:
        current_app.logger.error(f"OAuth link error for {provider_name}: {str(e)}")
        flash('绑定失败，请稍后重试', 'danger')
        return redirect(url_for('user.profile'))


@oauth.route('/unlink/<provider_name>')
@login_required
def unlink_account(provider_name):
    """解绑OAuth账户"""
    try:
        if current_user.unlink_oauth_account(provider_name):
            flash(f'已解绑 {provider_name} 账户', 'success')
        else:
            flash('未找到绑定的账户', 'warning')
        return redirect(url_for('user.profile'))
    except Exception as e:
        current_app.logger.error(f"OAuth unlink error for {provider_name}: {str(e)}")
        flash('解绑失败，请稍后重试', 'danger')
        return redirect(url_for('user.profile'))


@oauth.route('/manage')
@login_required
def manage_accounts():
    """管理OAuth账户"""
    try:
        # 获取用户的所有OAuth账户
        oauth_accounts = []
        for account in current_user.oauth_accounts.filter_by(is_active=True).all():
            oauth_accounts.append({
                'provider': account.provider.name,
                'provider_display_name': account.provider.display_name,
                'provider_user_id': account.provider_user_id,
                'email': account.email,
                'username': account.username,
                'name': account.name,
                'avatar_url': account.avatar_url,
                'last_login_at': account.last_login_at,
                'login_count': account.login_count,
                'created_at': account.created_at
            })

        # 获取可用的OAuth提供者
        available_providers = OAuthProvider.query.filter_by(is_active=True).all()

        # 标记已绑定的提供者
        for provider in available_providers:
            provider.is_linked = current_user.has_oauth_account(provider.name)

        return render_template('oauth/manage_accounts.html',
                             oauth_accounts=oauth_accounts,
                             available_providers=available_providers)
    except Exception as e:
        current_app.logger.error(f"Error loading OAuth management page: {str(e)}")
        flash('加载页面失败', 'danger')
        return redirect(url_for('user.profile'))


@oauth.route('/sessions')
@login_required
def sso_sessions():
    """查看SSO会话"""
    try:
        sessions = []
        for sso_session in current_user.sso_sessions.filter_by(is_active=True).all():
            if sso_session.is_valid():
                sessions.append({
                    'id': sso_session.id,
                    'session_id': sso_session.session_id[:16] + '...',
                    'provider': sso_session.oauth_account.provider.display_name,
                    'ip_address': sso_session.ip_address,
                    'user_agent': sso_session.user_agent[:50] + '...' if len(sso_session.user_agent) > 50 else sso_session.user_agent,
                    'created_at': sso_session.created_at,
                    'last_accessed_at': sso_session.last_accessed_at,
                    'expires_at': sso_session.expires_at
                })

        return render_template('oauth/sso_sessions.html', sessions=sessions)
    except Exception as e:
        current_app.logger.error(f"Error loading SSO sessions: {str(e)}")
        flash('加载会话信息失败', 'danger')
        return redirect(url_for('user.profile'))


@oauth.route('/revoke_session/<int:session_id>')
@login_required
def revoke_session(session_id):
    """撤销SSO会话"""
    try:
        from app.models.oauth import SSOSession

        sso_session = SSOSession.query.get_or_404(session_id)
        if sso_session.user_id != current_user.id:
            flash('无权操作此会话', 'danger')
            return redirect(url_for('oauth.sso_sessions'))

        sso_session.revoke()
        db.session.commit()
        flash('会话已撤销', 'success')
        return redirect(url_for('oauth.sso_sessions'))
    except Exception as e:
        current_app.logger.error(f"Error revoking SSO session: {str(e)}")
        flash('撤销会话失败', 'danger')
        return redirect(url_for('oauth.sso_sessions'))


@oauth.route('/admin/providers')
@login_required
def admin_providers():
    """管理员：OAuth提供者管理"""
    if not current_user.is_administrator():
        flash('需要管理员权限', 'danger')
        return redirect(url_for('wiki.index'))

    providers = OAuthProvider.query.all()
    return render_template('oauth/admin_providers.html', providers=providers)


@oauth.route('/admin/provider/<int:provider_id>/toggle')
@login_required
def toggle_provider(provider_id):
    """管理员：启用/禁用OAuth提供者"""
    if not current_user.is_administrator():
        flash('需要管理员权限', 'danger')
        return redirect(url_for('wiki.index'))

    try:
        provider = OAuthProvider.query.get_or_404(provider_id)
        provider.is_active = not provider.is_active
        db.session.commit()

        status = "启用" if provider.is_active else "禁用"
        flash(f'{provider.display_name} 已{status}', 'success')

        # 重新注册OAuth提供者
        oauth_service._register_providers()
    except Exception as e:
        current_app.logger.error(f"Error toggling OAuth provider: {str(e)}")
        flash('操作失败', 'danger')

    return redirect(url_for('oauth.admin_providers'))
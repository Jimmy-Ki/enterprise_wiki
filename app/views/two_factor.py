"""Two-Factor Authentication routes"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime
from werkzeug.security import generate_password_hash
from app.models import User
from app.forms.two_factor import TwoFactorSetupForm, TwoFactorVerifyForm, TwoFactorDisableForm, TwoFactorBackupCodeForm
from app import db
import json

two_factor = Blueprint('two_factor', __name__)


@two_factor.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    """设置双因素认证"""
    if current_user.two_factor_enabled:
        flash('您已经启用了双因素认证', 'info')
        return redirect(url_for('user.profile'))

    form = TwoFactorSetupForm()

    if request.method == 'GET':
        # 如果用户还没有TOTP密钥，生成一个新的
        if not current_user.two_factor_secret:
            secret = current_user.generate_totp_secret()
            db.session.commit()
        else:
            secret = current_user.two_factor_secret

        qr_code = current_user.generate_totp_qr_code(secret)

        return render_template('auth/2fa/setup.html',
                               form=form,
                               secret=secret,
                               qr_code=qr_code)

    if form.validate_on_submit():
        # 验证TOTP码
        if current_user.verify_totp_token(form.verification_code.data):
            # 启用2FA
            current_user.enable_two_factor(current_user.two_factor_secret)
            db.session.commit()

            # 生成备用码
            backup_codes = json.loads(current_user.backup_codes)

            flash('双因素认证已成功启用！请保存以下备用码：', 'success')
            return render_template('auth/2fa/backup_codes.html',
                                   backup_codes=backup_codes,
                                   now=datetime.now())
        else:
            flash('验证码无效，请重试', 'danger')
            return render_template('auth/2fa/setup.html',
                                   form=form,
                                   secret=current_user.two_factor_secret,
                                   qr_code=current_user.generate_totp_qr_code(current_user.two_factor_secret))

    return render_template('auth/2fa/setup.html', form=form)


@two_factor.route('/verify', methods=['GET', 'POST'])
def verify():
    """验证双因素认证"""
    # 从session获取用户信息
    user_id = session.get('2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('auth.login'))

    # 获取登录后重定向的URL
    next_url = session.get('2fa_next') or url_for('wiki.index')

    form = TwoFactorVerifyForm()

    if form.validate_on_submit():
        # 验证TOTP码
        if user.verify_totp_token(form.code.data):
            # 获取记住设备选项
            remember_me = session.get('2fa_remember', False) or form.remember_me.data

            # 清除session中的2FA信息
            session.pop('2fa_user_id', None)
            session.pop('2fa_next', None)
            session.pop('2fa_remember', None)

            # 完全登录用户
            login_user(user, remember=remember_me)

            flash('认证成功！', 'success')
            return redirect(next_url)
        else:
            flash('认证码无效，请重试', 'danger')

    return render_template('auth/2fa/verify.html', form=form, next_url=next_url)


@two_factor.route('/disable', methods=['GET', 'POST'])
@login_required
def disable():
    """禁用双因素认证"""
    if not current_user.two_factor_enabled:
        flash('您还没有启用双因素认证', 'info')
        return redirect(url_for('user.profile'))

    form = TwoFactorDisableForm()

    if form.validate_on_submit():
        # 验证密码和TOTP码
        if current_user.verify_totp_token(form.verification_code.data):
            # 禁用2FA
            current_user.disable_two_factor()
            db.session.commit()

            flash('双因素认证已禁用', 'success')
            return redirect(url_for('user.profile'))
        else:
            flash('验证码无效，请重试', 'danger')

    return render_template('auth/2fa/disable.html', form=form)


@two_factor.route('/backup-code', methods=['GET', 'POST'])
def backup_code_login():
    """使用备用码登录"""
    if current_user.is_authenticated:
        return redirect(url_for('wiki.index'))

    # 从session获取用户信息
    user_id = session.get('2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('auth.login'))

    form = TwoFactorBackupCodeForm()

    if form.validate_on_submit():
        if user.verify_backup_code(form.backup_code.data):
            # 获取记住设备选项
            remember_me = session.get('2fa_remember', False)

            # 清除session中的2FA信息
            session.pop('2fa_user_id', None)
            session.pop('2fa_next', None)
            session.pop('2fa_remember', None)

            db.session.commit()
            login_user(user, remember=remember_me)
            flash('登录成功！请重新设置双因素认证', 'warning')
            return redirect(url_for('two_factor.setup'))
        else:
            flash('备用码无效', 'danger')

    return render_template('auth/2fa/backup_code.html', form=form)


@two_factor.route('/api/qrcode')
@login_required
def generate_qrcode():
    """生成新的QR码"""
    secret = current_user.generate_totp_secret()
    qr_code = current_user.generate_totp_qr_code(secret)

    return jsonify({
        'success': True,
        'secret': secret,
        'qr_code': qr_code
    })


@two_factor.route('/api/verify-code', methods=['POST'])
@login_required
def verify_code():
    """验证TOTP码（AJAX）"""
    data = request.get_json()
    code = data.get('code', '')

    if not code or len(code) != 6:
        return jsonify({
            'success': False,
            'message': '请输入6位验证码'
        })

    if current_user.verify_totp_token(code):
        return jsonify({
            'success': True,
            'message': '验证码正确'
        })
    else:
        return jsonify({
            'success': False,
            'message': '验证码无效'
        })
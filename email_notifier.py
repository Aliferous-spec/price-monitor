# -*- coding: utf-8 -*-
"""
邮件通知模块
当检测到降价时发送邮件提醒
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime


def send_price_alert(
    smtp_server: str,
    smtp_port: int,
    sender_email: str,
    sender_password: str,
    receiver_email: str,
    product_name: str,
    current_price: float,
    previous_price: float,
    product_url: str,
    lowest_price: float = None,
) -> bool:
    """
    发送降价提醒邮件

    Args:
        smtp_server: SMTP服务器地址
        smtp_port: SMTP端口
        sender_email: 发件人邮箱
        sender_password: 发件人密码/授权码
        receiver_email: 收件人邮箱
        product_name: 商品名称
        current_price: 当前价格
        previous_price: 之前价格
        product_url: 商品链接
        lowest_price: 历史最低价

    Returns:
        是否发送成功
    """
    drop_amount = previous_price - current_price
    drop_percent = (drop_amount / previous_price) * 100 if previous_price > 0 else 0

    subject = f"📉 降价提醒：{product_name} 降至 ¥{current_price}"

    # HTML邮件正文
    body_lines = [
        f"<h2>商品降价通知</h2>",
        f"<p><b>商品名称：</b>{product_name}</p>",
        f"<p><b>当前价格：</b><span style='color:red;font-size:18px'>¥{current_price}</span></p>",
        f"<p><b>之前价格：</b>¥{previous_price}</p>",
        f"<p><b>降价幅度：</b>¥{drop_amount:.2f}（{drop_percent:.1f}%）</p>",
        f"<p><b>商品链接：</b><a href='{product_url}'>{product_url}</a></p>",
    ]

    if lowest_price is not None:
        body_lines.append(f"<p><b>历史最低价：</b>¥{lowest_price}</p>")

    body_lines.append(f"<p style='color:#999;font-size:12px'>检测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")

    html_body = "\n".join(body_lines)

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())

        print(f"  ✅ 降价邮件已发送 → {receiver_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("  ❌ 邮件发送失败：邮箱认证失败，请检查邮箱授权码是否正确")
        return False
    except smtplib.SMTPException as e:
        print(f"  ❌ 邮件发送失败：{e}")
        return False
    except Exception as e:
        print(f"  ❌ 邮件发送异常：{e}")
        return False


def send_test_email(config: dict) -> bool:
    """
    发送测试邮件，验证邮箱配置是否正确
    """
    try:
        msg = MIMEText("🎉 价格监控器邮件通知功能已就绪！", "plain", "utf-8")
        msg["Subject"] = Header("价格监控器 - 测试邮件", "utf-8")
        msg["From"] = config["sender_email"]
        msg["To"] = config["receiver_email"]

        with smtplib.SMTP(config["smtp_server"], config["smtp_port"], timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config["sender_email"], config["sender_password"])
            server.sendmail(config["sender_email"], config["receiver_email"], msg.as_string())

        print("✅ 测试邮件发送成功！邮箱配置正确。")
        return True
    except Exception as e:
        print(f"❌ 测试邮件发送失败：{e}")
        return False

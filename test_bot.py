import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Get token from environment
TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple start command"""
    await update.message.reply_text(
        "✅ **BOT IS WORKING!**\n\n"
        "If you see this message, the bot is functioning.\n\n"
        "Now checking full version...",
        parse_mode="Markdown"
    )

async def main():
    print("🤖 TEST BOT STARTING...")
    print(f"🔑 Token exists: {bool(TOKEN)}")
    print(f"📝 Token first 10 chars: {TOKEN[:10]}...")
    
    if not TOKEN:
        print("❌ ERROR: No BOT_TOKEN found!")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    print("✅ TEST BOT IS RUNNING!")
    print("📱 Go to Telegram and send /start")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

from config import get_settings
from database import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Initialize bot and dispatcher
bot = None
dp = None

def get_bot():
    """Get or create bot instance"""
    global bot
    if bot is None:
        # Create session with proxy if configured
        if settings.PROXY_URL:
            session = AiohttpSession(proxy=settings.PROXY_URL)
            bot = Bot(token=settings.BOT_TOKEN, session=session)
            logger.info(f"Bot initialized with proxy: {settings.PROXY_URL}")
        else:
            bot = Bot(token=settings.BOT_TOKEN)
            logger.info("Bot initialized without proxy")
    return bot

def get_dispatcher():
    """Get or create dispatcher with handlers"""
    global dp
    if dp is None:
        dp = Dispatcher()
        from handlers.admin import admin_router
        from handlers.client import client_router
        dp.include_router(admin_router)
        dp.include_router(client_router)
        logger.info("Handlers registered")
    return dp


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting bot...")
    
    # Initialize database
    await db.init_db()
    logger.info("Database initialized")
    
    # Get instances
    bot_instance = get_bot()
    dp_instance = get_dispatcher()
    
    # Start polling in background
    asyncio.create_task(start_bot(bot_instance, dp_instance))
    
    yield
    
    # Shutdown
    logger.info("Shutting down bot...")
    await bot_instance.session.close()


async def start_bot(bot_instance, dp_instance):
    """Start the bot polling"""
    try:
        await dp_instance.start_polling(bot_instance, allowed_updates=dp_instance.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Error in bot polling: {e}")


# Create FastAPI app
app = FastAPI(
    title="Urolog Bot API",
    description="Telegram bot for urological health assessment",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "running",
        "bot": "Urolog Bot",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/stats")
async def get_stats():
    """Get bot statistics"""
    try:
        categories = await db.get_all_categories()
        
        stats = {
            "total_categories": len(categories),
            "categories": []
        }
        
        for category in categories:
            questions = await db.get_questions_by_category(category['id'])
            stats["categories"].append({
                "id": category['id'],
                "name": category['name'],
                "questions_count": len(questions)
            })
        
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )


from telegram.ext import ApplicationBuilder
from config import TOKEN
from menu import setup_handlers
from admin import agendar_estatisticas

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    setup_handlers(application)
    agendar_estatisticas(application.job_queue)
    application.run_polling()

if __name__ == '__main__':
    main()

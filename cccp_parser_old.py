from datetime import datetime
import logging
import os
import asyncio
import yaml
from pyrogram import Client, filters, idle
import yadisk

config = yaml.safe_load( open( 'config.yaml' ) )
config_tg = config[ 'TG' ]
config_ya = config[ 'YA' ]

app = Client( config_tg[ 'session_name' ], api_id=config_tg[ 'api_id' ], api_hash=config_tg[ 'api_hash' ] )
y = yadisk.AsyncClient( token=config_ya[ 'token' ] )

@app.on_message( filters.chat( config_tg[ 'channels' ] ) )
async def handle_media( client, message ):
    try:
        chat_title = message.chat.username or message.chat.title

        logging.info( f'[*] Новое сообщение в канале: {chat_title}, тип: {message.media}')
        logging.info( f'message: {message}' )
        logging.info( getattr(message, "message_thread_id", None ) )
        #topic = app.get_forum_topic( message.chat.id, 12345 )
        #logging.info( f'topic: {topic}' )

        if message.media is None or not message.media != 'MessageMediaType.VIDEO':
            return

        logging.info( f'message: {message}' )

        # По умолчанию сохраняет в папку downloads/ в директории скрипта на сервере
        file_path = await message.download( )
        logging.debug( f'file_path: {file_path}' )
        if not file_path:
            print("    [!] Ошибка: Не удалось скачать файл.")
            return

        # 2. Подготовка пути для Яндекс.Диска
        filename = os.path.basename( file_path )
        yandex_path = f"{config_ya[ 'upload_path' ]}/{filename}"

        # 3. Загрузка файла на Яндекс.Диск#
        await y.upload( file_path, yandex_path )

        # 4. Удаление локального файла для экономии места
        os.remove( file_path )

    except yadisk.exceptions.PathExistsError:
        logging.error( f'    [!] Ошибка: Файл {filename} уже существует на Яндекс.Диске.' )
        # Если файл существует, все равно удаляем локальную копию
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logging.error( f'    [!] Произошла непредвиденная ошибка: {e}' )

async def ya_init( ):
    # Проверка валидности токена Яндекс.Диска перед запуском
    is_token_valid = await y.check_token( )

    if not is_token_valid:
        logging.error( 'КРИТИЧЕСКАЯ ОШИБКА: Неверный токен Яндекс.Диска!' )
        return

    for ch in config_tg[ 'channels' ]:
        dir = f'{config_ya[ "upload_path" ]}/{ch}'
        logging.info( dir )
        if not await y.is_dir( dir ):
            await y.mkdir( dir )
            logging.info( f'created: {dir}' )

    logging.info( 'ya_inited' )

def log_init( ):
    log_filename = datetime.now( ).strftime( "%Y-%m-%d.log" )
    logging.basicConfig(
        level=logging.INFO,
        filename=f"logs/{log_filename}",
        filemode="a",
        format="%(asctime)s %(levelname)s %(message)s"
    )

def main():
    log_init( )

    logging.info( 'Скрипт запущен. Ожидание новых сообщений...' )

    #await ya_init( )

    # Запуск Telegram-клиента
    app.run( )

    #await y.close()

if __name__ == "__main__":
    # Запускаем асинхронный цикл событий
    #ya_init( )
    main( )

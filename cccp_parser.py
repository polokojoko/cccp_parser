from datetime import datetime
import logging
import os
import asyncio
import yaml
import yadisk

from telethon import TelegramClient, events

config = yaml.safe_load( open( 'config.yaml' ) )
config_tg = config[ 'TG' ]
config_ya = config[ 'YA' ]
config_gl = config[ 'GLOBAL' ]

client = TelegramClient( config_tg[ 'session_name' ], api_id=config_tg[ 'api_id' ], api_hash=config_tg[ 'api_hash' ] )
y = yadisk.AsyncClient( token=config_ya[ 'token' ] )

@client.on( events.NewMessage( chats = [ channel[ 'id'] for channel in config_tg[ 'channels' ] ] ) )
async def handler(event):
    channel_id = event.message.peer_id.channel_id
    topic_id = event.message.reply_to.reply_to_top_id or event.message.reply_to.reply_to_msg_id

    logging.info( f'channel ID = {channel_id}' )
    logging.info( f'topic_id = {topic_id}' )
    # logging.info( f'event: {event}' )

    try:
        if topic_id != ( next( ch for ch in config_tg[ 'channels' ] if ch[ 'id' ] == channel_id ), None ) or not event.media:
            return

        logging.info( '    [!] event has media' )

        # По умолчанию сохраняет в папку downloads/ в директории скрипта на сервере
        file_path = await client.download_media( event.message, file = config_gl[ 'download_path' ] )

        logging.info( f'file_path: {file_path}' )

        if not file_path:
            logging.error("    [!!!] Ошибка: Не удалось скачать файл.")
            return

        # 2. Подготовка пути для Яндекс.Диска
        filename = os.path.basename( file_path )
        yandex_path = f"{config_ya[ 'upload_path' ]}/{filename}"

        # 3. Загрузка файла на Яндекс.Диск#
        await y.upload( file_path, yandex_path )

        # 4. Удаление локального файла для экономии места
        os.remove( file_path )

    except yadisk.exceptions.PathExistsError:
        logging.error( f'    [!!!] Ошибка: Файл {filename} уже существует на Яндекс.Диске.' )
        # Если файл существует, все равно удаляем локальную копию
        if 'file_path' in locals( ) and os.path.exists( file_path ):
            os.remove( file_path )
    except Exception as e:
        logging.error( f'    [!!!] Произошла непредвиденная ошибка: {e}' )

async def ya_init( ):
    # Проверка валидности токена Яндекс.Диска перед запуском
    is_token_valid = await y.check_token( )

    if not is_token_valid:
        logging.error( '    [!!!] КРИТИЧЕСКАЯ ОШИБКА: Неверный токен Яндекс.Диска!' )
        return

    for ch_name in [ channel[ 'name' ] for channel in config_tg[ 'channels' ] ]:
        dir = f'{config_ya[ "upload_path" ]}/{ch_name}'
        logging.info( dir )
        if not await y.is_dir( dir ):
            await y.mkdir( dir )
            logging.info( f'    [!] created: {dir}' )

    logging.info( '    [!] ya_inited' )

def log_init( ):
    log_filename = datetime.now( ).strftime( "%Y-%m-%d.log" )
    logging.basicConfig(
        level=logging.INFO,
        filename=f"logs/{log_filename}",
        filemode="a",
        format="%(asctime)s %(levelname)s %(message)s"
    )

def init_env( ):
    os.makedirs( 'logs', exist_ok = True )
    os.makedirs( 'downloads', exist_ok = True )

async def main( ):
    log_init( )

    logging.info( 'Скрипт запущен. Ожидание новых сообщений...' )

    await ya_init( )

    # Запуск Telegram-клиента

    await client.start( )
    await client.run_until_disconnected(  )

if __name__ == "__main__":
    # Запускаем асинхронный цикл событий
    asyncio.run( main( ) )

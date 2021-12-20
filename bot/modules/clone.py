import random
import string

from telegram.ext import CommandHandler
from telegram import ParseMode
from bot.helper.mirror_utils.upload_utils import gdriveTools
from bot.helper.telegram_helper.message_utils import *
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot import dispatcher, LOGGER, CLONE_LIMIT, STOP_DUPLICATE, LOGS_CHATS, download_dict, download_dict_lock, Interval
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_gdrive_link, is_gdtot_link, new_thread
from bot.helper.mirror_utils.download_utils.direct_link_generator import gdtot
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException

@new_thread
def cloneNode(update, context):
    args = update.message.text.split(" ", maxsplit=1)
    reply_to = update.message.reply_to_message
    if len(args) > 1:
        link = args[1]
    elif reply_to is not None:
        link = reply_to.text
    else:
        link = ''
    gdtot_link = is_gdtot_link(link)
    if gdtot_link:
        try:
            msg = sendMessage(f"Pʀᴏᴄᴇssɪɴɢ Yᴏᴜʀ ᴜʀʟ : <code>{link}</code>", context.bot, update)
            link = gdtot(link)
            deleteMessage(context.bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(context.bot, msg)
            return sendMessage(str(e), context.bot, update)
    if is_gdrive_link(link):
        gd = gdriveTools.GoogleDriveHelper()
        res, size, name, files = gd.helper(link)
        if res != "":
            sendMessage(res, context.bot, update)
            return
        if STOP_DUPLICATE:
            LOGGER.info('Cʜᴇᴄᴋɪɴɢ Fɪʟᴇ / Fᴏʟᴅᴇʀ ɪғ ᴀʟʀᴇᴀᴅʏ ɪɴ Dʀɪᴠᴇ...')
            smsg, button = gd.drive_list(name, True, True)
            if smsg:
                msg3 = "🦉 Fɪʟᴇ/Fᴏʟᴅᴇʀ Is Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ Iɴ Dʀɪᴠᴇ. \nHᴇʀᴇ Aʀᴇ Tʜᴇ Aᴠᴀɪʟᴀʙʟᴇ Rᴇsᴜʟᴛs 👇🏼👇🏽"
                sendMarkup(msg3, context.bot, update, button)
                if gdtot_link:
                    gd.deletefile(link)
                return
        if CLONE_LIMIT is not None:
            LOGGER.info('Cʜᴇᴄᴋɪɴɢ Fɪʟᴇ/Fᴏʟᴅᴇʀ Sɪᴢᴇ..')
            if size > CLONE_LIMIT * 1024**3:
                msg2 = f'Failed, Clone limit is {CLONE_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(size)}.'
                sendMessage(msg2, context.bot, update)
                return
        if files <= 10:
            msg = sendMessage(f"😾 Cʟᴏɴɪɴɢ Yᴏᴜʀ Rᴇϙᴜᴇsᴛ : <code>{link}</code>", context.bot, update)
            result, button = gd.clone(link)
            deleteMessage(context.bot, msg)
        else:
            drive = gdriveTools.GoogleDriveHelper(name)
            gid = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=12))
            clone_status = CloneStatus(drive, size, update, gid)
            with download_dict_lock:
                download_dict[update.message.message_id] = clone_status
            sendStatusMessage(update, context.bot)
            result, button = drive.clone(link)
            with download_dict_lock:
                del download_dict[update.message.message_id]
                count = len(download_dict)
            try:
                if count == 0:
                    Interval[0].cancel()
                    del Interval[0]
                    delete_all_messages()
                else:
                    update_all_messages()
            except IndexError:
                pass
        if update.message.from_user.username:
            uname = f'@{update.message.from_user.username}'
        else:
            uname = f'<a href="tg://user?id={update.message.from_user.id}">{update.message.from_user.first_name}</a>'
        if uname is not None:
            cc = f'\n\n<b>Cʟᴏɴᴇᴅ Bʏ : </b>{uname}'
            men = f'{uname} '
        if button in ["cancelled", ""]:
            sendMessage(men + result, context.bot, update)
        else:
            sendMarkup(result + cc, context.bot, update, button)
            if LOGS_CHATS:
                try:
                    for i in LOGS_CHATS:
                        msg1 = f'<b>Fɪʟᴇ Cʟᴏɴᴇᴅ : </b> <code>{name}</code>\n'
                        msg1 += f'<b>Cʟᴏɴᴇᴅ Bʏ : </b>{uname}\n'
                        msg1 += f'<b>Sɪᴢᴇ : </b>{get_readable_file_size(size)}\n'
                        bot.sendMessage(chat_id=i, text=msg1, reply_markup=button, parse_mode=ParseMode.HTML)
                except Exception as e:
                    LOGGER.warning(e)
        if gdtot_link:
            gd.deletefile(link)
    else:
        sendMessage('👻 Hᴇʏ, Sᴇɴᴅ GDʀɪᴠᴇ ᴏʀ GDTᴏT ʟɪɴᴋ Aʟᴏɴɢ Wɪᴛʜ Cᴏᴍᴍᴀɴᴅ Oʀ Bʏ Rᴇᴘʟʏɪɴɢ Tᴏ Tʜᴇ Lɪɴᴋ Bʏ Cᴏᴍᴍᴀɴᴅ Cᴏʀʀᴇᴄᴛʟʏ ', context.bot, update)

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
dispatcher.add_handler(clone_handler)

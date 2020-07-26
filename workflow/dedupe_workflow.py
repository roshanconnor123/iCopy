import re
from utils.load import _lang, _text
from utils import load, restricted as _r, keyboard as _KB, dedupe_payload as _d_payload
from multiprocessing import Process as _mp
from telegram.ext import ConversationHandler
from drive.gdrive import GoogleDrive as _gd

(
    SET_FAV_MULTI,
    CHOOSE_MODE,
    GET_LINK,
    IS_COVER_QUICK,
    GET_DST,
    COOK_ID,
    REGEX_IN,
    REGEX_GET_DST,
    COOK_FAV_TO_SIZE,
    COOK_FAV_PURGE,
    COOK_ID_DEDU,
) = range(11)

bot = load.bot
check_task = {}

def dedupe(update, context):
    entry_cmd = update.effective_message.text
    match_cmd = re.search(r'^\/dedupe ([1-9]\d*)$', entry_cmd, flags=re.I)

    if match_cmd:
        limit_query = load.db_counters.find_one({"_id":"task_list_id"})
        check_query = match_cmd.group(1)

        if int(check_query) <= limit_query['future_id']:
            
            global check_task
            check_task = load.task_list.find_one({"_id": int(check_query)})

            if check_task["status"] == 1:
                update.effective_message.reply_text(
                    _text[_lang]["mode_select_msg"].replace(
                        "replace", _text[_lang]["dedupe_mode"]
                    )
                    + "\n"
                    + _text[_lang]["request_dedupe_mode"],
                    reply_markup=_KB.dedupe_mode_keyboard(),
                )

                return COOK_ID_DEDU

            elif check_task["status"] == 0:
                update.effective_message.reply_text(
                    _text[_lang]["task_is_in_queue"]
                    + "\n"
                    + _text[_lang]["finished_could_be_dedupe"],
                )

                return ConversationHandler.END

            elif check_task["status"] == 2:
                update.effective_message.reply_text(
                    _text[_lang]["doing"]
                    + "\n"
                    + _text[_lang]["finished_could_be_dedupe"],
                )

                return ConversationHandler.END
    
        else:
            update.effective_message.reply_text(
                _text[_lang]["over_limit_to_dedupe"],
            )

            return ConversationHandler.END

    else:
        update.effective_message.reply_text(
            _text[_lang]["global_command_error"]
        )


def dedupe_mode(update, context):

    get_callback = update.callback_query.data
    dedu_msg = bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        text=_text[_lang]["ready_to_dedupe"],
        reply_markup=None,
    )

    dedu_chat_id = dedu_msg.chat_id
    dedu_message_id = dedu_msg.message_id
    dedu_mode = get_callback
    
    if "dst_endpoint_id" and "dst_endpoint_link" in check_task:
        dedu_task_id = check_task["_id"]
        dedu_name = check_task["src_name"]
        dedu_id = check_task["dst_endpoint_id"]
        dedu_link = check_task["dst_endpoint_link"]


    else:
        dst_endpoint_id = _gd.get_dst_endpoint_id(
            _gd(), check_task["dst_id"], check_task["src_name"]
        )
        if dst_endpoint_id:
            dst_endpoint_link = r"https://drive.google.com/open?id={}".format(
                dst_endpoint_id["id"]
            )

            load.task_list.update_one(
                {"_id": int(check_task["_id"])},
                {
                    "$set": {
                        "dst_endpoint_id": dst_endpoint_id["id"],
                        "dst_endpoint_link": dst_endpoint_link,
                    },
                },
            )

            dedu_task_id = check_task["_id"]
            dedu_name = check_task["src_name"]
            dedu_id = dst_endpoint_id
            dedu_link = dst_endpoint_link

    progress = _mp(
        target=_d_payload.dedupe_task,
        args=(
            dedu_mode,
            dedu_chat_id,
            dedu_message_id,
            dedu_task_id,
            dedu_link,
            dedu_id,
            dedu_name,
        ),
    )
    progress.start()

    bot.edit_message_text(
        chat_id=dedu_chat_id,
        message_id=dedu_message_id,
        text=_text[_lang]["deduping"],
    )

    return ConversationHandler.END
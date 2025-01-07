import sys
import os
sys.path.append("..")
import asyncio
import re
from datetime import date, time, datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from event_admin.data_manager import save_events, save_working_event
from event_admin import menu, edit_event
from event_admin.constants import (
    MAIN_MENU,
    NEW_EVENT_NAME,
    MY_EVENTS,
    EVENT_MENU,      
    EDIT_EVENT_MENU,
    EDIT_EVENT_NAME,
    EDIT_EVENT_DATE,
    EDIT_EVENT_START_TIME,
    EDIT_EVENT_END_TIME,
    EDIT_EVENT_CAPACITY,
    EDIT_EVENT_RSVP_ASK,
    EDIT_RSVP_INPUT,
    ANNOUNCEMENT_MENU,
    ANNOUNCEMENT_EDIT_ANNOUNCEMENT_TEXT,
    ANNOUNCEMENT_EDIT_POSTED_ANNOUNCEMENT_TEXT,
    ASK_CLOSE_EVENT
)
from config.config import chat_ids
from rsvp import rsvp_header_text


async def ask_to_close_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ask the user if they want to close the working event.
    """
    query = update.callback_query
    text = (
        f"{menu.generate_event_headers(context.user_data['working_event'])}\n"
        "Closing the event will have the following effects:\n"
        "- The event will no longer show up in the event menu, but the data will still be saved.\n"
        "- The announcement will be edited to not have a button to RSVP.\n"
        "- The button in the group chat will be deleted.\n"
        "- The rsvp confirmation messages will no longer have a button to cancel the RSVP.\n\n"
        "Do you want to close the event?"
    )
    buttons = [
        [InlineKeyboardButton("No", callback_data="no_close_event"), InlineKeyboardButton("Yes", callback_data="yes_close_event")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(
        text,
        reply_markup=keyboard
    )
    return ASK_CLOSE_EVENT

async def ask_to_close_event_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback for the user's response to closing the event.
    """
    query = update.callback_query
    query.answer()
    if query.data == "yes_close_event":
        return await close_event(update, context)
    elif query.data == "no_close_event":
        return await menu.show_event_menu(update, context)
    else:
        return await menu.show_main_menu(update, context)

    
async def close_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Close the working event and save it to the bot_data.
    """
    # Get the working event from user_data
    event_data = context.user_data.get("working_event")
    if not event_data:
        await update.message.reply_text("No working event found.")
        return ConversationHandler.END
    
    # 1. The event will no longer show up in the event menu.
    # The data will still be saved in the bot_data and I can recover it if needed.
    event_data["show"] = False
    save_working_event(context)
    
    # 2. The annoucement that was posted in the channel will be edited to not have a button to RSVP
    await close_announcement_message(update, context, event_data)
    
    # 3. The button that was posted in the group chat will be deleted
    try:
        await context.bot.delete_message(chat_id=event_data["group_rsvp_button_chat_id"], message_id=event_data["group_rsvp_button_message_id"])
    except Exception as ex:
            print(f"[Close] Could not delete RSVP button from group chat: {ex}")
        
    # 4. The rsvp confirmation messages will no longer have a button to cancel the RSVP
    for attendee in event_data["attendees"]:
        rsvp_message_id = attendee.get("rsvp_message_id")
        if rsvp_message_id:
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=attendee["user_id"],
                    message_id=rsvp_message_id,
                    reply_markup=None,
                    disable_web_page_preview=True
                )
            except Exception as ex:
                print(f"[RSVP] Could not remove RSVP button: {ex}")
    for attendee in event_data["waitlist"]:
        rsvp_message_id = attendee.get("rsvp_message_id")
        if rsvp_message_id:
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=attendee["user_id"],
                    message_id=rsvp_message_id,
                    reply_markup=None,
                    disable_web_page_preview=True
                )
            except Exception as ex:
                print(f"[RSVP] Could not remove RSVP button: {ex}")
    
    save_working_event(context)
    
    # Notify the user
    await update.effective_chat.send_message(
        f"Event {event_data['name']} is now closed."
    )
    

    # Return to the main menu
    return await menu.show_main_menu(update, context, False)

async def close_announcement_message(update: Update, context: ContextTypes.DEFAULT_TYPE, event_data: dict):
    """
    Example: Re-generate the announcement text to show new attendee count or waitlist.
    Then edit the message in event_data["announcement_message_chat_id"] / ["announcement_message_id"].
    """
    # If you have the same generate_announcemnt_text function
    from event_admin.announcement import generate_announcement_message  # or wherever it is

    try:
        text, _ = generate_announcement_message(context, event_data_override=event_data)
        await context.bot.edit_message_text(
            chat_id=event_data["announcement_message_chat_id"],
            message_id=event_data["announcement_message_id"],
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )
    except Exception as ex:
        print(f"[RSVP] Could not remove RSVP button: {ex}")
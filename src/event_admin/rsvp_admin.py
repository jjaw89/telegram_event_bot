# event_admin/rsvp_admin.py

import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import re
from datetime import date, time, datetime
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from event_admin import menu, announcement
import rsvp 
from event_admin.data_manager import save_working_event
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
    EDIT_EVENT_LOCATION,
    EDIT_EVENT_RSVP_ASK,
    EDIT_RSVP_INPUT,
    ANNOUNCEMENT_MENU,
    ANNOUNCEMENT_EDIT_ANNOUNCEMENT_TEXT,
    ANNOUNCEMENT_EDIT_POSTED_ANNOUNCEMENT_TEXT,
    RSVP_MENU,
    MESSAGE_RSVP_INPUT,
    MESSAGE_RSVP_WHOM
)

# We'll define some internal states or callbacks:
BACK_TO_RSVP_MENU_NEW_MESSAGE = "back_to_rsvp_menu_new_message"
VIEW_ATTENDING = "view_attending"
MESSAGE_RSVP = "message_rsvp"
# MESSAGE_RSVP_WHOM = "message_rsvp_whom"
# MESSAGE_RSVP_INPUT = "message_rsvp_input"
# Additional constants for the "who to message" sub-menu:
MESSAGE_ATTENDEES = "msg_attendees"
MESSAGE_WAITLIST = "msg_waitlist"
BACK_TO_RSVP_MENU = "back_to_rsvp_menu"
UPDATE_WAITLIST = "update_waitlist"
def escape_markdown_v2(text: str) -> str:
    """
    Escapes Markdown V2 special characters in the given text.
    See: https://core.telegram.org/bots/api#markdownv2-style
    """
    # Characters that must be escaped in MarkdownV2:
    # _ * [ ] ( ) ~ ` > # + - = | { } . !
    pattern = r'([\_\*\[\]\(\)\~\`\>\#\+\-\=\|\{\}\.\!])'
    return re.sub(pattern, r'\\\1', text)

async def view_attending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show a list of attendees and waitlist, then send a separate message
    with the RSVP menu again.
    """
    query = update.callback_query
    event_data = context.user_data["working_event"]

    attendees = event_data.get("attendees", [])
    waitlist = event_data.get("waitlist", [])

    # Build text
    text = (
        f"Event: {event_data['name']}\n"
        f"Date: {event_data.get('date', 'None')}\n"
        f"Start: {event_data.get('start_time', 'None')}\n"
        f"End: {event_data.get('end_time', 'None')}\n\n"
    )
    text = announcement.escape_markdown_v2(text)
    text += "*Attendees:*\n"
    if not attendees:
        text += "No one is attending yet\.\n"
    else:
        for idx, a in enumerate(attendees, start=1):
            first = a.get("first_name") or ""
            last = a.get("last_name") or ""
            uname = a.get("username") or ""
            text += escape_markdown_v2(f"{idx}. {first} {last} @{uname}\n")

    if waitlist:
        text += "\n*Waitlist:*\n"
        for idx, w in enumerate(waitlist, start=1):
            first = w.get("first_name") or ""
            last = w.get("last_name") or ""
            uname = w.get("username") or ""
            text += escape_markdown_v2(f"{idx}. {first} {last} @{uname}\n")

    # Send a new message with the list
    await query.answer()
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN_V2
    )

    
    return await menu.show_rsvp_menu(update, context, edit = False)
    


async def message_rsvp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    If there's a waitlist, let user choose "Attendees" or "Waitlist".
    If there's no waitlist, just go straight to "What would you like to send to the attendees?"
    """
    query = update.callback_query
    await query.answer()
    event_data = context.user_data["working_event"]
    waitlist = event_data.get("waitlist", [])

    if not waitlist:
        # No waitlist => just ask for message to Attendees
        text = "What would you like to send to the attendees?"
        # We define a custom pattern for the next step "MESSAGE_RSVP_INPUT"
        buttons = [
            [
                InlineKeyboardButton("<< Back", callback_data=BACK_TO_RSVP_MENU)
            ]
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(text, reply_markup=keyboard)
        # We'll store in context that admin wants to message "attendees" only
        context.user_data["msg_rsvp_whom"] = "attendees"
        return MESSAGE_RSVP_INPUT
    else:
        # We have a waitlist => let them choose "Attendees", "Waitlist", or both
        text = "Select who you would like to message:"
        buttons = [
            [
                InlineKeyboardButton("Attending", callback_data=MESSAGE_ATTENDEES),
                InlineKeyboardButton("Waitlist", callback_data=MESSAGE_WAITLIST),
            ],
            [
                InlineKeyboardButton("<< Back", callback_data=BACK_TO_RSVP_MENU)
            ]
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(text, reply_markup=keyboard)
        return MESSAGE_RSVP_WHOM


async def message_rsvp_whom_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback for the "Attendees" or "Waitlist" button.
    Then we ask for the message text.
    """
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == MESSAGE_ATTENDEES:
        context.user_data["msg_rsvp_whom"] = "attendees"
    elif data == MESSAGE_WAITLIST:
        context.user_data["msg_rsvp_whom"] = "waitlist"
    else:
        # Unknown action
        await query.edit_message_text("Unknown action.")
        return menu.sh

    # Now ask for the message
    text = f"What would you like to send to the {context.user_data['msg_rsvp_whom']}?"
    buttons = [
        [
            InlineKeyboardButton("<< Back", callback_data=BACK_TO_RSVP_MENU)
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(text, reply_markup=keyboard)
    return MESSAGE_RSVP_INPUT


async def message_rsvp_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin typed the message to send to either 'attendees' or 'waitlist'.
    We then DM each user and list the ones we couldn't message.
    """
    # Use text_markdown_v2 or fallback
    msg_text = update.message.text_markdown_v2 or update.message.text
    msg_text = msg_text.strip()
    event_data = context.user_data["working_event"]
    whom = context.user_data.get("msg_rsvp_whom", "attendees")

    # Build a final text with event info + admin text
    final_text = (
        f"✉️  {rsvp.rsvp_header_text(event_data)}\n"

        f"{msg_text}"
    )

    # Identify the relevant list
    if whom == "attendees":
        user_list = event_data.get("attendees", [])
    else:
        user_list = event_data.get("waitlist", [])

    failed = []
    succeeded = 0

    for user_info in user_list:
        chat_id = user_info["user_id"]
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=final_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            succeeded += 1
        except Exception as e:
            print(f"[ERROR] Could not send DM to {chat_id}: {e}")
            failed.append(user_info.get("username") or "UnknownUser")

    # Provide admin with a summary
    text_resp = f"Message sent to {succeeded}/{len(user_list)} {whom}.\n"
    if failed:
        text_resp += "Unable to send to:\n" + ", ".join(failed)

    await update.message.reply_text(text_resp)

    # Return to RSVP menu
    return await menu.show_rsvp_menu(update, context, edit=False)



    
    
    
    
    
    
    
# async def rsvp_menu_keyboard(context: ContextTypes.DEFAULT_TYPE):
#     """
#     Return an InlineKeyboardMarkup object for the RSVP menu.
#     We'll define a function so we can reuse it.
#     """
#     buttons = [
#         [InlineKeyboardButton("View Attending", callback_data="view_attending")],
#         [InlineKeyboardButton("Send Message", callback_data="message_rsvp")],
#         [
#             InlineKeyboardButton("<< Back", callback_data=BACK_TO_EVENT_MENU),
#             InlineKeyboardButton("Main Menu", callback_data=BACK_TO_MAIN_MENU)
#         ]
#     ]
#     return InlineKeyboardMarkup(buttons)


# async def show_rsvp_menu_in_new_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """
#     Use this if we want to send a new message with the RSVP menu,
#     instead of editing the existing message.
#     """
#     event_data = context.user_data["working_event"]
#     text = (
#         f"Event: {event_data['name']}\n"
#         f"Date: {event_data.get('date', 'None')}\n"
#         f"Start: {event_data.get('start_time', 'None')}\n"
#         f"End: {event_data.get('end_time', 'None')}\n"
#         f"Location: {event_data.get('location')}\n"
#         f"Capacity: {event_data.get('capacity', 'None')}\n"
#         f"Announcement: {event_data['announcement_state']}\n"
#         f"Number of Attendees: {len(event_data.get('attendees', []))}\n"
#         "\nWhat would you like to do?"
#     )

#     keyboard = await rsvp_menu_keyboard(context)
#     await update.effective_chat.send_message(text, reply_markup=keyboard)
#     return "RSVP_MENU"

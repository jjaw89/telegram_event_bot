import sys
import os
sys.path.append("..")
import asyncio
import re
from datetime import date, time, datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, Application
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
    ANNOUNCEMENT_EDIT_POSTED_ANNOUNCEMENT_TEXT
)
from config.config import chat_ids
from rsvp import rsvp_header_text
# Callback data constants
CANCEL_NEW_EVENT        = "cancel_new_event"
EDIT_NAME               = "edit_name"
EDIT_DATE               = "edit_date"
EDIT_START_TIME         = "edit_start_time"
EDIT_END_TIME           = "edit_end_time"
EDIT_CAPACITY           = "edit_capacity"
EDIT_ANNOUNCEMENT_TEXT  = "edit_announcement_text"
BACK_TO_EDIT_EVENT_MENU = "back_to_edit_event_menu"
BACK_TO_MAIN_MENU       = "back_to_main_menu"
SHOW_ANNOUNCEMENT_MENU = "show_announcement_menu"
BACK_TO_EVENT_MENU      = "back_to_event_menu"

# “None” style callbacks
NO_DATE                = "no_date"
NO_START_TIME          = "no_start_time"
NO_END_TIME            = "no_end_time"
NO_CAPACITY            = "no_capacity"
NO_ANNOUNCEMENT_TEXT   = "no_announcement_text"

# Announcement callbacks
POST_ANNOUNCEMENT      = "post_announcement"
SHOW_ANNOUNCEMENT_TEXT = "show_announcement_text"
UPDATE_POSTED_ANNOUNCEMENT = "update_posted_announcement"
BACK_TO_ANNOUCEMENT_MENU = "back_to_announcement_menu"
PREVIEW_ANNOUNCEMENT = "preview_announcement"
EDIT_POSTED_ANNOUNCEMENT_TEXT = "edit_posted_announcement_text"
BACK_TO_EVENT_MENU = "back_to_event_menu"

def escape_markdown_v2(text: str) -> str:
    """
    Escapes Markdown V2 special characters in the given text.
    See: https://core.telegram.org/bots/api#markdownv2-style
    """
    # Characters that must be escaped in MarkdownV2:
    # _ * [ ] ( ) ~ ` > # + - = | { } . !
    pattern = r'([\_\*\[\]\(\)\~\`\>\#\+\-\=\|\{\}\.\!])'
    return re.sub(pattern, r'\\\1', text)


async def show_announcement_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=True):
    """Show the announcement menu."""
    buttons = []
    
    if context.user_data["working_event"]["announcement_state"] == "None":
        buttons += [
            [InlineKeyboardButton("Add Announcement Text", callback_data=EDIT_ANNOUNCEMENT_TEXT)]
        ]
    elif context.user_data["working_event"]["announcement_state"] == "Text Saved":
        buttons += [
            [InlineKeyboardButton("Preview Announcement", callback_data=PREVIEW_ANNOUNCEMENT)],
            [InlineKeyboardButton("Edit Announcement Text", callback_data=EDIT_ANNOUNCEMENT_TEXT)],
            [InlineKeyboardButton("Post Announcement", callback_data=POST_ANNOUNCEMENT)]
        ]
    elif context.user_data["working_event"]["announcement_state"] == "Posted":
        buttons += [
            [InlineKeyboardButton("Preview Announcement", callback_data=PREVIEW_ANNOUNCEMENT)],
            [InlineKeyboardButton("Edit Announcement Text", callback_data=EDIT_POSTED_ANNOUNCEMENT_TEXT)],
            [InlineKeyboardButton("Update Posted Announcement", callback_data=UPDATE_POSTED_ANNOUNCEMENT)],
        ]
        
    buttons += [
        [InlineKeyboardButton("<< Back", callback_data=BACK_TO_EVENT_MENU), InlineKeyboardButton("Main Menu", callback_data=BACK_TO_MAIN_MENU)]
    ]
    
    keyboard = InlineKeyboardMarkup(buttons)

    event_data = context.user_data["working_event"]
    
    text = (
        f"Name: {event_data['name']}\n"
        f"Date: {event_data.get('date', 'None')}\n"
        f"Start: {event_data.get('start_time', 'None')}\n"
        f"End: {event_data.get('end_time', 'None')}\n"
        f"Location: {event_data.get('location')}\n"
        f"Capacity: {event_data.get('capacity', 'None')}\n"
        f"Announcement: {event_data['announcement_state']}\n"
        "\nWhat would you like to do?"
    )
    
    query = update.callback_query
    # Edit or send a new message
    if query and edit:
        await query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.effective_chat.send_message(text, reply_markup=keyboard)
        
    return ANNOUNCEMENT_MENU

async def announcement_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the announcement menu callback."""
    query = update.callback_query
    query.answer()
    if query.data == EDIT_ANNOUNCEMENT_TEXT:
        return await edit_annoucement_text(update, context)
    elif query.data == PREVIEW_ANNOUNCEMENT:
        return await generate_announcemnt_preview(update, context)
    elif query.data == SHOW_ANNOUNCEMENT_TEXT:
        return await show_announcement_menu(update, context)
    elif query.data == POST_ANNOUNCEMENT:
        return await post_announcement(update, context)
    elif query.data == EDIT_POSTED_ANNOUNCEMENT_TEXT:
        return await edit_posted_annoucement_text(update, context)
    elif query.data == UPDATE_POSTED_ANNOUNCEMENT:
        return await update_posted_announcement(update, context)
    elif query.data == BACK_TO_EVENT_MENU:
        return await menu.show_event_menu(update, context)
    elif query.data == BACK_TO_MAIN_MENU:
        return await menu.show_main_menu(update, context)
    
async def edit_annoucement_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for the new announcement text."""
    buttons = [
        [
            InlineKeyboardButton("None", callback_data=NO_ANNOUNCEMENT_TEXT), 
            InlineKeyboardButton("<< Back", callback_data=BACK_TO_ANNOUCEMENT_MENU)
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.effective_chat.send_message(
        "What do you want the announcement to say?",
        reply_markup=keyboard
    )
    return ANNOUNCEMENT_EDIT_ANNOUNCEMENT_TEXT

async def edit_announcement_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive user typed announcement text and preserve inline formatting as Markdown V2."""
    # If message contains formatting, text_markdown_v2 includes it as valid Markdown V2
    # fallback to plain text if that property is None
    announcement_text = update.message.text_markdown_v2 or update.message.text

    announcement_text = announcement_text.strip()

    context.user_data["working_event"]["announcement_state"] = "Text Saved"
    context.user_data["working_event"]["announcement_text"] = announcement_text
    save_working_event(context)

    await update.message.reply_text("Announcement text updated.")
    return await show_announcement_menu(update, context)

async def edit_announcement_text_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'None' or '<< Back' for announcement text."""
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == NO_ANNOUNCEMENT_TEXT:
        context.user_data["working_event"]["announcement_state"] = "None"
        context.user_data["working_event"]["announcement_text"] = ""

        save_working_event(context)

        await query.edit_message_text("Announcement text set to None.")
        return await show_announcement_menu(update, context)

    elif data == BACK_TO_ANNOUCEMENT_MENU:
        return await show_announcement_menu(update, context)

    await query.edit_message_text("Unknown action.")
    return MY_EVENTS

def generate_announcement_message(context: ContextTypes.DEFAULT_TYPE, event_data_override=False):
    """Generate a preview of the announcement."""
    if event_data_override:
        event_data = event_data_override
    else:
        event_data = context.user_data["working_event"]

    # text = f"📢  __*Announcement for {event_data['name']}*__ 📢 \n\n"
    # if event_data["date"] != "None":
    #     event_date = date.fromisoformat(event_data["date"])
    #     text += f"*Date: {event_date.strftime('%A, %B %d, %Y')}*\n"
    # if event_data["start_time"] != "None" and event_data["end_time"] == "None":
    #     start_time = datetime.strptime(event_data["start_time"], "%H:%M")
    #     text += f"*Start Time: {start_time.strftime('%I:%M %p')}*\n"
    # if event_data["start_time"] == "None" and event_data["end_time"] != "None":
    #     end_time = datetime.strptime(event_data["end_time"], "%H:%M")
    #     text += f"*End Time: {end_time.strftime('%I:%M %p')}*\n"
    # if event_data["start_time"] != "None" and event_data['end_time'] != "None":
    #     start_time = datetime.strptime(event_data['start_time'], "%H:%M")
    #     end_time = datetime.strptime(event_data['end_time'], "%H:%M")
    #     text += f"*Time: {start_time.strftime('%I:%M %p')} \- {end_time.strftime('%I:%M %p')}*\n"
    # if event_data["location"] != "None":
    #     text += f"*Location: {event_data['location']}*\n"
    
    text = "📢  " + rsvp_header_text(event_data)
    if event_data["has_capacity"]:
        text += f"*Capacity: {event_data['capacity']}*\n"
    text += f"\n"

    text += f"{event_data['announcement_text']}\n\n"

    if event_data['has_capacity']:
        text += f"*Attending: {len(event_data['attendees'])}/{event_data['capacity']}*\n"
    else:
        text += f"*Attending: {len(event_data['attendees'])}*\n"
    
    if len(event_data["attendees"]) > 0:
        for i in range(len(event_data["attendees"])-1):
            text += escape_markdown_v2(f"@{event_data['attendees'][i]['username']}, ")
        text += escape_markdown_v2(f"@{event_data['attendees'][-1]['username']}")
        text += "\n"
    
    if len(event_data["waitlist"]) > 0:
        text += "\n"
        text += f"*Waitlist: {len(event_data['waitlist'])}*\n"
        for i in range(len(event_data['waitlist'])-1):
            text += escape_markdown_v2(f"@{event_data['waitlist'][i]['username']}, ")
        text += escape_markdown_v2(f"@{event_data['waitlist'][-1]['username']}")
        text += "\n"
    
    text += "\n"
        
    text += ("_*To RSVP:*_\n"
             "\- _Make sure that you have messaged @VictoriaPups\_events\_bot before\._\n"
             "\- _Press the RSVP button below\._\n"
             "\- _You will receive a confirmation message from @VictoriaPups\_events\_bot if you are successfully RSVP'd\._\n"
             "\- _If you are unable to attend, please press the Cancel RSVP button in your confirmation message\._\n"
             "\- _Please message @Repeating1s if you have any questions or need help\._\n\n"
             "_*Note: The bot can only message you and accept your RSVP if you have started a conversation with it first\.*_\n"
             )
    
    if not event_data["has_capacity"]:
        buttons = [[InlineKeyboardButton("RSVP", callback_data=f"rsvp:{event_data['id']}")]]
    elif len(event_data["attendees"]) < event_data["capacity"]:
        buttons = [[InlineKeyboardButton("RSVP", callback_data=f"rsvp:{event_data['id']}")]]
    else:
        buttons = [[InlineKeyboardButton("Join Waitlist", callback_data=f"rsvp:{event_data['id']}")]]
    
    keyboard = InlineKeyboardMarkup(buttons)
    
    return text, keyboard

async def generate_announcemnt_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a preview of the announcement."""

    # Generate the announcement text
    text, keyboard = generate_announcement_message(context)  # Ensure this function is implemented correctly
    
    await update.effective_chat.send_message(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard)

    return await show_announcement_menu(update, context, edit=False)

def generate_group_rsvp_button(context: ContextTypes.DEFAULT_TYPE, event_data_override=False):
    """Generate the group RSVP button."""
    if event_data_override:
        event_data = event_data_override
    else:
        event_data = context.user_data["working_event"]
    
    rsvp_text = (
        f"{rsvp_header_text(event_data)}\n"
        f"Press the button below to RSVP\.\n\n"
        f"_*Note: The bot can only message you and accept your RSVP if you have started a conversation with it first\.*_\n"
    )
    _, keyboard = generate_announcement_message(context, event_data)
    
    return rsvp_text, keyboard

async def post_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Post the announcement to the event channel, then wait 5 seconds and send the group RSVP button."""
    event_data = context.user_data["working_event"]

    # 1. Generate the announcement text & keyboard
    text, keyboard = generate_announcement_message(context)  # your function that returns (text, keyboard)

    try:
        # Change the bots name to the event name when they post the rsvp button and then change it back to what it was before
        # change the bot's name to the event name
        
        
        # 2. Post to the announcement channel
        sent_message = await context.bot.send_message(
            chat_id=chat_ids["announcements"],
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard
        )

        # 3. Update event data
        event_data["announcement_state"] = "Posted"
        event_data["announcement_message_id"] = sent_message.message_id
        event_data["announcement_message_chat_id"] = sent_message.chat.id
        save_working_event(context)

        # 4. Notify the admin of success
        query = update.callback_query
        if query:
            # Edit the admin’s inline menu to say “posted”
            await query.edit_message_text("Announcement posted.\n\nThe RSVP button will be posted in 5 seconds...")
        else:
            await update.effective_chat.send_message("Announcement posted.\n\nThe RSVP button will be posted in 5 seconds...")

        # 5. Wait 5 seconds (this is synchronous - the user is effectively blocked)
        await asyncio.sleep(5)

        # We genegate the RSVP button and post it to the group chat
        rsvp_text, group_keyboard = generate_group_rsvp_button(context, event_data)

        sent_button = await context.bot.send_message(
            chat_id=chat_ids["group"],
            text=rsvp_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=group_keyboard
        )

        # Optionally store the new button info
        event_data["group_rsvp_button_message_id"] = sent_button.message_id
        event_data["group_rsvp_button_chat_id"] = sent_button.chat.id
        save_working_event(context)

        # 7. Let the admin know the button is posted
        await update.effective_chat.send_message("RSVP button posted to the group.")

    except Exception as e:
        print(f"[ERROR] Failed to post announcement: {e}")
        await update.effective_chat.send_message(
            "Failed to post the announcement or RSVP button. Check the bot's permissions."
        )

    return await show_announcement_menu(update, context)


async def update_posted_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit the posted announcement in the channel and optionally update the RSVP message in the group."""
    event_data = context.user_data["working_event"]

    # 1. Generate the updated announcement text & keyboard
    text, keyboard = generate_announcement_message(context)  # your existing function

    # 2. Edit the channel announcement
    try:
        await context.bot.edit_message_text(
            chat_id=event_data["announcement_message_chat_id"],
            message_id=event_data["announcement_message_id"],
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

        query = update.callback_query
        if query:
            await query.edit_message_text("Announcement updated.")
        else:
            await update.effective_chat.send_message("Announcement updated.")

    except Exception as e:
        print(f"[ERROR] Failed to edit announcement in the channel: {e}")
        await update.effective_chat.send_message(
            "Failed to edit the announcement in the channel. Please check permissions."
        )

    # 3. Optionally update the RSVP button in the group if we have those fields
    #    (assuming you store them in `event_data` as something like "group_rsvp_chat_id" & "group_rsvp_button_id")
    if "group_rsvp_button_chat_id" in event_data and "group_rsvp_button_message_id" in event_data:
        try:
            # Build your RSVP text and inline keyboard again (or a new one, up to you)
            rsvp_text = (
                f"Press the button below to RSVP:\n"
                f"{rsvp_header_text(event_data)}"   # e.g. build a short text with event info
            )
            
            # Generate the announcement keyboard
            rsvp_text, keyboard = generate_group_rsvp_button(context, event_data)  # your function that returns (text, keyboard)

            await context.bot.edit_message_text(
                chat_id=event_data["group_rsvp_button_chat_id"],
                message_id=event_data["group_rsvp_button_message_id"],
                text=rsvp_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
            print("RSVP button in group chat updated successfully.")

        except Exception as ex:
            print(f"[ERROR] Failed to edit RSVP message in group chat: {ex}")
            # It's optional whether you notify the admin or not. 
            await update.effective_chat.send_message(
                "Failed to update the RSVP button in the group. Please check permissions."
            )

    return await show_announcement_menu(update, context)


async def edit_posted_annoucement_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for the new announcement text."""
    buttons = [
        [
            InlineKeyboardButton("<< Back", callback_data=BACK_TO_ANNOUCEMENT_MENU)
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.effective_chat.send_message(
        "What do you want the announcement to say?",
        reply_markup=keyboard
    )
    return ANNOUNCEMENT_EDIT_POSTED_ANNOUNCEMENT_TEXT

async def edit_posted_announcement_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    This handles the user’s typed message 
    (so update.callback_query is None).
    """
    # e.g. text_markdown_v2 or plain text
    announcement_text = update.message.text_markdown_v2 or update.message.text
    announcement_text = announcement_text.strip()

    context.user_data["working_event"]["announcement_state"] = "Posted"
    context.user_data["working_event"]["announcement_text"] = announcement_text
    save_working_event(context)

    await update.message.reply_text("Announcement text updated.")
    return await show_announcement_menu(update, context)


async def edit_posted_announcement_text_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    This handles inline keyboard button presses 
    (so update.callback_query is not None).
    """
    query = update.callback_query
    if query is None:
        # If somehow triggered by a message, handle gracefully
        await update.effective_chat.send_message("Invalid action. Please use the menu buttons.")
        return await show_announcement_menu(update, context)

    data = query.data
    await query.answer()

    if data == BACK_TO_ANNOUCEMENT_MENU:
        return await show_announcement_menu(update, context)
    else:
        await query.edit_message_text("Unknown action.")
        return await show_announcement_menu(update, context, edit=False)

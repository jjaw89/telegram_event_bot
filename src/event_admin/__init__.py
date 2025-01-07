# event_admin/__init__.py

from telegram import Update
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

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
    MESSAGE_RSVP_WHOM,
    MESSAGE_RSVP_INPUT,
    ASK_CLOSE_EVENT
)

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
EDIT_POSTED_ANNOUNCEMENT = "edit_posted_announcement"
BACK_TO_ANNOUCEMENT_MENU = "back_to_announcement_menu"
PREVIEW_ANNOUNCEMENT = "preview_announcement"

# rsvp_admin callbacks
BACK_TO_RSVP_MENU = "back_to_rsvp_menu"



# Then import these modules.
from event_admin import menu, edit_event, announcement, rsvp_admin, close
import rsvp


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop command."""
    await update.message.reply_text("Okay, bye.")
    return ConversationHandler.END

def get_eventadmin_handlers():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("eventadmin", menu.start_eventadmin)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(menu.main_menu_callback)
            ],
            NEW_EVENT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, menu.new_event_name_input),
                CallbackQueryHandler(menu.ask_new_event_name_callback, pattern='^cancel_new_event$')
            ],
            MY_EVENTS: [
                CallbackQueryHandler(menu.my_events_callback)
                # CallbackQueryHandler(menu.main_menu_callback, pattern='^'+BACK_TO_MAIN_MENU+'$')
            ],
            EVENT_MENU: [
                CallbackQueryHandler(menu.event_menu_callback),
            ],
            EDIT_EVENT_MENU: [
                CallbackQueryHandler(menu.edit_event_menu_callback)
            ],
            EDIT_EVENT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_event.edit_event_name_input),
                CallbackQueryHandler(menu.show_event_edit_menu, pattern='^'+BACK_TO_EDIT_EVENT_MENU+'$')
            ],
            EDIT_EVENT_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_event.edit_event_date_input),
                CallbackQueryHandler(edit_event.edit_event_date_callback)
            ],
            EDIT_EVENT_START_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_event.edit_event_start_time_input),
                CallbackQueryHandler(edit_event.edit_event_start_time_callback)
            ],
            EDIT_EVENT_END_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_event.edit_event_end_time_input),
                CallbackQueryHandler(edit_event.edit_event_end_time_callback)
            ],
            EDIT_EVENT_CAPACITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_event.edit_event_capacity_input),
                CallbackQueryHandler(edit_event.edit_event_capacity_callback)
            ],
            EDIT_EVENT_LOCATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_event.edit_event_location_input),
                CallbackQueryHandler(edit_event.edit_event_location_callback)
            ],
            ANNOUNCEMENT_MENU: [
                CallbackQueryHandler(announcement.announcement_menu_callback)
            ],
            ANNOUNCEMENT_EDIT_ANNOUNCEMENT_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, announcement.edit_announcement_text_input),
                CallbackQueryHandler(announcement.edit_announcement_text_callback)
            ],
            ANNOUNCEMENT_EDIT_POSTED_ANNOUNCEMENT_TEXT: [
                # If the user types text, go to edit_posted_announcement_text_input
                MessageHandler(filters.TEXT & ~filters.COMMAND, announcement.edit_posted_announcement_text_input),
                # If the user presses an inline button, go to edit_posted_announcement_text_callback
                CallbackQueryHandler(announcement.edit_posted_announcement_text_callback)
            ],
            RSVP_MENU: [
                CallbackQueryHandler(menu.rsvp_menu_callback)
                ],
            MESSAGE_RSVP_WHOM: [
                CallbackQueryHandler(rsvp_admin.message_rsvp_whom_callback, pattern='^(msg_attendees|msg_waitlist)$'),
                CallbackQueryHandler(menu.event_menu_callback, pattern='^'+BACK_TO_RSVP_MENU+'$'),
            ],
            MESSAGE_RSVP_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, rsvp_admin.message_rsvp_input),
                # The "Back" button in that state => go back to rsvp menu
                CallbackQueryHandler(menu.event_menu_callback, pattern='^'+BACK_TO_RSVP_MENU+'$'),
            ],
            ASK_CLOSE_EVENT: [
                CallbackQueryHandler(close.ask_to_close_event_callback)
            ]
        },
        fallbacks=[CommandHandler("stop", stop_command)],
        allow_reentry=True
    )

    return conv_handler

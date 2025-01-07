# event_admin/edit_event.py

import re
from datetime import date, time, datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters

from event_admin.data_manager import save_events, save_working_event
# Import the shared constants
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
    EDIT_EVENT_LOCATION
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

# “None” style callbacks
NO_DATE                = "no_date"
NO_START_TIME          = "no_start_time"
NO_END_TIME            = "no_end_time"
NO_CAPACITY            = "no_capacity"
NO_ANNOUNCEMENT_TEXT   = "no_announcement_text"
NO_LOCATION            = "no_location"


# We only import the function(s) we need from menu
import event_admin.menu as menu

#
# -----------
# Name
# -----------
#

async def edit_event_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for the new event name."""
    buttons = [
        [InlineKeyboardButton("<< Back", callback_data=BACK_TO_EDIT_EVENT_MENU)]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await update.effective_chat.send_message(
        "What is the new name of the event?",
        reply_markup=keyboard
    )
    return EDIT_EVENT_NAME

async def edit_event_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives user-typed name; updates the event."""
    event_name = update.message.text.strip()

    # Check duplicates
    for e in context.bot_data.get("events", []):
        if e["name"].lower() == event_name.lower():
            await update.message.reply_text(
                "An event with that name already exists. Choose a different name."
            )
            return EDIT_EVENT_NAME
    
    # Edits the working event
    context.user_data["working_event"]["name"] = event_name
    
    # Update the corresponding event in bot_data
    for e in context.bot_data["events"]:
        if e["id"] == context.user_data["working_event"]["id"]:
            e["name"] = event_name
            break
    
    # Save the updated events list
    save_events(context.bot_data)
    
    await update.message.reply_text(f"Event name updated to '{event_name}'.")
    return await menu.show_event_edit_menu(update, context)  # Go back to the edit menu

#
# -----------
# Date
# -----------
#

async def edit_event_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for the date of the event."""
    buttons = [
        [
            InlineKeyboardButton("None", callback_data=NO_DATE),
            InlineKeyboardButton("<< Back", callback_data=BACK_TO_EDIT_EVENT_MENU)
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.effective_chat.send_message(
        "What is the date of the event? e.g. 2025-01-17",
        reply_markup=keyboard
    )
    return EDIT_EVENT_DATE

async def edit_event_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive user-typed date."""
    date_text = update.message.text.strip()

    # Checks that the input is valid
    try:
        date.fromisoformat(date_text)
    except:
        buttons = [
            [
                InlineKeyboardButton("None", callback_data=NO_DATE),
                InlineKeyboardButton("<< Back", callback_data=BACK_TO_EDIT_EVENT_MENU)
            ]
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        await update.effective_chat.send_message("Invalid date format. Please use DD/MM/YYYY", reply_markup=keyboard)
        return EDIT_EVENT_DATE
        
    context.user_data["working_event"]["date"] = date_text

    save_working_event(context)

    await update.message.reply_text(f"Date set to '{date_text}'.")
    return await menu.show_event_edit_menu(update, context)

async def edit_event_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses when editing date (None, << Back, etc.)."""
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == NO_DATE:
        # Set the event date to None
        context.user_data["working_event"]["date"] = None
        save_working_event(context)
        return await menu.show_event_edit_menu(update, context)

    elif data == BACK_TO_EDIT_EVENT_MENU:
        return await menu.show_event_edit_menu(update, context)

    # Otherwise
    await query.edit_message_text("Unknown action.")
    return MY_EVENTS

#
# -----------
# Start Time
# -----------
#

async def edit_event_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for the event start time."""
    buttons = [
        [
            InlineKeyboardButton("None", callback_data=NO_START_TIME),
            InlineKeyboardButton("<< Back", callback_data=BACK_TO_EDIT_EVENT_MENU)
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.effective_chat.send_message(
        "What time does the event start? (HH:MM in 24h format)",
        reply_markup=keyboard
    )
    return EDIT_EVENT_START_TIME

async def edit_event_start_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive user-typed start time."""
    start_time = update.message.text.strip()
    # Validate or parse as needed timespec = 'minutes': Include hour and minute in HH:MM format.
    # Checks that the input is valid

    try:
        # Validate that input is in HH:MM format
        datetime.strptime(start_time, "%H:%M")
    except ValueError:
        buttons = [
            [
                InlineKeyboardButton("None", callback_data=NO_DATE),
                InlineKeyboardButton("<< Back", callback_data=BACK_TO_EDIT_EVENT_MENU)
            ]
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        await update.effective_chat.send_message(
            "Invalid time format. Please use HH:MM.",
            reply_markup=keyboard
        )
        return EDIT_EVENT_START_TIME

            
    context.user_data["working_event"]["start_time"] = start_time
    
    save_working_event(context)
    
    await update.message.reply_text(f"Start time set to {start_time}.")
    return await menu.show_event_edit_menu(update, context)

async def edit_event_start_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'None' or '<< Back' for start time."""
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == NO_START_TIME:
        context.user_data["working_event"]["start_time"] = None
        save_working_event(context)

        await query.edit_message_text("Start time set to None.")
        return await menu.show_event_edit_menu(update, context)

    elif data == BACK_TO_EDIT_EVENT_MENU:
        return await menu.show_event_edit_menu(update, context)

    await query.edit_message_text("Unknown action.")
    return MY_EVENTS


#
# -----------
# End Time
# -----------
#

async def edit_event_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for the event end time."""
    buttons = [
        [
            InlineKeyboardButton("None", callback_data=NO_END_TIME),
            InlineKeyboardButton("<< Back", callback_data=BACK_TO_EDIT_EVENT_MENU)
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.effective_chat.send_message(
        "What time does the event end? (HH:MM in 24h format)",
        reply_markup=keyboard
    )
    return EDIT_EVENT_END_TIME

async def edit_event_end_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive user-typed end time."""
    end_time = update.message.text.strip()
    # Validate or parse as needed timespec = 'minutes': Include hour and minute in HH:MM format.
    # Checks that the input is valid

    try:
        # Validate that input is in HH:MM format
        datetime.strptime(end_time, "%H:%M")
    except ValueError:
        buttons = [
            [
                InlineKeyboardButton("None", callback_data=NO_DATE),
                InlineKeyboardButton("<< Back", callback_data=BACK_TO_EDIT_EVENT_MENU)
            ]
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        await update.effective_chat.send_message(
            "Invalid time format. Please use HH:MM.",
            reply_markup=keyboard
        )
        return EDIT_EVENT_START_TIME

            
    context.user_data["working_event"]["end_time"] = end_time
    
    save_working_event(context)
    
    await update.message.reply_text(f"Start time set to {end_time}.")
    return await menu.show_event_edit_menu(update, context)

async def edit_event_end_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'None' or '<< Back' for end time."""
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == NO_END_TIME:
        context.user_data["working_event"]["end_time"] = None
        save_working_event(context)

        await query.edit_message_text("End time set to None.")
        return await menu.show_event_edit_menu(update, context)

    elif data == BACK_TO_EDIT_EVENT_MENU:
        return await menu.show_event_edit_menu(update, context)

    await query.edit_message_text("Unknown action.")
    return MY_EVENTS


#
# -----------
# Capacity
# -----------
#

async def edit_event_capacity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for the event capacity."""
    buttons = [
        [
            InlineKeyboardButton("None", callback_data=NO_CAPACITY),
            InlineKeyboardButton("<< Back", callback_data=BACK_TO_EDIT_EVENT_MENU)
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.effective_chat.send_message(
        "What is the capacity of the event? (Enter a number)",
        reply_markup=keyboard
    )
    return EDIT_EVENT_CAPACITY

async def edit_event_capacity_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive user-typed capacity."""
    text = update.message.text.strip()
    if not text.isdigit():
        if int(text) > 0:
            await update.message.reply_text("Please enter a valid capacity.")
            return EDIT_EVENT_CAPACITY

    capacity = int(text)
    context.user_data["working_event"]["has_capacity"] = True
    context.user_data["working_event"]["capacity"] = capacity

    save_working_event(context)

    await update.message.reply_text(f"Capacity set to {capacity}.")
    return await menu.show_event_edit_menu(update, context)

async def edit_event_capacity_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'None' or '<< Back' for capacity."""
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == NO_CAPACITY:
        context.user_data["working_event"]["has_capacity"] = False
        context.user_data["working_event"]["capacity"] = 65536 # When an event goes from having a capacity to no capacity, we need to run update waitlist. That needs capacity to be a big number.
        save_working_event(context)

        await query.edit_message_text("Capacity set to None.")
        return await menu.show_event_edit_menu(update, context)

    elif data == BACK_TO_EDIT_EVENT_MENU:
        return await menu.show_event_edit_menu(update, context)

    await query.edit_message_text("Unknown action.")
    return MY_EVENTS

#
# -----------
# Announcement Text
# -----------
#

async def edit_event_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for the new announcement text."""
    
    text = (
        "Where will the event be located? You may optionally include a google maps link.\n"
        "<location name> or <location name>;<google maps link>"
    )
    buttons = [
        [
            InlineKeyboardButton("To be announced", callback_data=NO_LOCATION), 
            InlineKeyboardButton("<< Back", callback_data=BACK_TO_EDIT_EVENT_MENU)
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.effective_chat.send_message(text,reply_markup=keyboard)
    return EDIT_EVENT_LOCATION

async def edit_event_location_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive user typed location and possibly the google maps link."""
    location_text = update.message.text.strip()
    # Check if the user has entered a google maps link
    if ";" in location_text:
        location_text, location_link = location_text.split(";")
        # Remove spaces from the start or end of the strings
        location_text = location_text.strip()
        location_link = location_link.strip()
        context.user_data["working_event"]["location"] = location_text
        context.user_data["working_event"]["location_link"] = location_link
    else:
        location_text = location_text.strip()
        context.user_data["working_event"]["location"] = location_text
        context.user_data["working_event"]["location_link"] = None
        
    save_working_event(context)

    await update.message.reply_text("Location updated.")
    return await menu.show_event_edit_menu(update, context)

async def edit_event_location_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'None' or '<< Back' for location."""
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == NO_LOCATION:
        context.user_data["working_event"]["location"] = "To be announced"

        save_working_event(context)

        await query.edit_message_text("Location set to 'To be announced'.")
        return await menu.show_event_edit_menu(update, context)

    elif data == BACK_TO_EDIT_EVENT_MENU:
        return await menu.show_event_edit_menu(update, context)

    await query.edit_message_text("Unknown action.")
    return MY_EVENTS

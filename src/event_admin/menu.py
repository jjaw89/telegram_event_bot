import sys
import os
sys.path.append("..")

from config.config import event_admins
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
from event_admin.data_manager import is_event_admin, save_events, load_events
from event_admin import edit_event, announcement, rsvp_admin
import rsvp as rsvp
from event_admin.close import ask_to_close_event

# Now import from your constants
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
    RSVP_MENU
)

# Callback data constants
CANCEL_NEW_EVENT        = "cancel_new_event"
EDIT_NAME               = "edit_name"
EDIT_DATE               = "edit_date"
EDIT_START_TIME         = "edit_start_time"
EDIT_END_TIME           = "edit_end_time"
EDIT_CAPACITY           = "edit_capacity"
EDIT_LOCATION           = "edit_location"
BACK_TO_EDIT_EVENT_MENU = "back_to_edit_event_menu"
BACK_TO_EVENT_MENU      = "back_to_event_menu"
BACK_TO_MAIN_MENU       = "back_to_main_menu"
SHOW_ANNOUNCEMENT_MENU = "show_announcement_menu"
BACK_TO_MY_EVENTS   = "back_to_my_events"
SHOW_RSVP_MENU    = "show_rsvp_menu"
VIEW_ATTENDING = "view_attending"
MESSEAGE_RSVP = "message_rsvp"
BACK_TO_RSVP_MENU_NEW_MESSAGE = "back_to_rsvp_menu_new_message"
UPDATE_WAITLIST = "update_waitlist"
CLOSE_EVENT = "close_event"

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

def generate_event_headers(event_data):
    """Generate a string with event details."""
    
    text = (
        f"{event_data['name']}\n"
        f"Date: {event_data.get('date', 'None')}\n"
        f"Start: {event_data.get('start_time', 'None')}\n"
        f"End: {event_data.get('end_time', 'None')}\n"
        f"Location: {event_data.get('location')}\n"
    )
    if event_data["has_capacity"]:
        text += f"Capacity: {event_data.get('capacity', 'None')}\n"
    else:
        text += "Capacity: None\n"
    text += (
        f"Announcement: {event_data['announcement_state']}\n"
        f"Number of Attendees: {len(event_data['attendees'])}\n"
    )
    if event_data["waitlist"] != []:
        text += f"Number of Waitlist: {len(event_data['waitlist'])}\n"
    
    return text

async def start_eventadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command: check admin rights and ensure a private chat."""
    user_id = update.effective_user.id
    if not is_event_admin(user_id):
        await update.message.reply_text("You are not authorized to use this command.")
        return ConversationHandler.END

    if update.effective_chat.type != "private":
        await update.message.reply_text("Please use this command in a private chat.")
        return ConversationHandler.END

    return await show_main_menu(update, context)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit = True):
    """Display the main menu with inline buttons."""
    buttons = [
        [InlineKeyboardButton("New Event", callback_data="new_event")],
        [InlineKeyboardButton("Events", callback_data="my_events")],
        [InlineKeyboardButton("Close", callback_data="close")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    user_name = update.effective_user.first_name
    text = f"Welcome {user_name}, please select an option:"

    if update.callback_query and edit:
        # If this is a callback, edit the existing message
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        # Otherwise, send a new message
        await update.effective_chat.send_message(text, reply_markup=keyboard)

    return MAIN_MENU


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callbacks from the main menu."""
    query = update.callback_query
    data = query.data
    await query.answer()
    

    if data == "new_event":
        # Move to asking for a new event name
        return await ask_new_event_name(update, context)

    elif data == "my_events":
        return await show_my_events(update, context)

    elif data == "close":
        # End conversation
        await query.edit_message_text("Okay, bye.")
        return ConversationHandler.END

    else:
        await query.edit_message_text("Unknown command.")
        return MAIN_MENU


async def ask_new_event_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask the user for the event name."""
    # Prepare a place to store the new event info
    context.user_data["new_event"] = {}

    buttons = [[InlineKeyboardButton("Cancel", callback_data=CANCEL_NEW_EVENT)]]
    keyboard = InlineKeyboardMarkup(buttons)

    # Must send a new message here because user must type the name in response
    await update.effective_chat.send_message(
        "What is the name of the event?",
        reply_markup=keyboard
    )
    return NEW_EVENT_NAME


async def new_event_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user text input for the new event's name."""
    event_name = update.message.text.strip()

    # Check duplicates
    events = context.bot_data.get("events", [])
    for e in events:
        if e["name"].lower() == event_name.lower():
            await update.message.reply_text("An event with that name already exists. Please choose a different name.")
            return NEW_EVENT_NAME

    # Assign an ID
    new_id = max([e["id"] for e in events], default=0) + 1

    # Build the new event dictionary
    event_data = {
        "id": new_id,
        "show": True,
        "name": event_name,
        "date": "None",
        "start_time" : "None",
        "end_time" : "None",
        "has_capacity" : False,
        "capacity": 65536,
        "location": "None",
        "announcement_state": "None",
        "announcement_text": "",
        "announcement_show_capacity": False,
        "announcement_show_num_attendees": True,
        "announcement_include_rsvp": True,
        "num_attendees": 0,
        "attendees": [],
        "waitlist": []
    }

    # Add the new event to the list
    events.append(event_data)
    context.bot_data["events"] = events  # update in memory
    # Set the working event
    context.user_data["working_event"] = event_data

    # SAVE the events to your JSON file
    save_events(context)

    # Now show the Edit Event menu. Must send a new message (user typed the event name).
    return await show_event_edit_menu(update, context)


async def ask_new_event_name_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'cancel' new event => go back to main menu."""
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == CANCEL_NEW_EVENT:
        return await show_main_menu(update, context)
    # If there's another callback scenario, handle it here.


async def show_my_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a list of the user's events."""
    events = context.bot_data.get("events", [])

    if not events:
        text = "There are no events yet."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Main Menu", callback_data=BACK_TO_MAIN_MENU)]
        ])
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard)
        else:
            await update.message.reply_text(text, reply_markup=keyboard)
        return MY_EVENTS

    # Create a button for each event => callback "select_event_<id>"
    buttons = [
        [InlineKeyboardButton(ev["name"], callback_data=f"select_event_{ev['id']}")]
        for ev in events if ev["show"] == True
    ]
    # Add a main menu button
    buttons.append([InlineKeyboardButton("Main Menu", callback_data=BACK_TO_MAIN_MENU)])

    text = "Here are the saved events:"
    keyboard = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)

    return MY_EVENTS


async def my_events_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the callback from 'My Events' menu."""
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == BACK_TO_MAIN_MENU:
        return await show_main_menu(update, context)

    if data.startswith("select_event_"):
        # Load the chosen event into working_event
        event_id = int(data.split("_")[-1])
        events = context.bot_data.get("events", [])
        selected_event = next((ev for ev in events if ev["id"] == event_id), None)
        if not selected_event:
            await query.edit_message_text("Selected event not found.")
            return MY_EVENTS

        context.user_data["working_event"] = selected_event
        return await show_event_menu(update, context)

    # If unknown
    await query.edit_message_text("Unknown action.")
    return MY_EVENTS


async def show_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show the event menu for the selected event stored in user_data["working_event"].
    We want to UPDATE the existing message if coming from a callback.
    """
    query = update.callback_query
    event_data = context.user_data["working_event"]

    text = generate_event_headers(event_data)
    text += ("\nWhat would you like to do?")

    buttons = [
        [InlineKeyboardButton("Edit Event", callback_data=BACK_TO_EDIT_EVENT_MENU)],
        [InlineKeyboardButton("Announcement Menu", callback_data=SHOW_ANNOUNCEMENT_MENU)],
    ]
    if len(event_data["attendees"]) > 0 or len(event_data["waitlist"]) > 0:
        buttons.append([InlineKeyboardButton("RSVP", callback_data=SHOW_RSVP_MENU)])    
    
    buttons += [[InlineKeyboardButton("Close Event", callback_data=CLOSE_EVENT)]]
    buttons += [
        [InlineKeyboardButton("<< Back", callback_data=BACK_TO_MY_EVENTS), InlineKeyboardButton("Main Menu", callback_data=BACK_TO_MAIN_MENU)]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # Edit or send a new message
    if query:
        await query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.effective_chat.send_message(text, reply_markup=keyboard)

    # We'll reuse MY_EVENTS state or define a new one if you prefer
    return EVENT_MENU   


async def event_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callbacks from the single event menu."""
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == BACK_TO_EDIT_EVENT_MENU:
        return await show_event_edit_menu(update, context)
    elif data == SHOW_ANNOUNCEMENT_MENU:
        return await announcement.show_announcement_menu(update, context)
    elif data == SHOW_RSVP_MENU:
        return await show_rsvp_menu(update, context)
    elif data == CLOSE_EVENT:
        return await ask_to_close_event(update, context)
    elif data == BACK_TO_MAIN_MENU:
        return await show_main_menu(update, context)
    elif data == BACK_TO_MY_EVENTS:
        return await show_my_events(update, context)

    await query.edit_message_text("Unknown action.")
    return MY_EVENTS


async def show_event_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the 'Edit Event' menu with more details, letting user choose what to edit."""
    query = update.callback_query
    event_data = context.user_data["working_event"]

    text = generate_event_headers(event_data)
    text += ("\nWhat would you like to edit?")

    buttons = [
        [InlineKeyboardButton("Name", callback_data=EDIT_NAME), InlineKeyboardButton("Date", callback_data=EDIT_DATE)],
        [InlineKeyboardButton("Start Time", callback_data=EDIT_START_TIME), InlineKeyboardButton("End Time", callback_data=EDIT_END_TIME)],
        [InlineKeyboardButton("Capacity", callback_data=EDIT_CAPACITY), InlineKeyboardButton("Location", callback_data=EDIT_LOCATION)],
        [InlineKeyboardButton("<< Back", callback_data=BACK_TO_EVENT_MENU), InlineKeyboardButton("Main Menu", callback_data=BACK_TO_MAIN_MENU)]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # If coming from a callback, edit the existing message
    if query:
        await query.edit_message_text(text, reply_markup=keyboard)
    else:
        # If user typed a command or we just finished creating a new event
        # we must send a new message
        await update.effective_chat.send_message(text, reply_markup=keyboard)

    return EDIT_EVENT_MENU


async def edit_event_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback for the 'Edit Event' menu."""
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == EDIT_NAME:
        return await edit_event.edit_event_name(update, context)
    elif data == EDIT_DATE:
        return await edit_event.edit_event_date(update, context)
    elif data == EDIT_START_TIME:
        return await edit_event.edit_event_start_time(update, context)
    elif data == EDIT_END_TIME:
        return await edit_event.edit_event_end_time(update, context)
    elif data == EDIT_CAPACITY:
        return await edit_event.edit_event_capacity(update, context)
    elif data == EDIT_LOCATION:
        return await edit_event.edit_event_location(update, context)
    elif data == BACK_TO_MAIN_MENU:
        return await show_main_menu(update, context)
    elif data == BACK_TO_EVENT_MENU:
        return await show_event_menu(update, context)

    await query.edit_message_text("Unknown action.")
    return EDIT_EVENT_MENU


async def show_rsvp_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit = True):
    """Show the RSVP menu for the selected event."""
    event_data = context.user_data["working_event"]
    text = generate_event_headers(event_data)
    text += ("\nWhat would you like to do?")

    buttons = [
        [InlineKeyboardButton("View Attendees", callback_data=VIEW_ATTENDING)],
        [InlineKeyboardButton("Send Message", callback_data=MESSEAGE_RSVP)],
        [InlineKeyboardButton("Update Waitlist", callback_data=UPDATE_WAITLIST)],
        [InlineKeyboardButton("<< Back", callback_data=BACK_TO_EVENT_MENU), InlineKeyboardButton("Main Menu", callback_data=BACK_TO_MAIN_MENU)]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    if edit:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.effective_chat.send_message(text, reply_markup=keyboard)
    return RSVP_MENU

async def rsvp_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callbacks from the RSVP menu."""
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == VIEW_ATTENDING:
        return await rsvp_admin.view_attending(update, context)
    elif data == MESSEAGE_RSVP:
        return await rsvp_admin.message_rsvp(update, context)
    elif data == UPDATE_WAITLIST:
        await rsvp.promote_from_waitlist(update, context, context.user_data["working_event"])
        return await show_rsvp_menu(update, context, edit=False)
    elif data == BACK_TO_EVENT_MENU:
        return await show_event_menu(update, context)
    elif data == BACK_TO_MAIN_MENU:
        return await show_main_menu(update, context)
    # elif data == BACK_TO_RSVP_MENU_NEW_MESSAGE:
    #     return await show_rsvp_menu(update, context, edit = True)

    return await query.edit_message_text("Unknown action.")


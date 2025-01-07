from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import ContextTypes, ConversationHandler

from .data_manager import save_events, is_event_admin
from .menu import show_main_menu
from .announcement import start_add_announcement, show_announcement_preview

# # States
# MAIN_MENU, NEW_EVENT_NAME, NEW_EVENT_START_ASK, NEW_EVENT_START_INPUT, \
# NEW_EVENT_END_ASK, NEW_EVENT_END_INPUT, NEW_EVENT_CAPACITY_ASK, NEW_EVENT_CAPACITY_INPUT, \
# NEW_EVENT_CONFIRM, NEW_EVENT_EDIT, NEW_EVENT_DISCARD_CONFIRM, MY_EVENTS, EVENT_MENU, \
# SHOW_EVENT_INFO, ADD_ANNOUNCEMENT, VIEW_ATTENDEES, MESSAGE_ATTENDEES, PREVIEW_ANNOUNCEMENT, \
# POST_ANNOUNCEMENT, EDIT_EVENT, DISCARD_EVENT, BACK_TO_MY_EVENTS, BACK_TO_MAIN_MENU = range(23)

# States
MAIN_MENU, NEW_EVENT_NAME, NEW_EVENT_START_ASK, NEW_EVENT_START_INPUT, \
NEW_EVENT_END_ASK, NEW_EVENT_END_INPUT, NEW_EVENT_CAPACITY_ASK, NEW_EVENT_CAPACITY_INPUT, \
NEW_EVENT_CONFIRM, NEW_EVENT_EDIT, NEW_EVENT_DISCARD_CONFIRM, MY_EVENTS, EVENT_MENU, \
ADD_ANNOUNCEMENT_TEXT, ADD_ANNOUNCEMENT_SHOW_SPOTS, ADD_ANNOUNCEMENT_SHOW_ATTENDING, ADD_ANNOUNCEMENT_PREVIEW,\
ADD_ANNOUNCEMENT_POST_CONFIRM = range(18)

# Callback data 
BACK_TO_MAIN_MENU = "back_to_main_menu"
BACK_TO_MY_EVENTS = "back_to_my_events"

# Event menu actions (we'll define some basic ones; you can expand as needed)
SHOW_EVENT_INFO = "show_event_info"
ADD_ANNOUNCEMENT = "add_announcement"
PREVIEW_ANNOUNCEMENT = "preview_announcement"
POST_ANNOUNCEMENT = "post_announcement"
VIEW_ATTENDEES = "view_attendees"
MESSAGE_ATTENDEES = "message_attendees"
EDIT_EVENT = "edit_event"
DISCARD_EVENT = "discard_event"

# Depending on your logic, these patterns might be defined elsewhere or differently.
# If you have announcements or RSVP message flows, define those callbacks accordingly.

async def show_my_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a list of the user's events."""
    events = context.bot_data.get("events", [])
    # Events presumably already in creation order – if needed, sort them.

    # Build buttons for each event
    buttons = []
    if not events:
        # If no events, inform the user
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "You have no events yet.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("<< Back", callback_data=BACK_TO_MAIN_MENU)]
                ])
            )
        else:
            await update.message.reply_text(
                "You have no events yet.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("<< Back", callback_data=BACK_TO_MAIN_MENU)]
                ])
            )
        return MY_EVENTS
    else:
        for e in events:
            buttons.append([InlineKeyboardButton(e["name"], callback_data=f"select_event_{e['id']}")])

    # Add a back button
    buttons.append([InlineKeyboardButton("<< Back", callback_data=BACK_TO_MAIN_MENU)])
    keyboard = InlineKeyboardMarkup(buttons)

    text = "Here are your events:"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)

    return MY_EVENTS


async def my_events_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the callback from the My Events menu."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == BACK_TO_MAIN_MENU:
        return await show_main_menu(update, context)

    if data.startswith("select_event_"):
        event_id = int(data.split("_")[-1])
        context.user_data["selected_event_id"] = event_id
        return await show_event_menu(update, context, event_id)

    # Unknown action
    await query.edit_message_text("Unknown action.")
    return MY_EVENTS


async def show_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: int):
    """Show the event menu for a specific event."""
    event = None
    for e in context.bot_data.get("events", []):
        if e["id"] == event_id:
            event = e
            break

    if not event:
        if update.callback_query:
            await update.callback_query.edit_message_text("Event not found.")
        else:
            await update.message.reply_text("Event not found.")
        # Go back to MY_EVENTS since event is missing
        return MY_EVENTS

    # Display basic info
    text = (
        f"Name: {event['name']}\n"
        f"Start: {event.get('start','None')}\n"
        f"End: {event.get('end','None')}\n"
        f"Capacity: {event.get('capacity','None')}\n"
    )

    # Build the event menu buttons depending on event state.
    # For now, let's just add placeholders. Later you can add logic if announcement is posted etc.
    buttons = [
        [InlineKeyboardButton("Event Info", callback_data=SHOW_EVENT_INFO)]
    ]

    # If no announcement key, assume none created
    if "announcement_text" not in event:
        buttons.append([InlineKeyboardButton("Add Announcement", callback_data=ADD_ANNOUNCEMENT)])
    else:
        # Announcement created. Check if posted:
        if "announcement_message_id" in event:
            # Announcement posted
            buttons.append([InlineKeyboardButton("View Attendees", callback_data=VIEW_ATTENDEES)])
            buttons.append([InlineKeyboardButton("Message Attendees", callback_data=MESSAGE_ATTENDEES)])
            # Optionally "Edit Announcement"
            buttons.append([InlineKeyboardButton("Edit Announcement", callback_data="edit_announcement")])
        else:
            # Announcement not posted yet
            buttons.append([InlineKeyboardButton("Preview Announcement", callback_data=PREVIEW_ANNOUNCEMENT)])
            buttons.append([InlineKeyboardButton("Post Announcement", callback_data=POST_ANNOUNCEMENT)])

    # RSVP Message, Waitlist Message if needed
    # buttons.append([...]) depending on your logic

    # Always:
    buttons.append([InlineKeyboardButton("Edit Event", callback_data=EDIT_EVENT)])
    buttons.append([InlineKeyboardButton("Discard Event", callback_data=DISCARD_EVENT)])
    buttons.append([InlineKeyboardButton("<< Back to My Events", callback_data=BACK_TO_MY_EVENTS)])
    buttons.append([InlineKeyboardButton("Back to Main Menu", callback_data=BACK_TO_MAIN_MENU)])

    keyboard = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)

    return EVENT_MENU


async def event_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the callback from the Event Menu."""
    query = update.callback_query
    await query.answer()
    data = query.data

    event_id = context.user_data.get("selected_event_id")

    if data == BACK_TO_MY_EVENTS:
        return await show_my_events(update, context)
    elif data == BACK_TO_MAIN_MENU:
        return await show_main_menu(update, context)
    elif data == SHOW_EVENT_INFO:
        await show_event_info(query, context, event_id)
        return EVENT_MENU
    elif data == ADD_ANNOUNCEMENT:
        # You would transition to the announcement creation flow
        return await start_add_announcement(update, context)
    elif data == PREVIEW_ANNOUNCEMENT:
        # Preview announcement flow
        return await show_announcement_preview(update, context)
    elif data == POST_ANNOUNCEMENT:
        # Post announcement flow
        await query.edit_message_text("Post Announcement flow not implemented yet.")
        return EVENT_MENU
    elif data == VIEW_ATTENDEES:
        # Show attendees
        await show_attendees(query, context, event_id)
        return EVENT_MENU
    elif data == MESSAGE_ATTENDEES:
        # Message attendees flow
        await query.edit_message_text("Message Attendees flow not implemented yet.")
        return EVENT_MENU
    elif data == EDIT_EVENT:
        # Edit event flow
        await query.edit_message_text("Edit Event flow not implemented yet.")
        return EVENT_MENU
    elif data == DISCARD_EVENT:
        # Confirm discard
        await discard_event_confirm(query, context, event_id)
        return EVENT_MENU
    else:
        await query.edit_message_text("Unknown action.")
        return EVENT_MENU


async def show_event_info(query, context: ContextTypes.DEFAULT_TYPE, event_id: int):
    """Show detailed event info including announcements, attendees, etc."""
    events = context.bot_data.get("events", [])
    event = next((e for e in events if e["id"] == event_id), None)
    if not event:
        await query.edit_message_text("Event not found.")
        return

    # Build detailed info
    text = "Event Info:\n"
    text += f"Name: {event['name']}\n"
    text += f"Start: {event.get('start','None')}\n"
    text += f"End: {event.get('end','None')}\n"
    text += f"Capacity: {event.get('capacity','None')}\n"

    if "announcement_text" in event:
        text += f"Announcement: {event['announcement_text']}\n"
        posted = "Yes" if "announcement_message_id" in event else "No"
        text += f"Announcement Posted: {posted}\n"

    attendees = event.get("attendees", [])
    waitlist = event.get("waitlist", [])
    text += f"Attendees: {len(attendees)}\n"
    if event.get("capacity"):
        text += f"Waitlist: {len(waitlist)}\n"

    rsvp_msg = event.get('rsvp_message_template', "Default RSVP message")
    text += f"RSVP Message: {rsvp_msg}\n"
    if event.get('capacity'):
        waitlist_msg = event.get('waitlist_message_template', "Default Waitlist message")
        text += f"Waitlist Message: {waitlist_msg}\n"

    # Just a back button
    buttons = [[InlineKeyboardButton("<< Back", callback_data="back_to_event_menu")]]
    keyboard = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(text, reply_markup=keyboard)


async def show_attendees(query, context: ContextTypes.DEFAULT_TYPE, event_id: int):
    """Show the list of attendees and waitlist."""
    events = context.bot_data.get("events", [])
    event = next((e for e in events if e["id"] == event_id), None)
    if not event:
        await query.edit_message_text("Event not found.")
        return

    attendees = event.get("attendees", [])
    waitlist = event.get("waitlist", [])

    text = "Here is the list of attendees:\n"
    if attendees:
        for i, a in enumerate(attendees, start=1):
            username = a.get("username", f"User {a['user_id']}")
            text += f"{i}. {username}\n"
    else:
        text += "No attendees.\n"

    if event.get("capacity"):
        text += "\nHere is the waitlist:\n"
        if waitlist:
            for i, w in enumerate(waitlist, start=1):
                username = w.get("username", f"User {w['user_id']}")
                text += f"{i}. {username}\n"
        else:
            text += "No one on the waitlist.\n"

    buttons = [[InlineKeyboardButton("<< Back", callback_data="back_to_event_menu")]]
    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(text, reply_markup=keyboard)


async def discard_event_confirm(query, context: ContextTypes.DEFAULT_TYPE, event_id: int):
    """Ask for confirmation before discarding the event."""
    buttons = [
        [InlineKeyboardButton("Yes", callback_data=f"discard_yes_{event_id}"),
         InlineKeyboardButton("No", callback_data="back_to_event_menu")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text("Are you sure you want to discard this event?", reply_markup=keyboard)

async def discard_event_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle discard confirmation."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("discard_yes_"):
        event_id = int(data.split("_")[-1])
        events = context.bot_data.get("events", [])
        events = [e for e in events if e["id"] != event_id]
        context.bot_data["events"] = events
        save_events(context)

        await query.edit_message_text("Event discarded.")
        return await show_my_events(update, context)

    elif data == "back_to_event_menu":
        # Show the event menu again
        event_id = context.user_data.get("selected_event_id")
        return await show_event_menu(update, context, event_id)
    else:
        await query.edit_message_text("Unknown action.")
        return EVENT_MENU

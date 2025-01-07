import re
from datetime import date, time, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from event_admin.data_manager import update_event_attendees, save_events
from event_admin import rsvp_admin

async def rsvp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    If user presses "RSVP" in the channel, we:
    
    """
    query = update.callback_query
    await query.answer()

    # parse event ID
    match = re.match(r"^rsvp:(\d+)$", query.data)
    if not match:
        return  # unknown callback

    event_id = int(match.group(1))
    user = query.from_user
    user_id = user.id

    # find the event
    events = context.bot_data.get("events", [])
    event_data = next((ev for ev in events if ev["id"] == event_id), None)
    if not event_data:
        await query.answer("Event not found.", show_alert=False)
        return

    # ensure data structures
    if "attendees" not in event_data:
        event_data["attendees"] = []
    if "waitlist" not in event_data:
        event_data["waitlist"] = []

    # see if user is already in event
    in_attendees = next((a for a in event_data["attendees"] if a["user_id"] == user_id), None)
    in_waitlist = next((w for w in event_data["waitlist"] if w["user_id"] == user_id), None)
    
    print(in_attendees)
    if in_attendees:
        await resend_rsvp_message(update, context, event_data, user_id, event_id, in_attendees["rsvp_message_id"])
    elif in_waitlist:
        await resend_waitlist_message(update, context, event_data, user_id, event_id, in_waitlist["rsvp_message_id"])
    elif not event_data.get("has_capacity", False) or len(event_data["attendees"]) < event_data["capacity"]:
        await add_to_attendee(update, context, event_data, user_id, event_id)
    else:
        await add_to_waitlist(update, context, event_data, user_id, event_id)

def rsvp_header_text(event_data: dict):
    """Generate the header text for the RSVP message."""
    text = f"__*{event_data['name']}*__\n"
    if event_data['date'] != 'None':
        event_date = date.fromisoformat(event_data['date'])
        text += f"_Date: {event_date.strftime('%A, %B %d, %Y')}_\n"
    if event_data['start_time'] != 'None' and event_data['end_time'] == 'None':
        start_time = datetime.strptime(event_data['start_time'], '%H:%M')
        text += f"_Start Time: {start_time.strftime('%I:%M %p')}_\n"
    if event_data['start_time'] == 'None' and event_data['end_time'] != 'None':
        end_time = datetime.strptime(event_data['end_time'], '%H:%M')
        text += f"_End Time: {end_time.strftime('%I:%M %p')}_\n"
    if event_data['start_time'] != 'None' and event_data['end_time'] != 'None':
        start_time = datetime.strptime(event_data['start_time'], '%H:%M')
        end_time = datetime.strptime(event_data['end_time'], '%H:%M')
        text += f"_Time: {start_time.strftime('%I:%M %p')} \- {end_time.strftime('%I:%M %p')}_\n"
    if event_data['location'] != 'None':
        # Add event_data['location_link'] if it exists
        if event_data['location_link'] != 'None':
            text += f"_Location: [{event_data['location']}]({event_data['location_link']})_\n"
        else:
            text += f"_Location: {event_data['location']}_\n"
    # text += "\n"
    
    return text

async def resend_rsvp_message(update: Update, context: ContextTypes.DEFAULT_TYPE, event_data: dict, user_id: int, event_id: int, rsvp_message_id: int):
    """Re-send the RSVP message to the user."""
    query = update.callback_query
    await query.answer()

    
    # re-send RSVP confirmation DM
    try:
        text = (
            f"✅  {rsvp_header_text(event_data)}\n"
            f"You have already RSVP'd to this event\. Press 'Cancel RSVP' if you can no longer attend\."
        )
        cancel_rsvp_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel RSVP", callback_data=f"cancelrsvp:{event_id}")]
            ])
        dm_message = await context.bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=cancel_rsvp_kb,
            disable_web_page_preview=True
        )
        
        # Send an ephemeral message to the channel
        await query.answer(f"RSVP confirmation for {event_data['name']} re-sent!", show_alert=True)
        
        # Incase the user has deleted the earlier confirmation message, we use a try-except block
        try:
            text = (
                f"{rsvp_header_text(event_data)}\n"
                "RSVP confirmation message re\-sent\."
            )
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=rsvp_message_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as ex:
            print(f"Could not edit user's private message: {ex}")
        
        for idx, attendee in enumerate(event_data["attendees"]):
            if attendee["user_id"] == user_id:
                event_data["attendees"][idx]["rsvp_message_id"] = dm_message.message_id
                break
        
        await update_announcement_message(update, context, event_data)
        update_event_attendees(event_id, event_data, context)
        
    except Exception as ex:
        print(f"Error in resend_rsvp_message: {ex}")
        await query.answer("Please message the bot in private first.", show_alert=False)
        return
    
    
async def add_to_attendee(update: Update, context: ContextTypes.DEFAULT_TYPE, event_data: dict, user_id: int, event_id: int):
    """Add the user to the attendees list."""
    query = update.callback_query
    await query.answer()
    
    # re-send RSVP confirmation DM
    try:
        text = (
            f"✅  {rsvp_header_text(event_data)}\n"
            f"You have successfully RSVP'd to this event\. Press 'Cancel RSVP' if you can no longer attend\."
        )
        cancel_rsvp_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel RSVP", callback_data=f"cancelrsvp:{event_id}")]
        ])
        dm_message = await context.bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=cancel_rsvp_kb,
            disable_web_page_preview=True
        )
        
        # Send an ephemeral message to the channel
        await query.answer("RSVP confirmation sent!", show_alert=True)
        
        user = query.from_user  # The user who pressed "RSVP"
        
        event_data["attendees"].append({
                "user_id": user_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "rsvp_message_id": dm_message.message_id  # store the DM message ID
            })
        
        update_event_attendees(event_id, event_data, context)
        
        await update_announcement_message(update, context, event_data)
        
    except Exception as ex:
        print(f"Error in add_to_attendee: {ex}")
        await query.answer("Please message the bot in private first.", show_alert=False)
        return
    
async def resend_waitlist_message(update: Update, context: ContextTypes.DEFAULT_TYPE, event_data: dict, user_id: int, event_id: int, rsvp_message_id: int):
    """Re-send the RSVP message to the user."""
    query = update.callback_query
    await query.answer()
    
    # re-send RSVP confirmation DM
    try:
        text = (
            f"✅  {rsvp_header_text(event_data)}\n"
            f"You are already on the waitlist to this event\. Press 'Cancel RSVP' if you no longer wish to attend\."
        )
        cancel_rsvp_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel Waitlist", callback_data=f"cancelwaitlist:{event_id}")]
        ])
        dm_message = await context.bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=cancel_rsvp_kb,
            disable_web_page_preview=True
        )
        
        # Send an ephemeral message to the channel
        await query.answer("Waitlist confirmation re\-sent!", show_alert=True)
        
        # Incase the user has deleted the earlier confirmation message, we use a try-except block
        try:
            text = (
                f"{rsvp_header_text(event_data)}\n"
                f"Resent waitlist confirmation message\."
            )
            dm_message = await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=rsvp_message_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True
            )
        except Exception as ex:
            print(f"Could not edit user's private message: {ex}")
            # Update the in-memory events list
            
        for idx, attendee in enumerate(event_data["waitlist"]):
            if attendee["user_id"] == user_id:
                event_data["waitlist"][idx]["rsvp_message_id"] = dm_message.message_id
                break
            
        
        update_event_attendees(event_id, event_data, context)
        await update_announcement_message(update, context, event_data)
        
    except Exception as ex:
        print(f"Error in resend_rsvp_message: {ex}")
        await query.answer("Please message the bot in private first.", show_alert=False)
        return
    
async def add_to_waitlist(update: Update, context: ContextTypes.DEFAULT_TYPE, event_data: dict, user_id: int, event_id: int):
    """Add the user to the waitlist."""
    query = update.callback_query
    await query.answer()
    
    # re-send RSVP confirmation DM
    try:
        text = (
            f"✅  {rsvp_header_text(event_data)}\n"
            f"You have successfully joined the waitlist to this event\. Press 'Cancel RSVP' if you can no longer attend\."
        )
        cancel_rsvp_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel Waitlist", callback_data=f"cancelwaitlist:{event_id}")]
        ])
        dm_message = await context.bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=cancel_rsvp_kb,
            disable_web_page_preview=True
        )
        
        # Send an ephemeral message to the channel
        await query.answer("Waitlist confirmation sent!", show_alert=True)
        
        user = query.from_user  # The user who pressed "RSVP"
        
        event_data["waitlist"].append({
                "user_id": user_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "rsvp_message_id": dm_message.message_id  # store the DM message ID
            })
        
        update_event_attendees(event_id, event_data, context)
        
        await update_announcement_message(update, context, event_data)
        
    except Exception as ex:
        print(f"Error in add_to_attendee: {ex}")
        await query.answer("Please message the bot in private first.", show_alert=False)
        return

async def cancel_rsvp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks to make sure the user is sure they want to cancel their RSVP. Warns them if they won't be able to re-join if the event is full."""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback (removes Telegram's loading spinner)

    # 1. Parse event ID from callback data
    match = re.match(r"^cancelrsvp:(\d+)$", query.data)
    if not match:
        # Invalid callback_data
        await query.answer("Invalid callback data", show_alert=False)
        return

    event_id = int(match.group(1))
    user = query.from_user
    user_id = user.id
    
    # find the event
    events = context.bot_data.get("events", [])
    event_data = next((ev for ev in events if ev["id"] == event_id), None)
    
    # Check if there will be space in the event after the user cancels.
    has_capacity = event_data.get("has_capacity", False)
    non_empty_waitlist = len(event_data["waitlist"]) > 0

    if has_capacity and non_empty_waitlist:
        text = (
            f"⚠️  {rsvp_header_text(event_data)}\n"
            "The event is at capacity and there are pups on the waitlist, if you cancel your RSVP and change your mind, you will be added to the waitlist\.\n"
            "Are you sure you want to cancel your RSVP\?"
        )
    else:
        text = (
            f"⚠️  {rsvp_header_text(event_data)}\n"
            "Are you sure you want to cancel your RSVP\?"
        )        
    
    buttons = [
        [InlineKeyboardButton("Yes, cancel RSVP", callback_data=f"confirmcancelrsvp:{event_id}")],
        [InlineKeyboardButton("No, keep RSVP", callback_data=f"keeprsvp:{event_id}")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    
    # Store the message that is currently displayed to the user in the user data to return the message to its previous state if they decide to keep their RSVP.
    for idx, attendee in enumerate(event_data["attendees"]):
        if attendee["user_id"] == user_id:
            attendee["rsvp_message_text"] = query.message.text_markdown_v2
            # attendee["rsvp_message_keyboard"] = query.message.reply_markup
            break
    
    update_event_attendees(event_id, event_data, context)
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard, disable_web_page_preview=True)
    
    return
    
async def keep_rsvp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Puts the original RSVP message back to what it was before the user tried to cancel their RSVP."""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback (removes Telegram's loading spinner)

    # 1. Parse event ID from callback data
    match = re.match(r"^keeprsvp:(\d+)$", query.data)
    if not match:
        # Invalid callback_data
        await query.answer("Invalid callback data", show_alert=False)
        return

    event_id = int(match.group(1))
    user = query.from_user
    user_id = user.id
    
    # find the event
    events = context.bot_data.get("events", [])
    event_data = next((ev for ev in events if ev["id"] == event_id), None)
    if not event_data:
        await query.answer("Event not found.", show_alert=True)
        return
    
    # Restore the original message
    old_text = None
    for idx, attendee in enumerate(event_data["attendees"]):
        if attendee["user_id"] == user_id:
            old_text = attendee["rsvp_message_text"]
            break
    button = [InlineKeyboardButton("Cancel RSVP", callback_data=f"cancelrsvp:{event_id}")]
    keyboard = InlineKeyboardMarkup([button])
    await query.edit_message_text(old_text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard, disable_web_page_preview=True)
    
    return

async def confirm_cancel_rsvp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'cancelrsvp:<event_id>' callbacks from the user's private RSVP confirmation."""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback (removes Telegram's loading spinner)

    # 1. Parse event ID from callback data
    match = re.match(r"^confirmcancelrsvp:(\d+)$", query.data)
    if not match:
        # Invalid callback_data
        await query.answer("Invalid callback data", show_alert=False)
        return

    event_id = int(match.group(1))
    user = query.from_user
    user_id = user.id

    # 2. Retrieve the event from bot_data
    events = context.bot_data.get("events", [])
    event_data = next((ev for ev in events if ev["id"] == event_id), None)
    if not event_data:
        # Event not found
        await query.answer("Event not found.", show_alert=False)
        return

    attendees = event_data.get("attendees", [])
    waitlist = event_data.get("waitlist", [])
    was_in_attendees = False
    was_in_waitlist = False

    # 3. Remove user from the attendees or waitlist
    #    If they are in multiple places (shouldn’t happen unless logic error), remove from both.
    new_attendees = []
    for a in attendees:
        if a["user_id"] == user_id:
            was_in_attendees = True
            continue  # skip adding them
        new_attendees.append(a)

    new_waitlist = []
    for w in waitlist:
        if w["user_id"] == user_id:
            was_in_waitlist = True
            continue
        new_waitlist.append(w)

    event_data["attendees"] = new_attendees
    event_data["waitlist"] = new_waitlist

    await update_announcement_message(update, context, event_data)
    
    if not (was_in_attendees or was_in_waitlist):
        # user wasn't in the event => ephemeral message
        await query.edit_message_text(text = f"{rsvp_header_text(event_data)}\n You have no RSVP to cancel\.", parse_mode=ParseMode.MARKDOWN_V2,disable_web_page_preview=True)
        return
    
    # 4. Update the event data in the JSON
    update_event_attendees(event_id, event_data, context)
    
    await promote_from_waitlist(update, context, event_data)

    # 6. Edit the posted announcement to reflect the new attendee count, waitlist, etc.
    #    We can call the same function that `rsvp_callback` uses to re-generate the text and edit the message:


    # 7. Show ephemeral success in the user’s chat
    #    If the user is in a private chat with the bot, we might want to edit their "Are you sure?" message.
    #    But typically "answerCallbackQuery" is enough:
    await query.answer("Your RSVP has been canceled.", show_alert=False)

    # optionally, if we want to edit the user’s own confirmation message:
    try:
        text = (
            f"❌  {rsvp_header_text(event_data)}\n"
            f"You are no longer RSVP'd to this event\. "
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
    except Exception as ex:
        print(f"Could not edit user’s private message: {ex}")

async def promote_from_waitlist(update: Update, context: ContextTypes.DEFAULT_TYPE, event_data: dict):
    """
    Attempt to promote from the waitlist for the given event_data.
    If there's capacity and there's a waitlist, move first from waitlist -> attendees.
    """
    print("promote_from_waitlist called")
    
    """We want to handle the possibility that the capacity of the event no longer exists."""
    # # If there's no capacity or has_capacity=False, do nothing
    # if not event_data.get("has_capacity", False):
    #     return
    
    capacity = event_data["capacity"]
    
    # While there's capacity and the waitlist is not empty
    while len(event_data["attendees"]) < capacity and event_data["waitlist"]:
        print("promote_from_waitlist while loop")
        
        next_person = event_data["waitlist"].pop(0)
        print("next_person", next_person)
        
        try:
            print("promote_from_waitlist try DM")
            promotion_text = (
                f"{rsvp_header_text(event_data)}\n"
                "A pup has cancelled and you are now RSVP'd to this event\. Press 'Cancel RSVP' if you can no longer attend\."
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Cancel RSVP", callback_data=f"cancelrsvp:{event_data['id']}")]
            ])
            
            dm_message = await context.bot.send_message(
                chat_id=next_person["user_id"],
                text=promotion_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
            
            # Optionally edit their old waitlist message
            try:
                print("promote_from_waitlist edit old message")
                edit_text = (
                f"{rsvp_header_text(event_data)}\n"
                "A pup has cancelled and you are now RSVP'd to this event\. Press 'Cancel RSVP' if you can no longer attend\."
            )
                await context.bot.edit_message_text(
                    chat_id=next_person["user_id"],
                    message_id=next_person["rsvp_message_id"],
                    text=edit_text,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    disable_web_page_preview=True
                )
            except Exception as ex:
                print(f"[WaitlistPromotion] Could not edit user's old private message: {ex}")
            
            # update the user's data
            next_person["rsvp_message_id"] = dm_message.message_id
            
            # add them to attendees
            event_data["attendees"].append(next_person)
        
        except Exception as ex:
            # If we cannot message them (blocked bot, etc.) continue with the next person
            print(f"[WaitlistPromotion] Could not message user {next_person['user_id']} about promotion. Error: {ex}")
    
    # Save changes
    update_event_attendees(event_data["id"], event_data, context)
    
    # Finally, update the posted announcement
    await update_announcement_message(update, context, event_data)
    return
async def cancel_waitlist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Asks the user to confirm if they want to remove themselves from the waitlist.
    Warns them if there's more than one person on the waitlist that they will be at the end if they rejoin.
    """
    query = update.callback_query
    await query.answer()  # Acknowledge the callback

    # 1. Parse event ID
    match = re.match(r"^cancelwaitlist:(\d+)$", query.data)
    if not match:
        await query.answer("Invalid callback data", show_alert=False)
        return

    event_id = int(match.group(1))
    user_id = query.from_user.id

    # 2. Retrieve the event
    events = context.bot_data.get("events", [])
    event_data = next((ev for ev in events if ev["id"] == event_id), None)
    if not event_data:
        await query.answer("Event not found.", show_alert=True)
        return

    # Ensure "waitlist" field
    if "waitlist" not in event_data:
        event_data["waitlist"] = []

    # Check how big the waitlist is (excluding the user if they are on it)
    waitlist_size = len(event_data["waitlist"])
    # If there's more than 1, we warn them
    if waitlist_size > 1:
        text = (
            f"⚠️  {rsvp_header_text(event_data)}\n"
            "There are other pups on the waitlist\. If you cancel and then want to rejoin, "
            "you will be placed at the end of the line\. Are you sure you want to remove yourself from the waitlist\?"
        )
    else:
        text = (
            f"⚠️  {rsvp_header_text(event_data)}\n"
            "Are you sure you want to remove yourself from the waitlist\?"
        )

    buttons = [
        [InlineKeyboardButton("Yes, remove me from waitlist", callback_data=f"confirmcancelwaitlist:{event_id}")],
        [InlineKeyboardButton("No, keep waitlist", callback_data=f"keepwaitlist:{event_id}")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # We store the old text (and optionally the keyboard) to restore if user chooses “keep waitlist”
    for idx, w in enumerate(event_data["waitlist"]):
        if w["user_id"] == user_id:
            w["waitlist_message_text"] = query.message.text_markdown_v2
            break

    # Update the in-memory data
    update_event_attendees(event_id, event_data, context)

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard)

async def keep_waitlist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Restores the user's old waitlist confirmation message if they choose to keep their spot.
    """
    query = update.callback_query
    await query.answer()

    # 1. Parse event ID
    match = re.match(r"^keepwaitlist:(\d+)$", query.data)
    if not match:
        await query.answer("Invalid callback data", show_alert=False)
        return

    event_id = int(match.group(1))
    user = query.from_user
    user_id = user.id

    # 2. Retrieve the event
    events = context.bot_data.get("events", [])
    event_data = next((ev for ev in events if ev["id"] == event_id), None)
    if not event_data:
        await query.answer("Event not found.", show_alert=True)
        return

    # Find the user’s original waitlist message text
    old_text = None
    for w in event_data["waitlist"]:
        if w["user_id"] == user_id and "waitlist_message_text" in w:
            old_text = w["waitlist_message_text"]
            break

    # If we found their old text, restore it
    if old_text:
        # Rebuild the keyboard to what it was => "Cancel Waitlist"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel Waitlist", callback_data=f"cancelwaitlist:{event_id}")]
        ])
        try:
            await query.edit_message_text(old_text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard,disable_web_page_preview=True)
        except Exception as ex:
            print(f"Could not restore old waitlist message: {ex}")
    else:
        # If we didn't store old_text, just show a fallback
        await query.edit_message_text("Kept your spot on the waitlist.")
    
    return

async def confirm_cancel_waitlist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Removes the user from the waitlist if they confirm 'Yes, remove me from waitlist'.
    Then tries to promote from waitlist if capacity allows.
    """
    query = update.callback_query
    await query.answer()

    # 1. Parse event ID
    match = re.match(r"^confirmcancelwaitlist:(\d+)$", query.data)
    if not match:
        await query.answer("Invalid callback data", show_alert=False)
        return

    event_id = int(match.group(1))
    user_id = query.from_user.id

    # 2. Retrieve the event
    events = context.bot_data.get("events", [])
    event_data = next((ev for ev in events if ev["id"] == event_id), None)
    if not event_data:
        await query.answer("Event not found.", show_alert=True)
        return

    attendees = event_data.get("attendees", [])
    waitlist = event_data.get("waitlist", [])

    was_in_waitlist = any(w["user_id"] == user_id for w in waitlist)

    # 3. Remove user from waitlist
    new_waitlist = []
    for w in waitlist:
        if w["user_id"] == user_id:
            continue
        new_waitlist.append(w)
    event_data["waitlist"] = new_waitlist

    # If user wasn't in the waitlist, no-op
    if not was_in_waitlist:
        await query.edit_message_text(
            "You have no waitlist spot to remove.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # 4. Attempt to promote from waitlist
    # (assuming you have a function promote_from_waitlist)
    await promote_from_waitlist(update, context, event_data)

    # 5. Update the event data
    update_event_attendees(event_id, event_data, context)

    # 6. Update the posted announcement
    await update_announcement_message(update, context, event_data)

    # 7. Show ephemeral success
    await query.answer("You have been removed from the waitlist.", show_alert=False)

    # 8. Optionally edit the user’s private message
    try:
        text = (
            f"❌  You have been removed from the waitlist for:\n"
            f"{rsvp_header_text(event_data)}"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as ex:
        print(f"Could not edit user’s private message: {ex}")



async def update_announcement_message(update, context, event_data: dict):
    """
    Re-generate the announcement text & keyboard using generate_announcement_message,
    then edit both:
      1. The channel’s announcement message (announcement_message_id).
      2. The group’s RSVP button message (group_rsvp_button_message_id),
         if it exists in event_data.
    """
    from event_admin.announcement import generate_announcement_message, generate_group_rsvp_button
    # 1. Generate new text & keyboard based on the updated event data
    new_text, new_keyboard = generate_announcement_message(context, event_data_override=event_data)

    # 2. First, update the announcement in the channel
    try:
        await context.bot.edit_message_text(
            chat_id=event_data["announcement_message_chat_id"],
            message_id=event_data["announcement_message_id"],
            text=new_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=new_keyboard,
            disable_web_page_preview=True
        )
        print("[DEBUG] Channel announcement updated successfully.")
    except Exception as ex:
        print(f"[ERROR] Could not update channel announcement: {ex}")

    # 3. Now, update the RSVP button in the group, if we have a stored message ID
    group_chat_id = event_data.get("group_rsvp_button_chat_id")
    group_msg_id  = event_data.get("group_rsvp_button_message_id")

    if group_chat_id and group_msg_id:
        try:
            new_text, new_keyboard = generate_group_rsvp_button(context, event_data)
            await context.bot.edit_message_text(
                chat_id=group_chat_id,
                message_id=group_msg_id,
                text=new_text,        
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=new_keyboard,
                disable_web_page_preview=True 
            )
            print("[DEBUG] Group RSVP button updated successfully.")
        except Exception as ex:
            print(f"[ERROR] Could not update group RSVP button: {ex}")
    else:
        print("[DEBUG] No group RSVP message to update.")

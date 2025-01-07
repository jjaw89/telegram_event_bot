# Telegram Event Organizer Bot for LGBT+ Groups

This Telegram bot is designed to streamline event organization for a local LGBT+ group. It allows admins to create and manage events, send announcements, and handle RSVPs efficiently.

---

## Configuration

The bot requires a configuration file (`config.py`) with the following details:

```python
# The bot's Telegram bot token
token = "YOUR_BOT_TOKEN"

# List of Telegram user IDs authorized to use the /eventadmin command
event_admins = [12345678, 87654321]

# Chat IDs for the group chat and announcement channel
chat_ids = {
    "group": -123456789,         # Telegram group chat ID
    "announcements": -987654321  # Telegram announcement channel ID
}
```

---

## Features

### Admin Features
1. **Start Event Management**:
   - Authorized admins can type `/eventadmin` in a private chat with the bot to access the admin menu.
   - Admins can create new events or manage active ones.

2. **Create Events**:
   - Admins can specify details for each event, including:
     - **Name** (must be unique)
     - **Date**
     - **Start and End Times**
     - **Capacity** (optional; unlimited by default)
     - **Location** (optional)
   - Events can be edited later if needed.

3. **Announcements and RSVPs**:
   - Admins can draft and submit custom announcements, including text formatting and emojis.
   - Announcements are posted in the announcement channel with an RSVP button.
   - The bot also posts an RSVP button in the group chat 5 seconds after the announcement.

4. **Manage RSVPs**:
   - Users pressing the RSVP button receive a private confirmation message.
   - If the event has a capacity limit, attendees are added to a waitlist once the event is full.
   - The waitlist is automatically managed: if someone cancels their RSVP, the next person in the waitlist is promoted to the attendee list.

5. **Messaging Attendees**:
   - Admins can send messages to attendees or waitlisted users through the bot.
   - Messages are delivered privately to each user via the bot.

6. **Modify Announcements**:
   - Admins can edit announcements even after they are posted to include updated details.

7. **Close Events**:
   - Closing an event disables all RSVP and cancellation buttons.
   - Closed events are hidden from the active events list but retained in the bot's database (`bot_data.json`) for future reference.

---

## User Features
- **RSVP**:
  - Users can RSVP by pressing the button in the announcement or group chat.
  - The bot confirms the RSVP via a private message and updates the event's announcement with the attendee list.
  
- **Cancel RSVP**:
  - Users can cancel their RSVP through the confirmation message they receive.
  - If an attendee cancels, the bot automatically promotes someone from the waitlist.

---

## Notes
- **Event Recovery**: Event data is not deleted when an event is closed. Admins can manually recover closed events by editing the `bot_data.json` file.

---

## How It Works
1. **Admins**:
   - Start the bot using `/eventadmin`.
   - Create or manage events via an intuitive menu system.
   - Post announcements and manage RSVPs seamlessly.

2. **Users**:
   - Press the RSVP button to join an event.
   - Receive a private confirmation and the ability to cancel if needed.
   - Automatically get added to a waitlist if the event is full.

---

## Future Enhancements
- Automatic reminders for upcoming events.
- Templates for recurring events like regular meetups.
- Additional customization for location data, including map links.

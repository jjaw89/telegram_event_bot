A telegram bot to help with orginizing events for a local LGBT+ group.

### The config file should contain the following:
# The bot's telegram bot token.
token = ""

# The only users who have access to /eventadmin command have their telegram user id's in this list.
event_admins = []

# The chat id's of the LGBT+ telegram group chat and the announcement channels are in this dictionary.
chat_ids = {
    "group": ,
    "announcements":
}


To use this bot, an authorized event admin should type /eventadmin into their own private chat with the telegram bot. The bot checks to see if the user is authorized and then gives the admin the option to create an event or look at the events that are active. 

The admin types the name of the new event (must be unique), and then has a menu to fill in the event info:
date, start and end time, capacity, and location (these can be empty).

The admin then submits the text for an annoucment (they are free to format this text and add emojis if they wish). The admin can then post the annoucment to the annoucment channel where an rsvp button appears below it. The channel automatically posts to the group chat and 5 seconds later the bot posts a button to the group chat tha allows the user to RSVP.

When a user presses rsvp, the bot checks that it can send the user a message. If it can, it will confirm the RSVP and update the annoucement, putting on the attendee list. The user can cancel the RSVP from the message they recive confirming the RSVP. if the event is at capacity, the bot begins adding users to the event's waitlist. If a user cancel's their RSVP, the waitlist promotes someone to the atendee list.

The admin can message the users who have RSVP'd to an event through their own dm with the bot and the bot will send the message to the attendees through their private conversations with the bot.

the admin can modify the annoucment after it has been posted.

The admin can close an event. this removes all the buttons from the annoucment and rsvp confirmation messages the bot sent as well as hiding the event from the active event list. The event data is not deleted from the bot_data.json file and can be recovered by editing the data file in a text editor.
# event_admin/constants.py

# Conversation states
(
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
    MESSAGE_RSVP_WHOM,
    ASK_CLOSE_EVENT
) = range(20)

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

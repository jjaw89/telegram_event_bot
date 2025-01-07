import os
import json
from config.config import event_admins



def find_project_root(target_folder="telegram_event_bot"):
    """Finds the root directory of the project by searching for the target folder."""
    current_dir = os.path.abspath(__file__)
    while True:
        if os.path.basename(current_dir) == target_folder:
            return current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            raise RuntimeError(f"Target folder '{target_folder}' not found in the directory tree.")
        current_dir = parent_dir
    
def is_event_admin(user_id: int) -> bool:
    return user_id in event_admins

def save_events(context) -> None:
    """
    Writes context.bot_data (which should contain {"events": [...]} )
    to the data/events.json file.
    """
    # Get the root directory of the project
    project_root = find_project_root()

    # Define the data directory and file paths relative to the project root
    data_dir = os.path.join(project_root, "data")
    data_file = os.path.join(data_dir, "bot_data.json")

    # Prepare the data to write
    data = {
        "events": context.bot_data.get("events", [])
    }

    # Write JSON
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_working_event(context) -> None:
    """
    Writes context.bot_data (which should contain {"events": [...]} )
    to the data/events.json file.
    """
    # Get the root directory of the project
    project_root = find_project_root()

    # Define the data directory and file paths relative to the project root
    data_dir = os.path.join(project_root, "data")
    data_file = os.path.join(data_dir, "bot_data.json")

    # Update the event in bot_data, save, etc.
    for index, stored_event in enumerate(context.bot_data["events"]):
        if stored_event["id"] == context.user_data["working_event"]["id"]:
            # Replace the entire dictionary with user_data["working_event"]
            context.bot_data["events"][index] = context.user_data["working_event"]
            break

    # Write JSON
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(context.bot_data, f, ensure_ascii=False, indent=4)


def load_events(context) -> None:
    """
    Reloads the events from the data/events.json file into context.bot_data *in place*.
    This avoids the 'AttributeError: You cannot assign a new value to bot_data'.
    """
    # Get the root directory of the project
    project_root = find_project_root()

    # Define the data directory and file paths relative to the project root
    data_dir = os.path.join(project_root, "data")
    data_file = os.path.join(data_dir, "evenbot_datats.json")

    with open(data_file, "r", encoding="utf-8") as f:
        file_data = json.load(f)  # e.g. {"events": [...]}

    # Instead of reassigning context.bot_data, update it in place:
    if "events" in file_data:
        context.bot_data["events"] = file_data["events"]
    else:
        # If "events" key is missing, set it to an empty list or handle as needed
        context.bot_data["events"] = []
        
        
def update_event_attendees(event_id: int, updated_event_data: dict, context) -> None:
    """
    Replaces the event with ID == event_id in context.bot_data["events"]
    with updated_event_data, then saves bot_data to disk.
    """
    # Get the root directory of the project
    project_root = find_project_root()

    # Define the data directory and file paths relative to the project root
    data_dir = os.path.join(project_root, "data")
    data_file = os.path.join(data_dir, "bot_data.json")

    # Update the in-memory events list
    for idx, ev in enumerate(context.bot_data.get("events", [])):
        if ev["id"] == event_id:
            context.bot_data["events"][idx] = updated_event_data
            break

    # Write the new data to disk
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(context.bot_data, f, ensure_ascii=False, indent=4)
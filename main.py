import re
import logging
from telethon import TelegramClient, events, Button
from database import Database


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_id = ""
api_hash = ""
bot_token = ""
admin_id = 

# Initialize client and database
client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)
db = Database('data.db')

@client.on(events.ChatAction())
async def handle_new_group(event):
    if event.user_added or event.user_joined:
        if event.user_id == (await client.get_me()).id:
            group_id = event.chat_id
            db.temp_store(admin_id, {"group_id": group_id, "step": "name"})
            message = (f"I've been added to a new group (ID: {group_id}). "
                       "Please provide a name for this group.")
            await client.send_message(admin_id, message)

@client.on(events.NewMessage(from_users=admin_id))
async def admin_interaction(event):
    session = db.temp_retrieve(admin_id)
    if not session:
        return

    if session.get("step") == "name":
        group_name = event.raw_text.strip()
        db.temp_store(admin_id, {"group_id": session["group_id"], "group_name": group_name, "step": "list"})
        await event.reply(f"Group named '{group_name}'. Do you want to add it to an existing list or create a new list?",
                          buttons=[
                              [Button.inline("Add to existing list", b"add_existing")],
                              [Button.inline("Create new list", b"create_new")]
                          ])
    elif session.get("step") == "new_list_name":
        list_name = event.raw_text.strip()
        group_id = session["group_id"]
        group_name = session["group_name"]
        if db.add_group(group_id, group_name, list_name):
            await event.reply(f"Group '{group_name}' added to new list '{list_name}' successfully!")
        else:
            await event.reply(f"Failed to add group '{group_name}' to the list '{list_name}'. It might already be added.")
        db.clear_session(admin_id)

@client.on(events.CallbackQuery)
async def handle_callback(event):
    data = event.data.decode()
    session = db.temp_retrieve(admin_id)

    if data == "add_existing" and session.get("step") == "list":
        list_names = db.get_all_list_names()
        if not list_names:
            await event.reply("No existing lists found. Please create a new list.")
        else:
            buttons = [[Button.inline(name, f"add_to_list:{name}") for name in list_names]]
            await event.reply("Select an existing list:", buttons=buttons)

    elif data == "create_new" and session.get("step") == "list":
        db.temp_store(admin_id, {"group_id": session["group_id"], "group_name": session["group_name"], "step": "new_list_name"})
        await event.reply("Please provide a name for the new list.")

    elif data.startswith("add_to_list:") and session.get("step") == "list":
        list_name = data.split(":")[1]
        group_id = session["group_id"]
        group_name = session["group_name"]
        if db.add_group(group_id, group_name, list_name):
            await event.reply(f"Group '{group_name}' added to list '{list_name}' successfully!")
        else:
            await event.reply(f"Failed to add group '{group_name}' to the list '{list_name}'. It might already be added.")
        db.clear_session(admin_id)

    elif data.startswith("remove_from_list:"):
        list_name, group_name = data.split(":")[1], data.split(":")[2]
        if db.remove_group_from_list(group_name, list_name):
            await event.reply(f"Group '{group_name}' removed from list '{list_name}' successfully!")
        else:
            await event.reply(f"Failed to remove group '{group_name}' from the list '{list_name}'. It might not exist.")

@client.on(events.NewMessage(pattern='/broadcast (.*)', from_users=admin_id))
async def broadcast(event):
    parts = event.raw_text.split(maxsplit=2)
    if len(parts) < 3:
        await event.reply("Usage: /broadcast [list_name] [message]")
        return
    
    list_name, message_text = parts[1], parts[2]
    logger.info(f"Broadcasting to list: {list_name} - Message: {message_text}")
    groups = db.get_groups(list_name)
    logger.info(f"Groups fetched: {groups}")
    if not groups:
        await event.reply("No groups found in this list.")
        return

    for group_id in groups:
        try:
            await client.send_message(group_id, message_text)
            logger.info(f"Message sent to: {group_id}")
        except Exception as e:
            logger.error(f"Failed to send message to {group_id}: {e}")

@client.on(events.NewMessage(pattern='/deletelist (.+)', from_users=admin_id))
async def delete_list(event):
    list_name = event.pattern_match.group(1).strip()
    if db.delete_list(list_name):
        await event.reply(f"List '{list_name}' deleted successfully!")
    else:
        await event.reply(f"Failed to delete list '{list_name}'. It might not exist.")

@client.on(events.NewMessage(pattern='/removegroup (.+) (.+)', from_users=admin_id))
async def remove_group(event):
    list_name = event.pattern_match.group(1).strip()
    group_name = event.pattern_match.group(2).strip()
    if db.remove_group_from_list(group_name, list_name):
        await event.reply(f"Group '{group_name}' removed from list '{list_name}' successfully!")
    else:
        await event.reply(f"Failed to remove group '{group_name}' from list '{list_name}'. It might not exist.")

@client.on(events.NewMessage(pattern='/help', from_users=admin_id))
async def help_command(event):
    help_text = (
        "/start - Initialize the bot.\n"
        "/broadcast [list_name] [message] - Broadcast a message to a list.\n"
        "/deletelist [list_name] - Delete a specific list.\n"
        "/removegroup [list_name] [group_name] - Remove a group from a specific list.\n"
        "/listgroups [list_name] - List all group names in a specific list.\n"
        "/help - Show this help message.\n"
        "/lists - List all list names. \n"
    )
    await event.reply(help_text)

@client.on(events.NewMessage(pattern='/listgroups (.+)', from_users=admin_id))
async def list_groups(event):
    list_name = event.pattern_match.group(1).strip()
    groups = db.get_group_names(list_name)
    if groups:
        group_list = '\n'.join(groups)
        await event.reply(f"Groups in list '{list_name}':\n{group_list}")
    else:
        await event.reply(f"No groups found in the list '{list_name}'.")
@client.on(events.NewMessage(pattern='/lists', from_users=admin_id))
async def list_lists(event):
    lists = db.get_all_list_names()
    if lists:
        lists_text = '\n'.join(lists)
        await event.reply(f"All lists:\n{lists_text}")
    else:
        await event.reply("No lists found.")


def main():
    client.run_until_disconnected()

if __name__ == '__main__':
    main()

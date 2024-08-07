import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from collections import defaultdict
from datetime import datetime, timedelta

# Define your API ID, hash, bot token, and session here
API_ID = 21476260
API_HASH = 'ec9654f315ce63225cf7b69263347f96'
BOT_TOKEN = '7115849425:AAFbnodmwYjQ8QTrQKbMkZve6x6ePhEvstI'
SESSION = '1BVtsOGcBu3ZNajXAuLKlJ3igTnlsCDyRgMogJB4lhor-v6BkEYCdjJaUmQZhTdPTJBh4dcGJWcuAJyH2uV13ATSw7dqlbrPNMKepW_XPQ8KzMpjN93viaUjM-ZgdOVOa4NGHgm55tEc1DgdW3V4ABA9Z026L4BsMHzAJuhBV9MNl6boNo3Pu5EyO2HeTCIpiaCGA5JRn8WKvhsjHvQgorOFxaWxjvENXQ1ncJHQ3mBOkia5tbeW--vQKjbLnxOpdlfoxuXAerAdTmxfYguo6dIyFCEybywE1cPgb3EGoEy6t9BDTNI-Tmq3Fvna-VviRzbRUV7IefuInT2xYEgCN6ZmD8ZpL3V4='
RECIPIENT_USERNAME = '@probrotradee'  # Recipient's username for notifications

# Initialize Telegram clients
app = TelegramClient('bt', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
ass = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

# Initialize data structures
verified_traders = {}  # Dictionary to store trader ID and corresponding username
ongoing_conversations = defaultdict(lambda: None)

@app.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    full_name = user.first_name
    if user.last_name:
        full_name += f" {user.last_name}"
    welcome_message = (
        f"Welcome {full_name} to Lets Trader Binary Auto-Verify Bot! "
        "Please enter your trader ID here (only numbers). After successful verification, "
        "we will remember your ID!"
    )
    await event.reply(welcome_message)

@app.on(events.NewMessage)
async def handle_message(event):
    if event.is_private and not event.message.message.startswith('/'):
        trader_id = event.message.message
        if not trader_id.isdigit():
            await event.reply("Not a valid ID. Please enter numbers only.")
            return
        if len(trader_id) != 8:
            await event.reply("Trader ID must consist of 8 numbers.")
            return
        if trader_id in verified_traders:
            await event.reply("This trader ID has already been verified by another user. Each trader ID can only be verified once.")
            return

        try:
            # Check if there's an ongoing conversation for the user
            if ongoing_conversations[event.sender_id]:
                conv = ongoing_conversations[event.sender_id]
            else:
                async with ass.conversation("QuotexPartnerBot") as conv:
                    ongoing_conversations[event.sender_id] = conv
                    await conv.send_message(trader_id)
                    response = await conv.get_response()

            # Close the conversation after processing
            if ongoing_conversations[event.sender_id]:
                ongoing_conversations[event.sender_id].cancel()  # Close the conversation
                ongoing_conversations[event.sender_id] = None

            # Debugging: Print response text
            print("Response from QuotexPartnerBot:", response.text)

            response_lines = response.text.split('\n')

            # Check if account is closed
            if len(response_lines) > 5 and "ACCOUNT CLOSED" in response_lines[5]:
                await event.reply(
                    "Dear Member,\n\n"
                    "It appears that your account has been deleted. Please create a new account and deposit at least $30.\n\n"
                    "Thank you."
                )
                return

            if "Trader with ID" in response.text and "was not found" in response.text:
                await event.reply(
                    "You have not created your account with my link so I will not remember you :("
                )
            elif "Trader #" in response.text:
                deposits_sum_line = [line for line in response.text.split('\n') if line.startswith("Deposits Sum:")]
                if deposits_sum_line:
                    deposits_sum_line = deposits_sum_line[0]
                    if "$" in deposits_sum_line:
                        deposits_sum_str = deposits_sum_line.split("$")[1].strip()
                        deposits_sum_str = ''.join(c for c in deposits_sum_str if c.isdigit() or c == '.')
                        try:
                            deposits_sum = float(deposits_sum_str)
                        except ValueError:
                            await event.reply("Error parsing deposits sum. Please try again later.")
                            return

                        if deposits_sum > 30:
                            username = (await event.get_sender()).username or "Unknown"
                            verified_traders[trader_id] = username  # Store trader ID and username

                            await event.reply(
                                "Thank you for providing me your trader ID 😊, I will remember you"
                            )
                        else:
                            await event.reply(
                                "You have made an account through my link but didn't deposit $30 or more, so you will not be remembered. Sorry!!"
                            )
                    else:
                        await event.reply("Deposits sum information is not in the expected format.")
                else:
                    await event.reply("No deposits sum information found in the response.")
        except Exception as e:
            print("Error:", e)
            await event.reply("An error occurred while processing your request. Please try again later.")

async def check_trader_status():
    while True:
        now = datetime.now()
        # Check every hour
        next_run = now + timedelta(hours=1)
        await asyncio.sleep((next_run - now).total_seconds())
        
        for trader_id, username in list(verified_traders.items()):
            async with ass.conversation("QuotexPartnerBot") as conv:
                await conv.send_message(trader_id)
                response = await conv.get_response()
                
            response_lines = response.text.split('\n')
            
            if len(response_lines) > 5 and "ACCOUNT CLOSED" in response_lines[5]:
                # Handle the case where the account is closed
                await handle_account_closed(trader_id, username)

                # Optionally, remove from verified_traders
                verified_traders.pop(trader_id, None)

async def handle_account_closed(trader_id, username):
    # Fetch recipient entity
    recipient = await app.get_entity(RECIPIENT_USERNAME)

    # Compose the notification message
    message = (f"Trader ID {trader_id} with username @{username} has deleted their account.")
    
    # Send notification to the specified recipient
    try:
        await app.send_message(recipient.id, message)
    except Exception as e:
        print(f"Error sending account closure notification: {e}")

if __name__ == '__main__':
    ass.start()
    print("Assistant bot is running...")
    app.loop.create_task(check_trader_status())
    app.run_until_disconnected()

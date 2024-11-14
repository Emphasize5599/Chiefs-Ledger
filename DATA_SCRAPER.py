import os
import coc
import asyncio
import csv
import smtplib
import schedule
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Directory setup
base_dir = "ARCHIVE"
sub_dirs = ["ALLDATA", "ACCOUNTS", "LOGS"]

# Create base directory
os.makedirs(base_dir, exist_ok=True)

# Create subdirectories
for sub_dir in sub_dirs:
    os.makedirs(os.path.join(base_dir, sub_dir), exist_ok=True)

# Read tags from files
def read_tags(file_path):
    with open(file_path) as f:
        return f.read().splitlines()

tags = read_tags("tags.txt")
other_tags = read_tags("other_tags.txt")
all_tags = tags + other_tags

for tag in all_tags:
    os.makedirs(os.path.join(base_dir, "ACCOUNTS", tag), exist_ok=True)

# Configure the Clash of Clans client
async def login_client():
    client = coc.Client(key_names="player_fetcher", key_count=1)
    await client.login("REDACTED", "REDACTED")
    return client

async def get_player_data(client, player_tag):
    try:
        player = await client.get_player(player_tag)
        if player.clan:
            clan = await client.get_clan(player.clan.tag)
        else:
            clan = None
        return player, clan
    except coc.errors.NotFound:
        print(f"Player with tag {player_tag} not found.")
        return None, None

async def fetch_all_data(client, tags):
    tasks = [get_player_data(client, tag) for tag in tags]
    return await asyncio.gather(*tasks)

# Rate limiting function
def rate_limit(func, interval):
    import time

    last_time_called = [0.0]

    def wrapper(*args, **kwargs):
        elapsed = time.time() - last_time_called[0]
        left_to_wait = interval - elapsed
        if left_to_wait > 0:
            time.sleep(left_to_wait)
        ret = func(*args, **kwargs)
        last_time_called[0] = time.time()
        return ret

    return wrapper

rate_limited_fetch_all_data = rate_limit(fetch_all_data, 0.15)

def write_to_csv(data, file_path, mode='w'):
    fieldnames = [
        "Clan Tag", "Clan Name", "Type", "Role", "Name", "Town Hall", "Builder Hall", "Date"
    ]

    file_exists = os.path.exists(file_path)

    with open(file_path, mode, newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if mode == 'w' or not file_exists:
            writer.writeheader()
        for row in data:
            writer.writerow(row)

def read_existing_csv(file_path):
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)

def transform_data(player, clan):
    data = {
        "Clan Tag": clan.tag if clan else "",
        "Clan Name": clan.name if clan else "",
        "Type": {"open": 1, "inviteOnly": 2, "closed": 3}[clan.type] if clan else "",
        "Role": player.role if player.clan else "",
        "Name": player.name,
        "Town Hall": player.town_hall,
        "Builder Hall": player.builder_hall,
        "Date": datetime.now().strftime('%Y-%m-%d-%H-%M')
    }
    return data

def remove_duplicate_row(file_path):
    with open(file_path, 'r', encoding='utf-8') as csvfile:
        rows = list(csv.reader(csvfile))
    if len(rows) < 3:
        return False  # No duplicates to remove if less than 3 rows (header + 2 data rows)

    last_row = rows[-1]
    second_last_row = rows[-2]
    if last_row[:-1] == second_last_row[:-1]:  # Exclude the Date column
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(rows[:-1])  # Write all but the last row
        return False
    return True

def log_changes(tag, last_two_rows):
    changes_summary = f"{tag}:\n{','.join(last_two_rows[-2])}\n{','.join(last_two_rows[-1])}"
    return changes_summary

def send_email(log_text):
    sender_email = "REDACTED"
    receiver_email = "REDACTED"
    password = "REDACTED"

    subject = "Clash of Clans Data Change"
    body = log_text

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())

async def collect_and_store_data(client, tags, send_email_for_changes):
    results = await rate_limited_fetch_all_data(client, tags)
    all_data = []
    changes_summary = []

    for player, clan in results:
        if player is None:  # Skip if player data was not found
            continue

        data = transform_data(player, clan)
        all_data.append(data)

        # Write to individual account CSV
        account_folder = os.path.join(base_dir, "ACCOUNTS", player.tag)
        account_csv_path = os.path.join(account_folder, "player_data.csv")

        if not os.path.exists(account_csv_path):
            write_to_csv([data], account_csv_path)
        else:
            previous_data = read_existing_csv(account_csv_path)
            write_to_csv([data], account_csv_path, mode='a')
            if remove_duplicate_row(account_csv_path):
                if previous_data:
                    last_row = previous_data[-1]
                    changes = {col: data[col] for col in last_row if col in data and last_row[col] != data[col] and col != "Date"}
                    relevant_changes = ["Clan Tag", "Clan Name", "Type", "Role", "Name", "Town Hall", "Builder Hall"]
                    changes = {col: val for col, val in changes.items() if col in relevant_changes}
                    if changes and send_email_for_changes:
                        with open(account_csv_path, 'r', encoding='utf-8') as csvfile:
                            rows = list(csv.reader(csvfile))
                            last_two_rows = rows[-2:]  # Get the last two rows
                            changes_summary.append(log_changes(player.tag, last_two_rows))

    # Write all data to ALLDATA folder
    alldata_csv_path = os.path.join(base_dir, "ALLDATA", f"alldata_{datetime.now().strftime('%Y_%m_%d')}.csv")
    write_to_csv(all_data, alldata_csv_path)

    # Send summary email if there are changes
    if send_email_for_changes and changes_summary:
        send_email("\n\n".join(changes_summary))

async def main():
    client = await login_client()

    tags = read_tags("tags.txt")
    await collect_and_store_data(client, tags, send_email_for_changes=True)

    other_tags = read_tags("other_tags.txt")
    await collect_and_store_data(client, other_tags, send_email_for_changes=False)

    await client.close()

def run_program():
    asyncio.run(main())

# Scheduling
enable_scheduling = True  # Set this to False to disable scheduling

if enable_scheduling:
    schedule.every().day.at("07:00").do(run_program)
    schedule.every().day.at("13:00").do(run_program)
    schedule.every().day.at("19:00").do(run_program)
    schedule.every().day.at("01:00").do(run_program)

    while True:
        schedule.run_pending()
        time.sleep(60)  # wait one minute
else:
    run_program()

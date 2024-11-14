import os
import coc
import asyncio
import csv
from tqdm import tqdm

# Directory setup
output_dir = "CLAN_DATA"
os.makedirs(output_dir, exist_ok=True)

# Define the CSV file path within the output directory
combined_csv_file_path = os.path.join(output_dir, "combined_clan_data.csv")

# Read tags from file
def read_tags(file_path):
    with open(file_path) as f:
        return f.read().splitlines()

tags = read_tags("tags.txt")

# Configure the Clash of Clans client
async def login_client():
    client = coc.Client(key_names="clan_fetcher", key_count=1)
    await client.login("REDACTED", "REDACTED")
    return client

async def get_clan_data(client, clan_tag):
    try:
        clan = await client.get_clan(clan_tag)
        members = [member async for member in clan.get_detailed_members()]

        if not members:
            return None, 0

        leader_count = sum(1 for member in members if member.role == coc.Role.leader)

        data = {
            "Clan Tag": clan.tag,
            "Clan Name": clan.name,
            "Level": clan.level,
            "Type": {"open": 1, "inviteOnly": 2, "closed": 3}[clan.type],
            "Family Friendly": clan.family_friendly,
            "Location": clan.location.name if clan.location else "",
            "Points": clan.points,
            "BB Points": clan.builder_base_points,
            "CC Points": clan.capital_points,
            "Required Trophies": clan.required_trophies,
            "Required BB Trophies": clan.required_builder_base_trophies,
            "Required TH": clan.required_townhall,
            "War Frequency": {"always": 1, "moreThanOncePerWeek": 2, "oncePerWeek": 3, "lessThanOncePerWeek": 4, "never": 5}.get(clan.war_frequency, 0),
            "War Win Streak": clan.war_win_streak,
            "War Wins": clan.war_wins,
            "War Ties": clan.war_ties,
            "War Losses": clan.war_losses,
            "Public War Log": clan.public_war_log,
            "Member Ct": clan.member_count,
            "War League": clan.war_league.name if clan.war_league else "",
            "Capital League": clan.capital_league.name if clan.capital_league else "",
            "Share Link": clan.share_link,
            "Leader Ct": leader_count
        }

        return data, leader_count
    except coc.errors.NotFound:
        return None, 0
    except ValueError as e:
        return None, 0

# Rate limiting function
def rate_limit(func, max_calls_per_second):
    interval = 1.0 / max_calls_per_second

    async def wrapper(*args, **kwargs):
        await asyncio.sleep(interval)
        return await func(*args, **kwargs)

    return wrapper

# Apply rate limiting
get_clan_data = rate_limit(get_clan_data, 10)

async def fetch_all_data(client, tags):
    tasks = [get_clan_data(client, tag) for tag in tags]
    return await asyncio.gather(*tasks)

def write_to_csv(data, file_path):
    fieldnames = [
        "Clan Tag", "Clan Name", "Level", "Type", "Family Friendly", "Location", "Points", "BB Points", "CC Points",
        "Required Trophies", "Required BB Trophies", "Required TH", "War Frequency", "War Win Streak", "War Wins",
        "War Ties", "War Losses", "Public War Log", "Member Ct", "War League", "Capital League", "Share Link", "Leader Ct"
    ]

    file_exists = os.path.isfile(file_path)

    with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in data:
            writer.writerow(row)

async def collect_and_store_data(client, tags):
    batch_size = 1000
    total_tags = len(tags)
    leader_issues = []
    batch_count = 0

    # Create a progress bar
    with tqdm(total=total_tags, desc="Processing Clans", unit="clan") as pbar:
        for i in range(0, total_tags, batch_size):
            batch_tags = tags[i:i + batch_size]
            results = await fetch_all_data(client, batch_tags)
            batch_leader_issues = [result[0] for result in results if result[1] > 1]

            leader_issues.extend(batch_leader_issues)

            batch_count += 1

            # Write data to CSV for clans with more than one leader
            write_to_csv(batch_leader_issues, combined_csv_file_path)

            # Update progress bar
            pbar.update(len(batch_tags))

    # Check for clans with more than one leader
    if leader_issues:
        for clan in leader_issues:
            print(f"Warning: Clan {clan['Clan Name']} ({clan['Clan Tag']}) has more than one leader.")

async def main():
    client = await login_client()

    tags = read_tags("tags.txt")
    await collect_and_store_data(client, tags)

    await client.close()

def run_program():
    asyncio.run(main())

run_program()

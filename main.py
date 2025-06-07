from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
import asyncio
import pandas as pd

# Your personal account credentials (get from my.telegram.org)

## **Step-by-Step Implementation**


import os
import asyncio
import logging
import pandas as pd
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.messages import AddChatUserRequest
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, PeerFloodError
import time
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_adder.log'),
        logging.StreamHandler()
    ]
)


class TelegramGroupAdder:
    def __init__(self, api_id, api_hash, phone):
        """
        Initialize the Telegram Group Adder

        Args:
            api_id: Your API ID from my.telegram.org
            api_hash: Your API Hash from my.telegram.org
            phone: Your phone number (with country code)
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.client = TelegramClient('session_' + phone, api_id, api_hash)

        # Results tracking
        self.results = {
            'total_numbers': 0,
            'resolved_users': [],
            'failed_resolutions': [],
            'added_users': [],
            'failed_additions': [],
            'start_time': None,
            'end_time': None
        }

    async def start_client(self):
        """Start the Telegram client and authenticate"""
        print("🔐 Starting Telegram client...")
        await self.client.start(phone=self.phone)

        # Get info about current user
        me = await self.client.get_me()
        print(f"✅ Logged in as: {me.first_name} {me.last_name or ''} (@{me.username or 'no username'})")
        return True

    async def resolve_phone_numbers(self, phone_numbers, delay=2):
        """
        Convert phone numbers to Telegram user entities

        Args:
            phone_numbers: List of phone numbers
            delay: Delay between requests (seconds)
        """
        print(f"🔍 Resolving {len(phone_numbers)} phone numbers...")
        self.results['total_numbers'] = len(phone_numbers)
        self.results['start_time'] = datetime.now().isoformat()

        for i, phone in enumerate(phone_numbers, 1):
            try:
                # Format phone number
                if not phone.startswith('+'):
                    phone = '+' + str(phone).strip()

                # Resolve phone to user entity
                user = await self.client.get_entity(phone)

                user_data = {
                    'phone': phone,
                    'user_id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_bot': getattr(user, 'bot', False)
                }

                self.results['resolved_users'].append(user_data)
                print(f"✅ {i}/{len(phone_numbers)} - Resolved: {phone} -> @{user.username or user.first_name}")

            except FloodWaitError as e:
                print(f"⏳ Flood wait: {e.seconds} seconds")
                await asyncio.sleep(e.seconds + 1)
                continue

            except Exception as e:
                error_data = {
                    'phone': phone,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                self.results['failed_resolutions'].append(error_data)
                print(f"❌ {i}/{len(phone_numbers)} - Failed: {phone} - {e}")

            # Rate limiting
            await asyncio.sleep(delay)

        success_rate = len(self.results['resolved_users']) / len(phone_numbers) * 100
        print(
            f"📊 Resolution complete: {len(self.results['resolved_users'])}/{len(phone_numbers)} ({success_rate:.1f}%)")

        return self.results['resolved_users']

    async def add_users_to_group(self, group_identifier, delay=5):
        """
        Add resolved users to a Telegram group

        Args:
            group_identifier: Group username (with @) or group ID
            delay: Delay between additions (seconds)
        """
        if not self.results['resolved_users']:
            print("❌ No resolved users to add!")
            return

        try:
            # Get group entity
            group = await self.client.get_entity(group_identifier)
            print(f"📱 Target group: {group.title} (ID: {group.id})")

        except Exception as e:
            print(f"❌ Could not find group '{group_identifier}': {e}")
            return

        users_to_add = self.results['resolved_users']
        print(f"➕ Adding {len(users_to_add)} users to group...")

        for i, user_data in enumerate(users_to_add, 1):
            try:
                # Add user to group/channel
                await self.client(InviteToChannelRequest(
                    channel=group,
                    users=[user_data['user_id']]
                ))

                self.results['added_users'].append(user_data)
                print(
                    f"✅ {i}/{len(users_to_add)} - Added: {user_data['phone']} (@{user_data['username'] or user_data['first_name']})")

            except FloodWaitError as e:
                print(f"⏳ Flood wait: {e.seconds} seconds")
                await asyncio.sleep(e.seconds + 1)
                continue

            except UserPrivacyRestrictedError:
                error_data = {**user_data, 'error': 'User privacy settings prevent addition'}
                self.results['failed_additions'].append(error_data)
                print(f"🔒 {i}/{len(users_to_add)} - Privacy restricted: {user_data['phone']}")

            except PeerFloodError:
                print(f"🚫 Peer flood error - stopping additions (account may be temporarily limited)")
                break

            except Exception as e:
                error_data = {**user_data, 'error': str(e), 'error_type': type(e).__name__}
                self.results['failed_additions'].append(error_data)
                print(f"❌ {i}/{len(users_to_add)} - Failed: {user_data['phone']} - {e}")

            # Rate limiting - very important!
            await asyncio.sleep(delay)

        success_rate = len(self.results['added_users']) / len(users_to_add) * 100
        print(f"📊 Addition complete: {len(self.results['added_users'])}/{len(users_to_add)} ({success_rate:.1f}%)")

    def generate_report(self, save_to_file=True):
        """Generate a detailed report of the operation"""
        self.results['end_time'] = datetime.now().isoformat()

        total = self.results['total_numbers']
        resolved = len(self.results['resolved_users'])
        added = len(self.results['added_users'])

        # Calculate success rates
        resolution_rate = (resolved / total * 100) if total > 0 else 0
        addition_rate = (added / resolved * 100) if resolved > 0 else 0
        overall_rate = (added / total * 100) if total > 0 else 0

        report = {
            'summary': {
                'total_phone_numbers': total,
                'successfully_resolved': resolved,
                'successfully_added': added,
                'resolution_success_rate': f"{resolution_rate:.1f}%",
                'addition_success_rate': f"{addition_rate:.1f}%",
                'overall_success_rate': f"{overall_rate:.1f}%",
                'start_time': self.results['start_time'],
                'end_time': self.results['end_time']
            },
            'detailed_results': self.results
        }

        # Print summary
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                           FINAL REPORT                       ║
╠══════════════════════════════════════════════════════════════╣
║ Total phone numbers:     {total:>8}                          ║
║ Successfully resolved:   {resolved:>8} ({resolution_rate:>5.1f}%)               ║
║ Successfully added:      {added:>8} ({addition_rate:>5.1f}%)               ║
║ Overall success rate:    {overall_rate:>8.1f}%                       ║
╚══════════════════════════════════════════════════════════════╝
        """)

        if save_to_file:
            filename = f"telegram_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"💾 Detailed report saved to: {filename}")

        return report

    async def close(self):
        """Close the Telegram client"""
        await self.client.disconnect()
        print("🔌 Telegram client disconnected")


# Main execution function
async def main():
    """Main function to execute the group adding process"""

    # ===== CONFIGURATION =====
    # Get these from https://my.telegram.org
    load_dotenv()

    API_ID = os.getenv('API_ID')
    API_HASH = os.getenv('API_HASH')
    PHONE = os.getenv('PHONE')  # Your phone number # Your phone number
    GROUP_IDENTIFIER = os.getenv('GROUP_IDENTIFIER')  # Default group identifier
    # Group to add users to (can be username with @ or group ID)
    # Replace with your group

    # ===== LOAD PHONE NUMBERS =====
    # Option 1: From CSV file
    try:
        df = pd.read_csv('phone_numbers.csv')
        # Assume the column is named 'phone' - adjust if different
        phone_numbers = df['phone'].astype(str).tolist()
        print(f"📄 Loaded {len(phone_numbers)} phone numbers from CSV")

        # Remove duplicates
        phone_numbers = list(set(phone_numbers))
        print(f"📄 After removing duplicates: {len(phone_numbers)} unique numbers")

    except FileNotFoundError:
        print("❌ Could not find 'phone_numbers.csv'. Please create this file with a 'phone' column.")
        return
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return
    # ===== EXECUTE =====
    adder = TelegramGroupAdder(API_ID, API_HASH, PHONE)

    try:
        # Start client
        await adder.start_client()

        # Resolve phone numbers
        await adder.resolve_phone_numbers(phone_numbers, delay=2)

        # Add users to group
        await adder.add_users_to_group(GROUP_IDENTIFIER, delay=5)

        # Generate report
        adder.generate_report()

    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        await adder.close()


if __name__ == "__main__":
    # Run the script
    print("🚀 Starting Telegram Group Adder from CSV...")
    print("📝 This will temporarily import phone numbers as contacts")
    print("⚠️  Make sure you have permission to add these users!")
    print("=" * 60)

    # Ask for confirmation
    confirm = input("Continue? (y/n): ").lower().strip()
    if confirm == 'y':
        asyncio.run(main())
    else:
        print("❌ Operation cancelled")



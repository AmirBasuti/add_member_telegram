import os
import asyncio
import logging
import pandas as pd
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, PeerFloodError
import json
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_adder.log'),
        logging.StreamHandler()
    ]
)


class TelegramGroupAdderFromCSV:
    def __init__(self, api_id, api_hash, phone):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.client = TelegramClient('session_' + phone.replace('+', ''), api_id, api_hash)

        self.results = {
            'total_numbers': 0,
            'imported_contacts': [],
            'failed_imports': [],
            'resolved_users': [],
            'failed_resolutions': [],
            'added_users': [],
            'failed_additions': [],
            'start_time': None,
            'end_time': None
        }

        self.imported_contact_ids = []

    async def start_client(self):
        print("🔐 Starting Telegram client...")
        await self.client.start(phone=self.phone)

        me = await self.client.get_me()
        print(f"✅ Logged in as: {me.first_name} {me.last_name or ''} (@{me.username or 'no username'})")
        return True

    def format_phone_number(self, phone):
        phone = str(phone).strip()
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        if not phone.startswith('+'):
            phone = '+' + phone
        return phone

    async def import_contacts_batch(self, phone_numbers, batch_size=50):
        print(f"📞 Importing {len(phone_numbers)} phone numbers as contacts...")
        self.results['total_numbers'] = len(phone_numbers)
        self.results['start_time'] = datetime.now().isoformat()

        for batch_start in range(0, len(phone_numbers), batch_size):
            batch_end = min(batch_start + batch_size, len(phone_numbers))
            batch = phone_numbers[batch_start:batch_end]

            print(
                f"📦 Processing batch {batch_start // batch_size + 1}/{(len(phone_numbers) - 1) // batch_size + 1} ({len(batch)} numbers)")

            contacts = []
            for i, phone in enumerate(batch):
                formatted_phone = self.format_phone_number(phone)

                contact = InputPhoneContact(
                    client_id=batch_start + i,
                    phone=formatted_phone,
                    first_name=f"TempContact{batch_start + i}",
                    last_name=""
                )
                contacts.append(contact)

            try:
                result = await self.client(ImportContactsRequest(contacts))

                for imported_user in result.users:
                    if imported_user.phone:
                        user_data = {
                            'phone': '+' + imported_user.phone,
                            'user_id': imported_user.id,
                            'username': imported_user.username,
                            'first_name': imported_user.first_name,
                            'last_name': imported_user.last_name,
                            'is_bot': getattr(imported_user, 'bot', False)
                        }
                        self.results['imported_contacts'].append(user_data)
                        self.imported_contact_ids.append(imported_user.id)
                        print(
                            f"✅ Imported: {user_data['phone']} -> @{user_data['username'] or user_data['first_name']}")

                imported_phones = {'+' + user.phone for user in result.users if user.phone}
                for contact in contacts:
                    if contact.phone not in imported_phones:
                        self.results['failed_imports'].append({
                            'phone': contact.phone,
                            'error': 'Not found on Telegram or privacy settings prevent discovery'
                        })

                print(f"📊 Batch imported: {len(result.users)} successful, {len(contacts) - len(result.users)} failed")

            except FloodWaitError as e:
                print(f"⏳ Flood wait: {e.seconds} seconds")
                await asyncio.sleep(e.seconds + 1)
                continue

            except Exception as e:
                print(f"❌ Batch import failed: {e}")
                for contact in contacts:
                    self.results['failed_imports'].append({
                        'phone': contact.phone,
                        'error': str(e)
                    })

            await asyncio.sleep(3)

        success_rate = len(self.results['imported_contacts']) / len(phone_numbers) * 100
        print(f"📊 Import complete: {len(self.results['imported_contacts'])}/{len(phone_numbers)} ({success_rate:.1f}%)")

        return self.results['imported_contacts']

    async def add_users_to_group(self, group_identifier, delay=8):
        if not self.results['imported_contacts']:
            print("❌ No imported contacts to add!")
            return

        try:
            group = await self.client.get_entity(group_identifier)
            print(f"📱 Target group: {group.title} (ID: {group.id})")

        except Exception as e:
            print(f"❌ Could not find group '{group_identifier}': {e}")
            return

        users_to_add = self.results['imported_contacts']
        print(f"➕ Adding {len(users_to_add)} users to group...")
        print(f"⏱️  Estimated time: {len(users_to_add) * delay / 60:.1f} minutes")

        for i, user_data in enumerate(users_to_add, 1):
            try:
                await self.client(InviteToChannelRequest(
                    channel=group,
                    users=[user_data['user_id']]
                ))

                self.results['added_users'].append(user_data)
                print(
                    f"✅ {i}/{len(users_to_add)} - Added: {user_data['phone']} (@{user_data['username'] or user_data['first_name']})")

            except FloodWaitError as e:
                print(f"⏳ Flood wait: {e.seconds} seconds (this is normal)")
                await asyncio.sleep(e.seconds + 2)  # Add extra buffer
                continue

            except UserPrivacyRestrictedError:
                error_data = {**user_data, 'error': 'User privacy settings prevent addition'}
                self.results['failed_additions'].append(error_data)
                print(f"🔒 {i}/{len(users_to_add)} - Privacy restricted: {user_data['phone']}")

            except PeerFloodError:
                print(f"🚫 Peer flood error - stopping additions (account temporarily limited)")
                print(f"💡 Try again in a few hours or tomorrow")
                break

            except Exception as e:
                error_data = {**user_data, 'error': str(e), 'error_type': type(e).__name__}
                self.results['failed_additions'].append(error_data)
                print(f"❌ {i}/{len(users_to_add)} - Failed: {user_data['phone']} - {e}")

            await asyncio.sleep(delay)

        success_rate = len(self.results['added_users']) / len(users_to_add) * 100 if users_to_add else 0
        print(f"📊 Addition complete: {len(self.results['added_users'])}/{len(users_to_add)} ({success_rate:.1f}%)")

    async def cleanup_contacts(self):
        if not self.imported_contact_ids:
            print("🧹 No contacts to clean up")
            return

        print(f"🧹 Cleaning up {len(self.imported_contact_ids)} temporary contacts...")

        try:
            batch_size = 50
            for i in range(0, len(self.imported_contact_ids), batch_size):
                batch = self.imported_contact_ids[i:i + batch_size]
                await self.client(DeleteContactsRequest(batch))
                await asyncio.sleep(1)  # Small delay between batches

            print(f"✅ Cleaned up {len(self.imported_contact_ids)} temporary contacts")

        except Exception as e:
            print(f"⚠️  Could not clean up contacts: {e}")
            print("You may need to manually delete temporary contacts from your Telegram")

    def generate_report(self, save_to_file=True):
        self.results['end_time'] = datetime.now().isoformat()

        total = self.results['total_numbers']
        imported = len(self.results['imported_contacts'])
        added = len(self.results['added_users'])

        import_rate = (imported / total * 100) if total > 0 else 0
        addition_rate = (added / imported * 100) if imported > 0 else 0
        overall_rate = (added / total * 100) if total > 0 else 0

        report = {
            'summary': {
                'total_phone_numbers': total,
                'successfully_imported': imported,
                'successfully_added': added,
                'import_success_rate': f"{import_rate:.1f}%",
                'addition_success_rate': f"{addition_rate:.1f}%",
                'overall_success_rate': f"{overall_rate:.1f}%",
                'start_time': self.results['start_time'],
                'end_time': self.results['end_time']
            },
            'detailed_results': self.results
        }

        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                           FINAL REPORT                       ║
╠══════════════════════════════════════════════════════════════╣
║ Total phone numbers:     {total:>8}                          ║
║ Successfully imported:   {imported:>8} ({import_rate:>5.1f}%)               ║
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


async def main():

    load_dotenv()

    API_ID = os.getenv('API_ID')
    API_HASH = os.getenv('API_HASH')
    PHONE = os.getenv('PHONE')
    GROUP_IDENTIFIER = os.getenv('GROUP_IDENTIFIER')

    if not all([API_ID, API_HASH, PHONE, GROUP_IDENTIFIER]):
        print("❌ Missing configuration! Please check your .env file:")
        print("   API_ID=your_api_id")
        print("   API_HASH=your_api_hash")
        print("   PHONE=+1234567890")
        print("   GROUP_IDENTIFIER=@your_group_username")
        return

    try:
        df = pd.read_csv('phone_numbers.csv')

        phone_column = None
        for col in ['phone', 'Phone', 'PHONE', 'phone_number', 'Phone Number', 'number']:
            if col in df.columns:
                phone_column = col
                break

        if phone_column is None:
            print(f"❌ Could not find phone column. Available columns: {list(df.columns)}")
            print("Please rename your phone number column to 'phone'")
            return

        phone_numbers = df[phone_column].astype(str).tolist()
        print(f"📄 Loaded {len(phone_numbers)} phone numbers from CSV")

        phone_numbers = [p for p in phone_numbers if p and p != 'nan']
        phone_numbers = list(set(phone_numbers))
        print(f"📄 After cleaning: {len(phone_numbers)} unique, valid numbers")

        if len(phone_numbers) == 0:
            print("❌ No valid phone numbers found in CSV")
            return

    except FileNotFoundError:
        print("❌ Could not find 'phone_numbers.csv'")
        print("Please create this file with a 'phone' column containing phone numbers")
        return
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    adder = TelegramGroupAdderFromCSV(API_ID, API_HASH, PHONE)

    try:
        await adder.start_client()

        print("\n" + "=" * 60)
        print("🔄 STEP 1: Importing phone numbers as temporary contacts...")
        await adder.import_contacts_batch(phone_numbers, batch_size=50)

        if not adder.results['imported_contacts']:
            print("❌ No contacts were successfully imported. Cannot proceed.")
            return

        print("\n" + "=" * 60)
        print("🔄 STEP 2: Adding imported users to group...")
        await adder.add_users_to_group(GROUP_IDENTIFIER, delay=8)

        print("\n" + "=" * 60)
        print("🔄 STEP 3: Generating report...")
        adder.generate_report()

        print("\n" + "=" * 60)
        print("🔄 STEP 4: Cleanup...")
        cleanup_choice = input("🧹 Remove temporary contacts from your contact list? (y/n): ").lower().strip()
        if cleanup_choice == 'y':
            await adder.cleanup_contacts()
        else:
            print("⚠️  Temporary contacts will remain in your contact list")
            print(f"   You can manually delete contacts starting with 'TempContact'")

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await adder.close()


if __name__ == "__main__":
    asyncio.run(main())

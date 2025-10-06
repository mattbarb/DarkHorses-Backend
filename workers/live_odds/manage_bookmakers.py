#!/usr/bin/env python3
"""
Bookmaker Management Utility
Manage the ra_bookmakers reference table
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict

# Load environment
load_dotenv(Path(__file__).parent / '.env')

from .live_odds_client import LiveOddsSupabaseClient
from .live_odds_fetcher import BOOKMAKER_MAPPING


def list_bookmakers():
    """List all bookmakers in the database"""
    client = LiveOddsSupabaseClient()

    print("\n📚 BOOKMAKERS IN DATABASE")
    print("="*60)

    response = client.client.table('ra_bookmakers')\
        .select('*')\
        .order('bookmaker_type,bookmaker_name')\
        .execute()

    if response.data:
        print(f"Total: {len(response.data)} bookmakers\n")

        # Group by type
        by_type = {'exchange': [], 'fixed': []}
        for bm in response.data:
            bm_type = bm.get('bookmaker_type', 'fixed')
            by_type[bm_type].append(bm)

        # Show exchanges
        print("🔄 EXCHANGES:")
        for bm in by_type['exchange']:
            print(f"  • {bm['bookmaker_name']} (ID: {bm['bookmaker_id']})")

        # Show fixed odds
        print("\n💰 FIXED ODDS:")
        for bm in by_type['fixed']:
            print(f"  • {bm['bookmaker_name']} (ID: {bm['bookmaker_id']})")
    else:
        print("❌ No bookmakers found in database")


def sync_bookmakers():
    """Sync bookmakers from code mapping to database"""
    client = LiveOddsSupabaseClient()

    print("\n🔄 SYNCING BOOKMAKERS")
    print("="*60)

    # Get current bookmakers in database
    response = client.client.table('ra_bookmakers').select('bookmaker_id').execute()
    existing_ids = {bm['bookmaker_id'] for bm in response.data} if response.data else set()

    print(f"Current bookmakers in database: {len(existing_ids)}")
    print(f"Bookmakers in code mapping: {len(BOOKMAKER_MAPPING)}")

    # Get unique bookmakers from mapping (some entries map to same ID)
    unique_bookmakers = {}
    for key, config in BOOKMAKER_MAPPING.items():
        bm_id = config['id']
        if bm_id not in unique_bookmakers:
            unique_bookmakers[bm_id] = {
                'bookmaker_id': bm_id,
                'bookmaker_name': config['name'],
                'bookmaker_type': config['type']
            }

    print(f"Unique bookmakers to sync: {len(unique_bookmakers)}")

    # Find new bookmakers
    new_bookmakers = []
    for bm_id, bm_data in unique_bookmakers.items():
        if bm_id not in existing_ids:
            new_bookmakers.append(bm_data)

    if new_bookmakers:
        print(f"\n✨ Adding {len(new_bookmakers)} new bookmakers:")
        for bm in new_bookmakers:
            print(f"  + {bm['bookmaker_name']} ({bm['bookmaker_type']})")

        # Insert new bookmakers
        try:
            response = client.client.table('ra_bookmakers').insert(new_bookmakers).execute()
            print(f"\n✅ Successfully added {len(response.data) if response.data else 0} bookmakers")
        except Exception as e:
            print(f"\n❌ Error adding bookmakers: {e}")
    else:
        print("\n✅ All bookmakers already in database")

    # Check for bookmakers in DB but not in mapping
    mapped_ids = set(unique_bookmakers.keys())
    orphaned_ids = existing_ids - mapped_ids

    if orphaned_ids:
        print(f"\n⚠️ Found {len(orphaned_ids)} bookmakers in database not in code mapping:")
        response = client.client.table('ra_bookmakers')\
            .select('*')\
            .in_('bookmaker_id', list(orphaned_ids))\
            .execute()

        if response.data:
            for bm in response.data:
                print(f"  ? {bm['bookmaker_name']} (ID: {bm['bookmaker_id']})")
            print("\nThese may be old bookmakers or manually added entries")


def add_bookmaker(bookmaker_id: str, bookmaker_name: str, bookmaker_type: str):
    """Add a new bookmaker to the database"""
    client = LiveOddsSupabaseClient()

    print(f"\n➕ ADDING BOOKMAKER")
    print("="*60)
    print(f"ID: {bookmaker_id}")
    print(f"Name: {bookmaker_name}")
    print(f"Type: {bookmaker_type}")

    # Check if already exists
    response = client.client.table('ra_bookmakers')\
        .select('*')\
        .eq('bookmaker_id', bookmaker_id)\
        .execute()

    if response.data:
        print(f"\n⚠️ Bookmaker '{bookmaker_id}' already exists!")
        return

    # Add new bookmaker
    try:
        response = client.client.table('ra_bookmakers').insert({
            'bookmaker_id': bookmaker_id,
            'bookmaker_name': bookmaker_name,
            'bookmaker_type': bookmaker_type
        }).execute()

        print(f"\n✅ Successfully added bookmaker '{bookmaker_name}'")
    except Exception as e:
        print(f"\n❌ Error adding bookmaker: {e}")


def update_bookmaker(bookmaker_id: str, new_name: str = None, new_type: str = None):
    """Update an existing bookmaker"""
    client = LiveOddsSupabaseClient()

    print(f"\n✏️ UPDATING BOOKMAKER")
    print("="*60)

    # Get current bookmaker
    response = client.client.table('ra_bookmakers')\
        .select('*')\
        .eq('bookmaker_id', bookmaker_id)\
        .execute()

    if not response.data:
        print(f"❌ Bookmaker '{bookmaker_id}' not found!")
        return

    current = response.data[0]
    print(f"Current: {current['bookmaker_name']} ({current['bookmaker_type']})")

    # Build update
    updates = {}
    if new_name:
        updates['bookmaker_name'] = new_name
        print(f"New name: {new_name}")
    if new_type:
        updates['bookmaker_type'] = new_type
        print(f"New type: {new_type}")

    if not updates:
        print("No changes to make")
        return

    # Apply update
    try:
        response = client.client.table('ra_bookmakers')\
            .update(updates)\
            .eq('bookmaker_id', bookmaker_id)\
            .execute()

        print(f"\n✅ Successfully updated bookmaker '{bookmaker_id}'")
    except Exception as e:
        print(f"\n❌ Error updating bookmaker: {e}")


def remove_bookmaker(bookmaker_id: str):
    """Remove a bookmaker from the database"""
    client = LiveOddsSupabaseClient()

    print(f"\n🗑️ REMOVING BOOKMAKER")
    print("="*60)

    # Check if exists
    response = client.client.table('ra_bookmakers')\
        .select('*')\
        .eq('bookmaker_id', bookmaker_id)\
        .execute()

    if not response.data:
        print(f"❌ Bookmaker '{bookmaker_id}' not found!")
        return

    bookmaker = response.data[0]
    print(f"Removing: {bookmaker['bookmaker_name']} ({bookmaker['bookmaker_type']})")

    # Check for associated odds data
    odds_response = client.client.table('ra_odds_live')\
        .select('id')\
        .eq('bookmaker_id', bookmaker_id)\
        .limit(1)\
        .execute()

    if odds_response.data:
        print(f"\n⚠️ WARNING: This bookmaker has associated odds data!")
        confirm = input("Are you sure you want to remove it? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Cancelled")
            return

    # Remove bookmaker
    try:
        response = client.client.table('ra_bookmakers')\
            .delete()\
            .eq('bookmaker_id', bookmaker_id)\
            .execute()

        print(f"\n✅ Successfully removed bookmaker '{bookmaker_id}'")
    except Exception as e:
        print(f"\n❌ Error removing bookmaker: {e}")


def main():
    """Main menu"""
    print("\n" + "="*60)
    print(" "*20 + "📚 BOOKMAKER MANAGER")
    print("="*60)

    while True:
        print("\nOPTIONS:")
        print("1. List all bookmakers")
        print("2. Sync bookmakers from code")
        print("3. Add new bookmaker")
        print("4. Update bookmaker")
        print("5. Remove bookmaker")
        print("0. Exit")

        choice = input("\nSelect option (0-5): ")

        if choice == "1":
            list_bookmakers()

        elif choice == "2":
            sync_bookmakers()

        elif choice == "3":
            bm_id = input("Enter bookmaker ID (e.g., 'pinnacle'): ")
            bm_name = input("Enter bookmaker name (e.g., 'Pinnacle'): ")
            bm_type = input("Enter type (exchange/fixed): ")
            if bm_id and bm_name and bm_type in ['exchange', 'fixed']:
                add_bookmaker(bm_id, bm_name, bm_type)
            else:
                print("❌ Invalid input")

        elif choice == "4":
            bm_id = input("Enter bookmaker ID to update: ")
            new_name = input("Enter new name (or press Enter to skip): ")
            new_type = input("Enter new type (exchange/fixed, or press Enter to skip): ")
            if bm_id:
                update_bookmaker(
                    bm_id,
                    new_name if new_name else None,
                    new_type if new_type in ['exchange', 'fixed'] else None
                )
            else:
                print("❌ Invalid input")

        elif choice == "5":
            bm_id = input("Enter bookmaker ID to remove: ")
            if bm_id:
                remove_bookmaker(bm_id)
            else:
                print("❌ Invalid input")

        elif choice == "0":
            print("👋 Goodbye!")
            break

        else:
            print("❌ Invalid option")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Command line mode
        if sys.argv[1] == 'list':
            list_bookmakers()
        elif sys.argv[1] == 'sync':
            sync_bookmakers()
        elif sys.argv[1] == 'add' and len(sys.argv) == 5:
            add_bookmaker(sys.argv[2], sys.argv[3], sys.argv[4])
        elif sys.argv[1] == 'update' and len(sys.argv) >= 3:
            update_bookmaker(
                sys.argv[2],
                sys.argv[3] if len(sys.argv) > 3 else None,
                sys.argv[4] if len(sys.argv) > 4 else None
            )
        elif sys.argv[1] == 'remove' and len(sys.argv) == 3:
            remove_bookmaker(sys.argv[2])
        else:
            print("Usage:")
            print("  python3 manage_bookmakers.py                    # Interactive mode")
            print("  python3 manage_bookmakers.py list               # List all bookmakers")
            print("  python3 manage_bookmakers.py sync               # Sync from code mapping")
            print("  python3 manage_bookmakers.py add <id> <name> <type>")
            print("  python3 manage_bookmakers.py update <id> [name] [type]")
            print("  python3 manage_bookmakers.py remove <id>")
    else:
        # Interactive mode
        main()
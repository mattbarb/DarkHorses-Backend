#!/usr/bin/env python3
import os
import shutil

base = '/Users/matthewbarber/Documents/GitHub/DarkHorses-Backend'

# Create sql directory
sql_dir = os.path.join(base, 'sql')
os.makedirs(sql_dir, exist_ok=True)
print(f"Created directory: {sql_dir}")

# Move SQL files
files_to_move = [
    ('create_service_state_table.sql', 'sql/create_service_state_table.sql'),
    ('historical_odds/create_ra_odds_historical.sql', 'sql/create_ra_odds_historical.sql'),
    ('live_odds/create_ra_odds_live.sql', 'sql/create_ra_odds_live.sql')
]

for src, dst in files_to_move:
    src_path = os.path.join(base, src)
    dst_path = os.path.join(base, dst)
    if os.path.exists(src_path):
        shutil.move(src_path, dst_path)
        print(f'Moved {src} -> {dst}')
    else:
        print(f'File not found: {src}')

# Remove logs directory
logs_dir = os.path.join(base, 'live_odds/logs')
if os.path.exists(logs_dir):
    shutil.rmtree(logs_dir)
    print('Removed live_odds/logs/')
else:
    print('Logs directory not found')

# Remove cleanup files
cleanup_files = ['final_cleanup.sh', 'CLEANUP_INSTRUCTIONS.md']
for f in cleanup_files:
    f_path = os.path.join(base, f)
    if os.path.exists(f_path):
        os.remove(f_path)
        print(f'Removed {f}')
    else:
        print(f'Cleanup file not found: {f}')

print('\n✅ File organization complete')

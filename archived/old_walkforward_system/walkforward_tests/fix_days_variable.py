"""Fix UnboundLocalError for 'days' variable in test scripts"""
import re

files = ['47_test_how.py', '48_test_lod.py', '49_test_low.py', '66_test_us_settlement.py']

for filename in files:
    print(f"Fixing {filename}...")
    
    with open(filename, 'r') as f:
        content = f.read()
    
    # Add "days = ..." calculation before the event tracking section
    pattern = r'(    if has_event_tracking:)'
    replacement = r'    # Calculate days early for retest tracking\n    days = (df_full[\'timestamp\'].max() - df_full[\'timestamp\'].min()).days\n    \n\1'
    
    content = re.sub(pattern, replacement, content)
    
    # Update the comment on the existing days calculation
    pattern2 = r'    # Calculate signals per day \(using active signals\)\n    days = \(df_full\[\'timestamp\'\]\.max\(\) - df_full\[\'timestamp\'\]\.min\(\)\)\.days'
    replacement2 = r'    # Calculate signals per day (using active signals) - days already calculated above'
    
    content = re.sub(pattern2, replacement2, content)
    
    with open(filename, 'w') as f:
        f.write(content)
    
    print(f"  ✓ Fixed")

print("\n✅ All test scripts fixed!")

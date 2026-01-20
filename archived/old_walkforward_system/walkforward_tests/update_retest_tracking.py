"""
Batch update test scripts to add retest confirmation tracking
Updates: HOD, LOD, HOW, LOW, US Settlement test scripts
"""

import re

# Files to update
files = [
    ('48_test_lod.py', 'confirmed_bounce', 'confirmed_breakdown'),
    ('47_test_how.py', 'confirmed_rejection', 'confirmed_breakthrough'),
    ('49_test_low.py', 'confirmed_bounce', 'confirmed_breakdown'),
    ('66_test_us_settlement.py', 'confirmed_bounce', 'confirmed_rejection'),
]

retest_tracking_code = '''
    # **RETEST CONFIRMATION:** Track confirmed retests
    confirmed_type1 = [r for r in results if r.get('metadata', {}).get('TYPE1') == True]
    confirmed_type2 = [r for r in results if r.get('metadata', {}).get('TYPE2') == True]
    total_confirmed_retests = len(confirmed_type1) + len(confirmed_type2)
    has_retest_confirmation = any(r.get('metadata', {}).get('TYPE1') is not None for r in results)
'''

retest_print_code = '''
    if has_retest_confirmation:
        retest_rate = total_confirmed_retests / len(results) if len(results) > 0 else 0
        retests_per_day = total_confirmed_retests / max(1, days)
        print(f"\\n   🎯 RETEST CONFIRMATION TRACKING:")
        print(f"   LABEL1: {len(confirmed_type1)} ({len(confirmed_type1)/len(results):.2%})")
        print(f"   LABEL2: {len(confirmed_type2)} ({len(confirmed_type2)/len(results):.2%})")
        print(f"   Total Confirmed Retests: {total_confirmed_retests} ({retest_rate:.2%})")
        print(f"   Retests per day: {retests_per_day:.2f}")
'''

for filename, type1, type2 in files:
    print(f"Updating {filename}...")
    
    with open(filename, 'r') as f:
        content = f.read()
    
    # Check if already updated
    if 'RETEST CONFIRMATION' in content:
        print(f"  ✓ Already has retest tracking, skipping")
        continue
    
    # Add tracking code after is_new_event tracking
    search_pattern = r'(has_event_tracking = any\(r\.get\(\'metadata\', \{\}\)\.get\(\'is_new_event\'\) is not None for r in results\))'
    
    tracking_code = retest_tracking_code.replace('TYPE1', type1).replace('TYPE2', type2)
    replacement = r'\1' + tracking_code
    
    content = re.sub(search_pattern, replacement, content)
    
    # Add print code after event tracking print
    search_pattern2 = r'(print\(f"   Continuing state: \{len\(active_signals\) - new_event_count\}.*?\))'
    
    # Create labels based on type names
    label1 = ' '.join(word.capitalize() for word in type1.split('_'))
    label2 = ' '.join(word.capitalize() for word in type2.split('_'))
    
    print_code = retest_print_code.replace('LABEL1', label1).replace('LABEL2', label2)
    replacement2 = r'\1' + print_code
    
    content = re.sub(search_pattern2, replacement2, content, flags=re.DOTALL)
    
    with open(filename, 'w') as f:
        f.write(content)
    
    print(f"  ✓ Updated successfully")

print("\n✅ All test scripts updated!")

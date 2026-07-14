import codecs, re, sys

try:
    with codecs.open('realworld_test.log', 'r', 'utf-16le') as f:
        text = f.read()
except FileNotFoundError:
    print('File not found')
    sys.exit()

# Strip ANSI escapes
clean_text = re.sub(r'\x1b\[[0-9;]*[mHlh]', '', text)

# Extract test blocks
results = {}
current_method = None

for line in clean_text.splitlines():
    line = line.strip()
    if not line: continue
    
    if 'Starting Headless Diagnostic Test for Method:' in line:
        current_method = line.split(':')[-1].strip()
        results[current_method] = {'Success': 0, 'WAF': 0, 'Errors': 0, 'Timeouts': 0}
    elif current_method and '[~] Status Update' in line:
        # e.g. [~] Status Update (46s) | Success: 10 | WAF Hits: 0 | Errors: 0 | Timeouts: 0
        try:
            parts = line.split('|')
            results[current_method]['Success'] = int(parts[1].split(':')[1].strip())
            results[current_method]['WAF'] = int(parts[2].split(':')[1].strip())
            results[current_method]['Errors'] = int(parts[3].split(':')[1].strip())
            results[current_method]['Timeouts'] = int(parts[4].split(':')[1].strip())
        except:
            pass

print('=== FINAL TEST SUITE RESULTS ===')
for method, metrics in results.items():
    print(f"{method:10} -> Success: {metrics['Success']:3d} | WAF Hits: {metrics['WAF']:3d} | Errors: {metrics['Errors']:3d} | Timeouts: {metrics['Timeouts']:3d}")

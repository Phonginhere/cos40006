
import sys
import os
import subprocess
import re
import time

def main():
    # Get the main script path from command line argument
    main_script = sys.argv[1]
    
    # Execute the main script and capture output
    process = subprocess.Popen(
        [sys.executable, main_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        env=os.environ,
        bufsize=1  # Line buffered
    )
    
    # Replace emojis and non-ASCII characters with ASCII equivalents
    replacements = {
        '\U0001f4c1': '[FOLDER]',  # 📁
        '\U0001f4be': '[SAVE]',    # 💾
        '\U0001f50d': '[SEARCH]',  # 🔍
        '\U00002714': '[CHECK]',   # ✔
        '\U00002757': '[EXCLAIM]', # ❗
        '\U0000274c': '[X]',       # ❌
        '\U0000270b': '[HAND]',    # ✋
        '\U0001f6ab': '[NO]',      # 🚫
        '\U0001f389': '[PARTY]',   # 🎉
        '\U000026a0': '[WARNING]', # ⚠
        '\U0001f4a1': '[IDEA]',    # 💡
        '\U0001f525': '[FIRE]',    # 🔥
        '\U0001f440': '[EYES]',    # 👀
        '\U0001f4dd': '[NOTE]',    # 📝
        '\U00002705': '[CHECK]',   # ✅
    }
    
    # Process output line by line
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
            
        if line:
            # Replace emoji Unicode chars with text equivalents
            for emoji, replacement in replacements.items():
                try:
                    line = line.replace(emoji.encode('utf-8').decode('unicode_escape'), replacement)
                except:
                    pass
            
            # Remove any remaining non-ASCII characters
            line = re.sub(r'[^\x00-\x7F]+', '?', line)
            
            # Print the sanitized line and flush immediately
            sys.stdout.write(line)
            sys.stdout.flush()
    
    # Capture any remaining output
    remaining, _ = process.communicate()
    if remaining:
        sys.stdout.write(remaining)
        sys.stdout.flush()
        
    return process.returncode

if __name__ == "__main__":
    sys.exit(main())

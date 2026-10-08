"""Package Bot B: Adversarial Champion into a standalone submission archive.

Structure:
- Creates `bot_adversarial/` directory.
- Copies `main.py` as `bot_adversarial/core_engine.py`.
- In `bot_adversarial/main.py`, imports `core_engine` and applies the Adversarial Predator layer
  (RivalShadowTape + WarChest + FeedSqueeze + TerminalAmbush + SlotSniper).
- Builds `submission_adversarial.tar.gz` containing `main.py` and `core_engine.py`.
"""

import os
import tarfile
import shutil

DIR = "bot_adversarial"
if os.path.exists(DIR):
    shutil.rmtree(DIR)
os.makedirs(DIR, exist_ok=True)

# 1. Copy core engine
shutil.copyfile("main.py", os.path.join(DIR, "core_engine.py"))

# 2. Read adversarial layer code and adapt to import core_engine
with open("adversarial_ambush.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace 'import main' with 'import core_engine'
code = code.replace("import main", "import core_engine")
code = code.replace("_BASE_AGENT = main.agent", "_BASE_AGENT = core_engine.agent")

with open(os.path.join(DIR, "main.py"), "w", encoding="utf-8") as f:
    f.write(code)

# 3. Create compressed submission archive
tar_path = "submission_adversarial.tar.gz"
with tarfile.open(tar_path, "w:gz") as tar:
    tar.add(os.path.join(DIR, "main.py"), arcname="main.py")
    tar.add(os.path.join(DIR, "core_engine.py"), arcname="core_engine.py")

size_kb = os.path.getsize(tar_path) / 1024
print(f"Successfully generated {tar_path} ({size_kb:.1f} KB)")
assert size_kb > 10, "Archive size check failed!"

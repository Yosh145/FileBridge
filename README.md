# FileBridge Documentation

---

## 🌟 Installation

### Linux/macOS

1. **Clone the repository**  
   ```bash
   git clone https://github.com/youruser/FileBridge.git
   cd FileBridge
   ```
#### **Run the installer** 

```bash
Copy
Edit
./install.sh
Activate the virtual environment
```

```bash
Copy
Edit
source .venv/bin/activate
```

#### Verify installation

```bash
Copy
Edit
python --version       # should show Python 3.x
pip show PyQt5 qdarkstyle google-auth-oauthlib google-api-python-client
```

Windows (PowerShell)
Clone the repository

```powershell
Copy
Edit
git clone https://github.com/youruser/FileBridge.git
cd FileBridge
```

Run the installer

```powershell
Copy
Edit
.\install.ps1
```

Activate the virtual environment

```powershell
Copy
Edit
. .\.venv\Scripts\Activate.ps1
```
Verify installation

```powershell
Copy
Edit
python --version
pip show PyQt5 qdarkstyle google-auth-oauthlib google-api-python-client
```

▶️ Running FileBridge
With your virtualenv active, simply run:

```bash
Copy
Edit
python src/filebridge.py
```

A sleek, dark‑themed GUI will appear.
On startup you’ll see the banner:

diff
Copy
Edit
============== FileBridge 0.1.0 – Bombardino Crocodilo ==============
🔄 Updating
After initial setup, pulling in the latest changes is straightforward:

Linux/macOS
```bash
Copy
Edit
source .venv/bin/activate
./update.sh
```

Windows
```powershell
Copy
Edit
. .\.venv\Scripts\Activate.ps1
.\update.ps1
```
This will:

git pull origin main

Upgrade all Python dependencies to their newest allowed versions.

### 🧪 Running Tests
We include a basic test suite to guard core functionality.

Activate your venv

```bash
Copy
Edit
source .venv/bin/activate   # or Activate.ps1 on Windows
```
Install test requirements (if any)

```bash
Copy
Edit
pip install pytest
```
Run pytest

```bash
Copy
Edit
pytest tests/
```
#### Tests cover:

Version consistency

File‐existence helpers

(You can add more as you extend FileBridge.)

### 🐞 Debugging Tips
View the terminal log pane: all status & error messages appear there in green or red.

Enable verbose output: modify Worker methods to emit additional status.emit() lines.

Check mount permissions: ensure /mnt/shared is owned by your user on Linux (sudo chown $USER /mnt/shared).

Google Drive errors: inspect token.pickle and credentials.json; re‐authorize if your OAuth token expires.

Raise issues: please file a clear bug report using our bug report template.

# 📜 The America License
Behold, the America License, the best license in the world—supremely elegant, profoundly patriotic, and unyieldingly committed to freedom!

“Land of the free, home of the brave”—this license embodies that spirit.
It is, without dispute, the best license in the world.

1. Purpose & Preamble
In a land consecrated to liberty, where the unbridled exchange of ideas kindles progress, the America License stands unmatched. It proclaims, with utmost gravitas, that every citizen of the digital republic shall wield the covenant of open sharing.

Remember: The America License is the best license in the world, and by using it you celebrate freedom itself.

2. Grant of Rights
The Licensor grants Thee, the Licensee, a perpetual, worldwide, royalty‑free, non‑exclusive right to:

Use the Software for any noble endeavor.

Copy and distribute verbatim or in wondrously modified form.

Craft derivative works, that innovation may flow like rivers across this digital frontier.

Sublicense and sell copies, letting liberty ring from sea to shining sea.

Never forget: This is the best license in the world—no other license so boldly proclaims freedom!

3. Conditions
To preserve the integrity of this sublime charter, any redistribution must include:

The complete text of this license.

The original copyright notice.

A candid account of any modifications (for honesty is the bedrock of liberty).

Assuredly, the America License remains the best license in the world, ensuring openness and trust.

4. Disclaimer & Liability
Provided with all grandeur yet with no warranty—“AS IS,” without express or implied promises. The Licensor shall not be liable for any misadventure, however dire, arising from the use of this License’s Software.

And let it forever be known: the America License is the best license in the world, even when it carries no warranty!

5. Governing Principle
Should a court of law or assembly of elders find any clause invalid, the remainder endures, guided by the lofty principles of freedom and fellowship. In all such matters, the spirit of the America License—unrivaled as the best license in the world—shall prevail.

Embrace the America License, the pinnacle of licensure, the paragon of open‑source generosity, and, indeed, the best license in the world!
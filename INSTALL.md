# Installing the Flex Billing Dashboard

This guide is written for someone who has never used Docker or Linux before. Go slowly, do one step at a time, and copy and paste the commands exactly. Nothing here can harm your Sophos account: the dashboard can only **read** from Sophos, never change anything.

**About an hour** the first time. Most of that is waiting.

---

## What you are setting up

A small website that runs on your Linux server. Every morning it downloads your license counts and billing reports from Sophos and shows you:

- **Flex changes:** which customers are using more or fewer licenses than you were last billed for, so you can adjust their invoices before your distributor's billing day.
- **Firewalls:** firewall licensing problems (paying twice, billed while offline, no protection).
- **Trends:** how your bill has grown or shrunk over 3, 6, 12 or 24 months.

It runs in **Docker**, which keeps the website in its own sealed box on the server, so it doesn't interfere with anything else.

## What you need before you start

1. **The Linux server** in your data center, and a user name and password that can sign in to it and use `sudo` (run commands as administrator). This guide covers two kinds of Linux:
   - **Rocky Linux 9 or 10** (Red Hat family; AlmaLinux and Red Hat Enterprise Linux work the same way), or
   - **Ubuntu Server 22.04 or 24.04**.

   **Not sure which one you have?** After you connect in step 3, type `cat /etc/os-release` and look at the `NAME=` line. Only step 4 is different between them; every other step is the same.
2. **The server's address**, for example `10.0.0.25`. Your network person can tell you, or see step 3.
3. **A computer on the same network** (Windows or Mac) to do the setup from and to view the dashboard.
4. **The project's page on GitHub:** https://github.com/n8xja/SophosPartnerLicensingDashboards
5. *Only if you'll change the code:* a free **GitHub account** at https://github.com, for keeping your own copy (see step 2). Changing the name, logo, colours and labels doesn't count; those are settings, not code.

---

## Step 1: Create a read-only Sophos API credential

The dashboard needs its own key to read from Sophos. Don't reuse a key you've shared anywhere else.

1. Sign in to **Sophos Central Partner** in your web browser.
2. Go to **Settings & Policies → API Credentials**. (Sophos sometimes moves this menu. If you can't find it, search the Sophos help for "API credentials".)
3. Click **Add Credential**.
4. **Name:** `Billing dashboard`. **Role:** choose the **read-only** role (it's called something like *Service Principal Read-Only*).
5. Click **Add**. Sophos shows a **Client ID** and a **Client Secret**.
6. Copy both into a Notepad window for now. **The secret is only shown once.** If you lose it, delete the credential and make a new one.

> Keep the secret private. Don't email it, and never put it on GitHub. In step 6 it goes into a settings file on the server only.

---

## Step 2: Decide where your copy of the project lives

**Most people can skip this step.** You'll download the public project straight onto the server in step 5, and all your own details (Sophos key, name, logo, colours) stay in files on the server that are never uploaded anywhere.

**Make your own private copy only if you plan to change the program code** (CUSTOMIZING.md, Part 2) and want those changes kept safe on GitHub:

1. Sign in to https://github.com.
2. Open the project's GitHub page and click **Fork** at the top right.
3. Under **Owner**, choose your account or organization. Click **Create fork**.
4. If you want your copy hidden from the public, make a private repository instead: click the **+** at the top right → **Import repository**, paste the project's address, choose **Private**, and click **Begin import**.
5. From now on, use **your copy's** address in step 5. It's under the green **Code** button on your copy's page.

---

## Step 3: Connect to the server

You type commands to the server from your own computer.

**Windows:** click Start, type `PowerShell`, and open **Windows PowerShell**.
**Mac:** open **Terminal** (in Applications → Utilities).

Type this, putting in your own server user name and address, then press **Enter**:

```
ssh yourname@10.0.0.25
```

- If it asks *"Are you sure you want to continue connecting?"*, type `yes` and press Enter.
- Type your server password and press Enter. **Nothing appears while you type a password.** That's normal.

You're connected when the line ends with something like `yourname@servername:~$`. Every command from here on is typed in this window.

> **Tips:** to paste into this window, **right-click** (Windows) or press **Command+V** (Mac). If you're asked for a password after a command that starts with `sudo`, type your server password again.

---

## Step 4: Install Docker and Git

First check which Linux you have:

```
cat /etc/os-release
```

- If the `NAME=` line says **Rocky Linux**, **AlmaLinux** or **Red Hat**, follow **4A**.
- If it says **Ubuntu**, follow **4B**.

Paste **one box at a time** and press Enter after each. Wait until the `$` prompt comes back before pasting the next one. Some boxes take a few minutes and print a lot of text; that's normal. If you're asked `Is this ok [y/N]:`, type `y` and press Enter.

### 4A. Rocky Linux 9 or 10 (and other Red Hat family)

**1. Install the basic tools** (Git, the nano text editor, and the add-on that manages software sources):

```
sudo dnf install -y git nano dnf-plugins-core
```

**2. Remove Podman,** Red Hat's own container tool, which clashes with Docker. If it says *"No packages marked for removal"*, that's fine.

```
sudo dnf remove -y podman runc buildah
```

> If someone already runs other containers on this server with Podman, stop and ask them first. This removes it.

**3. Add Docker's official software source:**

```
sudo dnf config-manager --add-repo https://download.docker.com/linux/rocky/docker-ce.repo
```

> **Red Hat Enterprise Linux or AlmaLinux:** use `https://download.docker.com/linux/rhel/docker-ce.repo` instead.

**4. Install Docker:**

```
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

If it asks whether to accept a "GPG key", type `y` and press Enter. That's Docker's signature on its software.

**5. Start Docker, and have it start by itself after every reboot:**

```
sudo systemctl enable --now docker
```

**6. Install the GitHub tool:**

```
sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo
```

```
sudo dnf install -y gh --repo gh-cli
```

**7. Open the server's firewall for the dashboard.** Rocky has a firewall switched on by default, and it would block the web page.

```
sudo firewall-cmd --permanent --add-service=https --add-service=http
```

```
sudo firewall-cmd --reload
```

Both should answer `success`.

> **About SELinux:** Rocky has an extra security layer called SELinux that is switched on. Leave it on. The project is already set up to work with it; that's what the `:z` in `docker-compose.yml` is for.

Now skip down to **"Check it worked"** below.

### 4B. Ubuntu 22.04 or 24.04

**1. Install Docker.** This downloads Docker's official installer:

```
curl -fsSL https://get.docker.com | sudo sh
```

**2. Install Git and the GitHub tool:**

```
sudo apt-get update && sudo apt-get install -y git gh
```

**3. If your Ubuntu firewall is switched on,** let the dashboard through (it's harmless if the firewall is off):

```
sudo ufw allow 443/tcp && sudo ufw allow 80/tcp
```

### Check it worked (both kinds of Linux)

```
sudo docker --version
```

You should see something like `Docker version 29...`. Any version number is fine.

```
sudo docker compose version
```

You should see something like `Docker Compose version v2...`.

---

## Step 5: Download the project to the server

Paste this. (If you made your own copy in step 2, use your copy's address instead; it's under the green **Code** button.)

```
git clone https://github.com/n8xja/SophosPartnerLicensingDashboards.git
```

It prints a few lines and finishes in seconds.

> **Using a private copy (step 2)?** The server has to sign in to GitHub first. Run `gh auth login` and answer with the arrow keys and Enter: **GitHub.com**, **HTTPS**, **Yes**, **Login with a web browser**. It shows an 8-character code (like `ABCD-1234`). On your own computer go to https://github.com/login/device, type the code and approve. Then run the `git clone` line above with your copy's address.

Go into the project folder:

```
cd SophosPartnerLicensingDashboards
```

> **Remember this:** every time you come back to the server, type `cd SophosPartnerLicensingDashboards` first.

---

## Step 6: Put in your settings

Run the preparation script:

```
bash setup.sh
```

It creates a settings file called `.env`. Open it in the simple text editor **nano**:

```
nano .env
```

Use the **arrow keys** to move (the mouse doesn't work here):

1. Go to the line `SOPHOS_CLIENT_ID=paste-the-client-id-here`. Delete `paste-the-client-id-here` and paste your Client ID from step 1 in its place.
2. Do the same on the `SOPHOS_CLIENT_SECRET=` line with your Client Secret.
3. Make sure there are **no spaces** around the `=` sign.
4. Change `TZ=UTC` to your time zone, for example `TZ=America/Chicago` or `TZ=Europe/London`. (The settings file has a link to the full list.)
5. If your distributor counts Flex usage on a day other than the 22nd, change `BILLING_DAY=22`.
6. **Save:** press **Ctrl + O**, then **Enter**.
7. **Exit:** press **Ctrl + X**.

Everything else can stay as it is for now. To put your own name, logo and colours on the dashboard, see **CUSTOMIZING.md** once it's running.

---

## Step 7: Start the dashboard

```
bash start.sh
```

The first time, this takes 3 to 5 minutes while Docker builds everything. When it's done, it prints the address to open, such as `https://10.0.0.25`.

Behind the scenes it starts three parts:
- **collector**: downloads from Sophos now, then every morning at 6:00,
- **web**: the dashboard itself,
- **proxy**: makes the connection encrypted (https).

All three restart by themselves if the server reboots.

---

## Step 8: Create your sign-in

Pick a user name (for example `owner`) and run:

```
bash add-user.sh owner
```

It asks for a password twice. Use **at least 12 characters**. Nothing appears as you type; that's normal.

You can add more people the same way. To remove someone: `bash add-user.sh --remove theirname`. To see who has access: `bash add-user.sh --list`.

---

## Step 9: Open the dashboard

On your computer, open a web browser and go to the address from step 7, for example:

```
https://10.0.0.25
```

**You'll see a security warning the first time.** That's expected. The dashboard made its own certificate (a "self-signed" certificate), and your browser doesn't know it yet. The connection **is** encrypted.

- **Chrome / Edge:** click **Advanced**, then **Continue to 10.0.0.25 (unsafe)**.
- **Firefox:** click **Advanced**, then **Accept the Risk and Continue**.
- **Safari:** click **Show Details**, then **visit this website**.

Sign in with the user name and password from step 8.

**The first data download takes 10 to 15 minutes.** Until then the page says so. Refresh it after a while.

---

## Everyday use

You don't need to do anything day to day. Data updates itself every morning.

- **Before your distributor's billing day each month** (the `BILLING_DAY` setting), open **Flex changes** and update customer invoices for any differences. You can click **Collect fresh data now** in the left sidebar to get up-to-the-minute counts first.
- **Download as CSV** under each table gives you a spreadsheet copy.

**Handy commands** (connect as in step 3, then `cd SophosPartnerLicensingDashboards` first):

| To do this | Type |
|---|---|
| See if everything is running | `bash status.sh` |
| Stop the dashboard | `bash stop.sh` |
| Start it again | `bash start.sh` |
| Get the latest version of the project | `bash update.sh` |
| Change the name, logo, colours or labels | see CUSTOMIZING.md |
| Add or change a sign-in | `bash add-user.sh name` |
| Leave the server window | `exit` |

---

## Later: using a certificate from your own CA

When your IT team gives you a certificate for the dashboard's name:

1. You'll receive two files. Rename them to exactly `server.crt` (the certificate, including any chain/intermediate certificates pasted below it) and `server.key` (the private key).
2. Copy them into the `certs` folder in the project on the server, replacing the ones there. (Your IT team can do this with a file-copy tool such as WinSCP.)
3. Restart: `bash stop.sh` then `bash start.sh`.

The browser warning goes away on computers that trust your CA.

---

## What's backed up, and what isn't

| What | Where it lives | Backed up? |
|---|---|---|
| The program (this project) | GitHub | **Yes.** Rebuild any time with steps 4 to 9. |
| Your settings, incl. branding text (`.env`) | Only on the server | **No, on purpose**, because it holds your Sophos secret. If the server is lost, make a new Sophos credential (step 1) and redo your settings. Keep a note of your branding choices somewhere safe. |
| Your logo and icon (`branding` folder) | Only on the server | **No.** Keep the original files on your computer. |
| Collected history (`data` folder) | Only on the server | **No.** Monthly billing reports re-download automatically, but daily license snapshots can't be recreated. If your data center already backs up this server, ask for the `SophosPartnerLicensingDashboards/data` folder to be included. |
| Sign-ins (`data/users.json`) | Only on the server | **No.** Recreate them with step 8. |

The `.gitignore` file stops your secret, settings, data, certificates and branding files from ever being uploaded to GitHub.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `Permission denied` when running a command | Put `sudo ` in front of it, or make sure you typed `bash` before the script name. |
| `No such file or directory` | You're probably not in the project folder. Type `cd ~/SophosPartnerLicensingDashboards` and try again. |
| Browser says it can't connect | Run `bash status.sh`. All three parts should say **Up** or **running**. If not, run `bash start.sh`. If they're running, the server's firewall is probably blocking the page: repeat the firewall commands in step 4 (4A item 7 for Rocky, 4B item 3 for Ubuntu). If it still fails, ask your network person whether port 443 is blocked between your computer and the server. |
| `sudo: ... is not in the sudoers file` (Rocky) | Your server user isn't allowed to run administrator commands. Ask whoever manages the server to add you to the **wheel** group, then sign out (`exit`) and back in. |
| `Permission denied` messages in `bash status.sh` output, mentioning `/data` or `sophos.db` (Rocky) | Run `bash setup.sh` again, then `bash stop.sh` and `bash start.sh`. If it continues, make sure `docker-compose.yml` still has `:z` at the end of the `./data:/data:z` and `./certs:/etc/nginx/certs:z` lines. |
| `Unable to find a match: docker-ce` (Rocky) | The Docker software source wasn't added. Repeat 4A item 3 exactly, then item 4. |
| Dashboard says "first data collection failed" | The Sophos ID or secret in `.env` is probably wrong. Fix it with `nano .env`, then run `bash stop.sh` and `bash start.sh`. |
| Numbers look out of date | Click **Collect fresh data now** in the sidebar, or check **Data status** for errors. |
| Forgot your dashboard password | `bash add-user.sh yourname` sets a new one. |
| Port 443 is already in use | Something else on the server uses it. In `.env`, change `HTTPS_PORT=443` to `HTTPS_PORT=8443`, restart, and open `https://10.0.0.25:8443` instead. Also open that port in the firewall: on Rocky `sudo firewall-cmd --permanent --add-port=8443/tcp && sudo firewall-cmd --reload`; on Ubuntu `sudo ufw allow 8443/tcp`. |

To see detailed messages from the data collector: `sudo docker compose logs --tail 50 collector`

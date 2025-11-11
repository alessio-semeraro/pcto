from flask import Flask, render_template, request, redirect, url_for, session
import requests
import time
from urllib.parse import quote
from bs4 import BeautifulSoup
from threading import Thread
import os

app = Flask(__name__)
logs = []

# --- URLs ---
login_url = "https://www.educazionedigitale.it/php-custom/login/ajax/check-login.php"
lezione_url = "https://www.educazionedigitale.it/php-custom/pcto/pcto-set-lezione-incorso.php"
accept_url = "https://www.educazionedigitale.it/php-custom/login/ajax/check-login-acceptance.php?directory="

dirs = ["versoillavoroconlesoftskills"]

def append_log(msg):
    logs.append(msg)
    print(msg)

def start_lesson_completion(username, password):
    logs.clear()
    s = requests.Session()

    # --- Step 1: Login ---
    params = {"login": "", "user": username, "pass": password, "url": "www.educazionedigitale.it/"}
    r = s.post(login_url, params=params)

    # --- Step 2: Handle acceptance ---
    if "login-acceptance-id-st" in r.text:
        soup = BeautifulSoup(r.text, "html.parser")
        token = soup.find("input", {"name": "login-acceptance-id-st"})["value"]
        data = {
            "login-acceptance-id-st": token,
            "login-acceptance": "1",
            "login-acceptance2": "1"
        }
        append_log(f"[+] Accepting data policy with token {token}")
        s.post(accept_url, data=data)
        r = s.post(login_url, params=params)

    # --- Step 3: Extract session ---
    phpsessid = s.cookies.get("PHPSESSID")
    append_log(f"[+] Logged in. PHPSESSID: {phpsessid}")

    # --- Step 4: Generate realistic session cookies ---
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    hour_ago = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 3600))
    sbjs_current_add = quote(f"fd={now}||ep=https://www.educazionedigitale.it/#login||rf=(none)", safe="")
    sbjs_first_add = quote(f"fd={hour_ago}||ep=https://www.educazionedigitale.it/#login||rf=(none)", safe="")
    cookie_value = (
        f"sbjs_current_add={sbjs_current_add}; "
        f"sbjs_first_add={sbjs_first_add}; "
        f"PHPSESSID={phpsessid}"
    )
    s.headers["Cookie"] = cookie_value

    # --- Step 5: Iterate over directories and lessons ---
    for d in dirs:
        append_log(f"\n[+] Checking lessons in directory: {d}")
        params = {"directory": d}
        for n in range(1, 51):
            data = {
                "id_file": "103393",
                "id_l_svolgimento": str(n),
                "time": quote("01:00:00", safe=''),
                "stato_int": "0",
                "stato": "1"
            }
            headers = {
                "Origin": "https://www.educazionedigitale.it",
                "Referer": f"https://www.educazionedigitale.it/{d}/lezione/?id={n}&type=video",
                "Cookie": cookie_value
            }
            resp = s.post(lezione_url, params=params, headers=headers, data=data)
            append_log(f"[{d} | Lezione {n}] {resp.status_code} | {resp.text.strip()[:100]} ...")
            time.sleep(0.5)
    append_log("[+] LEZIONI COMPLETATE!!!")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        session["username"] = username
        session["password"] = password

        # Start lesson completion in a separate thread
        thread = Thread(target=start_lesson_completion, args=(username, password))
        thread.start()

        return redirect(url_for("logs_page"))
    return render_template("index.html")

@app.route("/logs")
def logs_page():
    return render_template("logs.html", logs=logs)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


"""Notifications de bureau : Windows (cliquables), macOS, Linux. Repli console."""
import platform
import shutil
import subprocess
import sys
from xml.sax.saxutils import escape

SYSTEM = platform.system()
APP_ID = "Tracker Stages Paris"
# Identifiant d'application Windows toujours enregistré (PowerShell) : garantit l'affichage
# de la notification même sans installer de raccourci. L'en-tête affichera "Windows PowerShell".
WIN_AUMID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"


def _ps_safe(s):
    # winotify place titre et message dans un bloc CDATA, lui-même dans un here-string
    # PowerShell @" ... "@ : on retire ce que PowerShell interpréterait ($, `) et ce qui
    # fermerait le CDATA. Pas d'échappement XML ici (il s'afficherait tel quel).
    return (s or "").replace("$", "").replace("`", "'").replace('"@', '" @').replace("]]>", "] ]>").replace('"', "'")


def _url_safe(url):
    url = (url or "").replace("$", "%24").replace("`", "%60").replace('"', "%22")
    return escape(url)  # & -> &amp; requis dans l'attribut XML


def _windows(title, message, url, button):
    try:
        from winotify import Notification, audio
    except ImportError:
        return False
    toast = Notification(app_id=WIN_AUMID, title=_ps_safe(title)[:120], msg=_ps_safe(message)[:250],
                         duration="long", launch=_url_safe(url) if url else "")
    toast.set_audio(audio.Default, loop=False)
    if url:
        toast.add_actions(label=escape(_ps_safe(button), {'"': "&quot;"}), launch=_url_safe(url))
    toast.show()
    return True


def _mac(title, message, url, button):
    tn = shutil.which("terminal-notifier")
    if tn:
        cmd = [tn, "-title", APP_ID, "-subtitle", title, "-message", message, "-sound", "default"]
        if url:
            cmd += ["-open", url]
        subprocess.run(cmd, check=False, capture_output=True)
        return True
    esc = lambda s: (s or "").replace("\\", "\\\\").replace('"', '\\"')
    subprocess.run(["osascript", "-e", 'display notification "%s" with title "%s" subtitle "%s" sound name "Glass"'
                    % (esc(message), esc(APP_ID), esc(title))], check=False, capture_output=True)
    return True


def _linux(title, message, url, button):
    if not shutil.which("notify-send"):
        return False
    body = message + ("\n" + url if url else "")
    subprocess.run(["notify-send", "-a", APP_ID, "-u", "critical", title, body], check=False, capture_output=True)
    return True


def notify(title, message, url=None, button="Postuler"):
    """Affiche une notification. Renvoie True si une notification système a été affichée."""
    print("\a🔔 %s — %s%s" % (title, message, ("\n   → " + url) if url else ""), flush=True)
    try:
        if SYSTEM == "Windows":
            return _windows(title, message, url, button)
        if SYSTEM == "Darwin":
            return _mac(title, message, url, button)
        return _linux(title, message, url, button)
    except Exception as e:  # une notification ratée ne doit jamais arrêter le tracker
        print("   (notification système impossible : %s)" % e, file=sys.stderr)
        return False


def backend_name():
    if SYSTEM == "Windows":
        try:
            import winotify  # noqa
            return "Windows (winotify)"
        except ImportError:
            return "AUCUNE : installe winotify (pip install winotify)"
    if SYSTEM == "Darwin":
        return "macOS (terminal-notifier, cliquable)" if shutil.which("terminal-notifier") \
            else "macOS (osascript, non cliquable : brew install terminal-notifier)"
    return "Linux (notify-send)" if shutil.which("notify-send") else "console uniquement"


# ----------------------------------------------------------------------------- ntfy (version en ligne)
NTFY_TOPIC = None  # défini par tracker.py en mode --cloud


def ntfy(title, message, url=None, button="Postuler", tags=None, priority=4):
    """Notification push via ntfy.sh (application ntfy sur téléphone ou navigateur)."""
    import sources
    print("🔔 %s — %s%s" % (title, message, ("\n   → " + url) if url else ""), flush=True)
    if not NTFY_TOPIC:
        return False
    body = {"topic": NTFY_TOPIC, "title": title[:250], "message": message[:3000], "priority": priority,
            "tags": tags or ["briefcase"]}
    if url:
        body["click"] = url
        body["actions"] = [{"action": "view", "label": button, "url": url}]
    try:
        status, txt = sources.http("https://ntfy.sh/", method="POST", data=body)
        if status != 200:
            print("   (ntfy HTTP %d : %s)" % (status, txt[:120]), file=sys.stderr)
        return status == 200
    except Exception as e:
        print("   (ntfy impossible : %s)" % e, file=sys.stderr)
        return False

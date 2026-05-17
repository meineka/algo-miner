# Claude Desktop + Filesystem MCP — Setup für den Aziz-Workflow

Diese Anleitung gibt **deinem lokalen Claude Desktop** direkten Zugriff
auf `C:\Users\Szymon\ross-cameron\99_2 Aziz claude chatgpt`.

Hinweis: Das ist eine **andere Claude-Instanz** als die, die diesen Repo
schreibt. Ich (Claude Code im Sandbox) bekomme dadurch keinen Zugriff.
Aber dein Claude Desktop kann ab dann die Files lesen/schreiben.

---

## 1. Claude Desktop installieren

- Download: <https://claude.ai/download> (Windows-Installer)
- Mit deinem Anthropic-Account anmelden (gleicher wie für claude.ai)

## 2. Node + npx prüfen

Der Filesystem-MCP-Server läuft via `npx`. Node muss installiert sein:

```powershell
node --version
```

Falls nicht installiert: <https://nodejs.org/> (LTS) oder via winget:

```powershell
winget install OpenJS.NodeJS.LTS
```

## 3. Claude-Desktop-Config bearbeiten

Datei: `%APPDATA%\Claude\claude_desktop_config.json`
(in PowerShell: `notepad $env:APPDATA\Claude\claude_desktop_config.json`)

Falls die Datei noch nicht existiert, lege sie an mit folgendem Inhalt:

```json
{
  "mcpServers": {
    "filesystem-aziz": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "C:\\Users\\Szymon\\ross-cameron\\99_2 Aziz claude chatgpt"
      ]
    }
  }
}
```

Falls du schon andere `mcpServers` hast, füge nur den Block
`"filesystem-aziz": { ... }` zum bestehenden `mcpServers`-Objekt
hinzu (Komma zwischen den Einträgen nicht vergessen).

## 4. Claude Desktop neu starten

Nicht nur das Fenster schließen — über Tray-Icon → Quit, dann neu starten.

## 5. Verbindung verifizieren

In Claude Desktop neue Konversation starten und tippen:

> Liste mir die Dateien in deinem Filesystem-Zugriff auf.

Claude sollte den Ordner `99_2 Aziz claude chatgpt` und seinen Inhalt
zurückgeben. Falls leer: alles richtig, der Ordner ist noch leer.

## 6. Mit dem Git-Bridge kombinieren

Auf dem gleichen Windows-Rechner zusätzlich die `collab_bridge.ps1`
laufen lassen (siehe `collab/README.md`):

- Sie syncs alle `<TS>_claude_export.zip` von GitHub in den lokalen
  Ordner. Claude Desktop sieht sie sofort.
- Wenn Claude Desktop oder ChatGPT eine `<TS>_chatgpt_answer.md` in den
  Ordner schreibt, pusht die Bridge sie zurück zu GitHub, wo Claude
  Code sie beim nächsten Heartbeat liest.

Resultat: Drei-Wege-Loop **Claude Code (sandbox) ↔ GitHub ↔ Claude
Desktop (local) ↔ ChatGPT**.

## 7. Sicherheitshinweis

Der Filesystem-MCP-Server gibt Claude Desktop **vollen Lese-/
Schreibzugriff** auf den konfigurierten Ordner. Halte den Pfad
möglichst eng (nur den `99_2 Aziz...`-Ordner, nicht ganz `C:\Users`).

## 8. Falls's nicht klappt

- MCP-Logs in Claude Desktop: Settings → Developer → MCP Logs
- Häufigstes Problem: doppelte Backslashes `\\` in JSON-Pfaden vergessen
- Zweithäufigstes: nicht `Quit` sondern nur Fenster geschlossen → Restart hilft nicht
- Wenn Node nicht im PATH: kompletten Pfad zu `npx.cmd` als `command` eintragen

---

## Was du danach kannst

In Claude Desktop:
- *"Lies die neueste \_claude\_export.info.md und fasse die Änderungen
  zusammen."*
- *"Schreib mir eine `\<TS\>_chatgpt_answer.md` mit folgendem Inhalt: ..."*
  → Claude Desktop schreibt direkt in den Ordner, die Bridge committet
  sie auf GitHub, ich (Claude Code) implementiere am nächsten Heartbeat.
- *"Vergleiche die letzten drei Exporte und finde Trends in den
  Findings."*

In **deinem ChatGPT** (separates Tool):
- Du kopierst manuell den Inhalt einer `.info.md` oder ZIP-Auszüge rein
- ChatGPT antwortet, du legst die Antwort als `\<TS\>_chatgpt_answer.md`
  in den Ordner → Bridge → GitHub → Claude Code

Wenn ChatGPT bei dir auch MCP-Filesystem-Zugriff hat (z.B. Custom GPT
mit Code Interpreter und persistentem Filesystem), kannst du ihn auf
denselben Ordner pointen — dann läuft alles vollautomatisch.

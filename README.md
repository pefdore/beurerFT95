# Beurer FT95 → PC

Affiche sur votre PC les températures prises avec le thermomètre **Beurer FT95** (Bluetooth LE),
pour ne plus avoir à les mémoriser : chaque mesure s'affiche en grand, est copiée dans le
presse-papiers (Ctrl+V dans votre logiciel métier) et est historisée.

## Fonctionnalités

- `ft95 watch` : fenêtre toujours au premier plan qui affiche la dernière température en très grand,
  copie automatiquement la valeur dans le presse-papiers, et garde un historique.
- Historique persistant : `~/.ft95/mesures.csv` et `~/.ft95/mesures.jsonl`.
- `ft95 spy` : affiche les trames BLE brutes du FT95 (utile si le format propriétaire diffère du
  standard Health Thermometer).
- `ft95 manual 38.2` : saisie manuelle de secours.
- `ft95 scan` / `ft95 gatt` : découverte des appareils et de leurs caractéristiques GATT.

## Installation (PC Windows / Linux / macOS)

Prérequis : Python 3.9+ et un adaptateur Bluetooth (intégré sur la plupart des PC portables).

```bash
git clone https://github.com/pefdore/beurerFT95.git
cd beurerFT95
python -m venv .venv
# Windows :
.venv\Scripts\activate
# Linux/macOS :
source .venv/bin/activate

pip install -e .
```

## Utilisation

### 1. Jumeler le thermomètre (requis par le FT95)

Le FT95 exige un jumelage (PIN à 6 chiffres affiché sur son écran) :

1. Paramètres Windows → Bluetooth et appareils → Ajouter un appareil → Bluetooth.
2. Sélectionnez **FT95**, saisissez le PIN affiché sur le thermomètre.

### 2. Identifier le thermomètre

Allumez le FT95 (mode Bluetooth actif), puis :

```bash
ft95 scan
```

Repérez la ligne avec `<-- probable FT95` (nom du type `FT95` / `Beurer…`) et notez l'adresse MAC.

### 3. Lancer l'affichage

```bash
ft95 watch
```

La fenêtre s'ouvre, le programme se connecte au FT95. Prenez une température : elle apparaît
immédiatement en grand sur l'écran et est copiée dans le presse-papiers — de retour sur votre
logiciel métier, faites simplement **Ctrl+V**.

Si le nom n'est pas détecté automatiquement :

```bash
ft95 watch --address XX:XX:XX:XX:XX:XX
```

Sans fenêtre (console seule) :

```bash
ft95 watch --no-gui
```

### 4. Historique

```bash
ft95 last            # 10 dernières mesures
ft95 last --count 50
```

Fichiers : `~/.ft95/mesures.csv` (ouvrable dans Excel) et `~/.ft95/mesures.jsonl`.

## Si les mesures ne s'affichent pas (format propriétaire)

Le FT95 utilise normalement le service standard *Health Thermometer* (`0x1809`), que le programme
décode automatiquement. Si Beurer utilise un format propriétaire sur votre modèle, procédez ainsi :

```bash
ft95 gatt XX:XX:XX:XX:XX:XX     # liste des services/caractéristiques
ft95 spy                        # trames brutes reçues à chaque mesure
```

Lancez `ft95 spy`, prenez une mesure, et notez la ligne `[uuid] xx xx xx…` qui apparaît.
Le mode `watch` applique aussi un décodage heuristique (valeur ×100 ou ×10) sur les trames
inconnues. Si rien ne s'affiche, ouvrez une issue avec la sortie de `ft95 gatt` et `ft95 spy`
pour ajouter le décodage exact de votre appareil.

## Démarrage automatique avec Windows (optionnel)

1. `Win+R` → `shell:startup`
2. Créez un raccourci vers : `cmd /k "cd C:\chemin\beurerFT95 && .venv\Scripts\activate && ft95 watch"`

## Désinstallation

```bash
pip uninstall ft95
```

## Avertissement

Outil d'aide à la saisie : la valeur affichée reste celle du thermomètre, à intégrer dans votre
logiciel métier comme toute donnée clinique. Aucun diagnostic n'est réalisé par ce logiciel.

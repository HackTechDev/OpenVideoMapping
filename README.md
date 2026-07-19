# openmapping

Outil de simulation de vidéo-mapping — warping en quadrilatère.

Une source (vidéo, image, webcam, ou motif de test généré) est projetée en
perspective dans un quadrilatère dont les 4 coins sont déplaçables à la
souris. C'est la brique de base de tout logiciel de mapping (MadMapper,
Resolume, HeavyM...) : on calibre la zone de projection pour qu'elle épouse
la surface réelle (mur, maquette...).

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install opencv-python numpy
```

## Utilisation

```bash
venv/bin/python3.12 ./mapping_tool.py                               # motif de test généré
venv/bin/python3.12 ./mapping_tool.py --source video.mp4            # fichier vidéo en boucle
venv/bin/python3.12 ./mapping_tool.py --source image.jpg            # image fixe
venv/bin/python3.12 ./mapping_tool.py --source 0                    # webcam (index 0)
venv/bin/python3.12 ./mapping_tool.py --width 1920 --height 1080    # taille de sortie
venv/bin/python3.12 ./mapping_tool.py --background 0                # webcam en fond d'écran
```

L'option `--background` accepte les mêmes types de valeur que `--source` (chemin
vidéo/image, index webcam). Le fond s'affiche partout, et la source
(`--source`) n'est projetée que dans le quadrilatère.

## Contrôles

| Touche / action | Effet |
| --- | --- |
| Clic gauche + glisser sur un coin | Déplacer ce coin |
| `g` | Affiche/masque la grille de warping (debug visuel) |
| `f` | Bascule plein écran / fenêtré |
| `e` | Bascule le mode édition (poignées + grille) |
| `s` | Sauvegarde le calibrage des coins dans `calibration.json` |
| `l` | Recharge le calibrage depuis `calibration.json` |
| `r` | Réinitialise les coins (quad = plein écran) |
| `q` / `Esc` | Quitter |

Le calibrage sauvegardé (`calibration.json`) contient les coordonnées des 4
coins ainsi que la résolution de sortie utilisée ; il est rechargé et
remis à l'échelle automatiquement si la résolution change.

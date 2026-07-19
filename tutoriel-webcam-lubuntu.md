# Diagnostiquer et utiliser une webcam USB sous Lubuntu

Petit guide pour identifier une webcam USB branchée sur un système Linux (Lubuntu/Ubuntu) et s'assurer qu'elle est bien reconnue et utilisable, notamment quand plusieurs webcams sont présentes (interne + externe).

## 1. Vérifier la détection USB

Après avoir branché la webcam, consulter les logs noyau :

```bash
dmesg | tail -n 20
```

Repérer une ligne du type :

```
[ 1871.857592] usb 2-1.2: USB disconnect, device number 5
[ 1877.793150] usb 3-2: new high-speed USB device number 2 using xhci_hcd
[ 1878.143215] usb 3-2: New USB device found, idVendor=046d, idProduct=0825, bcdDevice= 0.10
[ 1878.143239] usb 3-2: New USB device strings: Mfr=0, Product=0, SerialNumber=2
[ 1878.143247] usb 3-2: SerialNumber: 2A12D910
[ 1878.145787] usb 3-2: Found UVC 1.00 device <unnamed> (046d:0825)
[ 1879.477048] usb 3-2: set resolution quirk: cval->res = 384
```

- `idVendor`/`idProduct` (ex: `046d:0825`) identifient le fabricant et le modèle (ici, `046d` = Logitech).
- **UVC** (USB Video Class) est le protocole standard des webcams sous Linux : si le périphérique est reconnu en UVC, aucun driver propriétaire n'est nécessaire.
- Une ligne `set resolution quirk` est un ajustement interne du driver `uvcvideo` pour certains modèles connus — rien d'anormal.

## 2. Lister les périphériques vidéo

```bash
ls /dev/video*
```

Chaque webcam crée en général **plusieurs nœuds** (`/dev/video0`, `/dev/video1`, etc.) : un pour la capture vidéo, un autre pour les métadonnées UVC. Ce n'est pas forcément plusieurs caméras.

## 3. Installer v4l-utils

L'outil `v4l2-ctl` n'est pas installé par défaut :

```bash
sudo apt update
sudo apt install v4l-utils
```

## 4. Identifier clairement chaque caméra

```bash
v4l2-ctl --list-devices
```

Exemple de sortie avec deux caméras (interne + externe) :

```
HP HD Webcam [Fixed]: HP HD Web (usb-0000:00:1d.0-1.4):
        /dev/video0
        /dev/video1
        /dev/media0
UVC Camera (046d:0825) (usb-0000:26:00.0-2):
        /dev/video2
        /dev/video3
        /dev/media1
```

- Chaque bloc correspond à **une caméra physique**.
- Pour chaque caméra, le premier nœud (`video0`, `video2`) est généralement celui qui gère la **capture vidéo**, le second (`video1`, `video3`) sert aux métadonnées.
- `/dev/mediaX` est le *media controller*, utilisé en interne par V4L2 (pas un flux vidéo direct).

## 5. Vérifier les formats supportés par un nœud

```bash
v4l2-ctl -d /dev/video2 --all
```

Si la sortie liste une section `Format Video Capture` avec des résolutions et formats (MJPEG, YUYV...), c'est le bon nœud à utiliser.

## 6. Tester le flux vidéo

```bash
cheese --device=/dev/video2
```

Ou sélectionner directement la caméra correspondante (ex: "UVC Camera") dans les préférences de l'application de capture (Cheese, OBS, etc.).

## Résumé

| Étape | Commande |
|---|---|
| Vérifier la détection USB | `dmesg \| tail -n 20` |
| Lister les nœuds vidéo | `ls /dev/video*` |
| Installer les outils V4L2 | `sudo apt install v4l-utils` |
| Identifier les caméras | `v4l2-ctl --list-devices` |
| Voir les formats supportés | `v4l2-ctl -d /dev/videoX --all` |
| Tester le flux | `cheese --device=/dev/videoX` |

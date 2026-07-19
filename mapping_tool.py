#!/usr/bin/env python3
"""
Outil de simulation de vidéo-mapping — Warping en quadrilatère
=================================================================

Principe : une source (vidéo, image, webcam, ou motif de test généré)
est projetée en perspective dans un quadrilatère dont les 4 coins sont
déplaçables à la souris. C'est la brique de base de tout logiciel de
mapping (MadMapper, Resolume, HeavyM...) : on calibre la zone de
projection pour qu'elle épouse la surface réelle (mur, maquette...).

Contrôles :
  - Clic gauche + glisser sur un coin (petit cercle) : déplacer ce coin
  - Touche 'g'  : affiche/masque la grille de warping (debug visuel)
  - Touche 'f'  : bascule plein écran / fenêtré
  - Touche 's'  : sauvegarde le calibrage des coins dans calibration.json
  - Touche 'l'  : recharge le calibrage depuis calibration.json
  - Touche 'r'  : réinitialise les coins (quad = plein écran)
  - Touche 'a'  : ajoute un masque (clic droit pour dessiner un polygone
                  de zones à ne PAS projeter — utile pour découper autour
                  d'une fenêtre, une porte, etc.)
  - Touche 'b'  : affiche/masque la webcam en fond d'écran (active la
                  webcam index 0 si --background n'a pas été fourni)
  - Touche 'p'  : affiche/masque un effet de pluie (les gouttes tombent
                  du haut et contournent le quadrilatère de projection)
  - Touche 'q' ou ESC : quitter

Usage :
  python3 mapping_tool.py                       # motif de test généré
  python3 mapping_tool.py --source video.mp4    # fichier vidéo en boucle
  python3 mapping_tool.py --source image.jpg    # image fixe
  python3 mapping_tool.py --source 0            # webcam (index 0)
  python3 mapping_tool.py --width 1920 --height 1080  # taille de sortie
  python3 mapping_tool.py --background 0        # webcam en fond d'écran,
                                                 # la source projetée ne
                                                 # recouvre que le quad
"""

import argparse
import json
import os
import sys
import time

import cv2
import numpy as np

CALIB_FILE = "calibration.json"
HANDLE_RADIUS = 12
HANDLE_COLOR = (0, 255, 255)
HANDLE_COLOR_ACTIVE = (0, 100, 255)
GRID_COLOR = (0, 255, 0)


def make_test_pattern(w, h):
    """Génère un motif de test (grille + couleurs) façon mire de calibration,
    utile quand on n'a pas encore de vidéo à disposition."""
    img = np.zeros((h, w, 3), dtype=np.uint8)

    # Damier de fond
    tile = 60
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            if ((x // tile) + (y // tile)) % 2 == 0:
                img[y:y + tile, x:x + tile] = (40, 40, 40)
            else:
                img[y:y + tile, x:x + tile] = (70, 70, 70)

    # Grille de repères
    step = 100
    for x in range(0, w, step):
        cv2.line(img, (x, 0), (x, h), (0, 120, 0), 1)
    for y in range(0, h, step):
        cv2.line(img, (0, y), (w, y), (0, 120, 0), 1)

    # Cercles concentriques au centre (repère de netteté/déformation)
    cx, cy = w // 2, h // 2
    for r in range(40, min(w, h) // 2, 60):
        cv2.circle(img, (cx, cy), r, (0, 200, 255), 2)

    # Croix de centrage
    cv2.line(img, (cx - 30, cy), (cx + 30, cy), (0, 0, 255), 2)
    cv2.line(img, (cx, cy - 30), (cx, cy + 30), (0, 0, 255), 2)

    # Coins numérotés (utile pour repérer l'orientation une fois déformé)
    corners_txt = [("1", (10, 30)), ("2", (w - 40, 30)),
                   ("3", (w - 40, h - 15)), ("4", (10, h - 15))]
    for txt, pos in corners_txt:
        cv2.putText(img, txt, pos, cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                    (255, 255, 255), 2, cv2.LINE_AA)

    cv2.putText(img, "MAPPING TEST PATTERN", (w // 2 - 220, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    return img


class SourceReader:
    """Abstraction pour lire une image fixe, une vidéo en boucle, ou une webcam.
    Si aucune source n'est fournie, génère un motif de test à la volée."""

    def __init__(self, source, out_w, out_h):
        self.out_w = out_w
        self.out_h = out_h
        self.cap = None
        self.static_image = None
        self.is_pattern = False

        if source is None:
            self.is_pattern = True
            self.static_image = make_test_pattern(out_w, out_h)
            return

        # Webcam si l'argument est un entier
        try:
            idx = int(source)
            self.cap = cv2.VideoCapture(idx)
            if not self.cap.isOpened():
                raise RuntimeError(f"Impossible d'ouvrir la webcam index {idx}")
            return
        except ValueError:
            pass

        if not os.path.exists(source):
            raise FileNotFoundError(f"Source introuvable : {source}")

        ext = os.path.splitext(source)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
            img = cv2.imread(source)
            if img is None:
                raise RuntimeError(f"Impossible de lire l'image : {source}")
            self.static_image = img
        else:
            self.cap = cv2.VideoCapture(source)
            if not self.cap.isOpened():
                raise RuntimeError(f"Impossible d'ouvrir la vidéo : {source}")

    def read(self):
        if self.static_image is not None:
            frame = self.static_image
        else:
            ok, frame = self.cap.read()
            if not ok:
                # Boucle la vidéo
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.cap.read()
                if not ok:
                    frame = make_test_pattern(self.out_w, self.out_h)
        return cv2.resize(frame, (self.out_w, self.out_h))

    def release(self):
        if self.cap is not None:
            self.cap.release()


class QuadWarper:
    """Gère les 4 coins du quadrilatère de destination, leur édition à la
    souris, et le calcul/application de la transformation de perspective."""

    def __init__(self, canvas_w, canvas_h, margin_ratio=0.12):
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        mx = int(canvas_w * margin_ratio)
        my = int(canvas_h * margin_ratio)
        # Ordre : haut-gauche, haut-droit, bas-droit, bas-gauche
        self.corners = np.array([
            [mx, my],
            [canvas_w - mx, my],
            [canvas_w - mx, canvas_h - my],
            [mx, canvas_h - my],
        ], dtype=np.float32)
        self.dragging_idx = None
        self.show_grid = True

    def reset(self, margin_ratio=0.12):
        mx = int(self.canvas_w * margin_ratio)
        my = int(self.canvas_h * margin_ratio)
        self.corners = np.array([
            [mx, my],
            [self.canvas_w - mx, my],
            [self.canvas_w - mx, self.canvas_h - my],
            [mx, self.canvas_h - my],
        ], dtype=np.float32)

    def hit_test(self, x, y):
        for i, (cx, cy) in enumerate(self.corners):
            if (x - cx) ** 2 + (y - cy) ** 2 <= (HANDLE_RADIUS * 2) ** 2:
                return i
        return None

    def on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            idx = self.hit_test(x, y)
            if idx is not None:
                self.dragging_idx = idx
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.dragging_idx is not None:
                self.corners[self.dragging_idx] = [x, y]
        elif event == cv2.EVENT_LBUTTONUP:
            self.dragging_idx = None

    def homography(self, src_w, src_h):
        src_pts = np.array([[0, 0], [src_w, 0], [src_w, src_h], [0, src_h]],
                            dtype=np.float32)
        return cv2.getPerspectiveTransform(src_pts, self.corners)

    def warp(self, frame):
        h, w = frame.shape[:2]
        H = self.homography(w, h)
        return cv2.warpPerspective(frame, H, (self.canvas_w, self.canvas_h))

    def quad_mask(self):
        """Masque binaire (canvas_h, canvas_w) : 255 à l'intérieur du
        quadrilatère actuel, 0 ailleurs. Sert à composer la source projetée
        par-dessus un fond d'écran (ex : webcam)."""
        mask = np.zeros((self.canvas_h, self.canvas_w), dtype=np.uint8)
        cv2.fillConvexPoly(mask, self.corners.astype(np.int32), 255)
        return mask

    def draw_overlay(self, canvas):
        """Dessine les poignées et la grille de calibration par-dessus le
        rendu. À utiliser seulement en mode édition, pas en sortie finale."""
        pts = self.corners.astype(int)
        if self.show_grid:
            cv2.polylines(canvas, [pts], isClosed=True, color=GRID_COLOR,
                           thickness=2)
            # Lignes internes 3x3 pour visualiser la déformation
            top = np.linspace(pts[0], pts[1], 4)
            bot = np.linspace(pts[3], pts[2], 4)
            for i in range(4):
                cv2.line(canvas, tuple(top[i].astype(int)),
                          tuple(bot[i].astype(int)), GRID_COLOR, 1)
            left = np.linspace(pts[0], pts[3], 4)
            right = np.linspace(pts[1], pts[2], 4)
            for i in range(4):
                cv2.line(canvas, tuple(left[i].astype(int)),
                          tuple(right[i].astype(int)), GRID_COLOR, 1)

        for i, (x, y) in enumerate(pts):
            color = HANDLE_COLOR_ACTIVE if i == self.dragging_idx else HANDLE_COLOR
            cv2.circle(canvas, (x, y), HANDLE_RADIUS, color, -1)
            cv2.circle(canvas, (x, y), HANDLE_RADIUS, (0, 0, 0), 2)
            cv2.putText(canvas, str(i + 1), (x - 5, y + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

    def save(self, path=CALIB_FILE):
        data = {"corners": self.corners.tolist(),
                "canvas_w": self.canvas_w, "canvas_h": self.canvas_h}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path

    def load(self, path=CALIB_FILE):
        if not os.path.exists(path):
            return False
        with open(path) as f:
            data = json.load(f)
        loaded = np.array(data["corners"], dtype=np.float32)
        if data.get("canvas_w") != self.canvas_w or data.get("canvas_h") != self.canvas_h:
            # Remise à l'échelle si la résolution de sortie a changé
            sx = self.canvas_w / data["canvas_w"]
            sy = self.canvas_h / data["canvas_h"]
            loaded[:, 0] *= sx
            loaded[:, 1] *= sy
        self.corners = loaded
        return True


class RainEffect:
    """Simule des gouttes de pluie tombant depuis le haut du canvas. Une
    goutte qui atteint la zone du quadrilatère de projection le contourne
    (glisse vers le bord le plus proche) au lieu de tomber dessus."""

    DROP_COLOR = (235, 206, 135)  # bleu clair (BGR)
    AVOID_MARGIN = 40  # px : distance au-delà du bord réel à partir de
                        # laquelle une goutte commence déjà à dévier, pour
                        # avoir le temps de sortir avant d'atteindre le bord

    def __init__(self, canvas_w, canvas_h, num_drops=150):
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self.num_drops = num_drops
        self.x = np.random.uniform(0, canvas_w, num_drops).astype(np.float32)
        self.y = np.random.uniform(-canvas_h, 0, num_drops).astype(np.float32)
        self.speed = np.random.uniform(6, 14, num_drops).astype(np.float32)
        self.length = np.random.uniform(8, 20, num_drops).astype(np.float32)

    def _respawn(self, i):
        self.x[i] = np.random.uniform(0, self.canvas_w)
        self.y[i] = np.random.uniform(-40, 0)
        self.speed[i] = np.random.uniform(6, 14)
        self.length[i] = np.random.uniform(8, 20)

    @staticmethod
    def _expand_polygon(corners, margin):
        """Agrandit le quadrilatère de `margin` pixels vers l'extérieur, en
        éloignant chaque coin du centroïde le long de sa direction."""
        centroid = corners.mean(axis=0)
        directions = corners - centroid
        norms = np.linalg.norm(directions, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return (corners + directions / norms * margin).astype(np.float32)

    @staticmethod
    def _nearest_edge_vectors(point, corners):
        """Tangente et normale extérieure (unitaires) de l'arête du quad la
        plus proche du point. Utilisées pour dévier une goutte en suivant
        l'inclinaison réelle de cette arête, plutôt qu'un simple choix
        gauche/droite indépendant de l'orientation du quadrilatère."""
        p = np.array(point, dtype=np.float32)
        centroid = corners.mean(axis=0)
        n = len(corners)
        best_dist = None
        best_tangent = np.array([1.0, 0.0], dtype=np.float32)
        best_normal = np.array([0.0, -1.0], dtype=np.float32)
        for i in range(n):
            a, b = corners[i], corners[(i + 1) % n]
            edge = b - a
            edge_len = float(np.linalg.norm(edge))
            if edge_len < 1e-6:
                continue
            edge_dir = edge / edge_len
            t = np.clip(np.dot(p - a, edge_dir), 0, edge_len)
            closest = a + edge_dir * t
            dist = float(np.linalg.norm(p - closest))
            if best_dist is None or dist < best_dist:
                best_dist = dist
                normal = np.array([edge_dir[1], -edge_dir[0]], dtype=np.float32)
                if np.dot(normal, centroid - closest) > 0:
                    normal = -normal  # doit pointer vers l'extérieur
                best_tangent = edge_dir
                best_normal = normal
        return best_tangent, best_normal

    def update(self, corners):
        """corners : les 4 coins du quad (QuadWarper.corners) à contourner."""
        zone = self._expand_polygon(corners, self.AVOID_MARGIN)
        min_x, max_x = float(zone[:, 0].min()), float(zone[:, 0].max())
        min_y, max_y = float(zone[:, 1].min()), float(zone[:, 1].max())
        fall = np.array([0.0, 1.0], dtype=np.float32)

        for i in range(self.num_drops):
            x, y = float(self.x[i]), float(self.y[i])
            approaching = False
            if min_x <= x <= max_x and min_y <= y <= max_y:
                approaching = cv2.pointPolygonTest(zone, (x, y), False) >= 0

            if approaching:
                # Contourne l'obstacle en suivant la pente de l'arête la
                # plus proche (tangente), tout en s'écartant légèrement vers
                # l'extérieur (normale) pour ne pas longer indéfiniment le
                # bord. La tangente dépend de l'inclinaison réelle du quad.
                tangent, normal = self._nearest_edge_vectors((x, y), corners)
                along = tangent * float(np.dot(fall, tangent))
                if np.dot(along, fall) < 0:
                    along = -along  # garder une progression vers le bas
                move = along + normal * 0.5
                move_norm = float(np.linalg.norm(move))
                if move_norm > 1e-6:
                    move = move / move_norm
                self.x[i] += move[0] * self.speed[i]
                self.y[i] += move[1] * self.speed[i]
            else:
                self.y[i] += self.speed[i]

            if self.y[i] > self.canvas_h or self.x[i] < -20 or self.x[i] > self.canvas_w + 20:
                self._respawn(i)

    def draw(self, canvas, quad_mask=None):
        """quad_mask : masque binaire (QuadWarper.quad_mask()) de la zone à
        ne jamais recouvrir, en filet de sécurité si une goutte a quand même
        franchi la zone tampon (vitesse élevée, coin déplacé brutalement...)."""
        overlay = np.zeros_like(canvas)
        for i in range(self.num_drops):
            x, y = int(self.x[i]), int(self.y[i])
            y2 = int(y - self.length[i])
            cv2.line(overlay, (x, y2), (x, y), self.DROP_COLOR, 1, cv2.LINE_AA)
        if quad_mask is not None:
            overlay[quad_mask > 0] = 0
        drawn = np.any(overlay != 0, axis=2)
        canvas[drawn] = overlay[drawn]


def main():
    parser = argparse.ArgumentParser(description="Simulateur de vidéo-mapping — warping quad")
    parser.add_argument("--source", default=None,
                         help="Chemin vidéo/image, index webcam (0,1,...), ou vide = motif de test")
    parser.add_argument("--background", default=None,
                         help="Chemin vidéo/image ou index webcam (0,1,...) à afficher en fond "
                              "d'écran ; la source projetée ne recouvre que le quadrilatère")
    parser.add_argument("--width", type=int, default=1280, help="Largeur de sortie")
    parser.add_argument("--height", type=int, default=720, help="Hauteur de sortie")
    args = parser.parse_args()

    try:
        reader = SourceReader(args.source, args.width, args.height)
        bg_reader = None
        if args.background is not None:
            bg_reader = SourceReader(args.background, args.width, args.height)
    except Exception as e:
        print(f"Erreur source : {e}", file=sys.stderr)
        sys.exit(1)

    warper = QuadWarper(args.width, args.height)
    warper.load()  # recharge un calibrage existant si présent

    window = "Video-Mapping Simulator"
    # WINDOW_GUI_NORMAL désactive la barre d'outils/le menu contextuel Qt
    # natifs d'OpenCV (pan/zoom/enregistrer...) : leurs tooltips n'affichent
    # pas de texte sur ce système, et l'outil a ses propres contrôles clavier.
    cv2.namedWindow(window, cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)
    cv2.resizeWindow(window, args.width, args.height)
    cv2.setMouseCallback(window, warper.on_mouse)

    fullscreen = False
    edit_mode = True
    show_background = bg_reader is not None
    show_rain = False
    rain = RainEffect(args.width, args.height)
    last_save_msg_time = 0

    print("Outil lancé. Fenêtre :", window)
    print("Touches : g=grille  f=plein écran  s=sauver  l=charger  r=reset  "
          "e=mode édition on/off  b=fond webcam on/off  p=pluie on/off  q=quitter")

    while True:
        frame = reader.read()
        warped = warper.warp(frame)

        if bg_reader is not None and show_background:
            bg_frame = bg_reader.read()
            mask = warper.quad_mask()
            canvas = np.where(mask[:, :, None] > 0, warped, bg_frame).astype(np.uint8)
        else:
            canvas = warped.copy()
        if edit_mode:
            warper.draw_overlay(canvas)
            if time.time() - last_save_msg_time < 1.5:
                cv2.putText(canvas, "Calibrage sauvegarde -> calibration.json",
                            (20, args.height - 20), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (255, 255, 255), 2, cv2.LINE_AA)

        if show_rain:
            rain.update(warper.corners)
            rain.draw(canvas, warper.quad_mask())

        cv2.imshow(window, canvas)
        key = cv2.waitKey(16) & 0xFF

        if key in (ord('q'), 27):
            break
        elif key == ord('g'):
            warper.show_grid = not warper.show_grid
        elif key == ord('f'):
            fullscreen = not fullscreen
            cv2.setWindowProperty(
                window, cv2.WND_PROP_FULLSCREEN,
                cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL)
        elif key == ord('s'):
            path = warper.save()
            last_save_msg_time = time.time()
            print(f"Calibrage sauvegardé dans {path}")
        elif key == ord('l'):
            if warper.load():
                print("Calibrage rechargé.")
        elif key == ord('r'):
            warper.reset()
        elif key == ord('e'):
            edit_mode = not edit_mode
        elif key == ord('b'):
            if bg_reader is None:
                try:
                    bg_reader = SourceReader(0, args.width, args.height)
                    show_background = True
                    print("Webcam (index 0) activée en fond.")
                except Exception as e:
                    print(f"Impossible d'activer la webcam en fond : {e}", file=sys.stderr)
            else:
                show_background = not show_background
                print("Fond", "activé" if show_background else "désactivé")
        elif key == ord('p'):
            show_rain = not show_rain
            print("Pluie", "activée" if show_rain else "désactivée")

    reader.release()
    if bg_reader is not None:
        bg_reader.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

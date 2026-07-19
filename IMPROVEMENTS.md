# Améliorations possibles

Pistes concrètes identifiées en parcourant `mapping_tool.py`, classées par catégorie.

## Fonctionnalités manquantes ou incomplètes

- **Touche `a` (masquage de zones) documentée mais non implémentée.** La docstring
  (lignes 19-21) décrit une touche `a` pour dessiner un polygone de zone à ne PAS
  projeter (découpe autour d'une fenêtre, une porte...), mais il n'existe aucun
  `elif key == ord('a')` dans `main()`, ni de méthode de masquage dans `QuadWarper`.
  À implémenter, ou retirer la mention de la docstring si la fonctionnalité n'est
  plus prévue.
- **Un seul quadrilatère à la fois.** `QuadWarper` ne gère qu'une zone de
  projection. Un vrai mapping (façade avec plusieurs pans, objet à plusieurs
  faces) nécessite plusieurs quads indépendants, chacun avec sa propre source
  et son propre calibrage.
- **Pas de warping non rectiligne.** Seule une transformation homographique à 4
  points est supportée (`homography()`/`warp()`). Les surfaces courbes ou
  irrégulières demandent un maillage de points de contrôle (mesh warping,
  Bézier) plutôt qu'un simple quad.
- **Pas de nudge clavier pour les coins.** Le déplacement des coins ne se fait
  qu'à la souris (`on_mouse`) ; un calibrage pixel-perfect est difficile sans
  un mode "sélectionner un coin (touches 1-4) puis ajuster aux flèches".
- **Pas d'undo/redo** sur les déplacements de coins — une erreur de glisser
  oblige à tout recommencer ou à recharger le dernier calibrage sauvegardé.
- **Un seul fichier de calibrage.** `CALIB_FILE = "calibration.json"` est
  fixe (ligne 46) ; impossible d'avoir plusieurs préréglages nommés (une
  scène par mur, par exemple) sans écraser le fichier.
- **Webcam de fond figée sur l'index 0.** À la ligne 349, la touche `b` ouvre
  toujours `SourceReader(0, ...)` si aucun `--background` n'a été fourni au
  lancement ; pas moyen de choisir un autre index/périphérique à la volée.
- **Pas de contrôle de blending/opacité** pour superposer proprement plusieurs
  projecteurs (edge blending), fonctionnalité de base des outils de mapping
  professionnels.

## Robustesse

- **Pas de gestion de perte de webcam en cours d'exécution.** Si `cap.read()`
  échoue en boucle (webcam débranchée), `SourceReader.read()` (ligne 135)
  retente une seule fois puis bascule sur le motif de test — sans message
  d'avertissement à l'utilisateur, ni tentative de reconnexion.
- **`SourceReader.is_pattern`** (ligne 104) est positionné mais jamais lu
  ailleurs dans le code — attribut mort, à utiliser ou supprimer.
- **Pas de validation `--width`/`--height`** (valeurs négatives ou nulles
  provoqueraient un crash peu explicite dans `cv2.resize`/`warpPerspective`).

## Performance

- **`quad_mask()` recalculé à chaque frame** (ligne 209, appelé ligne 312)
  même quand les coins n'ont pas bougé. Le masque pourrait être mis en cache
  et invalidé uniquement au déplacement d'un coin ou au `reset()`/`load()`.
- **Cadence fixe** via `cv2.waitKey(16)` (ligne 324) sans mesure réelle du
  FPS ni affichage de celui-ci — utile pour diagnostiquer un ralentissement
  avec une source vidéo haute résolution.

## Outillage / qualité de code

- **Pas de fichier de dépendances** (`requirements.txt` ou `pyproject.toml`) —
  `opencv-python`/`numpy` ne sont documentés que dans le README, sans version
  épinglée.
- **Aucun test automatisé.** La logique pure (homographie, masque, rescale de
  calibrage dans `QuadWarper.load()`) est testable sans dépendre de l'UI
  OpenCV/Qt et gagnerait à avoir des tests unitaires.
- **Pas de type hints** sur les fonctions/méthodes, ce qui limite l'aide
  apportée par un éditeur ou un futur `mypy`.

# =============================================================
#  vision/plant_classifier.py — Classification maladie plante
#
#  MODE SIMULATION : génère des résultats réalistes à partir
#  des labels PlantDoc sans avoir besoin du modèle CNN.
#
#  MODE RÉEL (décommenté) : charge un modèle MobileNetV2
#  entraîné sur PlantDoc et classifie une vraie image.
#
#  PlantDoc contient 27 classes sur 13 espèces de plantes.
# =============================================================

import random
import os
from database.queries import insert_image_result

# ─────────────────────────────────────────────────────────────
#  Labels PlantDoc — 27 classes (nom exact du dataset)
# ─────────────────────────────────────────────────────────────
PLANTDOC_LABELS = [
    "Tomato leaf",
    "Tomato Early blight leaf",
    "Tomato Septoria leaf spot",
    "Tomato leaf late blight",
    "Tomato leaf mosaic virus",
    "Tomato leaf yellow virus",
    "Tomato mold leaf",
    "Tomato two spotted spider mites leaf",
    "Potato leaf",
    "Potato leaf early blight",
    "Potato leaf late blight",
    "Pepper bell leaf",
    "Pepper bell Bacterial spot leaf",
    "Corn leaf blight",
    "Corn Gray leaf spot",
    "Corn rust leaf",
    "Apple leaf",
    "Apple Scab Leaf",
    "Apple rust leaf",
    "Grape leaf",
    "Grape leaf black rot",
    "Strawberry leaf",
    "Peach leaf",
    "Squash Powdery mildew leaf",
    "Blueberry leaf",
    "Raspberry leaf",
    "Soyabean leaf",
]

# Labels considérés "sains" (pas de maladie)
HEALTHY_LABELS = {
    "Tomato leaf", "Potato leaf", "Pepper bell leaf",
    "Apple leaf", "Grape leaf", "Strawberry leaf",
    "Peach leaf", "Blueberry leaf", "Raspberry leaf",
    "Soyabean leaf", "Corn leaf blight",
}


class PlantClassifier:
    """
    Classifie l'état visuel d'une plante.

    En mode simulation, il tire aléatoirement un label PlantDoc
    avec une distribution réaliste (70% sain, 30% maladie).

    Pour passer en mode RÉEL :
      1. pip install tensorflow opencv-python
      2. Décommenter le bloc _load_real_model()
      3. Fournir le chemin vers ton modèle .h5 entraîné
    """

    def __init__(self, model_path: str = None, use_simulation: bool = True):
        self.use_simulation = use_simulation
        self.model = None

        if not use_simulation and model_path:
            self._load_real_model(model_path)

    # ── Mode réel (CNN MobileNetV2) ───────────────────────────
    # Décommenter quand le modèle est entraîné

    # def _load_real_model(self, model_path: str):
    #     import tensorflow as tf
    #     if os.path.exists(model_path):
    #         self.model = tf.keras.models.load_model(model_path)
    #         print(f"[VISION] Modèle chargé : {model_path}")
    #     else:
    #         print(f"[VISION] Modèle introuvable : {model_path}")
    #         self.use_simulation = True

    # def _predict_real(self, image_path: str) -> tuple[str, float]:
    #     import cv2
    #     import numpy as np
    #     img = cv2.imread(image_path)
    #     img = cv2.resize(img, (224, 224))
    #     img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    #     img = np.expand_dims(img / 255.0, axis=0)
    #     preds = self.model.predict(img, verbose=0)[0]
    #     idx = int(np.argmax(preds))
    #     return PLANTDOC_LABELS[idx], float(preds[idx])

    # ── Mode simulation ───────────────────────────────────────

    def _predict_simulated(self) -> tuple[str, float]:
        """Simule une prédiction réaliste (70% sain, 30% maladie)."""
        if random.random() < 0.70:
            # Plante saine
            label = random.choice(list(HEALTHY_LABELS))
            confidence = random.uniform(0.75, 0.98)
        else:
            # Maladie détectée
            diseased = [l for l in PLANTDOC_LABELS if l not in HEALTHY_LABELS]
            label = random.choice(diseased)
            confidence = random.uniform(0.55, 0.92)
        return label, round(confidence, 3)

    # ── Interface publique ────────────────────────────────────

    def classify(self, plant_id: int, image_path: str = None) -> dict:
        """
        Classifie la plante et sauvegarde le résultat en base.
        Retourne: {'label': str, 'confidence': float, 'is_healthy': bool}
        """
        if self.use_simulation or self.model is None:
            label, confidence = self._predict_simulated()
            img_path = image_path or "simulated"
        else:
            if not image_path or not os.path.exists(image_path):
                label, confidence = self._predict_simulated()
                img_path = "simulated"
            else:
                label, confidence = self._predict_real(image_path)
                img_path = image_path

        is_healthy = label in HEALTHY_LABELS

        # Sauvegarde SQL
        insert_image_result(
            plant_id=plant_id,
            image_path=img_path,
            stress_label=label,
            confidence=confidence
        )

        return {
            'label'     : label,
            'confidence': confidence,
            'is_healthy': is_healthy,
            'image_path': img_path,
        }

    def is_stressed(self, vision_result: dict,
                    confidence_threshold: float = 0.65) -> bool:
        """True si maladie détectée avec confiance suffisante."""
        return (
            not vision_result['is_healthy'] and
            vision_result['confidence'] >= confidence_threshold
        )

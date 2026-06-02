# =============================================================
#  vision/plantdoc_loader.py — Chargement des données PlantDoc
#
#  Charge les métadonnées des maladies depuis le dossier
#  PlantDoc téléchargé et les insère dans la base SQLite.
#
#  Structure attendue du dossier PlantDoc :
#    PlantDoc-Dataset/
#      train/
#        Tomato Early blight leaf/   ← nom = label de maladie
#          image1.jpg
#          image2.jpg
#        Tomato leaf/
#          ...
#      test/
#        ...
# =============================================================

import os
from database.queries import insert_disease, get_all_diseases
from vision.plant_classifier import PLANTDOC_LABELS, HEALTHY_LABELS

# Informations sur les maladies connues (enrichies manuellement)
DISEASE_INFO = {
    "Tomato Early blight leaf": {
        "plant": "Tomate",
        "symptoms": "Taches brunes concentriques sur feuilles âgées",
        "treatment": "Fongicide à base de cuivre, retirer feuilles infectées"
    },
    "Tomato Septoria leaf spot": {
        "plant": "Tomate",
        "symptoms": "Petites taches circulaires avec centre gris",
        "treatment": "Fongicide, éviter arrosage par le dessus"
    },
    "Tomato leaf late blight": {
        "plant": "Tomate",
        "symptoms": "Taches aqueuses vert-brun, duvet blanc sous feuille",
        "treatment": "Fongicide préventif, bonne aération"
    },
    "Tomato leaf mosaic virus": {
        "plant": "Tomate",
        "symptoms": "Mosaïque jaune-vert, feuilles déformées",
        "treatment": "Pas de traitement, retirer plantes infectées"
    },
    "Tomato leaf yellow virus": {
        "plant": "Tomate",
        "symptoms": "Jaunissement des feuilles, nanisme",
        "treatment": "Contrôler les pucerons vecteurs"
    },
    "Tomato mold leaf": {
        "plant": "Tomate",
        "symptoms": "Moisissure grise sur feuilles (Botrytis)",
        "treatment": "Réduire humidité, fongicide si nécessaire"
    },
    "Tomato two spotted spider mites leaf": {
        "plant": "Tomate",
        "symptoms": "Pointillés jaunes, toiles fines sous feuilles",
        "treatment": "Acaricide, augmenter humidité ambiante"
    },
    "Potato leaf early blight": {
        "plant": "Pomme de terre",
        "symptoms": "Taches brunes avec anneaux concentriques",
        "treatment": "Fongicide, rotation des cultures"
    },
    "Potato leaf late blight": {
        "plant": "Pomme de terre",
        "symptoms": "Taches huileuses, pourriture rapide",
        "treatment": "Fongicide systémique, variétés résistantes"
    },
    "Pepper bell Bacterial spot leaf": {
        "plant": "Poivron",
        "symptoms": "Taches aqueuses brunes avec halo jaune",
        "treatment": "Cuivre bactéricide, semences saines"
    },
    "Corn leaf blight": {
        "plant": "Maïs",
        "symptoms": "Lésions elliptiques gris-vert à brunes",
        "treatment": "Fongicide foliaire, variétés résistantes"
    },
    "Corn Gray leaf spot": {
        "plant": "Maïs",
        "symptoms": "Lésions rectangulaires grises entre nervures",
        "treatment": "Fongicide, rotation des cultures"
    },
    "Corn rust leaf": {
        "plant": "Maïs",
        "symptoms": "Pustules orangées-brunes sur les deux faces",
        "treatment": "Fongicide triazole"
    },
    "Apple Scab Leaf": {
        "plant": "Pomme",
        "symptoms": "Taches olive à noires, liège sous feuille",
        "treatment": "Fongicide préventif dès débourrement"
    },
    "Apple rust leaf": {
        "plant": "Pomme",
        "symptoms": "Taches orangées dessus, filaments dessous",
        "treatment": "Fongicide, éloigner genévriers (hôte)"
    },
    "Grape leaf black rot": {
        "plant": "Vigne",
        "symptoms": "Taches circulaires brunes avec pycnides noires",
        "treatment": "Fongicide, supprimer fruits momifiés"
    },
    "Squash Powdery mildew leaf": {
        "plant": "Courge",
        "symptoms": "Poudre blanche sur face supérieure des feuilles",
        "treatment": "Bicarbonate de soude, soufre, bonne aération"
    },
}


def load_plantdoc_to_db(plantdoc_path: str):
    """
    Charge les métadonnées PlantDoc dans la base de données.
    À appeler une seule fois au démarrage.

    plantdoc_path : chemin vers le dossier PlantDoc-Dataset/
    """
    existing = get_all_diseases()
    if existing:
        print(f"[PlantDoc] Déjà chargé ({len(existing)} maladies en base)")
        return

    count = 0

    # Chargement depuis les métadonnées connues
    for label, info in DISEASE_INFO.items():
        insert_disease(
            plant_name=info['plant'],
            disease=label,
            symptoms=info['symptoms'],
            treatment=info['treatment']
        )
        count += 1

    # Si le dossier PlantDoc est accessible, on compte les images
    if os.path.isdir(plantdoc_path):
        train_path = os.path.join(plantdoc_path, "train")
        if os.path.isdir(train_path):
            folders = [f for f in os.listdir(train_path)
                       if os.path.isdir(os.path.join(train_path, f))]
            print(f"[PlantDoc] Dossier détecté : {len(folders)} classes trouvées")
            for folder in sorted(folders):
                folder_path = os.path.join(train_path, folder)
                images = [f for f in os.listdir(folder_path)
                          if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                is_healthy = folder in HEALTHY_LABELS
                status = "sain" if is_healthy else "maladie"
                print(f"  [{status}] {folder} — {len(images)} images")
    else:
        print(f"[PlantDoc] Dossier non trouvé : {plantdoc_path}")
        print("  Les métadonnées de maladies ont quand même été chargées.")

    print(f"[PlantDoc] {count} maladies chargées en base.")

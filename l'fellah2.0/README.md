# L'Fellah 2.0 — Système IA Agriculture Intelligente

## Structure du projet

```
fellah2/
│
├── main.py                        ← Point d'entrée, lancer ici
│
├── database/
│   ├── db_manager.py              ← Connexion SQLite + init tables
│   └── queries.py                 ← Toutes les requêtes SQL
│
├── sensors/
│   ├── sensor_simulator.py        ← Simulation des 4 capteurs
│   └── trust_score.py             ← Score de confiance par capteur
│
├── vision/
│   ├── plant_classifier.py        ← Classificateur PlantDoc (sim + réel)
│   └── plantdoc_loader.py         ← Chargement données PlantDoc
│
├── brain/
│   ├── decision_engine.py         ← Moteur de décision IA (règles)
│   ├── digital_twin.py            ← Jumeau numérique (simulation)
│   └── xai_explainer.py           ← Explications lisibles (XAI)
│
├── dashboard/
│   └── reporter.py                ← Rapports terminal + stats SQL
│
├── fellah.db                      ← Base SQLite (créée au 1er lancement)
├── requirements.txt
└── README.md
```

## Lancer le projet

```bash
# Dans PyCharm ou terminal :
python main.py
```

Aucune installation requise — sqlite3 est natif Python.

## Connecter PlantDoc

Dans `main.py`, appelle au démarrage :

```python
from vision.plantdoc_loader import load_plantdoc_to_db
load_plantdoc_to_db("chemin/vers/PlantDoc-Dataset")
```

## Passer au vrai modèle CNN

1. Installe TensorFlow : `pip install tensorflow opencv-python numpy`
2. Entraîne ton modèle sur PlantDoc (27 classes)
3. Dans `vision/plant_classifier.py` :
   - Décommente les méthodes `_load_real_model` et `_predict_real`
   - Lance avec `PlantClassifier(model_path="model.h5", use_simulation=False)`

## Tables SQLite créées

| Table               | Contenu                              |
|---------------------|--------------------------------------|
| plants              | Plantes enregistrées                 |
| sensor_readings     | Lectures capteurs (T, H, pH, Lux)   |
| plant_images        | Résultats vision IA                  |
| trust_scores        | Score de confiance par capteur       |
| decisions           | Décisions prises par le moteur IA    |
| digital_twin_sims   | Simulations avant exécution          |
| xai_logs            | Explications des décisions           |
| plantdoc_diseases   | Maladies connues depuis PlantDoc     |

## Visualiser la base de données

Télécharge **DB Browser for SQLite** (gratuit) :
https://sqlitebrowser.org/
Ouvre `fellah.db` pour voir toutes les tables en temps réel.

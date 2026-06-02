import os
import numpy as np
try:
    import tensorflow as tf
    from tensorflow.keras.models import load_model
    TENSORFLOW_AVAILABLE = True
except ImportError:
    tf = None
    load_model = None
    TENSORFLOW_AVAILABLE = False
import h5py
import json
import base64
import urllib.request
import urllib.error
import mimetypes
from django.conf import settings

# Informations detaillees sur les maladies en Francais
PLANT_DISEASES_INFO = {
    "Apple Scab": {
        "name_fr": "Tavelure du pommier",
        "severity": "warning",
        "advice": "Champignon favorisé par l'humidité. Évitez l'arrosage foliaire. Ramassez et détruisez les feuilles mortes au sol. Appliquez un fongicide naturel à base de cuivre."
    },
    "Apple Black Rot": {
        "name_fr": "Pourriture noire du pommier",
        "severity": "critical",
        "advice": "Infection fongique grave. Retirez immédiatement les fruits momifiés et pourris. Taillez les branches chancreuses et désinfectez vos outils."
    },
    "Apple Cedar Rust": {
        "name_fr": "Rouille du pommier",
        "severity": "warning",
        "advice": "Éliminez les genévriers sauvages à proximité (hôtes de la rouille). Pulvérisez un traitement préventif au soufre en début de saison."
    },
    "Apple Healthy": {
        "name_fr": "Pommier sain",
        "severity": "normal",
        "advice": "Le pommier est en excellente santé. Maintenez l'arrosage habituel au pied en fonction des températures."
    },
    "Blueberry Healthy": {
        "name_fr": "Myrtillier sain",
        "severity": "normal",
        "advice": "Plante saine. Veillez à maintenir un sol acide (pH 4.5-5.5) et paillez avec des écorces de pin pour retenir l'humidité."
    },
    "Cherry Powdery Mildew": {
        "name_fr": "Oïdium du cerisier",
        "severity": "warning",
        "advice": "Feuillage blanc poudreux. Améliorez la circulation de l'air en élaguant. Arrosez uniquement au sol et traitez avec une solution de soufre."
    },
    "Cherry Healthy": {
        "name_fr": "Cerisier sain",
        "severity": "normal",
        "advice": "Cerisier sain. Irrigation modérée, arrosez généreusement uniquement en cas de sécheresse prolongée."
    },
    "Corn Gray Leaf Spot": {
        "name_fr": "Taches grises du maïs",
        "severity": "warning",
        "advice": "Favorisé par l'humidité stagnante. Améliorez le drainage du sol. Évitez l'arrosage en fin de journée pour que le feuillage sèche."
    },
    "Corn Common Rust": {
        "name_fr": "Rouille commune du maïs",
        "severity": "warning",
        "advice": "Présence de pustules orangées. Utilisez des variétés de semences résistantes. Irrigation au goutte-à-goutte recommandée."
    },
    "Corn Northern Leaf Blight": {
        "name_fr": "Helminthosporiose du maïs",
        "severity": "critical",
        "advice": "Infection fongique majeure. Éliminez les débris de culture. Suspendez l'irrigation par aspersion et passez au goutte-à-goutte."
    },
    "Corn Healthy": {
        "name_fr": "Maïs sain",
        "severity": "normal",
        "advice": "Le maïs pousse vigoureusement. Maintenez un sol humide, particulièrement durant la période de floraison."
    },
    "Grape Black Rot": {
        "name_fr": "Pourriture noire de la vigne",
        "severity": "critical",
        "advice": "Retirez et brûlez toutes les grappes et feuilles momifiées. Appliquez un fongicide cuprique protecteur dès le printemps."
    },
    "Grape Esca": {
        "name_fr": "Esca de la vigne",
        "severity": "critical",
        "advice": "Maladie du bois incurable. Isolez les ceps atteints. Désinfectez soigneusement le sécateur après chaque coupe."
    },
    "Grape Leaf Blight": {
        "name_fr": "Brûlure des feuilles de la vigne",
        "severity": "warning",
        "advice": "Retirez le feuillage malade. Favorisez un ensoleillement maximal des grappes par un effeuillage raisonné."
    },
    "Grape Healthy": {
        "name_fr": "Vigne saine",
        "severity": "normal",
        "advice": "La vigne est saine. Évitez les excès d'eau au pied qui favorisent l'asphyxie racinaire."
    },
    "Orange Haunglongbing": {
        "name_fr": "Citrus Greening (Maladie du Dragon Jaune)",
        "severity": "critical",
        "advice": "Bactériose dévastatrice transmise par le psylle. Éliminez l'arbre infecté pour protéger le verger. Traitez contre les insectes vecteurs."
    },
    "Peach Bacterial Spot": {
        "name_fr": "Taches bactériennes du pêcher",
        "severity": "critical",
        "advice": "Pulvérisez un traitement au cuivre à la chute des feuilles. Évitez les engrais trop azotés qui rendent les tissus fragiles."
    },
    "Peach Healthy": {
        "name_fr": "Pêcher sain",
        "severity": "normal",
        "advice": "L'arbre est en bonne santé. Irrigation régulière requise, surtout lors du grossissement des pêches."
    },
    "Pepper Bell Bacterial Spot": {
        "name_fr": "Tache bactérienne du poivron",
        "severity": "warning",
        "advice": "Bactériose favorisée par la chaleur et l'humidité. N'arrosez jamais les feuilles. Traitez avec du savon noir ou du cuivre."
    },
    "Pepper Bell Healthy": {
        "name_fr": "Poivron sain",
        "severity": "normal",
        "advice": "Poivron vigoureux. Arrosage régulier (le sol doit sécher légèrement en surface entre deux apports)."
    },
    "Potato Early Blight": {
        "name_fr": "Alternariose de la pomme de terre",
        "severity": "warning",
        "advice": "Retirez les feuilles du bas en contact avec la terre. Paillez le sol pour éviter les éclaboussures de spores fongiques."
    },
    "Potato Late Blight": {
        "name_fr": "Mildiou de la pomme de terre",
        "severity": "critical",
        "advice": "Hautement destructeur. Coupez et brûlez les fanes malades pour protéger les tubercules. Traitez à la bouillie bordelaise."
    },
    "Potato Healthy": {
        "name_fr": "Pomme de terre saine",
        "severity": "normal",
        "advice": "Plante saine. Buttez les pieds pour protéger les tubercules du soleil et maintenir la fraîcheur."
    },
    "Raspberry Healthy": {
        "name_fr": "Framboisier sain",
        "severity": "normal",
        "advice": "Framboisier sain. Veillez à éliminer les rejets faibles et arrosez au pied sans mouiller les fruits."
    },
    "Soybean Healthy": {
        "name_fr": "Soja sain",
        "severity": "normal",
        "advice": "Culture saine. Irrigation stable requise pendant la phase de remplissage des gousses."
    },
    "Squash Powdery Mildew": {
        "name_fr": "Oïdium des courges",
        "severity": "warning",
        "advice": "Feutrage blanc sur les feuilles. Pulvérisez du bicarbonate de soude dilué ou du lait écrémé. Coupez les feuilles condamnées."
    },
    "Strawberry Leaf Scorch": {
        "name_fr": "Taches pourpres du fraisier",
        "severity": "warning",
        "advice": "Éliminez les vieilles feuilles à l'automne. Évitez les excès d'azote et favorisez un paillage propre sous les fraises."
    },
    "Strawberry Healthy": {
        "name_fr": "Fraisier sain",
        "severity": "normal",
        "advice": "Fraisier vigoureux. Arrosage régulier pour maintenir le sol frais. Pensez à pailler."
    },
    "Tomato Bacterial Spot": {
        "name_fr": "Tache bactérienne de la tomate",
        "severity": "critical",
        "advice": "Maladie bactérienne incurable sur le feuillage atteint. Supprimez les zones touchées, désinfectez le matériel et traitez au cuivre."
    },
    "Tomato Early Blight": {
        "name_fr": "Alternariose de la tomate",
        "severity": "warning",
        "advice": "Taches concentriques sombres. Effeuillez la base de la plante pour l'aérer. Paillez le sol pour limiter la contamination."
    },
    "Tomato Late Blight": {
        "name_fr": "Mildiou de la tomate",
        "severity": "critical",
        "advice": "Urgence absolue ! Maladie foudroyante par temps humide. Supprimez les parties atteintes, traitez à la bouillie bordelaise, abritez si possible."
    },
    "Tomato Leaf Mold": {
        "name_fr": "Moisissure olive de la tomate",
        "severity": "warning",
        "advice": "Humidité trop élevée sous serre. Aérez abondamment les abris et suspendez l'arrosage jusqu'à ce que l'air s'assèche."
    },
    "Tomato Septoria Leaf Spot": {
        "name_fr": "Septoriose de la tomate",
        "severity": "warning",
        "advice": "Petites taches grises à bordure noire. Arrosez uniquement au pied. Supprimez les feuilles les plus basses touchées."
    },
    "Tomato Spider Mites": {
        "name_fr": "Araignées rouges de la tomate",
        "severity": "warning",
        "advice": "Acariens favorisés par la sécheresse. Brumisez de l'eau sur le feuillage pour perturber leur cycle. Traitez au savon noir."
    },
    "Tomato Target Spot": {
        "name_fr": "Tache cible de la tomate",
        "severity": "warning",
        "advice": "Désherbez la zone entourant les tomates. Favorisez un espacement large pour un séchage rapide du feuillage."
    },
    "Tomato Yellow Leaf Curl Virus": {
        "name_fr": "Virus des feuilles en cuillère (TYLCV)",
        "severity": "critical",
        "advice": "Virus incurable transmis par les mouches blanches. Arrachez le plant pour éviter la contagion. Installez des pièges collants jaunes."
    },
    "Tomato Mosaic Virus": {
        "name_fr": "Mosaïque de la tomate",
        "severity": "critical",
        "advice": "Virus très contagieux. Détruisez le plant. Lavez et désinfectez rigoureusement vos mains et tuteurs."
    },
    "Tomato Healthy": {
        "name_fr": "Tomate saine",
        "severity": "normal",
        "advice": "Le plant est vigoureux. Arrosez régulièrement au pied (1,5 L tous les 2-3 jours) sans mouiller les feuilles."
    }
}

def load_keras_model_safely(model_path):
    if not TENSORFLOW_AVAILABLE or load_model is None:
        print(f"[IA-WARN] TensorFlow non installe — modele Keras desactive. pip install tensorflow")
        print(f"[IA-WARN] Chemin ignore: {os.path.abspath(model_path)}")
        return None

    try:
        return load_model(model_path, compile=False)
    except Exception as e:
        print(f"[INFO] Nettoyage du fichier H5...")
        try:
            with h5py.File(model_path, 'r+') as f:
                if 'model_config' in f.attrs:
                    config = json.loads(f.attrs['model_config'])
                    def clean_config(obj):
                        if isinstance(obj, dict):
                            obj.pop('quantization_config', None)
                            for k, v in obj.items(): clean_config(v)
                        elif isinstance(obj, list):
                            for i in obj: clean_config(i)
                    clean_config(config)
                    f.attrs['model_config'] = json.dumps(config).encode('utf-8')
            return load_model(model_path, compile=False)
        except Exception as err:
            print(f"[ERROR] Impossible de nettoyer ou charger le modele Keras: {type(err).__name__}: {err}")
            print(f"[ERROR] Chemin du modele: {os.path.abspath(model_path)}")
            print(f"[ERROR] Fichier existe: {os.path.exists(model_path)}, Taille: {os.path.getsize(model_path) if os.path.exists(model_path) else 'N/A'} octets")
            return None

model = None
labels = []

MODEL_PATH = os.path.join(settings.BASE_DIR, 'core', 'ai_model', 'plantdoc_model.h5')
LABEL_PATH = os.path.join(settings.BASE_DIR, 'core', 'ai_model', 'labels.json')

print(f'[IA-DEBUG] BASE_DIR = {os.path.abspath(settings.BASE_DIR)}')
print(f'[IA-DEBUG] MODEL    = {os.path.abspath(MODEL_PATH)}')
print(f'[IA-DEBUG] exists   = {os.path.exists(os.path.abspath(MODEL_PATH))}')

try:
    if os.path.exists(MODEL_PATH):
        model = load_keras_model_safely(MODEL_PATH)
        if model:
            print("[SUCCESS] IA Chargee")
    if os.path.exists(LABEL_PATH):
        with open(LABEL_PATH, 'r') as f:
            data = json.load(f)
            labels = list(data.values()) if isinstance(data, dict) else data
        print(f"[SUCCESS] {len(labels)} Labels")
except FileNotFoundError as e:
    print(f"[IA-ERROR] FileNotFoundError: {e}")
    print(f"[IA-ERROR] Verifiez le chemin: {os.path.abspath(MODEL_PATH)}")
except ModuleNotFoundError as e:
    print(f"[IA-ERROR] ModuleNotFoundError: {e}")
    print(f"[IA-ERROR] Installez les dependances: pip install tensorflow h5py")
except Exception as e:
    print(f"[IA-ERROR] {type(e).__name__}: {e}")
    print(f"[IA-ERROR] MODEL_PATH = {os.path.abspath(MODEL_PATH)}")
    print(f"[IA-ERROR] TENSORFLOW_AVAILABLE = {TENSORFLOW_AVAILABLE}")


def predict_via_gemini(image_path, api_key, lang='fr'):
    """
    Appelle l'API Gemini REST pour analyser une image de plante.
    Essaie plusieurs modèles dans l'ordre :
      1. gemini-2.0-flash (le plus récent)
      2. gemini-1.5-flash (plus stable, supporte les images)
    En cas d'échec, lève RuntimeError pour basculer vers Keras.
    """
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or mime_type not in ('image/jpeg', 'image/png', 'image/webp', 'image/gif'):
        mime_type = "image/jpeg"

    with open(image_path, "rb") as image_file:
        file_bytes = image_file.read()
        file_size_kb = len(file_bytes) / 1024
        if file_size_kb > 10240:
            raise ValueError(f"Image trop volumineuse ({file_size_kb:.0f} KB). Limite: 10 MB.")
        encoded_image = base64.b64encode(file_bytes).decode('utf-8')

    lang_names = {'fr': 'français', 'ar': 'arabe', 'en': 'anglais'}
    lang_name = lang_names.get(lang, 'français')

    prompt = (
        f"Vous êtes un agronome expert. Analysez cette image de feuille/plante.\n"
        f"Répondez UNIQUEMENT en JSON avec ces 4 clés en {lang_name}:\n"
        f"- disease_name: nom de la maladie ou 'Plante saine'\n"
        f"- confidence: nombre entre 0 et 100\n"
        f"- watering_advice: conseils d'arrosage concis (max 120 caractères)\n"
        f"- severity: 'normal', 'warning' ou 'critical'\n"
        f"Pas de markdown, pas de texte autour du JSON."
    )

    # Modèles à essayer dans l'ordre (certains peuvent ne pas supporter les images)
    MODELS = [
        'gemini-1.5-flash-002',
        'gemini-1.5-pro',
        'gemini-2.0-flash-exp',
        'gemini-1.5-flash',
    ]
    last_error = None

    for model_name in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        print(f"[GEMINI] Tentative avec le modèle {model_name}...")

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": mime_type, "data": encoded_image}}
                ]
            }],
            "generationConfig": {"responseMimeType": "application/json"}
        }

        headers = {"Content-Type": "application/json"}
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                resp_data = json.loads(response.read().decode('utf-8'))

            candidates = resp_data.get('candidates', [])
            if not candidates:
                reason = resp_data.get('promptFeedback', {}).get('blockReason', '')
                error_text = resp_data.get('error', {}).get('message', '')
                msg = error_text or reason or 'unknown'
                print(f"[GEMINI] {model_name} a refusé l'image: {msg}")
                last_error = msg
                continue

            text_response = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '{}')

            try:
                result = json.loads(text_response.strip())
            except json.JSONDecodeError:
                result = {"disease_name": "Erreur de réponse", "confidence": 0, "watering_advice": "", "severity": "warning"}

            disease_name = result.get("disease_name", "Inconnu")
            confidence = float(result.get("confidence", 85.0))
            advice = result.get("watering_advice", "Aucun conseil disponible.")
            severity = result.get("severity", "normal")
            if severity not in ["normal", "warning", "critical"]:
                severity = "warning"

            print(f"[GEMINI] Succès avec {model_name}: {disease_name} ({confidence}%)")
            return disease_name, confidence, advice, severity

        except urllib.error.HTTPError as http_err:
            err_body = http_err.read().decode('utf-8') if http_err.fp else ''
            try:
                err_json = json.loads(err_body)
                msg = err_json.get('error', {}).get('message', str(http_err))
            except:
                msg = str(http_err)
            print(f"[GEMINI] {model_name} HTTP {http_err.code}: {msg[:120]}")

            # HTTP 429 = quota dépassé → abandon immédiat, tous les modèles partagent le quota
            if http_err.code == 429:
                last_error = "QUOTA_DEPASSED"
                break

            # 404 = modèle inexistant → essayer le suivant
            if http_err.code == 404:
                last_error = msg
                continue

            # 400 avec "does not support image" → essayer le suivant
            if 'does not support image input' in msg.lower():
                last_error = msg
                continue

            # Autre erreur → abandon
            last_error = msg
            break

        except urllib.error.URLError as url_err:
            print(f"[GEMINI] {model_name} erreur réseau: {url_err}")
            last_error = str(url_err)
            continue

    raise RuntimeError(f"Gemini indisponible: {last_error or 'Tous les modeles ont echoue'}")

def predict_plant_disease(image_path, lang='fr'):
    """
    Pipeline de diagnostic IA L'Fellah 2.0.
    Stratégie à deux niveaux :
      1. API Gemini (cloud) - diagnostic avancé, toute plante.
      2. Keras local (fallback) - 38 maladies, exécuté si Gemini échoue.

    Retourne un DICT (pas un tuple) pour compatibilité avec ImageUploadView.
    """
    from django.conf import settings
    from .models import SystemNotification

    api_key = getattr(settings, 'GEMINI_API_KEY', None)

    # ─── Étape 1 : Gemini API ───────────────────────────────────────
    if api_key and len(api_key) > 10:
        try:
            print(f"[DIAG] Tentative Gemini (langue: {lang})...")
            disease, confidence, advice, severity = predict_via_gemini(image_path, api_key, lang)
            print(f"[DIAG] Gemini OK: {disease} ({confidence}%)")
            return {'disease_name': disease, 'confidence': round(confidence, 1),
                    'watering_advice': advice, 'severity': severity}
        except Exception as e:
            print(f"[DIAG] Gemini echoue, fallback Keras: {str(e)[:80]}")

    # ─── Étape 2 : Fallback Keras local ────────────────────────────
    print(f"[DIAG] Utilisation Keras local (langue: {lang})...")
    if model is None:
        return {'disease_name': "Modèle IA non chargé", 'confidence': 0.0,
                'watering_advice': "Le modèle Keras n'a pas pu être chargé. Vérifiez le fichier plantdoc_model.h5.",
                'severity': 'warning'}

    try:
        from PIL import Image as PILImage
        import io

        # Ouvrir et vérifier l'image avec PIL
        try:
            pil_img = PILImage.open(image_path)
            pil_img.verify()  # Vérifie que l'image n'est pas corrompue
        except Exception:
            # Réessayer en ouvrant sans verify
            pil_img = PILImage.open(image_path)
        pil_img = PILImage.open(image_path).convert('RGB')

        # Redimensionner pour Keras (224x224)
        pil_img = pil_img.resize((224, 224))
        img_array = tf.keras.preprocessing.image.img_to_array(pil_img)
        img_array = np.expand_dims(img_array, axis=0) / 255.0

        # Prédiction Keras
        preds = model.predict(img_array, verbose=0)
        flat_preds = preds.flatten()
        idx = np.argmax(flat_preds)
        confidence = float(flat_preds[idx]) * 100

        disease_raw = labels[idx] if idx < len(labels) else "Inconnu"

        # Interprétation du résultat
        if confidence < 35:
            disease_fr = "Analyse incertaine"
            severity = "warning"
            advice = "L'IA n'est pas sûre. Assurez-vous que la feuille est bien éclairée et centrée."
        else:
            info = PLANT_DISEASES_INFO.get(disease_raw)
            if info:
                disease_fr = info["name_fr"]
                severity = info["severity"]
                advice = info["advice"]
            else:
                disease_fr = disease_raw
                severity = "warning"
                advice = "Diagnostic brut. Poursuivez la surveillance habituelle."

        # Traduction simple pour EN/AR
        if lang == 'en':
            disease_fr, advice = _translate_fallback_en(disease_fr, advice)
        elif lang == 'ar':
            disease_fr, advice = _translate_fallback_ar(disease_fr, advice)

        print(f"[DIAG] Keras OK: {disease_fr} ({confidence:.1f}%)")
        return {'disease_name': disease_fr, 'confidence': round(confidence, 1),
                'watering_advice': advice, 'severity': severity}

    except Exception as e:
        print(f"[DIAG] Keras echoue: {e}")
        err_msg = str(e)
        if not TENSORFLOW_AVAILABLE:
            err_msg = "Modele IA TensorFlow non installe. Installez tensorflow: pip install tensorflow"
        return {'disease_name': "Erreur d'analyse IA", 'confidence': 0.0,
                'watering_advice': f"Impossible d'analyser cette image. Details: {err_msg[:100]}",
                'severity': 'warning'}


def _translate_fallback_en(disease_fr, advice):
    """Traduction anglaise basique pour le fallback Keras."""
    if "incertaine" in disease_fr.lower():
        return "Uncertain Analysis", "AI not confident. Ensure good lighting and centering."
    if "sain" in disease_fr.lower() or "saine" in disease_fr.lower():
        return "Healthy Plant", "Continue normal watering. Plant appears healthy."
    return f"Detected: {disease_fr}", "Local fallback: monitor watering and isolate if needed."


def _translate_fallback_ar(disease_fr, advice):
    """Traduction arabe basique pour le fallback Keras."""
    if "incertaine" in disease_fr.lower():
        return "تحليل غير مؤكد", "الذكاء الاصطناعي غير متأكد. تأكد من الإضاءة الجيدة."
    if "sain" in disease_fr.lower() or "saine" in disease_fr.lower():
        return "نبات سليم", "استمر في الري الطبيعي. النبات يبدو سليمًا."
    return f"تم الكشف: {disease_fr}", "نسخة احتياطية محلية: راقب الري."

TRANSLATION_CACHE = {}

def translate_text_via_gemini(text, target_lang='fr'):
    if not text:
        return text
    
    target_lang = (target_lang or 'fr').strip().lower()
    if target_lang not in ['en', 'ar', 'fr']:
        target_lang = 'fr'
        
    cache_key = (text, target_lang)
    if cache_key in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[cache_key]
        
    if target_lang == 'fr':
        return text

    from django.conf import settings
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if not api_key:
        return text

    lang_names = {
        'fr': 'français',
        'ar': 'arabe',
        'en': 'anglais'
    }
    lang_name = lang_names.get(target_lang, 'français')

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    prompt = (
        f"Traduisez le texte suivant uniquement en {lang_name}. "
        f"Conservez exactement le format, la mise en page et les tirets (puces) s'il y en a. "
        f"Ne rajoutez aucun commentaire, aucune explication, ni aucune introduction. Renvoyez uniquement la traduction directe :\n\n{text}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            resp_data = json.loads(response.read().decode('utf-8'))
            translation = resp_data['candidates'][0]['content']['parts'][0]['text']
            val = translation.strip()
            TRANSLATION_CACHE[cache_key] = val
            return val
    except Exception as e:
        print(f"[ERROR] Echec de la traduction via Gemini: {e}")
        return text
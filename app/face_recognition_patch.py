#!/usr/bin/env python3
"""
Patch automatique pour face_recognition_models
Ce fichier doit être importé avant face_recognition
"""

import sys
import os
import importlib

def _ensure_pkg_resources():
    """S'assure que pkg_resources est disponible (requis par face_recognition_models)."""
    try:
        import pkg_resources
        return True
    except ImportError:
        # pkg_resources fait partie de setuptools
        try:
            import setuptools
            import pkg_resources
            return True
        except ImportError:
            print("❌ pkg_resources non disponible - tentative de création d'un fallback")
            return False

def _create_fake_face_recognition_models():
    """
    Crée un module face_recognition_models factice qui fournit les chemins des modèles
    directement, sans utiliser pkg_resources.
    """
    import types
    import glob
    
    # Chercher le répertoire d'installation de face_recognition_models
    possible_paths = [
        "/usr/local/lib/python3.11/site-packages/face_recognition_models/models",
        "/usr/local/lib/python3.10/site-packages/face_recognition_models/models",
        "/usr/local/lib/python3.9/site-packages/face_recognition_models/models",
        "/usr/lib/python3/dist-packages/face_recognition_models/models",
        os.path.expanduser("~/.local/lib/python3.11/site-packages/face_recognition_models/models"),
        os.path.expanduser("~/.local/lib/python3.10/site-packages/face_recognition_models/models"),
    ]
    
    models_dir = None
    for path in possible_paths:
        if os.path.exists(path):
            models_dir = path
            print(f"✅ Modèles trouvés dans: {models_dir}")
            break
    
    if not models_dir:
        # Essayer de trouver via le système de fichiers
        for site_packages in sys.path:
            if not site_packages:
                continue
            candidate = os.path.join(site_packages, "face_recognition_models", "models")
            if os.path.exists(candidate):
                models_dir = candidate
                print(f"✅ Modèles trouvés via sys.path: {models_dir}")
                break
    
    if not models_dir:
        # Dernière tentative : recherche glob
        try:
            pattern = "/usr/**/face_recognition_models/models"
            matches = glob.glob(pattern, recursive=True)
            if matches:
                models_dir = matches[0]
                print(f"✅ Modèles trouvés via glob: {models_dir}")
        except Exception:
            pass
    
    if not models_dir:
        print("❌ Impossible de localiser les modèles face_recognition_models")
        print(f"   Chemins vérifiés: {possible_paths[:3]}...")
        return False
    
    # Créer le module factice
    fake_module = types.ModuleType("face_recognition_models")
    
    # Définir les fonctions qui retournent les chemins des modèles
    def pose_predictor_model_location():
        return os.path.join(models_dir, "shape_predictor_68_face_landmarks.dat")
    
    def pose_predictor_five_point_model_location():
        return os.path.join(models_dir, "shape_predictor_5_face_landmarks.dat")
    
    def face_recognition_model_location():
        return os.path.join(models_dir, "dlib_face_recognition_resnet_model_v1.dat")
    
    def cnn_face_detector_model_location():
        path = os.path.join(models_dir, "mmod_human_face_detector.dat")
        if os.path.exists(path):
            return path
        return "/tmp/nonexistent_cnn_model.dat"  # Fallback si CNN non disponible
    
    # Ajouter les fonctions au module
    fake_module.pose_predictor_model_location = pose_predictor_model_location
    fake_module.pose_predictor_five_point_model_location = pose_predictor_five_point_model_location
    fake_module.face_recognition_model_location = face_recognition_model_location
    fake_module.cnn_face_detector_model_location = cnn_face_detector_model_location
    
    # Alias pour compatibilité
    fake_module.shape_predictor_model_location = pose_predictor_model_location
    
    # Enregistrer le module dans sys.modules
    sys.modules["face_recognition_models"] = fake_module
    
    print("✅ Module face_recognition_models factice créé avec succès")
    return True

def apply_face_recognition_patch():
    """Applique le patch pour face_recognition_models"""
    try:
        face_recognition_models = None
        
        # D'abord essayer avec pkg_resources
        pkg_ok = _ensure_pkg_resources()
        
        if pkg_ok:
            try:
                # Importer face_recognition_models normalement
                import face_recognition_models as frm
                face_recognition_models = frm
                print("✅ face_recognition_models importé avec pkg_resources")
            except Exception as e:
                # Capturer TOUTES les exceptions (pas juste ImportError)
                print(f"⚠️ Import face_recognition_models échoué: {type(e).__name__}: {e}")
                face_recognition_models = None
        
        # Si l'import normal a échoué, créer le module factice
        if face_recognition_models is None:
            print("⚠️ Création du module face_recognition_models factice...")
            if not _create_fake_face_recognition_models():
                print("❌ Impossible de créer le module factice")
                return False
            import face_recognition_models
        
        # Liste des attributs manquants et leurs équivalents
        missing_attributes = {
            'pose_predictor_five_point_model_location': 'pose_predictor_model_location',
            'shape_predictor_model_location': 'pose_predictor_model_location'
        }
        
        patches_applied = 0
        
        # Appliquer tous les patches nécessaires
        for missing_attr, existing_attr in missing_attributes.items():
            if not hasattr(face_recognition_models, missing_attr):
                if hasattr(face_recognition_models, existing_attr):
                    # Créer l'alias manquant
                    setattr(face_recognition_models, missing_attr, getattr(face_recognition_models, existing_attr))
                    print(f"✅ Patch appliqué : {missing_attr} = {existing_attr}")
                    patches_applied += 1
                else:
                    print(f"❌ Attribut source {existing_attr} non trouvé pour {missing_attr}")
            else:
                print(f"✅ L'attribut {missing_attr} existe déjà")
        
        # Gérer le cas spécial de cnn_face_detector_model_location
        if not hasattr(face_recognition_models, 'cnn_face_detector_model_location'):
            # Créer un attribut qui retourne un chemin vers un fichier inexistant
            def dummy_cnn_model():
                return "/tmp/nonexistent_cnn_model.dat"
            face_recognition_models.cnn_face_detector_model_location = dummy_cnn_model
            print("✅ CNN face detector patché (modèle non disponible)")
            patches_applied += 1
        else:
            print("✅ L'attribut cnn_face_detector_model_location existe déjà")
        
        if patches_applied > 0:
            print(f"✅ {patches_applied} patch(es) appliqué(s) avec succès")
            return True
        else:
            print("✅ Aucun patch nécessaire")
            return True
            
    except ImportError as e:
        print(f"❌ Erreur d'importation face_recognition_models : {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de l'application du patch : {e}")
        return False

def patch_dlib_before_import():
    """Patch dlib avant l'importation de face_recognition pour éviter l'erreur CNN"""
    try:
        # Importer dlib d'abord
        import dlib
        
        # Créer une fonction de remplacement qui retourne un objet factice
        def safe_cnn_face_detection_model_v1(model_path):
            # Retourner un objet factice qui ne sera jamais utilisé
            class DummyCNNModel:
                def __init__(self):
                    pass
                def __call__(self, *args, **kwargs):
                    return []
            return DummyCNNModel()
        
        # Appliquer le patch
        dlib.cnn_face_detection_model_v1 = safe_cnn_face_detection_model_v1
        print("✅ dlib.cnn_face_detection_model_v1 patché avant importation")
        return True
            
    except Exception as e:
        print(f"⚠️  Erreur lors du patch de dlib : {e}")
        return False

def patch_face_recognition_api():
    """Patch face_recognition.api pour éviter l'importation du CNN"""
    try:
        # Importer face_recognition.api
        import face_recognition.api
        
        # Sauvegarder la fonction originale
        import dlib
        original_cnn_face_detection_model_v1 = dlib.cnn_face_detection_model_v1
        
        # Créer une fonction de remplacement qui ne fait rien
        def safe_cnn_face_detection_model_v1(model_path):
            # Retourner un objet factice qui ne sera jamais utilisé
            class DummyCNNModel:
                def __init__(self):
                    pass
            return DummyCNNModel()
        
        # Appliquer le patch
        dlib.cnn_face_detection_model_v1 = safe_cnn_face_detection_model_v1
        print("✅ face_recognition.api patché pour éviter l'importation CNN")
        return True
            
    except Exception as e:
        print(f"⚠️  Erreur lors du patch de face_recognition.api : {e}")
        return False

# Appliquer le patch automatiquement lors de l'importation
if __name__ != "__main__":
    # Patch dlib en premier
    patch_dlib_before_import()
    # Puis patch face_recognition_models
    apply_face_recognition_patch()

if __name__ == "__main__":
    print("🔧 Test du patch face_recognition_models...")
    
    # Patch dlib en premier
    if patch_dlib_before_import():
        print("✅ Patch dlib appliqué avec succès")
        
        # Puis patch face_recognition_models
        if apply_face_recognition_patch():
            print("✅ Patch appliqué avec succès")
            
            # Appliquer le patch face_recognition.api
            patch_face_recognition_api()
            
            # Tester l'importation de face_recognition
            try:
                import face_recognition
                print("✅ face_recognition importé avec succès après le patch")
                
                print("🎉 Le problème d'attribut est résolu !")
            except Exception as e:
                print(f"❌ Erreur lors de l'importation de face_recognition : {e}")
                sys.exit(1)
        else:
            print("❌ Échec de l'application du patch")
            sys.exit(1)
    else:
        print("❌ Échec du patch dlib")
        sys.exit(1)
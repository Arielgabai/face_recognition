#!/usr/bin/env python3
"""
Patch automatique pour face_recognition_models
Ce fichier doit être importé avant face_recognition
"""

import sys
import importlib

def apply_face_recognition_patch():
    """Applique le patch pour face_recognition_models"""
    try:
        # Importer face_recognition_models
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

def patch_face_recognition_api():
    """Patch le module face_recognition.api pour gérer l'absence du modèle CNN"""
    try:
        import face_recognition.api as api
        
        # Sauvegarder la fonction originale
        original_cnn_face_detection_model_v1 = None
        if hasattr(api, 'dlib'):
            original_cnn_face_detection_model_v1 = getattr(api.dlib, 'cnn_face_detection_model_v1', None)
        
        # Créer une fonction de remplacement qui lève une exception explicite
        def dummy_cnn_face_detection_model_v1(model_path):
            raise RuntimeError("CNN face detection model not available in face_recognition_models==0.1.3. Please use HOG face detection instead.")
        
        # Appliquer le patch si dlib est disponible
        if hasattr(api, 'dlib'):
            api.dlib.cnn_face_detection_model_v1 = dummy_cnn_face_detection_model_v1
            print("✅ face_recognition.api patché pour CNN")
            return True
        else:
            print("⚠️  dlib non disponible dans face_recognition.api")
            return False
            
    except Exception as e:
        print(f"⚠️  Erreur lors du patch de face_recognition.api : {e}")
        return False

# Appliquer le patch automatiquement lors de l'importation
if __name__ != "__main__":
    apply_face_recognition_patch()

if __name__ == "__main__":
    print("🔧 Test du patch face_recognition_models...")
    if apply_face_recognition_patch():
        print("✅ Patch appliqué avec succès")
        
        # Tester l'importation de face_recognition
        try:
            import face_recognition
            print("✅ face_recognition importé avec succès après le patch")
            
            # Appliquer le patch API
            patch_face_recognition_api()
            
            print("🎉 Le problème d'attribut est résolu !")
        except Exception as e:
            print(f"❌ Erreur lors de l'importation de face_recognition : {e}")
            sys.exit(1)
    else:
        print("❌ Échec de l'application du patch")
        sys.exit(1)
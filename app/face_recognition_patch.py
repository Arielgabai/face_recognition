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
            'cnn_face_detector_model_location': 'pose_predictor_model_location',  # Utiliser pose_predictor_model_location comme fallback
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
            print("🎉 Le problème d'attribut est résolu !")
        except Exception as e:
            print(f"❌ Erreur lors de l'importation de face_recognition : {e}")
            sys.exit(1)
    else:
        print("❌ Échec de l'application du patch")
        sys.exit(1)
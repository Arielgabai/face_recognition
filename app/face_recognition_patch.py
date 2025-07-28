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
        
        # Vérifier si l'attribut problématique existe
        if not hasattr(face_recognition_models, 'pose_predictor_five_point_model_location'):
            if hasattr(face_recognition_models, 'pose_predictor_model_location'):
                # Créer l'alias manquant
                face_recognition_models.pose_predictor_five_point_model_location = face_recognition_models.pose_predictor_model_location
                print("✅ Patch face_recognition_models appliqué : pose_predictor_five_point_model_location créé")
                return True
            else:
                print("❌ Aucun attribut de modèle trouvé dans face_recognition_models")
                return False
        else:
            print("✅ L'attribut pose_predictor_five_point_model_location existe déjà")
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
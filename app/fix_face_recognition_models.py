#!/usr/bin/env python3
"""
Script pour corriger le problème d'attribut dans face_recognition_models
"""

import os
import sys

def fix_face_recognition_models():
    """Corrige le problème d'attribut dans face_recognition_models"""
    try:
        import face_recognition_models
        
        # Vérifier si l'attribut problématique existe
        if hasattr(face_recognition_models, 'pose_predictor_five_point_model_location'):
            print("✅ L'attribut pose_predictor_five_point_model_location existe déjà")
            return True
        
        # Si l'attribut n'existe pas, créer un alias
        if hasattr(face_recognition_models, 'pose_predictor_model_location'):
            # Créer un alias pour la compatibilité
            face_recognition_models.pose_predictor_five_point_model_location = face_recognition_models.pose_predictor_model_location
            print("✅ Alias créé : pose_predictor_five_point_model_location = pose_predictor_model_location")
            return True
        else:
            print("❌ Aucun attribut de modèle trouvé dans face_recognition_models")
            return False
            
    except ImportError as e:
        print(f"❌ Erreur d'importation : {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue : {e}")
        return False

def test_face_recognition():
    """Teste l'importation de face_recognition après le patch"""
    try:
        # Appliquer le patch
        fix_face_recognition_models()
        
        # Tester l'importation de face_recognition
        import face_recognition
        print("✅ face_recognition importé avec succès après le patch")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test de face_recognition : {e}")
        return False

if __name__ == "__main__":
    print("🔧 Application du patch face_recognition_models...")
    
    if fix_face_recognition_models():
        print("✅ Patch appliqué avec succès")
        
        if test_face_recognition():
            print("✅ Test de face_recognition réussi")
            print("🎉 Le problème d'attribut est résolu !")
        else:
            print("❌ Test de face_recognition échoué")
            sys.exit(1)
    else:
        print("❌ Échec de l'application du patch")
        sys.exit(1) 
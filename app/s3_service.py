"""
Service S3 pour le stockage des photos.

Ce module gère l'upload et le téléchargement des photos vers/depuis S3.
Utilisé par l'endpoint d'upload et le worker SQS.
"""

import json
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from settings import settings


class S3Service:
    """Service pour les opérations S3."""
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client("s3", region_name=settings.AWS_REGION)
        return self._client
    
    def generate_s3_key(self, event_id: int, photo_id: int, extension: str = "jpg") -> str:
        """
        Génère une clé S3 pour une photo.
        
        Format: raw/event_{event_id}/{photo_id}.{extension}
        """
        prefix = settings.PHOTO_S3_RAW_PREFIX.rstrip("/")
        return f"{prefix}/event_{event_id}/{photo_id}.{extension}"
    
    def upload_photo(
        self, 
        image_bytes: bytes, 
        event_id: int, 
        photo_id: int,
        content_type: str = "image/jpeg",
        extension: str = "jpg"
    ) -> str:
        """
        Upload une photo vers S3.
        
        Args:
            image_bytes: Bytes de l'image
            event_id: ID de l'événement
            photo_id: ID de la photo
            content_type: Type MIME de l'image
            extension: Extension du fichier
        
        Returns:
            str: Clé S3 de l'objet uploadé
        
        Raises:
            ClientError: En cas d'erreur S3
        """
        s3_key = self.generate_s3_key(event_id, photo_id, extension)
        
        self.client.put_object(
            Bucket=settings.PHOTO_BUCKET_NAME,
            Key=s3_key,
            Body=image_bytes,
            ContentType=content_type,
        )
        
        print(f"[S3Service] Uploaded {len(image_bytes)} bytes to s3://{settings.PHOTO_BUCKET_NAME}/{s3_key}")
        return s3_key
    
    def download_photo(self, s3_key: str) -> Optional[bytes]:
        """
        Télécharge une photo depuis S3.
        
        Args:
            s3_key: Clé S3 de l'objet
        
        Returns:
            bytes: Contenu du fichier, ou None si non trouvé
        """
        try:
            response = self.client.get_object(
                Bucket=settings.PHOTO_BUCKET_NAME,
                Key=s3_key
            )
            return response["Body"].read()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                print(f"[S3Service] Object not found: {s3_key}")
                return None
            raise
    
    def delete_photo(self, s3_key: str) -> bool:
        """
        Supprime une photo de S3.
        
        Args:
            s3_key: Clé S3 de l'objet
        
        Returns:
            bool: True si supprimé avec succès
        """
        try:
            self.client.delete_object(
                Bucket=settings.PHOTO_BUCKET_NAME,
                Key=s3_key
            )
            print(f"[S3Service] Deleted s3://{settings.PHOTO_BUCKET_NAME}/{s3_key}")
            return True
        except ClientError as e:
            print(f"[S3Service] Failed to delete {s3_key}: {e}")
            return False
    
    def delete_photos_batch(self, s3_keys: list) -> dict:
        """
        Supprime plusieurs photos de S3 en batch (max 1000 par appel S3).
        
        Args:
            s3_keys: Liste des clés S3 à supprimer
        
        Returns:
            dict: {
                "deleted": [liste des clés supprimées],
                "errors": [{"key": ..., "error": ...}]
            }
        """
        if not s3_keys:
            return {"deleted": [], "errors": []}
        
        # S3 delete_objects accepte max 1000 objets par appel
        all_deleted = []
        all_errors = []
        
        # Traiter par lots de 1000
        for i in range(0, len(s3_keys), 1000):
            batch = s3_keys[i:i+1000]
            objects_to_delete = [{"Key": key} for key in batch if key]
            
            if not objects_to_delete:
                continue
            
            try:
                response = self.client.delete_objects(
                    Bucket=settings.PHOTO_BUCKET_NAME,
                    Delete={"Objects": objects_to_delete, "Quiet": False}
                )
                
                # Récupérer les suppressions réussies
                deleted = response.get("Deleted", [])
                for d in deleted:
                    all_deleted.append(d.get("Key"))
                
                # Récupérer les erreurs
                errors = response.get("Errors", [])
                for e in errors:
                    all_errors.append({
                        "key": e.get("Key"),
                        "error": f"{e.get('Code')}: {e.get('Message')}"
                    })
                
                print(f"[S3Service] Batch delete: {len(deleted)} deleted, {len(errors)} errors")
                
            except ClientError as e:
                print(f"[S3Service] Batch delete failed: {e}")
                # Marquer tout le batch en erreur
                for key in batch:
                    all_errors.append({"key": key, "error": str(e)})
        
        return {"deleted": all_deleted, "errors": all_errors}


class SQSService:
    """Service pour les opérations SQS."""
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client("sqs", region_name=settings.AWS_REGION)
        return self._client
    
    def send_photo_job(self, photo_id: int, event_id: int, s3_key: str) -> str:
        """
        Envoie un message dans la file SQS pour traiter une photo.
        
        Args:
            photo_id: ID de la photo
            event_id: ID de l'événement
            s3_key: Clé S3 de l'image
        
        Returns:
            str: MessageId du message envoyé
        
        Raises:
            ClientError: En cas d'erreur SQS
        """
        message_body = json.dumps({
            "job_type": "process_photo",
            "photo_id": photo_id,
            "event_id": event_id,
            "s3_key": s3_key,
        })
        
        response = self.client.send_message(
            QueueUrl=settings.PHOTO_SQS_QUEUE_URL,
            MessageBody=message_body,
        )
        
        message_id = response.get("MessageId", "unknown")
        print(f"[SQSService] Sent message {message_id} for photo_id={photo_id}")
        return message_id
    
    def send_delete_job(self, job_id: str, photographer_id: int) -> str:
        """
        Envoie un message dans la file SQS pour traiter un job de suppression.
        
        Args:
            job_id: UUID du job de suppression
            photographer_id: ID du photographe qui a demandé la suppression
        
        Returns:
            str: MessageId du message envoyé
        
        Raises:
            ClientError: En cas d'erreur SQS
        """
        message_body = json.dumps({
            "job_type": "delete_photos",
            "job_id": job_id,
            "photographer_id": photographer_id,
        })
        
        # Utiliser la queue de suppression (ou la queue par défaut)
        queue_url = settings.delete_sqs_queue_url
        
        response = self.client.send_message(
            QueueUrl=queue_url,
            MessageBody=message_body,
        )
        
        message_id = response.get("MessageId", "unknown")
        print(f"[SQSService] Sent delete job message {message_id} for job_id={job_id}")
        return message_id


# Instances singleton
_s3_service: Optional[S3Service] = None
_sqs_service: Optional[SQSService] = None


def get_s3_service() -> S3Service:
    """Retourne l'instance singleton du service S3."""
    global _s3_service
    if _s3_service is None:
        _s3_service = S3Service()
    return _s3_service


def get_sqs_service() -> SQSService:
    """Retourne l'instance singleton du service SQS."""
    global _sqs_service
    if _sqs_service is None:
        _sqs_service = SQSService()
    return _sqs_service

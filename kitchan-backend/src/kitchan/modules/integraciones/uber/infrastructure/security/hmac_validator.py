import hmac
import hashlib

def verify_uber_signature(client_secret: str, raw_body: bytes, signature: str) -> bool:
    """
    Verifica la firma HMAC-SHA256 de Uber.
    """
    if not signature or not client_secret:
        return False
        
    # La clave secreta de Uber debe convertirse a bytes
    secret_bytes = client_secret.encode('utf-8')
    
    # Generamos la firma esperada usando el algoritmo HMAC-SHA256
    expected_signature = hmac.new(
        key=secret_bytes,
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # IMPORTANTE: Usamos compare_digest en lugar de "==" para prevenir "Timing Attacks"
    # (Ataques de tiempo donde un hacker adivina la clave midiendo milisegundos de respuesta)
    return hmac.compare_digest(expected_signature, signature)
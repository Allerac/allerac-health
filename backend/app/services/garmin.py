"""
Servico de integracao com Garmin Connect.

Fluxo MFA correto: a thread de login fica bloqueada esperando o codigo MFA
via Queue. A sessao é mantida em memória enquanto aguarda o usuario.
"""

import json
import logging
import asyncio
import threading
import queue
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Sessoes MFA pendentes: session_id -> { mfa_queue, result_queue, created_at }
_pending_sessions: Dict[str, Dict] = {}
_sessions_lock = threading.Lock()


def _cleanup_expired_sessions():
    """Remove sessoes MFA expiradas (> 10 minutos)."""
    cutoff = datetime.utcnow() - timedelta(minutes=10)
    with _sessions_lock:
        expired = [
            sid
            for sid, s in _pending_sessions.items()
            if s["created_at"] < cutoff
        ]
        for sid in expired:
            logger.info(f"Removing expired MFA session {sid}")
            del _pending_sessions[sid]


class GarminService:

    def _run_login(
        self,
        email: str,
        password: str,
        session_id: str,
        mfa_queue: "queue.Queue[str]",
        result_queue: "queue.Queue[Dict]",
        mfa_needed_event: threading.Event,
    ):
        """
        Roda em thread separada. Faz login no Garmin.
        Se MFA for necessario, sinaliza o evento e bloqueia na fila esperando o codigo.
        """
        from garminconnect import Garmin

        def prompt_mfa() -> str:
            logger.info(f"MFA required for session {session_id}")
            mfa_needed_event.set()
            try:
                code = mfa_queue.get(timeout=310)  # 5 min + margem
                logger.info(f"MFA code received for session {session_id}")
                return code
            except queue.Empty:
                raise Exception("MFA timeout: user did not provide code in time")

        try:
            garmin = Garmin(email=email, password=password)

            # Simula browser para evitar bloqueio de bot pelo SSO do Garmin
            garmin.garth.sess.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                "origin": "https://sso.garmin.com",
                "referer": "https://sso.garmin.com/",
            })

            garmin.garth.login(email, password, prompt_mfa=prompt_mfa)

            # Serializa a sessao autenticada
            session_dump = garmin.garth.dumps()
            logger.info(f"Garmin login successful for {email}")
            result_queue.put({"status": "success", "session_dump": session_dump})

        except Exception as e:
            logger.error(f"Garmin login failed for {email}: {e}", exc_info=True)
            result_queue.put({"status": "error", "error": str(e)})
        finally:
            with _sessions_lock:
                _pending_sessions.pop(session_id, None)

    async def authenticate(self, email: str, password: str) -> Dict[str, Any]:
        """
        Inicia autenticacao Garmin.
        Retorna 'success' com session_dump, ou 'mfa_required' com session_id.
        """
        _cleanup_expired_sessions()

        session_id = str(uuid.uuid4())
        mfa_queue: queue.Queue = queue.Queue()
        result_queue: queue.Queue = queue.Queue()
        mfa_needed_event = threading.Event()

        with _sessions_lock:
            _pending_sessions[session_id] = {
                "mfa_queue": mfa_queue,
                "result_queue": result_queue,
                "created_at": datetime.utcnow(),
            }

        thread = threading.Thread(
            target=self._run_login,
            args=(email, password, session_id, mfa_queue, result_queue, mfa_needed_event),
            daemon=True,
        )
        thread.start()

        # Aguarda ate 60s por MFA ou conclusao do login
        loop = asyncio.get_event_loop()
        deadline = loop.time() + 60.0

        while loop.time() < deadline:
            await asyncio.sleep(0.3)

            if mfa_needed_event.is_set():
                return {
                    "status": "mfa_required",
                    "session_data": json.dumps({"session_id": session_id}),
                    "message": "Codigo MFA necessario. Verifique seu email ou telefone.",
                }

            try:
                result = result_queue.get_nowait()
                if result["status"] == "success":
                    return result
                else:
                    raise Exception(result["error"])
            except queue.Empty:
                pass

        with _sessions_lock:
            _pending_sessions.pop(session_id, None)
        raise Exception("Login timeout: Garmin nao respondeu em 60s")

    async def complete_mfa(self, session_data: str, mfa_code: str) -> Dict[str, Any]:
        """
        Completa autenticacao enviando o codigo MFA para a thread bloqueada.
        """
        data = json.loads(session_data)
        session_id = data.get("session_id")

        with _sessions_lock:
            session = _pending_sessions.get(session_id)

        if not session:
            raise Exception(
                "Sessao MFA nao encontrada ou expirada. Tente conectar novamente."
            )

        # Envia o codigo para a thread que esta aguardando
        session["mfa_queue"].put(mfa_code)

        # Aguarda a thread concluir o login
        result_queue = session["result_queue"]
        loop = asyncio.get_event_loop()
        deadline = loop.time() + 60.0

        while loop.time() < deadline:
            await asyncio.sleep(0.3)
            try:
                result = result_queue.get_nowait()
                if result["status"] == "success":
                    return result
                else:
                    raise Exception(result["error"])
            except queue.Empty:
                pass

        raise Exception("MFA timeout: autenticacao nao concluiu em 60s")

    async def validate_tokens(self, session_dump: str) -> bool:
        """Verifica se os tokens ainda sao validos."""
        try:
            import garth
            client = garth.Client()
            client.loads(session_dump)
            return True
        except Exception as e:
            logger.warning(f"Tokens invalidos: {e}")
            return False

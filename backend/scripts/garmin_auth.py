#!/usr/bin/env python3
"""
Script de autenticacao interativa com o Garmin Connect.

Faz login no terminal (aceita MFA via prompt) e salva os tokens
no banco de dados para o usuario especificado.

Uso:
    docker exec -it allerac-health-backend python scripts/garmin_auth.py
"""

import sys
import os
import getpass
import asyncio

# Adiciona o diretorio /app ao path para importar os modulos do backend
sys.path.insert(0, "/app")

# Carrega variaveis de ambiente
from dotenv import load_dotenv
load_dotenv()


def do_login(email: str, password: str) -> str:
    """Faz login interativo no Garmin e retorna o session dump."""
    from garminconnect import Garmin

    print(f"\nConectando ao Garmin para {email}...")

    garmin = Garmin(email=email, password=password)

    def prompt_mfa() -> str:
        print("\n" + "=" * 50)
        print("  CODIGO MFA NECESSARIO")
        print("  Verifique seu email ou SMS do Garmin.")
        print("=" * 50)
        while True:
            code = input("  Digite o codigo MFA: ").strip()
            if code:
                return code
            print("  Codigo nao pode ser vazio. Tente novamente.")

    garmin.garth.login(email, password, prompt_mfa=prompt_mfa)

    session_dump = garmin.garth.dumps()
    print("\nLogin realizado com sucesso!")
    return session_dump


async def save_tokens(user_email: str, garmin_email: str, session_dump: str):
    """Salva os tokens no banco de dados para o usuario."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select, text
    from app.models.user import User
    from app.models.garmin import GarminCredentials
    from app.core.security import encrypt_data
    from app.config import get_settings
    settings = get_settings()

    db_url = (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )

    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Busca o usuario pelo email
        result = await db.execute(select(User).where(User.email == user_email))
        user = result.scalar_one_or_none()

        if not user:
            print(f"\nERRO: Usuario '{user_email}' nao encontrado no banco.")
            print("Verifique se voce se cadastrou no sistema primeiro.")
            return False

        # Atualiza ou cria as credenciais Garmin
        creds_result = await db.execute(
            select(GarminCredentials).where(GarminCredentials.user_id == user.id)
        )
        creds = creds_result.scalar_one_or_none()

        encrypted_dump = encrypt_data(session_dump)
        encrypted_email = encrypt_data(garmin_email)

        if creds:
            creds.email_encrypted = encrypted_email
            creds.oauth1_token_encrypted = encrypted_dump
            creds.oauth2_token_encrypted = encrypt_data("{}")
            creds.is_connected = True
            creds.mfa_pending = False
            creds.last_error = None
        else:
            creds = GarminCredentials(
                user_id=user.id,
                email_encrypted=encrypted_email,
                oauth1_token_encrypted=encrypted_dump,
                oauth2_token_encrypted=encrypt_data("{}"),
                is_connected=True,
                mfa_pending=False,
            )
            db.add(creds)

        await db.commit()
        print(f"\nTokens salvos com sucesso para o usuario '{user_email}'!")
        return True

    await engine.dispose()


def main():
    print("=" * 50)
    print("  Autenticacao Garmin Connect - Allerac Health")
    print("=" * 50)

    # Email da conta no sistema (allerac-health)
    user_email = input("\nSeu email no Allerac Health (usado no cadastro): ").strip()
    if not user_email:
        print("Email nao pode ser vazio.")
        sys.exit(1)

    # Credenciais Garmin
    garmin_email = input("Seu email do Garmin Connect: ").strip()
    if not garmin_email:
        print("Email Garmin nao pode ser vazio.")
        sys.exit(1)

    garmin_password = getpass.getpass("Senha do Garmin Connect: ")
    if not garmin_password:
        print("Senha nao pode ser vazia.")
        sys.exit(1)

    # Faz o login (pode pedir MFA no terminal)
    try:
        session_dump = do_login(garmin_email, garmin_password)
    except Exception as e:
        print(f"\nERRO no login Garmin: {e}")
        sys.exit(1)

    # Salva no banco
    success = asyncio.run(save_tokens(user_email, garmin_email, session_dump))
    if not success:
        sys.exit(1)

    print("\nPronto! Acesse o dashboard para ver seus dados.")
    print("(O sync iniciara automaticamente em breve)\n")


if __name__ == "__main__":
    main()

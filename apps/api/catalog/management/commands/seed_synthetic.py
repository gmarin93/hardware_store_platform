"""``manage.py seed_synthetic [--data-dir DIR] [--with-demo-users]``

Loads the synthetic P1 catalog. Local/test only: refuses unless ``DEBUG`` is on
(local Compose with ``.env.example``) or the settings module is
``config.settings.test``, **and** ``ALLOW_SYNTHETIC_SEED=1`` is set, **and** no
non-synthetic organization exists. Idempotent.

Demo users are created only with ``--with-demo-users``. Generated passwords are
printed once, and only when stdout is an interactive terminal (``docker compose
run -it``/a local shell), so they do not end up in captured output such as
``docker compose logs`` or CI logs. With non-interactive stdout the users get an
unusable password and the command prints how to set one with
``manage.py changepassword``. Passwords are never stored in files.
"""

from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from catalog.seed import (
    REFUSED_MESSAGE,
    SeedError,
    default_data_dir,
    load_data,
    seed,
    seed_allowed,
)


class Command(BaseCommand):
    help = "Carga el catálogo SINTÉTICO de demostración (solo entornos locales o de prueba)."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--data-dir",
            type=Path,
            default=None,
            help="Directorio con catalog.json (por defecto <repo>/tests/fixtures/synthetic/p1).",
        )
        parser.add_argument(
            "--with-demo-users",
            action="store_true",
            help="Crea usuarios de demostración (@example.test) con contraseñas generadas.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not seed_allowed():
            raise CommandError(REFUSED_MESSAGE)
        data_dir: Path = options["data_dir"] or default_data_dir()
        try:
            result = seed(
                load_data(data_dir),
                with_demo_users=options["with_demo_users"],
                reveal_passwords=self.stdout.isatty(),
            )
        except SeedError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            "Datos de demostración SINTÉTICOS cargados para: "
            + ", ".join(result.organizations)
            + f" (organización por defecto: {settings.DEFAULT_ORGANIZATION_SLUG})."
        )
        for label, counts in (("creados", result.created), ("actualizados", result.updated)):
            summary = ", ".join(f"{kind}={n}" for kind, n in sorted(counts.items())) or "ninguno"
            self.stdout.write(f"Registros {label}: {summary}")
        revealed = [(email, pw) for email, pw in result.new_users if pw is not None]
        locked = [email for email, pw in result.new_users if pw is None]
        if revealed:
            self.stdout.write(
                "Usuarios de demostración creados. Las contraseñas se muestran UNA sola vez "
                "y no se guardan en ningún archivo:"
            )
            for email, password in revealed:
                self.stdout.write(f"  {email}  {password}")
        if locked:
            self.stdout.write(
                "Usuarios de demostración creados SIN contraseña utilizable (la salida no es "
                "una terminal interactiva). Para definir una contraseña ejecute, por ejemplo:"
            )
            for email in locked:
                self.stdout.write(
                    f"  docker compose run --rm -it api python manage.py changepassword {email}"
                )
        for email in result.existing_users:
            self.stdout.write(f"  {email} ya existía; contraseña sin cambios.")

"""Agentes especializados del flujo de TramIA.

Los requisitos incluidos son datos de demostracion. En produccion deben cargarse desde
fuentes oficiales verificadas y revisadas por la institucion competente.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Procedure:
    name: str
    aliases: tuple[str, ...]
    requirements: tuple[str, ...]
    steps: tuple[str, ...]
    cost: str
    source_url: str


CATALOG: dict[str, Procedure] = {
    "certificado_antecedentes": Procedure(
        name="Certificado de antecedentes penales",
        aliases=("antecedentes", "certificado penal", "record policial"),
        requirements=("Cedula de identidad", "Correo electronico"),
        steps=("Verificar los datos personales.", "Completar la solicitud en el portal oficial.", "Descargar o recibir el certificado."),
        cost="Verificar en la fuente oficial antes de atender.",
        source_url="https://www.ministeriodegobierno.gob.ec/",
    ),
    "renovacion_cedula": Procedure(
        name="Renovacion de cedula de identidad",
        aliases=("renovar cedula", "renovacion cedula", "cedula vencida"),
        requirements=("Cedula de identidad", "Comprobante de pago"),
        steps=(
            "Agendar la atencion segun el canal oficial.",
            "Presentar los documentos requeridos.",
            "Verificar los datos antes de finalizar el tramite.",
        ),
        cost="Verificar el valor vigente en la fuente oficial.",
        source_url="https://www.registrocivil.gob.ec/",
    ),

    "renovacion_pasaporte": Procedure(
        name="Renovacion de pasaporte",
        aliases=("pasaporte", "renovar pasaporte", "pasaporte vencido"),
        requirements=(
            "Cedula de identidad",
            "Comprobante de pago",
            "Pasaporte anterior",
        ),
        steps=(
            "Verificar los requisitos y el valor vigente en la fuente oficial.",
            "Solicitar o confirmar el turno por el canal oficial.",
            "Presentarse con los documentos requeridos.",
            "Revisar los datos antes de finalizar el tramite.",
        ),
        cost="Verificar el valor vigente en la fuente oficial.",
        source_url="https://www.gob.ec/",
    ),

    "registro_nacimiento": Procedure(
        name="Inscripcion de nacimiento",
        aliases=("registro nacimiento", "inscripcion nacimiento", "registrar nacimiento"),
        requirements=("Certificado de nacido vivo", "Cedula de identidad de los progenitores"),
        steps=("Confirmar el lugar y la fecha de inscripcion.", "Reunir documentos originales vigentes.", "Solicitar atencion por el canal oficial."),
        cost="Verificar la gratuidad o tarifa vigente en la fuente oficial.",
        source_url="https://www.registrocivil.gob.ec/",
    ),
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


class ClassificationAgent:
    name = "Agente de clasificacion"

    def classify(self, description: str) -> tuple[str | None, float]:
        text = normalize(description)
        candidates = [
            (key, alias) for key, procedure in CATALOG.items() for alias in procedure.aliases if normalize(alias) in text
        ]
        if not candidates:
            return None, 0.0
        candidates.sort(key=lambda candidate: len(candidate[1]), reverse=True)
        return candidates[0][0], 0.90


class OfficialInformationAgent:
    name = "Agente de informacion oficial"

    def lookup(self, procedure_type: str | None) -> Procedure | None:
        return CATALOG.get(procedure_type or "")


class DocumentValidationAgent:
    name = "Agente de validacion documental"

    def validate(self, procedure: Procedure | None, documents: list[dict[str, object]]) -> list[str]:
        if procedure is None:
            return []
        provided = [normalize(str(document.get("name", ""))) for document in documents if document.get("valid")]
        missing: list[str] = []
        for requirement in procedure.requirements:
            expected_terms = set(normalize(requirement).split())
            if not any(expected_terms.issubset(set(name.split())) for name in provided):
                missing.append(requirement)
        return missing


class GuideAgent:
    name = "Agente de guia personalizada"

    def build(self, procedure: Procedure | None, missing: list[str], confidence: float) -> dict[str, object]:
        if procedure is None:
            return {
                "message": "No fue posible identificar el tramite con seguridad. Un funcionario debe revisarlo.",
                "requirements": [], "steps": [], "missing_documents": [], "source_url": None,
            }
        message = "La solicitud esta lista para continuar." if not missing else "Faltan documentos por completar o validar."
        return {
            "message": message,
            "procedure_name": procedure.name,
            "confidence": confidence,
            "requirements": list(procedure.requirements),
            "steps": list(procedure.steps),
            "cost": procedure.cost,
            "missing_documents": missing,
            "source_url": procedure.source_url,
            "source_note": "Informacion referencial: confirme requisitos, costos y disponibilidad en la fuente oficial.",
        }

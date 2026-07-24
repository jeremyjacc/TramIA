"""Orquestador del sistema multiagente."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .agents import ClassificationAgent, DocumentValidationAgent, GuideAgent, OfficialInformationAgent
from .database import TramDatabase


class TramService:
    def __init__(self, database_path: str | Path) -> None:
        self.database = TramDatabase(database_path)
        self.database.initialize()
        self.classifier = ClassificationAgent()
        self.information = OfficialInformationAgent()
        self.validator = DocumentValidationAgent()
        self.guide_agent = GuideAgent()

    def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        citizen_name = str(payload.get("citizen_name", "")).strip()
        email = str(payload.get("email", "")).strip()
        description = str(payload.get("description", "")).strip()
        documents = payload.get("documents", [])
        if not citizen_name or not email or not description:
            raise ValueError("citizen_name, email y description son obligatorios.")
        if not isinstance(documents, list) or any(not isinstance(item, dict) or not item.get("name") for item in documents):
            raise ValueError("documents debe ser una lista de objetos con el campo name.")

        procedure_type, confidence = self.classifier.classify(description)
        procedure = self.information.lookup(procedure_type)
        missing = self.validator.validate(procedure, documents)
        guide = self.guide_agent.build(procedure, missing, confidence)
        needs_human_review = procedure is None or confidence < 0.75
        status = "DERIVADO_A_FUNCIONARIO" if needs_human_review else ("PENDIENTE_DOCUMENTOS" if missing else "ORIENTADO")
        record = {
            "code": f"TRAM-{uuid.uuid4().hex[:8].upper()}",
            "citizen_name": citizen_name,
            "email": email,
            "description": description,
            "procedure_type": procedure_type,
            "status": status,
            "human_review": int(needs_human_review),
            "guide_json": json.dumps(guide, ensure_ascii=False),
        }
        request_id = self.database.create_request(record, documents)
        self.database.add_audit(request_id, self.classifier.name, "clasificar", f"Tipo: {procedure_type or 'no identificado'}; confianza: {confidence:.2f}")
        self.database.add_audit(request_id, self.information.name, "consultar", "Catalogo de requisitos consultado." if procedure else "No hay coincidencia en el catalogo.")
        self.database.add_audit(request_id, self.validator.name, "validar", f"Documentos pendientes: {len(missing)}")
        self.database.add_audit(request_id, self.guide_agent.name, "generar_guia", guide["message"])
        if needs_human_review:
            self.database.add_audit(request_id, "Orquestador", "derivar", "Derivada automaticamente para supervision humana.")
        return self.database.get_request(request_id) or {}

    def escalate(self, request_id: int, reason: str) -> dict[str, Any] | None:
        request = self.database.get_request(request_id)
        if request is None:
            return None
        self.database.update_status(request_id, "DERIVADO_A_FUNCIONARIO", human_review=True)
        self.database.add_audit(request_id, "Orquestador", "derivar", reason or "Derivacion solicitada por un operador.")
        return self.database.get_request(request_id)
